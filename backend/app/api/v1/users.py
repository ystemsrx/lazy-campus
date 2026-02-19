from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

from app.api.deps import require_completed_user, require_user
from app.db.session import get_db
from app.models.user import User, WorkerProfile
from app.schemas.user import CompleteProfileRequest, UserMe, UserPublic, WorkerProfileOut, WorkerProfileUpsert
from app.utils.user_display import display_name

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


@router.get('/workers', response_model=list[WorkerProfileOut])
def list_workers(
    keyword: str | None = Query(default=None),
    min_price: float | None = Query(default=None),
    max_price: float | None = Query(default=None),
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

    ranking_score = User.worker_rating_avg * (1 + User.worker_rating_count * 0.1) - User.blocked_by_count * 0.2
    rows = query.order_by(desc(ranking_score), desc(User.worker_rating_count)).all()

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
        worker_rating_avg=user.worker_rating_avg,
        worker_rating_count=user.worker_rating_count,
        blocked_by_count=user.blocked_by_count,
    )


@router.get('/{user_id}', response_model=UserPublic)
def get_user_public(user_id: int, db: Session = Depends(get_db)) -> UserPublic:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    return to_user_public(user)
