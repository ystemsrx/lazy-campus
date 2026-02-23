import json
from datetime import datetime

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ReportStatus, ReportType


class ReportCreate(BaseModel):
    task_id: int | None = None
    reported_user_id: int
    reason: str = Field(min_length=1)
    evidence: str = ''
    images: list[str] = Field(default_factory=list)


class ReportReview(BaseModel):
    status: ReportStatus
    admin_notes: str | None = None


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: ReportType
    task_id: int | None
    reporter_id: int
    reporter_name: str | None = None
    reporter_nickname: str | None = None
    reporter_account: str | None = None
    reported_user_id: int | None
    reported_user_name: str | None = None
    reported_user_nickname: str | None = None
    reported_user_account: str | None = None
    reported_user_ban_count: int | None = None
    reason: str
    evidence: str
    images: list[str] = Field(default_factory=list)
    status: ReportStatus
    admin_id: int | None
    admin_notes: str | None
    created_at: datetime

    @field_validator('images', mode='before')
    @classmethod
    def _parse_images(cls, v: Any) -> list[str]:
        """DB 中存的是 JSON 字符串，反序列化为列表。"""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, ValueError):
                return []
        return []


class AppealCreate(BaseModel):
    account: str
    password: str
    reason: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    images: list[str] = Field(default_factory=list)


class TaskSnapshotMessage(BaseModel):
    sender_display_name: str
    content: str
    created_at: datetime


class TaskSnapshotReview(BaseModel):
    reviewer_display_name: str
    target_role: str
    stars: int
    comment: str | None
    created_at: datetime


class TaskSnapshotOut(BaseModel):
    id: int
    title: str
    description: str
    deadline: datetime | None
    location: str | None
    price: float
    status: str
    publisher_display_name: str
    assignee_display_name: str | None
    created_at: datetime
    messages: list[TaskSnapshotMessage]
    reviews: list[TaskSnapshotReview]


class DirectChatMessage(BaseModel):
    sender_display_name: str
    content: str
    created_at: datetime


class DirectChatHistoryOut(BaseModel):
    reporter_display_name: str
    reported_user_display_name: str
    messages: list[DirectChatMessage]


class BlacklistCreate(BaseModel):
    blocked_user_id: int
    reason: str | None = None


class BanUserRequest(BaseModel):
    banned: bool
    reason: str | None = None
    innocent: bool = False


class BanContextRequest(BaseModel):
    account: str
    password: str


class BanRecord(BaseModel):
    source: str
    reason: str
    created_at: datetime


class BanContextOut(BaseModel):
    ban_until: datetime | None
    ban_count: int
    records: list[BanRecord]


class RegistrationSettingUpdate(BaseModel):
    registration_enabled: bool


class RegistrationSettingOut(BaseModel):
    registration_enabled: bool


class AdminUserItem(BaseModel):
    id: int
    account: str
    name: str
    nickname: str | None
    display_name: str
    avatar_url: str | None
    role: str
    is_banned: bool
    ban_reason: str | None
    ban_count: int
    ban_until: datetime | None
    created_at: datetime


class AdminUserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AdminUserItem]
