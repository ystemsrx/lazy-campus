from sqlalchemy import Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlatformSetting(Base):
    __tablename__ = 'platform_settings'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    registration_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    agent_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
