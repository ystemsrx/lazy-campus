from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

LOGIN_CAPTCHA_THRESHOLD = 8


class CaptchaChallenge(Base):
    __tablename__ = 'captcha_challenges'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    challenge_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    scene: Mapped[str] = mapped_column(String(64), index=True)
    expected_x: Mapped[int] = mapped_column(Integer)
    expected_y: Mapped[int] = mapped_column(Integer)
    tolerance: Mapped[int] = mapped_column(Integer, default=8)
    background_name: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class CaptchaTrajectoryLog(Base):
    __tablename__ = 'captcha_trajectory_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    challenge_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    scene: Mapped[str] = mapped_column(String(64), index=True)

    # 当次验证码答案
    expected_x: Mapped[int] = mapped_column(Integer)
    expected_y: Mapped[int] = mapped_column(Integer)
    submitted_x: Mapped[int] = mapped_column(Integer)
    submitted_y: Mapped[int] = mapped_column(Integer)

    # 验证结果
    passed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    fail_reason: Mapped[str] = mapped_column(String(255), default='')

    # 行为特征指标
    duration_ms: Mapped[float] = mapped_column(Float)
    point_count: Mapped[int] = mapped_column(Integer)
    avg_speed: Mapped[float] = mapped_column(Float)
    max_speed: Mapped[float] = mapped_column(Float)
    speed_cv: Mapped[float] = mapped_column(Float)
    pause_count: Mapped[int] = mapped_column(Integer)
    direction_changes: Mapped[int] = mapped_column(Integer)
    total_distance: Mapped[float] = mapped_column(Float)
    displacement: Mapped[float] = mapped_column(Float)

    # 原始轨迹坐标 [{x, t}, ...]
    path_coords: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class CaptchaGate(Base):
    __tablename__ = 'captcha_gates'
    __table_args__ = (UniqueConstraint('user_id', 'scene', name='uq_captcha_gate_user_scene'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    scene: Mapped[str] = mapped_column(String(64), index=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnonCaptchaChallenge(Base):
    """未登录场景（注册、登录）使用的验证码挑战，以 session_id 代替 user_id。"""
    __tablename__ = 'anon_captcha_challenges'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    challenge_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    scene: Mapped[str] = mapped_column(String(64), index=True)
    expected_x: Mapped[int] = mapped_column(Integer)
    expected_y: Mapped[int] = mapped_column(Integer)
    tolerance: Mapped[int] = mapped_column(Integer, default=8)
    background_name: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class LoginAttemptCounter(Base):
    """按账号跟踪连续登录失败次数，超过阈值后要求验证码。"""
    __tablename__ = 'login_attempt_counters'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    captcha_required: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    last_fail_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
