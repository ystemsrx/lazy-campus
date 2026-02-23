from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    receiver_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey('tasks.id'), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ChatAttachment(Base):
    __tablename__ = 'chat_attachments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uploader_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    peer_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey('tasks.id'), nullable=True, index=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey('chat_messages.id'), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_url: Mapped[str] = mapped_column(String(1000))
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
