from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ReportStatus, ReportType


class Report(Base):
    __tablename__ = 'reports'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[ReportType] = mapped_column(Enum(ReportType), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey('tasks.id'), nullable=True, index=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    reported_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    images: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.PENDING, index=True)
    admin_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Blacklist(Base):
    __tablename__ = 'blacklists'
    __table_args__ = (UniqueConstraint('user_id', 'blocked_user_id', name='uq_blacklist_pair'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    blocked_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AdminActionLog(Base):
    __tablename__ = 'admin_action_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_identifier: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(100))
    target_type: Mapped[str] = mapped_column(String(50))
    target_id: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
