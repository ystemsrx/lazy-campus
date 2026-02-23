from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CaptchaScene = Literal['view_worker_contact', 'chat_send', 'task_publish', 'task_accept']
AnonCaptchaScene = Literal['register', 'login']


class CaptchaChallengeCreate(BaseModel):
    scene: CaptchaScene


class CaptchaChallengeOut(BaseModel):
    challenge_id: str
    scene: CaptchaScene
    width: int
    height: int
    thumb_y: int
    thumb_width: int
    thumb_height: int
    image: str
    thumb: str
    expires_at: datetime


class TrajectoryPoint(BaseModel):
    x: float
    t: float


class CaptchaVerifyRequest(BaseModel):
    challenge_id: str = Field(min_length=8, max_length=64)
    x: int
    y: int
    trajectory: list[TrajectoryPoint] = Field(min_length=3, max_length=500)


class CaptchaVerifyOut(BaseModel):
    scene: CaptchaScene
    captcha_token: str


# ── 匿名场景（注册 / 登录）──────────────────────────────────────

class AnonCaptchaChallengeCreate(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    scene: AnonCaptchaScene


class AnonCaptchaChallengeOut(BaseModel):
    challenge_id: str
    scene: AnonCaptchaScene
    width: int
    height: int
    thumb_y: int
    thumb_width: int
    thumb_height: int
    image: str
    thumb: str
    expires_at: datetime


class AnonCaptchaVerifyRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    challenge_id: str = Field(min_length=8, max_length=64)
    x: int
    y: int
    trajectory: list[TrajectoryPoint] = Field(min_length=3, max_length=500)


class AnonCaptchaVerifyOut(BaseModel):
    scene: AnonCaptchaScene
    captcha_token: str
