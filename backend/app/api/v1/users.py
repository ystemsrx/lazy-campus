import io
import math
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from app.api.deps import optional_user, require_completed_user, require_user
from app.core.config import settings
from app.db.session import get_db
from app.models.enums import RatingTargetRole, TaskStatus
from app.models.moderation import Blacklist
from app.models.task import Task, TaskCategory, TaskReview
from app.models.user import User, WorkerContactView, WorkerProfile, worker_skill_tags
from app.schemas.user import (
    CompleteProfileRequest,
    SkillTagOut,
    UpdateProfileRequest,
    UserMe,
    UserPublic,
    UserReviewOut,
    WorkerContactRevealOut,
    WorkerContactRevealRequest,
    WorkerProfileOut,
    WorkerProfileUpsert,
)
from app.services.captcha_service import require_captcha_or_raise
from app.utils.user_display import display_name

UPLOAD_DIR = Path(__file__).resolve().parents[3] / 'uploads' / 'avatars'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_BAYESIAN_C = 3
_BLOCK_K = 0.5
_BAN_K = 1.5


def _overall_rating_stats(user: User) -> tuple[float, int]:
    total_count = (user.worker_rating_count or 0) + (user.publisher_rating_count or 0)
    if total_count <= 0:
        return 0.0, 0
    weighted = (
        (user.worker_rating_avg or 0) * (user.worker_rating_count or 0)
        + (user.publisher_rating_avg or 0) * (user.publisher_rating_count or 0)
    ) / total_count
    return round(float(weighted), 2), int(total_count)


def _completed_count_map(db: Session, user_ids: set[int]) -> dict[int, int]:
    if not user_ids:
        return {}
    return dict(
        db.query(Task.assignee_id, func.count(Task.id))
        .filter(Task.assignee_id.in_(user_ids), Task.status == TaskStatus.COMPLETED)
        .group_by(Task.assignee_id)
        .all()
    )


def _worker_mu(rows: list[tuple[WorkerProfile, User]]) -> float:
    values = []
    for _, user in rows:
        avg, count = _overall_rating_stats(user)
        if count > 0:
            values.append(avg)
    return float(sum(values) / len(values)) if values else 3.0


def _to_worker_profile_out(profile: WorkerProfile, user: User, completed_count: int, is_self: bool = False) -> WorkerProfileOut:
    overall_avg, overall_count = _overall_rating_stats(user)
    show_contact = profile.show_contact if profile.show_contact is not None else True
    return WorkerProfileOut(
        user_id=user.id,
        enabled=profile.enabled,
        skill_tags=[SkillTagOut(id=t.id, name=t.name) for t in (profile.skill_tags or [])],
        min_price=profile.min_price,
        max_price=profile.max_price,
        bio=profile.bio,
        has_contact=show_contact and bool(profile.phone or profile.wechat),
        phone=profile.phone if is_self else None,
        wechat=profile.wechat if is_self else None,
        show_contact=show_contact,
        display_name=display_name(user),
        avatar_url=user.avatar_url,
        gender=user.gender,
        worker_rating_avg=user.worker_rating_avg,
        worker_rating_count=user.worker_rating_count,
        overall_rating_avg=overall_avg,
        overall_rating_count=overall_count,
        worker_completed_count=completed_count,
        blocked_by_count=user.blocked_by_count,
    )

router = APIRouter(prefix='/users', tags=['users'])


def to_user_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        account=user.account,
        display_name=display_name(user),
        avatar_url=user.avatar_url,
        gender=user.gender,
        worker_rating_avg=user.worker_rating_avg,
        worker_rating_count=user.worker_rating_count,
        publisher_rating_avg=user.publisher_rating_avg,
        publisher_rating_count=user.publisher_rating_count,
        blocked_by_count=user.blocked_by_count,
    )


@router.get('/me', response_model=UserMe)
def get_me(user: User = Depends(require_user)) -> UserMe:
    return UserMe(
        id=user.id,
        account=user.account,
        name=user.name,
        nickname=user.nickname,
        email=user.email,
        gender=user.gender,
        avatar_url=user.avatar_url,
        is_banned=user.is_banned,
        ban_until=user.ban_until,
        role=user.role.value,
        created_at=user.created_at,
    )


@router.post('/me/complete-profile', response_model=UserMe)
def complete_profile(
    payload: CompleteProfileRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> UserMe:
    user.email = payload.email
    user.gender = payload.gender
    user.nickname = payload.nickname
    db.add(user)
    db.commit()
    db.refresh(user)
    return get_me(user)


@router.put('/me/profile', response_model=UserMe)
def update_profile(
    payload: UpdateProfileRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> UserMe:
    user.email = payload.email
    user.gender = payload.gender
    user.nickname = payload.nickname
    db.add(user)
    db.commit()
    db.refresh(user)
    return get_me(user)


@router.post('/me/avatar', response_model=UserMe)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> UserMe:
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail='仅支持图片文件')

    try:
        from PIL import Image
    except ImportError:
        raise HTTPException(status_code=500, detail='服务器缺少 Pillow 依赖')

    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail='图片大小不能超过 10MB')

    img = Image.open(io.BytesIO(raw))
    img = img.convert('RGBA') if img.mode == 'RGBA' else img.convert('RGB')

    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))

    if img.mode == 'RGBA':
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg

    filename = f'{user.id}_{uuid.uuid4().hex[:8]}.webp'
    filepath = UPLOAD_DIR / filename
    img.save(filepath, format='WEBP', quality=80)

    avatar_url = f'{settings.backend_public_url}/uploads/avatars/{filename}'
    user.avatar_url = avatar_url
    db.add(user)
    db.commit()
    db.refresh(user)
    return get_me(user)


@router.get('/workers', response_model=list[WorkerProfileOut])
def list_workers(
    keyword: str | None = Query(default=None),
    skill_tag_id: int | None = Query(default=None),
    min_price: float | None = Query(default=None),
    max_price: float | None = Query(default=None),
    sort: str = Query(default='ranking', pattern='^(ranking|worker_rating|worker_completed)$'),
    current_user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> list[WorkerProfileOut]:
    query = (
        db.query(WorkerProfile, User)
        .join(User, User.id == WorkerProfile.user_id)
        .filter(and_(WorkerProfile.enabled.is_(True), User.is_banned.is_(False)))
    )
    if skill_tag_id is not None:
        query = query.filter(
            WorkerProfile.id.in_(
                db.query(worker_skill_tags.c.worker_profile_id)
                .filter(worker_skill_tags.c.skill_tag_id == skill_tag_id)
            )
        )
    if keyword:
        like = f'%{keyword}%'
        skill_match = (
            db.query(worker_skill_tags.c.worker_profile_id)
            .join(TaskCategory, TaskCategory.id == worker_skill_tags.c.skill_tag_id)
            .filter(TaskCategory.name.like(like))
        )
        query = query.filter(
            or_(
                User.nickname.like(like),
                User.name.like(like),
                WorkerProfile.bio.like(like),
                WorkerProfile.id.in_(skill_match),
            )
        )
    if min_price is not None:
        query = query.filter(WorkerProfile.max_price.is_(None) | (WorkerProfile.max_price >= min_price))
    if max_price is not None:
        query = query.filter(WorkerProfile.min_price.is_(None) | (WorkerProfile.min_price <= max_price))

    rows = query.all()

    if current_user:
        blocked_ids = set(
            r[0] for r in db.query(Blacklist.blocked_user_id).filter(Blacklist.user_id == current_user.id).all()
        ) | set(
            r[0] for r in db.query(Blacklist.user_id).filter(Blacklist.blocked_user_id == current_user.id).all()
        )
        if blocked_ids:
            rows = [(p, u) for p, u in rows if u.id not in blocked_ids]

    uid_set = {u.id for _, u in rows}
    completed_map = _completed_count_map(db, uid_set)

    if sort == 'worker_rating':
        rows.sort(
            key=lambda r: (
                _overall_rating_stats(r[1])[0],
                _overall_rating_stats(r[1])[1],
                completed_map.get(r[1].id, 0),
            ),
            reverse=True,
        )
    elif sort == 'worker_completed':
        rows.sort(
            key=lambda r: (
                completed_map.get(r[1].id, 0),
                _overall_rating_stats(r[1])[0],
                _overall_rating_stats(r[1])[1],
            ),
            reverse=True,
        )
    else:
        mu = _worker_mu(rows)

        def _worker_score(u: User) -> float:
            rating_avg, rating_count = _overall_rating_stats(u)
            completion_evidence = math.sqrt(completed_map.get(u.id, 0))
            review_evidence = math.sqrt(rating_count)
            evidence = completion_evidence + review_evidence
            base_rating = rating_avg if rating_count > 0 else mu
            bayesian = (_BAYESIAN_C * mu + base_rating * evidence) / (_BAYESIAN_C + evidence) if evidence > 0 else mu
            return bayesian - math.log1p(u.blocked_by_count) * _BLOCK_K - math.log1p(u.ban_count or 0) * _BAN_K

        rows.sort(key=lambda r: _worker_score(r[1]), reverse=True)

    me_id = current_user.id if current_user else None
    return [_to_worker_profile_out(profile, user, completed_map.get(user.id, 0), is_self=user.id == me_id) for profile, user in rows]


@router.put('/me/worker-profile', response_model=WorkerProfileOut)
def upsert_worker_profile(
    payload: WorkerProfileUpsert,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> WorkerProfileOut:
    profile = db.query(WorkerProfile).filter(WorkerProfile.user_id == user.id).first()
    if not profile:
        profile = WorkerProfile(user_id=user.id)

    if payload.min_price is not None and payload.max_price is not None and payload.min_price > payload.max_price:
        raise HTTPException(status_code=422, detail='min_price cannot be greater than max_price')

    if len(payload.skill_tag_ids) > 5:
        raise HTTPException(status_code=422, detail='最多选择 5 个擅长类别')

    profile.enabled = payload.enabled
    profile.min_price = payload.min_price
    profile.max_price = payload.max_price
    profile.bio = payload.bio
    profile.phone = payload.phone.strip() if payload.phone else None
    profile.wechat = payload.wechat.strip() if payload.wechat else None
    profile.show_contact = payload.show_contact

    db.add(profile)
    db.flush()

    if payload.skill_tag_ids:
        tags = db.query(TaskCategory).filter(TaskCategory.id.in_(payload.skill_tag_ids)).all()
        if len(tags) != len(payload.skill_tag_ids):
            raise HTTPException(status_code=422, detail='部分类别不存在')
        profile.skill_tags = tags
    else:
        profile.skill_tags = []

    profile.skills = '、'.join(t.name for t in profile.skill_tags) if profile.skill_tags else None

    db.commit()
    db.refresh(profile)

    completed_count = _completed_count_map(db, {user.id}).get(user.id, 0)
    return _to_worker_profile_out(profile, user, completed_count, is_self=True)


@router.get('/me/worker-profile', response_model=WorkerProfileOut)
def get_my_worker_profile(user: User = Depends(require_user), db: Session = Depends(get_db)) -> WorkerProfileOut:
    profile = db.query(WorkerProfile).filter(WorkerProfile.user_id == user.id).first()
    if not profile:
        profile = WorkerProfile(user_id=user.id, enabled=False)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    completed_count = _completed_count_map(db, {user.id}).get(user.id, 0)
    return _to_worker_profile_out(profile, user, completed_count, is_self=True)


@router.get('/workers/{user_id}', response_model=WorkerProfileOut)
def get_worker_detail(
    user_id: int,
    current_user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> WorkerProfileOut:
    row = (
        db.query(WorkerProfile, User)
        .join(User, User.id == WorkerProfile.user_id)
        .filter(WorkerProfile.user_id == user_id, WorkerProfile.enabled.is_(True), User.is_banned.is_(False))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail='Worker not found')

    profile, user = row
    completed_count = _completed_count_map(db, {user.id}).get(user.id, 0)
    is_self = current_user is not None and current_user.id == user_id
    return _to_worker_profile_out(profile, user, completed_count, is_self=is_self)


@router.post('/workers/{user_id}/contact-view', response_model=WorkerContactRevealOut)
def view_worker_contact(
    user_id: int,
    payload: WorkerContactRevealRequest,
    viewer: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> WorkerContactRevealOut:
    row = (
        db.query(WorkerProfile, User)
        .join(User, User.id == WorkerProfile.user_id)
        .filter(WorkerProfile.user_id == user_id, WorkerProfile.enabled.is_(True), User.is_banned.is_(False))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail='Worker not found')
    if viewer.id == user_id:
        raise HTTPException(status_code=400, detail='不能查看自己的联系方式')

    require_captcha_or_raise(
        db=db,
        user_id=viewer.id,
        scene='view_worker_contact',
        token=payload.captcha_token.strip(),
        message='查看联系方式前请先完成滑块验证',
    )

    profile, _ = row
    show = profile.show_contact if profile.show_contact is not None else True
    record = WorkerContactView(
        worker_user_id=user_id,
        viewer_user_id=viewer.id,
        phone_snapshot=profile.phone if show else None,
        wechat_snapshot=profile.wechat if show else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return WorkerContactRevealOut(
        phone=profile.phone if show else None,
        wechat=profile.wechat if show else None,
        viewed_at=record.created_at,
    )


@router.get('/{user_id}/reviews', response_model=list[UserReviewOut])
def list_user_reviews(
    user_id: int,
    role: str = Query(default='publisher', pattern='^(publisher|worker)$'),
    db: Session = Depends(get_db),
) -> list[UserReviewOut]:
    target_role = RatingTargetRole.PUBLISHER if role == 'publisher' else RatingTargetRole.WORKER
    reviews = (
        db.query(TaskReview)
        .filter(TaskReview.reviewee_id == user_id, TaskReview.target_role == target_role)
        .order_by(desc(TaskReview.created_at))
        .limit(20)
        .all()
    )

    reviewer_ids = {r.reviewer_id for r in reviews}
    reviewers = {u.id: u for u in db.query(User).filter(User.id.in_(reviewer_ids)).all()} if reviewer_ids else {}

    return [
        UserReviewOut(
            id=r.id,
            stars=r.stars,
            comment=r.comment,
            reviewer_display_name=display_name(reviewers[r.reviewer_id]) if r.reviewer_id in reviewers else '未知用户',
            created_at=r.created_at,
        )
        for r in reviews
    ]


@router.get('/{user_id}', response_model=UserPublic)
def get_user_public(user_id: int, db: Session = Depends(get_db)) -> UserPublic:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    return to_user_public(user)
