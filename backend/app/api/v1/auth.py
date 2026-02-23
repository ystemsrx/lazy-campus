from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_current_auth
from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshResponse,
    RegistrationStatusResponse,
    RegisterRequest,
    RegisterResponse,
    TokenData,
)
from app.services.auth_service import get_registration_enabled, login_with_fallback, register_local_user
from app.services.captcha_service import (
    consume_anon_captcha_token,
    increment_login_fail,
    is_login_captcha_required,
    reset_login_fail,
)

router = APIRouter(prefix='/auth', tags=['auth'])


def _captcha_required_error(scene: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={'code': 'CAPTCHA_REQUIRED', 'scene': scene, 'message': message},
    )


@router.post('/login', response_model=LoginResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    # 管理员账号跳过失败计数
    from app.core.config import settings
    is_admin_attempt = (payload.account == settings.admin_account)

    if not is_admin_attempt and is_login_captcha_required(db, payload.account):
        if not consume_anon_captcha_token(
            db=db,
            session_id=payload.session_id or '',
            scene='login',
            token=payload.captcha_token,
        ):
            raise _captcha_required_error('login', '密码错误次数过多，请先完成滑块验证')

    try:
        result = await login_with_fallback(db, payload.account, payload.password)
    except HTTPException as exc:
        if not is_admin_attempt:
            # 只有"密码正确但账号被封禁"不计入失败次数（密码已匹配成功）；
            # 其余所有失败（本地密码错误、第三方 401/503/其他码）都计入。
            detail = exc.detail
            is_ban = isinstance(detail, dict) and detail.get('code') == 'USER_BANNED'
            if not is_ban:
                increment_login_fail(db, payload.account)
        raise

    # 登录成功：重置失败计数
    if not is_admin_attempt:
        reset_login_fail(db, payload.account)

    if result.role == 'admin':
        token = create_access_token(
            subject=f'admin:{result.admin_account}',
            extra={'kind': 'admin', 'account': result.admin_account, 'role': 'admin'},
        )
        return LoginResponse(
            token=TokenData(access_token=token),
            role='admin',
            profile_completed=True,
            user_id=None,
            display_name='管理员',
        )

    token = create_access_token(
        subject=str(result.user.id),
        extra={'kind': 'user', 'uid': result.user.id, 'role': 'user'},
    )
    return LoginResponse(
        token=TokenData(access_token=token),
        role='user',
        profile_completed=result.profile_completed,
        user_id=result.user.id,
        display_name=result.display_name,
    )


@router.post('/refresh', response_model=RefreshResponse)
def refresh_token(ctx: AuthContext = Depends(get_current_auth)) -> RefreshResponse:
    """用当前有效 token 换取一个新的 30 天 token（滑动窗口续期）"""
    if ctx.role == 'admin':
        new_token = create_access_token(
            subject=f'admin:{ctx.admin_account}',
            extra={'kind': 'admin', 'account': ctx.admin_account, 'role': 'admin'},
        )
    else:
        new_token = create_access_token(
            subject=str(ctx.user.id),
            extra={'kind': 'user', 'uid': ctx.user.id, 'role': 'user'},
        )
    return RefreshResponse(access_token=new_token)


@router.get('/registration-status', response_model=RegistrationStatusResponse)
def registration_status(db: Session = Depends(get_db)) -> RegistrationStatusResponse:
    return RegistrationStatusResponse(registration_enabled=get_registration_enabled(db))


@router.post('/register', response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    if not consume_anon_captcha_token(
        db=db,
        session_id=payload.session_id,
        scene='register',
        token=payload.captcha_token,
    ):
        raise _captcha_required_error('register', '注册前请先完成滑块验证')

    user = register_local_user(
        db=db,
        account=payload.account,
        password=payload.password,
        name=payload.name,
    )
    return RegisterResponse(user_id=user.id, account=user.account)
