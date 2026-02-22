from datetime import datetime

from pydantic import BaseModel


class ChatMessageOut(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    task_id: int | None
    content: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageSend(BaseModel):
    content: str


class ConversationOut(BaseModel):
    peer_id: int
    peer_name: str
    peer_avatar: str | None
    peer_gender: str | None
    peer_last_active: datetime | None
    task_id: int | None
    task_title: str | None
    task_price: float | None
    task_status: str | None
    task_icon: str | None
    last_message: str | None
    last_message_time: datetime | None
    unread_count: int
    blocked_by_me: bool
    blocked_by_them: bool


class ChatAttachmentOut(BaseModel):
    id: int
    uploader_id: int
    peer_id: int
    task_id: int | None
    message_id: int | None
    file_name: str
    file_url: str
    file_size: int
    mime_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class AttachmentCountOut(BaseModel):
    count: int
    limit: int
