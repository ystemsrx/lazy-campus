from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Gender, UserRole

worker_skill_tags = Table(
    'worker_skill_tags',
    Base.metadata,
    Column('worker_profile_id', Integer, ForeignKey('worker_profiles.id', ondelete='CASCADE'), primary_key=True),
    Column('skill_tag_id', Integer, ForeignKey('task_categories.id', ondelete='CASCADE'), primary_key=True),
)


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    nickname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gender: Mapped[Gender | None] = mapped_column(Enum(Gender), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    id_number: Mapped[str | None] = mapped_column(String(64), nullable=True)

    password_value: Mapped[str] = mapped_column(String(255))
    password_hashed: Mapped[bool] = mapped_column(Boolean, default=True)

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ban_count: Mapped[int] = mapped_column(Integer, default=0)
    ban_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ban_publish: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_accept: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_contact: Mapped[bool] = mapped_column(Boolean, default=False)

    publisher_rating_avg: Mapped[float] = mapped_column(Float, default=0)
    publisher_rating_count: Mapped[int] = mapped_column(Integer, default=0)
    worker_rating_avg: Mapped[float] = mapped_column(Float, default=0)
    worker_rating_count: Mapped[int] = mapped_column(Integer, default=0)
    blocked_by_count: Mapped[int] = mapped_column(Integer, default=0)

    last_active: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    worker_profile = relationship('WorkerProfile', back_populates='user', uselist=False)


class WorkerProfile(Base):
    __tablename__ = 'worker_profiles'
    __table_args__ = (UniqueConstraint('user_id', name='uq_worker_profile_user'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    wechat: Mapped[str | None] = mapped_column(String(64), nullable=True)
    show_contact: Mapped[bool] = mapped_column(Boolean, default=True)

    user = relationship('User', back_populates='worker_profile', primaryjoin='WorkerProfile.user_id == User.id')
    skill_tags = relationship('TaskCategory', secondary=worker_skill_tags, lazy='selectin')


class WorkerContactView(Base):
    __tablename__ = 'worker_contact_views'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    worker_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    viewer_user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    phone_snapshot: Mapped[str | None] = mapped_column(String(32), nullable=True)
    wechat_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
