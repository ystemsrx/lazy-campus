from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    description: str | None = None
    related_task_id: int | None = None
    related_report_id: int | None = None
    related_user_id: int | None = None
    dismiss_type: str
    is_read: bool
    created_at: datetime
