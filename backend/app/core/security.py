import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt

from app.core.config import settings

ALGORITHM = 'HS256'
PBKDF2_NAME = 'pbkdf2_sha256'
PBKDF2_ITERATIONS = 390000


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {'sub': subject, 'exp': expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


def get_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), PBKDF2_ITERATIONS)
    digest = base64.urlsafe_b64encode(dk).decode('utf-8')
    return f'{PBKDF2_NAME}${PBKDF2_ITERATIONS}${salt}${digest}'


def verify_password(plain_password: str, stored_hash: str) -> bool:
    parts = stored_hash.split('$')
    if len(parts) != 4 or parts[0] != PBKDF2_NAME:
        return False

    _, iter_str, salt, digest = parts
    try:
        iterations = int(iter_str)
    except ValueError:
        return False

    computed = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt.encode('utf-8'), iterations)
    computed_digest = base64.urlsafe_b64encode(computed).decode('utf-8')
    return hmac.compare_digest(computed_digest, digest)
