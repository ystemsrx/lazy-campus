import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class AgentAvailabilityOut(BaseModel):
    agent_enabled: bool
    remaining_count: int
    max_interactions: int
    max_files: int
    max_file_size_mb: int


class AgentStartOut(BaseModel):
    session_id: str
    task_id: int
    task_title: str
    task_status: str
    status: str
    interaction_count: int
    max_interactions: int
    remaining_count: int
    can_send: bool
    queue_waiting: bool = False
    queue_ahead_users: int = 0
    created_at: datetime
    updated_at: datetime


class AgentAttachmentOut(BaseModel):
    name: str
    stored_name: str
    workspace_path: str
    size: int


class AgentMessageOut(BaseModel):
    id: int
    role: str
    content: str | None = None
    tool_name: str | None = None
    tool_arguments: str | None = None
    tool_call_id: str | None = None
    attachments: list[AgentAttachmentOut] = Field(default_factory=list)
    created_at: datetime

    @field_validator('attachments', mode='before')
    @classmethod
    def _parse_attachments(cls, v: Any) -> list[dict[str, Any]]:
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


class AgentDeliverableOut(BaseModel):
    name: str
    size: int
    updated_at: datetime


class AgentSessionDetailOut(BaseModel):
    session_id: str
    task_id: int
    task_title: str
    task_status: str
    status: str
    interaction_count: int
    max_interactions: int
    remaining_count: int
    can_send: bool
    queue_waiting: bool = False
    queue_ahead_users: int = 0
    created_at: datetime
    updated_at: datetime
    deliverables: list[AgentDeliverableOut] = Field(default_factory=list)


class AgentMySessionItem(BaseModel):
    session_id: str
    task_id: int
    task_title: str
    task_status: str
    status: str
    interaction_count: int
    max_interactions: int
    can_send: bool
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime


class AgentMySessionListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AgentMySessionItem]


class AgentSendOut(BaseModel):
    queued: bool
    queue_ahead_users: int = 0
    interaction_count: int
    max_interactions: int


class AgentDeliverableDeleteBody(BaseModel):
    names: list[str] = Field(min_length=1)


class AgentDeliverableDeleteOut(BaseModel):
    deleted: list[str]


class AgentAdminConfigOut(BaseModel):
    agent_enabled: bool


class AgentAdminConfigUpdate(BaseModel):
    agent_enabled: bool


class AgentBatchGrantRequest(BaseModel):
    user_ids: list[int] = Field(default_factory=list)
    amount: int = Field(ge=0, le=1000000)
    mode: Literal['grant', 'set'] = 'grant'
    include_all: bool = False

    @model_validator(mode='after')
    def _validate_scope_and_amount(self) -> 'AgentBatchGrantRequest':
        if not self.include_all and not self.user_ids:
            raise ValueError('用户列表不能为空')
        if self.mode == 'grant' and self.amount <= 0:
            raise ValueError('发放次数必须大于 0')
        return self


class AgentBatchGrantOut(BaseModel):
    updated_user_count: int


class AgentAdminSessionItem(BaseModel):
    session_id: str
    task_id: int
    task_title: str
    user_id: int
    user_display_name: str
    status: str
    interaction_count: int
    max_interactions: int
    has_container: bool
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime


class AgentAdminSessionListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AgentAdminSessionItem]
