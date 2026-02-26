from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentSession(Base):
    __tablename__ = 'agent_sessions'
    __table_args__ = (
        Index('ix_agent_sessions_user_status', 'user_id', 'status'),
        Index('ix_agent_sessions_user_updated', 'user_id', 'updated_at'),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('tasks.id'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)

    kimi_session_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default='idle', index=True)
    container_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    max_interactions: Mapped[int] = mapped_column(Integer, default=8)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    last_activity_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentMessage(Base):
    __tablename__ = 'agent_messages'
    __table_args__ = (
        Index('ix_agent_messages_session_id_id', 'session_id', 'id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('agent_sessions.id'), index=True)

    role: Mapped[str] = mapped_column(String(32), index=True)  # user/assistant/tool/tool_call/system
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tool_arguments: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attachments_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
