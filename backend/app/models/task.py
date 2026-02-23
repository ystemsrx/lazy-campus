from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ContactVisibility, Gender, RatingTargetRole, TaskStatus


class TaskCategory(Base):
    __tablename__ = 'task_categories'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Task(Base):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    price: Mapped[float] = mapped_column(Float)

    contact_visibility: Mapped[ContactVisibility] = mapped_column(Enum(ContactVisibility), default=ContactVisibility.AFTER_ACCEPT)
    contact_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    required_gender: Mapped[Gender | None] = mapped_column(Enum(Gender), nullable=True, default=None)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)

    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.OPEN)
    publisher_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey('task_categories.id'), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskAttachment(Base):
    __tablename__ = 'task_attachments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('tasks.id'), index=True)
    uploader_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_url: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TaskMessage(Base):
    __tablename__ = 'task_messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('tasks.id'), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    # 发消息时任务的接单者，用于会话隔离
    session_assignee_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class TaskAbandonLog(Base):
    """记录接单者放弃接取任务的日志，用于24小时滑动窗口限速"""
    __tablename__ = 'task_abandon_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    task_id: Mapped[int] = mapped_column(Integer, index=True)
    abandoned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class TaskAcceptLog(Base):
    """记录接单行为，用于按日统计并触发验证码"""
    __tablename__ = 'task_accept_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    task_id: Mapped[int] = mapped_column(Integer, index=True)
    accepted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class TaskReview(Base):
    __tablename__ = 'task_reviews'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey('tasks.id'), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    reviewee_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    target_role: Mapped[RatingTargetRole] = mapped_column(Enum(RatingTargetRole))
    stars: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
