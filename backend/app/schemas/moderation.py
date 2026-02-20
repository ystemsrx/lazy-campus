from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReportStatus, ReportType


class ReportCreate(BaseModel):
    type: ReportType
    task_id: int | None = None
    reported_user_id: int | None = None
    reason: str = Field(min_length=5)
    evidence: str = Field(min_length=5)


class ReportReview(BaseModel):
    status: ReportStatus
    admin_notes: str | None = None


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: ReportType
    task_id: int | None
    reporter_id: int
    reported_user_id: int | None
    reason: str
    evidence: str
    status: ReportStatus
    admin_id: int | None
    admin_notes: str | None
    created_at: datetime


class BlacklistCreate(BaseModel):
    blocked_user_id: int
    reason: str | None = None


class BanUserRequest(BaseModel):
    banned: bool
    reason: str | None = None
    innocent: bool = False


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
    created_at: datetime


class AdminUserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AdminUserItem]
