from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ContactVisibility, Gender, RatingTargetRole, TaskStatus


def _to_naive_utc(v: datetime | None) -> datetime | None:
    """将带时区的 datetime 转为 naive UTC，无时区则原样返回。"""
    if v is not None and v.tzinfo is not None:
        v = v.astimezone(timezone.utc).replace(tzinfo=None)
    return v


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    sort_order: int = 0
    ai_agent_enabled: bool = False


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    sort_order: int
    ai_agent_enabled: bool = False
    task_count: int = 0
    worker_count: int = 0


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    deadline: datetime | None = None
    location: str | None = None
    price: float = Field(gt=0)
    category_id: int
    contact_visibility: ContactVisibility = ContactVisibility.AFTER_ACCEPT
    contact_info: str | None = None
    required_gender: Gender | None = None
    icon: str | None = None
    captcha_token: str | None = Field(default=None, min_length=8, max_length=64)

    @field_validator('deadline', mode='after')
    @classmethod
    def normalize_deadline(cls, v: datetime | None) -> datetime | None:
        return _to_naive_utc(v)


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    deadline: datetime | None = None
    location: str | None = None
    price: float | None = Field(default=None, gt=0)
    category_id: int | None = None
    contact_visibility: ContactVisibility | None = None
    contact_info: str | None = None
    required_gender: Gender | None = None
    icon: str | None = None

    @field_validator('deadline', mode='after')
    @classmethod
    def normalize_deadline(cls, v: datetime | None) -> datetime | None:
        return _to_naive_utc(v)


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    deadline: datetime | None
    location: str | None
    price: float
    status: TaskStatus
    is_pinned: bool = False
    is_urgent: bool = False
    admin_note: str | None = None
    category_id: int | None
    publisher_id: int
    assignee_id: int | None
    contact_visibility: ContactVisibility
    contact_info: str | None
    required_gender: Gender | None
    icon: str | None = None
    publisher_display_name: str
    assignee_display_name: str | None
    publisher_rating_avg: float = 0
    publisher_rating_count: int = 0
    publisher_completed_count: int = 0
    publisher_blocked_by_count: int = 0
    publisher_task_count: int = 0
    publisher_payment_qr_url: str | None = None
    created_at: datetime
    updated_at: datetime


class TaskListQuery(BaseModel):
    keyword: str | None = None
    category_id: int | None = None
    min_price: float | None = None
    max_price: float | None = None
    status: TaskStatus | None = None


class TaskMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class TaskMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    sender_id: int
    sender_display_name: str
    content: str
    created_at: datetime


class TaskReviewCreate(BaseModel):
    stars: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)
    target_role: RatingTargetRole


class TaskReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    reviewer_id: int
    reviewee_id: int
    target_role: RatingTargetRole
    stars: int
    comment: str | None
    created_at: datetime


class TaskAttachmentCreate(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_url: str = Field(min_length=1, max_length=1000)


class TaskAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    uploader_id: int
    file_name: str
    file_url: str
    created_at: datetime
