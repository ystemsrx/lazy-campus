import io
import math
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from app.api.deps import require_completed_user, require_user
from app.core.config import settings
from app.db.session import get_db
from app.models.enums import RatingTargetRole, TaskStatus
from app.models.task import Task, TaskReview
from app.models.user import User, WorkerProfile
from app.schemas.user import CompleteProfileRequest, UpdateProfileRequest, UserMe, UserPublic, UserReviewOut, WorkerProfileOut, WorkerProfileUpsert
from app.utils.user_display import display_name

UPLOAD_DIR = Path(__file__).resolve().parents[3] / 'uploads' / 'avatars'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_BAYESIAN_C = 3
_BLOCK_K = 0.5
_BAN_K = 1.5


def _worker_mu(db: Session) -> float:
    val = db.query(func.avg(User.worker_rating_avg)).filter(User.worker_rating_count > 0).scalar()
    return float(val) if val else 3.0

router = APIRouter(prefix='/users', tags=['users'])


def to_user_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        account=user.account,
        display_name=display_name(user),
        avatar_url=user.avatar_url,
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
    user.nickname = payload.nickname
    user.gender = payload.gender
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
    min_price: float | None = Query(default=None),
    max_price: float | None = Query(default=None),
    sort: str = Query(default='ranking', pattern='^(ranking|worker_rating|worker_completed)$'),
    db: Session = Depends(get_db),
) -> list[WorkerProfileOut]:
    query = (
        db.query(WorkerProfile, User)
        .join(User, User.id == WorkerProfile.user_id)
        .filter(and_(WorkerProfile.enabled.is_(True), User.is_banned.is_(False)))
    )
    if keyword:
        like = f'%{keyword}%'
        query = query.filter(
            or_(
                User.nickname.like(like),
                User.name.like(like),
                WorkerProfile.skills.like(like),
                WorkerProfile.bio.like(like),
            )
        )
    if min_price is not None:
        query = query.filter(WorkerProfile.max_price.is_(None) | (WorkerProfile.max_price >= min_price))
    if max_price is not None:
        query = query.filter(WorkerProfile.min_price.is_(None) | (WorkerProfile.min_price <= max_price))

    if sort == 'worker_rating':
        rows = query.order_by(desc(User.worker_rating_avg), desc(User.worker_rating_count)).all()
    elif sort == 'worker_completed':
        rows = query.all()
        uid_set = {u.id for _, u in rows}
        completed_map: dict[int, int] = {}
        if uid_set:
            completed_map = dict(
                db.query(Task.assignee_id, func.count(Task.id))
                .filter(Task.assignee_id.in_(uid_set), Task.status == TaskStatus.COMPLETED)
                .group_by(Task.assignee_id)
                .all()
            )
        rows.sort(key=lambda r: -completed_map.get(r[1].id, 0))
    else:
        rows = query.all()
        mu = _worker_mu(db)
        uid_set2 = {u.id for _, u in rows}
        cmap2: dict[int, int] = {}
        if uid_set2:
            cmap2 = dict(
                db.query(Task.assignee_id, func.count(Task.id))
                .filter(Task.assignee_id.in_(uid_set2), Task.status == TaskStatus.COMPLETED)
                .group_by(Task.assignee_id)
                .all()
            )

        def _worker_score(u: User) -> float:
            ce = math.sqrt(cmap2.get(u.id, 0))
            ra = u.worker_rating_avg if u.worker_rating_count > 0 else mu
            bayesian = (_BAYESIAN_C * mu + ra * ce) / (_BAYESIAN_C + ce)
            return bayesian - math.log1p(u.blocked_by_count) * _BLOCK_K - math.log1p(u.ban_count or 0) * _BAN_K

        rows.sort(key=lambda r: _worker_score(r[1]), reverse=True)

    out: list[WorkerProfileOut] = []
    for wp, user in rows:
        out.append(
            WorkerProfileOut(
                user_id=user.id,
                enabled=wp.enabled,
                skills=wp.skills,
                min_price=wp.min_price,
                max_price=wp.max_price,
                bio=wp.bio,
                display_name=display_name(user),
                avatar_url=user.avatar_url,
                gender=user.gender,
                worker_rating_avg=user.worker_rating_avg,
                worker_rating_count=user.worker_rating_count,
                blocked_by_count=user.blocked_by_count,
            )
        )
    return out


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

    profile.enabled = payload.enabled
    profile.skills = payload.skills
    profile.min_price = payload.min_price
    profile.max_price = payload.max_price
    profile.bio = payload.bio

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return WorkerProfileOut(
        user_id=user.id,
        enabled=profile.enabled,
        skills=profile.skills,
        min_price=profile.min_price,
        max_price=profile.max_price,
        bio=profile.bio,
        display_name=display_name(user),
        avatar_url=user.avatar_url,
        gender=user.gender,
        worker_rating_avg=user.worker_rating_avg,
        worker_rating_count=user.worker_rating_count,
        blocked_by_count=user.blocked_by_count,
    )


@router.get('/me/worker-profile', response_model=WorkerProfileOut)
def get_my_worker_profile(user: User = Depends(require_user), db: Session = Depends(get_db)) -> WorkerProfileOut:
    profile = db.query(WorkerProfile).filter(WorkerProfile.user_id == user.id).first()
    if not profile:
        profile = WorkerProfile(user_id=user.id, enabled=False)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return WorkerProfileOut(
        user_id=user.id,
        enabled=profile.enabled,
        skills=profile.skills,
        min_price=profile.min_price,
        max_price=profile.max_price,
        bio=profile.bio,
        display_name=display_name(user),
        avatar_url=user.avatar_url,
        gender=user.gender,
        worker_rating_avg=user.worker_rating_avg,
        worker_rating_count=user.worker_rating_count,
        blocked_by_count=user.blocked_by_count,
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
