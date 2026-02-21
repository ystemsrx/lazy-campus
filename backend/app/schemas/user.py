from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Gender


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account: str
    display_name: str
    avatar_url: str | None
    worker_rating_avg: float
    worker_rating_count: int
    publisher_rating_avg: float
    publisher_rating_count: int
    blocked_by_count: int


class UserMe(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account: str
    name: str
    nickname: str | None
    email: EmailStr | None
    gender: Gender | None
    avatar_url: str | None
    is_banned: bool
    ban_until: datetime | None
    role: str
    created_at: datetime


class CompleteProfileRequest(BaseModel):
    email: EmailStr
    gender: Gender
    nickname: str | None = Field(None, max_length=8)


class SkillTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class WorkerProfileUpsert(BaseModel):
    enabled: bool = False
    skill_tag_ids: list[int] = Field(default_factory=list)
    min_price: float | None = None
    max_price: float | None = None
    bio: str | None = None
    phone: str | None = Field(default=None, max_length=32)
    wechat: str | None = Field(default=None, max_length=64)


class WorkerProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    enabled: bool
    skill_tags: list[SkillTagOut] = []
    min_price: float | None
    max_price: float | None
    bio: str | None
    phone: str | None
    wechat: str | None
    display_name: str
    avatar_url: str | None
    gender: Gender | None
    worker_rating_avg: float
    worker_rating_count: int
    overall_rating_avg: float
    overall_rating_count: int
    worker_completed_count: int
    blocked_by_count: int


class UpdateProfileRequest(BaseModel):
    email: EmailStr
    gender: Gender
    nickname: str | None = Field(None, max_length=8)


class ContactSettingsUpdate(BaseModel):
    allow_contact_after_accept: bool = True


class UserReviewOut(BaseModel):
    id: int
    stars: int
    comment: str | None
    reviewer_display_name: str
    created_at: datetime


class WorkerContactRevealOut(BaseModel):
    phone: str | None
    wechat: str | None
    viewed_at: datetime
