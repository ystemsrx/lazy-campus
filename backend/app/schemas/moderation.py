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
    ban_types: list[str] = Field(default_factory=list)
    ban_days: int | None = None


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: ReportType
    task_id: int | None
    task_title: str | None = None
    reporter_id: int
    reporter_name: str | None = None
    reporter_nickname: str | None = None
    reporter_account: str | None = None
    reported_user_id: int | None
    reported_user_name: str | None = None
    reported_user_nickname: str | None = None
    reported_user_account: str | None = None
    reported_user_ban_count: int | None = None
    reporter_avatar_url: str | None = None
    reporter_gender: str | None = None
    reported_user_avatar_url: str | None = None
    reported_user_gender: str | None = None
    reason: str
    evidence: str
    images: list[str] = Field(default_factory=list)
    status: ReportStatus
    admin_id: int | None
    admin_notes: str | None
    ban_penalty: str | None = None
    is_admin_ban: bool = False
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


class AuthenticatedAppealCreate(BaseModel):
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
    is_deleted: bool = False
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
    ban_types: list[str] = Field(default_factory=list)
    ban_days: int | None = None


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
    email: str | None = None
    gender: str | None = None
    display_name: str
    avatar_url: str | None
    role: str
    is_active: bool = True
    is_banned: bool
    ban_reason: str | None
    ban_count: int
    ban_until: datetime | None
    ban_publish: bool = False
    ban_accept: bool = False
    ban_contact: bool = False
    blocked_by_count: int = 0
    worker_enabled: bool = False
    worker_skill_count: int = 0
    publisher_rating_avg: float = 0
    publisher_rating_count: int = 0
    worker_rating_avg: float = 0
    worker_rating_count: int = 0
    published_task_count: int = 0
    accepted_task_count: int = 0
    completed_task_count: int = 0
    report_received_count: int = 0
    last_active: datetime | None = None
    created_at: datetime


class AdminUserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AdminUserItem]


class AdminTrendPoint(BaseModel):
    date: str
    new_users: int = 0
    new_tasks: int = 0
    new_reports: int = 0
    new_messages: int = 0


class AdminRiskUser(BaseModel):
    user_id: int
    display_name: str
    ban_count: int = 0
    blocked_by_count: int = 0
    report_received_count: int = 0


class AdminTaskItem(BaseModel):
    id: int
    title: str
    status: str
    price: float
    category_id: int | None
    category_name: str | None
    publisher_id: int
    publisher_display_name: str
    assignee_id: int | None
    assignee_display_name: str | None
    is_pinned: bool = False
    is_urgent: bool = False
    is_deleted: bool = False
    demote_level: int = 0
    deadline: datetime | None
    created_at: datetime
    updated_at: datetime
    report_count: int = 0


class AdminTaskListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AdminTaskItem]


class AdminTaskOperateRequest(BaseModel):
    delete: bool = False
    set_pinned: bool | None = None
    set_urgent: bool | None = None
    set_demote_level: int | None = Field(default=None, ge=0, le=2)


class AdminChatConversationItem(BaseModel):
    user_a_id: int
    user_a_display_name: str
    user_b_id: int
    user_b_display_name: str
    task_id: int | None
    task_title: str | None
    message_count: int
    last_message: str | None
    last_message_time: datetime | None


class AdminChatConversationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AdminChatConversationItem]


class AdminChatMessageOut(BaseModel):
    id: int
    sender_id: int
    sender_display_name: str
    receiver_id: int
    receiver_display_name: str
    task_id: int | None
    content: str
    is_read: bool
    blocked: bool
    created_at: datetime


class AdminTaskChatConversationItem(BaseModel):
    task_id: int
    task_title: str
    publisher_id: int
    publisher_display_name: str
    session_assignee_id: int | None
    session_assignee_display_name: str | None
    message_count: int
    last_message: str | None
    last_message_time: datetime | None


class AdminTaskChatConversationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AdminTaskChatConversationItem]


class AdminTaskChatMessageOut(BaseModel):
    id: int
    task_id: int
    sender_id: int
    sender_display_name: str
    session_assignee_id: int | None
    content: str
    created_at: datetime


class AdminPushNotificationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=2000)
    user_ids: list[int] = Field(default_factory=list)
    include_all: bool = False
    include_banned: bool = False
    include_recent_active: bool = False
    dismiss_type: str = Field(default='read', pattern='^(read|action|source|persistent)$')
    type: str = Field(default='admin_notice', max_length=50)
    related_task_id: int | None = None
    related_report_id: int | None = None
    related_user_id: int | None = None


class AdminPushNotificationOut(BaseModel):
    sent_count: int
    target_user_ids: list[int]


class AdminMiniUser(BaseModel):
    id: int
    account: str
    display_name: str
    avatar_url: str | None = None


class AdminUserTaskBrief(BaseModel):
    id: int
    title: str
    status: str
    price: float
    created_at: datetime
    updated_at: datetime


class AdminUserReportBrief(BaseModel):
    id: int
    type: str
    status: str
    reason: str
    created_at: datetime


class AdminUserRadarMetrics(BaseModel):
    reliability: int = 0
    activity: int = 0
    cooperation: int = 0
    safety: int = 0
    growth: int = 0


class AdminUserProfileOut(BaseModel):
    id: int
    account: str
    name: str
    nickname: str | None
    email: str | None
    gender: str | None
    display_name: str
    avatar_url: str | None
    role: str
    is_active: bool
    is_banned: bool
    ban_reason: str | None
    ban_count: int
    ban_until: datetime | None
    ban_publish: bool = False
    ban_accept: bool = False
    ban_contact: bool = False
    blocked_by_count: int = 0
    last_active: datetime | None = None
    created_at: datetime
    worker_enabled: bool = False
    worker_bio: str | None = None
    worker_min_price: float | None = None
    worker_max_price: float | None = None
    worker_phone: str | None = None
    worker_wechat: str | None = None
    worker_show_contact: bool = True
    worker_skill_ids: list[int] = Field(default_factory=list)
    worker_skill_names: list[str] = Field(default_factory=list)
    blocked_users: list[AdminMiniUser] = Field(default_factory=list)
    published_task_count: int = 0
    accepted_task_count: int = 0
    completed_published_count: int = 0
    completed_accepted_count: int = 0
    report_submitted_count: int = 0
    report_received_count: int = 0
    pending_report_received_count: int = 0
    appeal_count: int = 0
    chat_message_count: int = 0
    publisher_rating_avg: float = 0
    publisher_rating_count: int = 0
    worker_rating_avg: float = 0
    worker_rating_count: int = 0
    radar: AdminUserRadarMetrics
    recent_tasks: list[AdminUserTaskBrief] = Field(default_factory=list)
    recent_reports: list[AdminUserReportBrief] = Field(default_factory=list)


class AdminUserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    nickname: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    gender: str | None = Field(default=None, pattern='^(male|female)$')
    role: str | None = Field(default=None, pattern='^(user|admin)$')
    is_active: bool | None = None
    is_banned: bool | None = None
    ban_publish: bool | None = None
    ban_accept: bool | None = None
    ban_contact: bool | None = None
    ban_reason: str | None = Field(default=None, max_length=2000)
    ban_until: datetime | None = None
    ban_count: int | None = Field(default=None, ge=0, le=9999)
    blocked_by_count: int | None = Field(default=None, ge=0, le=999999)
    worker_enabled: bool | None = None
    worker_bio: str | None = Field(default=None, max_length=2000)
    worker_min_price: float | None = Field(default=None, ge=0)
    worker_max_price: float | None = Field(default=None, ge=0)
    worker_phone: str | None = Field(default=None, max_length=32)
    worker_wechat: str | None = Field(default=None, max_length=64)
    worker_show_contact: bool | None = None
    worker_skill_tag_ids: list[int] | None = None


class AdminBlacklistItem(BaseModel):
    blocked_user_id: int
    blocked_display_name: str
    blocked_account: str
    blocked_avatar_url: str | None
    reason: str | None
    created_at: datetime


class AdminActionLogItem(BaseModel):
    id: int
    admin_identifier: str
    action: str
    target_type: str
    target_id: str
    detail: str | None
    created_at: datetime


class AdminActionLogListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AdminActionLogItem]
