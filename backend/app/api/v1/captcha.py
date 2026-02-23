from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_completed_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.captcha import (
    AnonCaptchaChallengeCreate,
    AnonCaptchaChallengeOut,
    AnonCaptchaVerifyOut,
    AnonCaptchaVerifyRequest,
    CaptchaChallengeCreate,
    CaptchaChallengeOut,
    CaptchaVerifyOut,
    CaptchaVerifyRequest,
)
from app.services.captcha_service import (
    create_anon_challenge,
    create_challenge,
    verify_anon_challenge,
    verify_challenge,
)

router = APIRouter(prefix='/captcha', tags=['captcha'])


@router.post('/challenges', response_model=CaptchaChallengeOut)
def create_captcha_challenge(
    payload: CaptchaChallengeCreate,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> CaptchaChallengeOut:
    return create_challenge(db=db, user_id=user.id, scene=payload.scene)


@router.post('/challenges/verify', response_model=CaptchaVerifyOut)
def verify_captcha_challenge(
    payload: CaptchaVerifyRequest,
    user: User = Depends(require_completed_user),
    db: Session = Depends(get_db),
) -> CaptchaVerifyOut:
    challenge = verify_challenge(
        db=db,
        user_id=user.id,
        challenge_id=payload.challenge_id,
        x=payload.x,
        y=payload.y,
        trajectory=payload.trajectory,
    )
    return CaptchaVerifyOut(scene=challenge.scene, captcha_token=challenge.challenge_id)


# ── 公开匿名端点（注册 / 登录，无需登录）────────────────────────

@router.post('/anon/challenges', response_model=AnonCaptchaChallengeOut)
def create_anon_captcha_challenge(
    payload: AnonCaptchaChallengeCreate,
    db: Session = Depends(get_db),
) -> AnonCaptchaChallengeOut:
    return create_anon_challenge(db=db, session_id=payload.session_id, scene=payload.scene)


@router.post('/anon/challenges/verify', response_model=AnonCaptchaVerifyOut)
def verify_anon_captcha_challenge(
    payload: AnonCaptchaVerifyRequest,
    db: Session = Depends(get_db),
) -> AnonCaptchaVerifyOut:
    challenge = verify_anon_challenge(
        db=db,
        session_id=payload.session_id,
        challenge_id=payload.challenge_id,
        x=payload.x,
        y=payload.y,
        trajectory=payload.trajectory,
    )
    return AnonCaptchaVerifyOut(scene=challenge.scene, captcha_token=challenge.challenge_id)
