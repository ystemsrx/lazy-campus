from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models.system import PlatformSetting
from app.models.user import User
from app.schemas.auth import ThirdPartyRequest, ThirdPartyResponse


@dataclass
class LoginResult:
    user: User | None
    role: str
    display_name: str
    profile_completed: bool
    admin_account: str | None = None


def _store_password_value(password: str) -> tuple[str, bool]:
    if settings.password_encryption:
        return get_password_hash(password), True
    return password, False


def _password_matches(user: User, password: str) -> bool:
    if user.password_hashed:
        try:
            return verify_password(password, user.password_value)
        except Exception:
            return False
    return user.password_value == password


def _check_user_ban(db: Session, user: User) -> None:
    if not user.is_banned:
        return
    if user.ban_until and datetime.now(timezone.utc) >= user.ban_until.replace(tzinfo=timezone.utc):
        user.is_banned = False
        user.ban_reason = None
        user.ban_until = None
        db.add(user)
        db.commit()
        return
    raise HTTPException(
        status_code=403,
        detail={
            'code': 'USER_BANNED',
            'ban_reason': user.ban_reason,
            'ban_until': user.ban_until.isoformat() if user.ban_until else None,
        },
    )


def _migrate_password_if_needed(db: Session, user: User, plain_password: str) -> None:
    if settings.password_encryption and not user.password_hashed:
        user.password_value = get_password_hash(plain_password)
        user.password_hashed = True
        db.add(user)
        db.commit()
        db.refresh(user)


def _get_or_create_platform_setting(db: Session) -> PlatformSetting:
    setting = db.get(PlatformSetting, 1)
    if setting:
        return setting

    setting = PlatformSetting(id=1, registration_enabled=settings.registration_default_enabled)
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def get_registration_enabled(db: Session) -> bool:
    setting = _get_or_create_platform_setting(db)
    return setting.registration_enabled


def set_registration_enabled(db: Session, enabled: bool) -> bool:
    setting = _get_or_create_platform_setting(db)
    setting.registration_enabled = enabled
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting.registration_enabled


def get_agent_enabled(db: Session) -> bool:
    setting = _get_or_create_platform_setting(db)
    return setting.agent_enabled


def set_agent_enabled(db: Session, enabled: bool) -> bool:
    setting = _get_or_create_platform_setting(db)
    setting.agent_enabled = enabled
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting.agent_enabled


def register_local_user(db: Session, account: str, password: str, name: str) -> User:
    normalized_account = account.strip()
    normalized_name = name.strip()
    if not normalized_account:
        raise HTTPException(status_code=422, detail='Account cannot be empty')
    if not normalized_name:
        raise HTTPException(status_code=422, detail='Name cannot be empty')

    if not get_registration_enabled(db):
        raise HTTPException(status_code=403, detail='Registration is disabled')

    if normalized_account == settings.admin_account:
        raise HTTPException(status_code=400, detail='This account name is reserved')

    existing = db.query(User).filter(User.account == normalized_account).first()
    if existing:
        raise HTTPException(status_code=409, detail='Account already exists')

    stored_password, hashed = _store_password_value(password)
    user = User(
        account=normalized_account,
        name=normalized_name,
        password_value=stored_password,
        password_hashed=hashed,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


async def third_party_auth(account: str, password: str) -> ThirdPartyResponse:
    payload = ThirdPartyRequest(account=account, password=password).model_dump()
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(settings.third_party_auth_url, json=payload)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail=f'Third-party auth unavailable: {exc}') from exc

    if resp.status_code >= 500:
        raise HTTPException(status_code=503, detail='Third-party auth service error')

    data = resp.json()
    parsed = ThirdPartyResponse.model_validate(data)
    return parsed


def _create_or_update_user(db: Session, account: str, password: str, third_party_data: dict) -> User:
    user = db.query(User).filter(User.account == account).first()
    stored_password, hashed = _store_password_value(password)

    new_id_number = third_party_data.get('idNumber') or None

    if user:
        user.name = third_party_data['name']
        user.avatar_url = third_party_data.get('avatarUrl')
        if new_id_number and new_id_number != user.id_number:
            user.id_number = new_id_number
        user.password_value = stored_password
        user.password_hashed = hashed
    else:
        user = User(
            account=account,
            name=third_party_data['name'],
            avatar_url=third_party_data.get('avatarUrl'),
            id_number=new_id_number,
            password_value=stored_password,
            password_hashed=hashed,
        )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def verify_credentials(db: Session, account: str, password: str) -> User | None:
    """Verify account+password and return user (without ban check). Returns None if invalid."""
    user = db.query(User).filter(User.account == account).first()
    if user and _password_matches(user, password):
        return user
    return None


async def login_with_fallback(db: Session, account: str, password: str) -> LoginResult:
    if account == settings.admin_account and password == settings.admin_password:
        return LoginResult(
            user=None,
            role='admin',
            display_name='管理员',
            profile_completed=True,
            admin_account=account,
        )

    user = db.query(User).filter(User.account == account).first()

    if user and _password_matches(user, password):
        _migrate_password_if_needed(db, user, password)
        _check_user_ban(db, user)
        return LoginResult(
            user=user,
            role='user',
            display_name=user.nickname or user.name,
            profile_completed=bool(user.email and user.gender),
        )

    third_party_result = await third_party_auth(account, password)
    if not third_party_result.success or not third_party_result.data:
        code = third_party_result.code if third_party_result.code else 401
        msg = third_party_result.msg or 'Authentication failed'
        raise HTTPException(status_code=code, detail=msg)

    synced_user = _create_or_update_user(
        db,
        account=account,
        password=password,
        third_party_data=third_party_result.data.model_dump(),
    )
    _check_user_ban(db, synced_user)
    return LoginResult(
        user=synced_user,
        role='user',
        display_name=synced_user.nickname or synced_user.name,
            profile_completed=bool(synced_user.email and synced_user.gender),
    )
