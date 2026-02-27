from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NewcomerRewardRule(Base):
    """Extensible newcomer reward rule.

    `reward_type` discriminates the kind of reward (e.g. 'agent_usage').
    `reward_detail` carries type-specific payload (e.g. number of agent uses as a string).
    New reward types can be added without schema changes.
    """

    __tablename__ = 'newcomer_reward_rules'
    __table_args__ = (
        Index('ix_newcomer_rules_type_status', 'reward_type', 'enabled'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reward_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reward_detail: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NewcomerRewardLog(Base):
    """Log entry each time a newcomer receives a reward."""

    __tablename__ = 'newcomer_reward_logs'
    __table_args__ = (
        Index('ix_newcomer_logs_user_rule', 'user_id', 'rule_id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    rule_id: Mapped[int] = mapped_column(Integer, ForeignKey('newcomer_reward_rules.id'), nullable=False, index=True)
    reward_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reward_detail: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default='success', nullable=False)
    fail_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
