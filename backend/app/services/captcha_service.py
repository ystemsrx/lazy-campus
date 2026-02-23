import base64
import io
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from random import choice, randint
import secrets

from fastapi import HTTPException
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.captcha import (
    AnonCaptchaChallenge,
    CaptchaChallenge,
    CaptchaGate,
    CaptchaTrajectoryLog,
    LoginAttemptCounter,
    LOGIN_CAPTCHA_THRESHOLD,
)
from app.schemas.captcha import AnonCaptchaChallengeOut, AnonCaptchaScene, CaptchaChallengeOut, CaptchaScene

CAPTCHA_BACKGROUND_DIR = Path(__file__).resolve().parents[1] / 'assets' / 'captcha' / 'backgrounds'
CAPTCHA_WIDTH = 320
CAPTCHA_HEIGHT = 200
CAPTCHA_PIECE_SIZE = 56
CAPTCHA_EXPIRE_SECONDS = 300
CAPTCHA_TOLERANCE = 8

# 拼图块内边距，给光晕留出向外扩散的空间
_PIECE_MARGIN = 5
# 多边形圆角模糊半径（sigma）
_POLY_BLUR = 5
# 多边形圆角阈值
_POLY_THRESHOLD = 128
# 外扩白色光晕模糊半径（保持紧凑）
_GLOW_RADIUS = 3


def _utcnow() -> datetime:
    return datetime.utcnow()


def captcha_required(scene: CaptchaScene, message: str) -> None:
    raise HTTPException(
        status_code=403,
        detail={
            'code': 'CAPTCHA_REQUIRED',
            'scene': scene,
            'message': message,
        },
    )


def _load_random_background() -> tuple[Image.Image, str]:
    files = [
        p for p in CAPTCHA_BACKGROUND_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}
    ] if CAPTCHA_BACKGROUND_DIR.exists() else []
    if not files:
        raise HTTPException(status_code=500, detail='验证码背景图缺失，请联系管理员')

    picked = secrets.choice(files)
    img = Image.open(picked).convert('RGB').resize((CAPTCHA_WIDTH, CAPTCHA_HEIGHT), Image.Resampling.LANCZOS)
    return img, picked.name


def _build_piece_mask(size: int) -> Image.Image:
    """随机从正方形、圆形、三角形、平行四边形中选一个形状，均带圆角。"""
    shape = choice(['square', 'circle', 'triangle', 'parallelogram'])
    m = _PIECE_MARGIN
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    inner = (m, m, size - m - 1, size - m - 1)
    sq_r = max(6, size // 9)

    if shape == 'square':
        draw.rounded_rectangle(inner, radius=sq_r, fill=255)
    elif shape == 'circle':
        draw.ellipse(inner, fill=255)
    elif shape == 'triangle':
        pts = [(size // 2, m), (size - m, size - m), (m, size - m)]
        draw.polygon(pts, fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=_POLY_BLUR))
        mask = mask.point(lambda v: 255 if v > _POLY_THRESHOLD else 0)
    else:  # parallelogram
        skew = (size - 2 * m) // 4
        pts = [
            (m + skew, m), (size - m, m),
            (size - m - skew, size - m), (m, size - m),
        ]
        draw.polygon(pts, fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=_POLY_BLUR))
        mask = mask.point(lambda v: 255 if v > _POLY_THRESHOLD else 0)

    return mask


def _add_piece_glow(piece: Image.Image, mask: Image.Image, size: int) -> Image.Image:
    """紧贴形状的白色细边框 + 微弱外扩白色光晕。"""
    # 1. 白色细边框：用 MinFilter 收缩 mask 1px，差集即为 ~2px 宽的边缘环
    eroded = mask.filter(ImageFilter.MinFilter(3))
    border_ring = ImageChops.subtract(mask, eroded)
    border_layer = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    border_layer.paste((255, 255, 255, 200), mask=border_ring)

    # 2. 外扩白色光晕：小半径模糊 mask，减去原 mask 仅保留向外溢出部分
    blurred = mask.filter(ImageFilter.GaussianBlur(radius=_GLOW_RADIUS))
    outer_glow = ImageChops.subtract(blurred, mask)
    glow_layer = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    glow_layer.paste((255, 255, 255, 150), mask=outer_glow)

    # 合成顺序：glow（底）→ piece → border（顶）
    result = Image.alpha_composite(glow_layer, piece)
    return Image.alpha_composite(result, border_layer)


def _to_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    data = base64.b64encode(buf.getvalue()).decode('ascii')
    return f'data:image/png;base64,{data}'


def _build_slide_images() -> tuple[str, str, int, int, str]:
    image, background_name = _load_random_background()
    x = randint(80, CAPTCHA_WIDTH - CAPTCHA_PIECE_SIZE - 20)
    y = randint(20, CAPTCHA_HEIGHT - CAPTCHA_PIECE_SIZE - 20)

    mask = _build_piece_mask(CAPTCHA_PIECE_SIZE)

    piece = image.crop((x, y, x + CAPTCHA_PIECE_SIZE, y + CAPTCHA_PIECE_SIZE)).convert('RGBA')
    piece.putalpha(mask)
    piece = _add_piece_glow(piece, mask, CAPTCHA_PIECE_SIZE)

    bg = image.convert('RGBA')
    dim = Image.new('RGBA', (CAPTCHA_PIECE_SIZE, CAPTCHA_PIECE_SIZE), (0, 0, 0, 95))
    outline = Image.new('RGBA', (CAPTCHA_PIECE_SIZE, CAPTCHA_PIECE_SIZE), (255, 255, 255, 36))
    bg.paste(dim, (x, y), mask)
    bg.paste(outline, (x, y), mask)

    return _to_data_uri(bg), _to_data_uri(piece), x, y, background_name


def create_challenge(db: Session, user_id: int, scene: CaptchaScene) -> CaptchaChallengeOut:
    now = _utcnow()
    db.execute(delete(CaptchaChallenge).where(CaptchaChallenge.expires_at < now - timedelta(days=1)))

    image, thumb, x, y, background_name = _build_slide_images()
    challenge = CaptchaChallenge(
        challenge_id=uuid.uuid4().hex,
        user_id=user_id,
        scene=scene,
        expected_x=x,
        expected_y=y,
        tolerance=CAPTCHA_TOLERANCE,
        background_name=background_name,
        expires_at=now + timedelta(seconds=CAPTCHA_EXPIRE_SECONDS),
    )
    db.add(challenge)
    db.commit()

    return CaptchaChallengeOut(
        challenge_id=challenge.challenge_id,
        scene=scene,
        width=CAPTCHA_WIDTH,
        height=CAPTCHA_HEIGHT,
        thumb_y=y,
        thumb_width=CAPTCHA_PIECE_SIZE,
        thumb_height=CAPTCHA_PIECE_SIZE,
        image=image,
        thumb=thumb,
        expires_at=challenge.expires_at,
    )


def _compute_trajectory_stats(points: list) -> dict:
    """从原始轨迹点计算行为特征指标。"""
    n = len(points)
    if n < 2:
        return dict(
            duration_ms=0, point_count=n, avg_speed=0, max_speed=0,
            speed_cv=0, pause_count=0, direction_changes=0,
            total_distance=0, displacement=0,
        )

    duration_ms = points[-1].t - points[0].t
    displacement = abs(points[-1].x - points[0].x)

    speeds: list[float] = []
    total_distance = 0.0
    pause_count = 0
    direction_changes = 0

    for i in range(1, n):
        dt = points[i].t - points[i - 1].t
        dx = points[i].x - points[i - 1].x
        total_distance += abs(dx)
        if dt > 150:
            pause_count += 1
        if dt > 0:
            speeds.append(abs(dx) / dt)

    for i in range(2, n):
        d_prev = points[i - 1].x - points[i - 2].x
        d_curr = points[i].x - points[i - 1].x
        if d_prev * d_curr < 0:
            direction_changes += 1

    avg_speed = sum(speeds) / len(speeds) if speeds else 0
    max_speed = max(speeds) if speeds else 0

    if len(speeds) >= 2 and avg_speed > 0:
        variance = sum((s - avg_speed) ** 2 for s in speeds) / len(speeds)
        speed_cv = variance ** 0.5 / avg_speed
    else:
        speed_cv = 0

    return dict(
        duration_ms=round(duration_ms, 1),
        point_count=n,
        avg_speed=round(avg_speed, 4),
        max_speed=round(max_speed, 4),
        speed_cv=round(speed_cv, 4),
        pause_count=pause_count,
        direction_changes=direction_changes,
        total_distance=round(total_distance, 1),
        displacement=round(displacement, 1),
    )


def _validate_trajectory(points: list, expected_x: int, tolerance: int) -> str:
    """
    校验轨迹合法性，返回空字符串表示通过，否则返回失败原因。
    """
    if len(points) < 3:
        return '轨迹数据不足，请重试'

    final_x = points[-1].x
    if abs(final_x - expected_x) > tolerance:
        return '滑块位置不正确，请重试'

    duration_ms = points[-1].t - points[0].t
    if duration_ms < 120:
        return '操作速度异常，请重试'
    if duration_ms > 30000:
        return '操作超时，请重试'

    if abs(points[-1].x - points[0].x) < 10:
        return '滑块位置不正确，请重试'

    speeds: list[float] = []
    for i in range(1, len(points)):
        dt = points[i].t - points[i - 1].t
        if dt > 0:
            speeds.append(abs(points[i].x - points[i - 1].x) / dt)

    if len(speeds) < 2:
        return '轨迹异常，请重试'

    avg_speed = sum(speeds) / len(speeds)
    if avg_speed <= 0:
        return '轨迹异常，请重试'

    if len(speeds) >= 8:
        variance = sum((s - avg_speed) ** 2 for s in speeds) / len(speeds)
        cv = variance ** 0.5 / avg_speed
        if cv < 0.08:
            return '轨迹异常，请重试'

    return ''


def verify_challenge(
    db: Session,
    user_id: int,
    challenge_id: str,
    x: int,
    y: int,
    trajectory: list,
) -> CaptchaChallenge:
    challenge = (
        db.query(CaptchaChallenge)
        .filter(CaptchaChallenge.challenge_id == challenge_id, CaptchaChallenge.user_id == user_id)
        .first()
    )
    if not challenge:
        raise HTTPException(status_code=404, detail='验证码不存在或已失效')

    now = _utcnow()
    if challenge.used_at:
        raise HTTPException(status_code=400, detail='验证码已被使用，请刷新后重试')
    if challenge.expires_at <= now:
        raise HTTPException(status_code=410, detail='验证码已过期，请刷新后重试')

    # 计算行为特征
    stats = _compute_trajectory_stats(trajectory)

    # 验证轨迹
    fail_reason = _validate_trajectory(trajectory, challenge.expected_x, challenge.tolerance)
    if not fail_reason:
        if abs(x - challenge.expected_x) > challenge.tolerance or abs(y - challenge.expected_y) > challenge.tolerance:
            fail_reason = '滑块位置不正确，请重试'

    passed = not fail_reason

    # 无论通过与否，都持久化行为轨迹日志
    log = CaptchaTrajectoryLog(
        challenge_id=challenge.challenge_id,
        user_id=user_id,
        scene=challenge.scene,
        expected_x=challenge.expected_x,
        expected_y=challenge.expected_y,
        submitted_x=x,
        submitted_y=y,
        passed=passed,
        fail_reason=fail_reason,
        path_coords=[{'x': p.x, 't': p.t} for p in trajectory],
        **stats,
    )
    db.add(log)

    if passed:
        challenge.verified_at = now
        db.add(challenge)

    db.commit()

    if not passed:
        raise HTTPException(status_code=422, detail=fail_reason)

    db.refresh(challenge)
    return challenge


def consume_captcha_token(
    db: Session,
    user_id: int,
    scene: CaptchaScene,
    token: str | None,
) -> bool:
    if not token:
        return False

    now = _utcnow()
    challenge = (
        db.query(CaptchaChallenge)
        .filter(
            CaptchaChallenge.challenge_id == token,
            CaptchaChallenge.user_id == user_id,
            CaptchaChallenge.scene == scene,
        )
        .first()
    )
    if not challenge:
        return False
    if challenge.used_at or not challenge.verified_at or challenge.expires_at <= now:
        return False

    challenge.used_at = now
    db.add(challenge)
    db.commit()
    return True


def require_captcha_or_raise(
    db: Session,
    user_id: int,
    scene: CaptchaScene,
    token: str | None,
    message: str,
) -> None:
    if consume_captcha_token(db=db, user_id=user_id, scene=scene, token=token):
        return
    captcha_required(scene=scene, message=message)


def _get_or_create_gate(db: Session, user_id: int, scene: CaptchaScene) -> CaptchaGate:
    gate = db.query(CaptchaGate).filter(CaptchaGate.user_id == user_id, CaptchaGate.scene == scene).first()
    if gate:
        return gate
    gate = CaptchaGate(user_id=user_id, scene=scene, required=False)
    db.add(gate)
    db.commit()
    db.refresh(gate)
    return gate


def is_gate_required(db: Session, user_id: int, scene: CaptchaScene) -> bool:
    gate = db.query(CaptchaGate).filter(CaptchaGate.user_id == user_id, CaptchaGate.scene == scene).first()
    return bool(gate and gate.required)


def set_gate_required(db: Session, user_id: int, scene: CaptchaScene) -> None:
    gate = _get_or_create_gate(db=db, user_id=user_id, scene=scene)
    if gate.required:
        return
    gate.required = True
    db.add(gate)
    db.commit()


def clear_gate_required(db: Session, user_id: int, scene: CaptchaScene) -> None:
    gate = db.query(CaptchaGate).filter(CaptchaGate.user_id == user_id, CaptchaGate.scene == scene).first()
    if not gate or not gate.required:
        return
    gate.required = False
    db.add(gate)
    db.commit()


# ── 匿名验证码（注册 / 登录场景）────────────────────────────────

def create_anon_challenge(db: Session, session_id: str, scene: AnonCaptchaScene) -> AnonCaptchaChallengeOut:
    now = _utcnow()
    db.execute(delete(AnonCaptchaChallenge).where(AnonCaptchaChallenge.expires_at < now - timedelta(days=1)))

    image, thumb, x, y, background_name = _build_slide_images()
    challenge = AnonCaptchaChallenge(
        challenge_id=uuid.uuid4().hex,
        session_id=session_id,
        scene=scene,
        expected_x=x,
        expected_y=y,
        tolerance=CAPTCHA_TOLERANCE,
        background_name=background_name,
        expires_at=now + timedelta(seconds=CAPTCHA_EXPIRE_SECONDS),
    )
    db.add(challenge)
    db.commit()

    return AnonCaptchaChallengeOut(
        challenge_id=challenge.challenge_id,
        scene=scene,
        width=CAPTCHA_WIDTH,
        height=CAPTCHA_HEIGHT,
        thumb_y=y,
        thumb_width=CAPTCHA_PIECE_SIZE,
        thumb_height=CAPTCHA_PIECE_SIZE,
        image=image,
        thumb=thumb,
        expires_at=challenge.expires_at,
    )


def verify_anon_challenge(
    db: Session,
    session_id: str,
    challenge_id: str,
    x: int,
    y: int,
    trajectory: list,
) -> AnonCaptchaChallenge:
    challenge = (
        db.query(AnonCaptchaChallenge)
        .filter(
            AnonCaptchaChallenge.challenge_id == challenge_id,
            AnonCaptchaChallenge.session_id == session_id,
        )
        .first()
    )
    if not challenge:
        raise HTTPException(status_code=404, detail='验证码不存在或已失效')

    now = _utcnow()
    if challenge.used_at:
        raise HTTPException(status_code=400, detail='验证码已被使用，请刷新后重试')
    if challenge.expires_at <= now:
        raise HTTPException(status_code=410, detail='验证码已过期，请刷新后重试')

    fail_reason = _validate_trajectory(trajectory, challenge.expected_x, challenge.tolerance)
    if not fail_reason:
        if abs(x - challenge.expected_x) > challenge.tolerance or abs(y - challenge.expected_y) > challenge.tolerance:
            fail_reason = '滑块位置不正确，请重试'

    if fail_reason:
        raise HTTPException(status_code=422, detail=fail_reason)

    challenge.verified_at = now
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return challenge


def consume_anon_captcha_token(
    db: Session,
    session_id: str,
    scene: AnonCaptchaScene,
    token: str | None,
) -> bool:
    if not token or not session_id:
        return False

    now = _utcnow()
    challenge = (
        db.query(AnonCaptchaChallenge)
        .filter(
            AnonCaptchaChallenge.challenge_id == token,
            AnonCaptchaChallenge.session_id == session_id,
            AnonCaptchaChallenge.scene == scene,
        )
        .first()
    )
    if not challenge:
        return False
    if challenge.used_at or not challenge.verified_at or challenge.expires_at <= now:
        return False

    challenge.used_at = now
    db.add(challenge)
    db.commit()
    return True


# ── 登录失败计数器 ───────────────────────────────────────────────

def _get_or_create_login_counter(db: Session, account: str) -> LoginAttemptCounter:
    counter = db.query(LoginAttemptCounter).filter(LoginAttemptCounter.account == account).first()
    if counter:
        return counter
    counter = LoginAttemptCounter(account=account, fail_count=0, captcha_required=False)
    db.add(counter)
    db.commit()
    db.refresh(counter)
    return counter


def is_login_captcha_required(db: Session, account: str) -> bool:
    counter = db.query(LoginAttemptCounter).filter(LoginAttemptCounter.account == account).first()
    return bool(counter and counter.captcha_required)


def increment_login_fail(db: Session, account: str) -> int:
    counter = _get_or_create_login_counter(db, account)
    counter.fail_count += 1
    counter.last_fail_at = _utcnow()
    if counter.fail_count >= LOGIN_CAPTCHA_THRESHOLD:
        counter.captcha_required = True
    db.add(counter)
    db.commit()
    return counter.fail_count


def reset_login_fail(db: Session, account: str) -> None:
    counter = db.query(LoginAttemptCounter).filter(LoginAttemptCounter.account == account).first()
    if not counter:
        return
    counter.fail_count = 0
    counter.captcha_required = False
    db.add(counter)
    db.commit()
