from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.utils.user_display import profile_completed

bearer_scheme = HTTPBearer(auto_error=True)
bearer_optional = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    role: str
    user: User | None = None
    admin_account: str | None = None


class ProfileIncompleteException(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=428, detail='Please complete email, gender and nickname first')


def get_current_auth(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token') from exc

    kind = payload.get('kind')
    if kind == 'admin':
        return AuthContext(role=UserRole.ADMIN.value, admin_account=payload.get('account'))

    user_id = payload.get('uid')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token payload')

    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User inactive or not found')
    if user.is_banned:
        if user.ban_until and datetime.now(timezone.utc) >= user.ban_until.replace(tzinfo=timezone.utc):
            user.is_banned = False
            user.ban_reason = None
            user.ban_until = None
            db.add(user)
            db.commit()
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User banned')
    return AuthContext(role=user.role.value, user=user)


def require_user(ctx: AuthContext = Depends(get_current_auth)) -> User:
    if not ctx.user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='User account required')
    return ctx.user


def require_admin(ctx: AuthContext = Depends(get_current_auth)) -> AuthContext:
    if ctx.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Admin required')
    return ctx


def require_completed_user(user: User = Depends(require_user)) -> User:
    if not profile_completed(user):
        raise ProfileIncompleteException()
    return user


def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_optional),
    db: Session = Depends(get_db),
) -> User | None:
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        return None
    user_id = payload.get('uid')
    if not user_id:
        return None
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        return None
    if user.is_banned:
        if user.ban_until and datetime.now(timezone.utc) >= user.ban_until.replace(tzinfo=timezone.utc):
            user.is_banned = False
            user.ban_reason = None
            user.ban_until = None
            db.add(user)
            db.commit()
        else:
            return None
    return user
