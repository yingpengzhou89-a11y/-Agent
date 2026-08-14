from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(
        String(320),
        unique=True,
        nullable=True,
    )

    display_name: Mapped[str] = mapped_column(
        String(120),
        default="Local User",
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    preferences_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    resumes = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    jobs = relationship(
        "JobDescription",
        back_populates="user",
        cascade="all, delete-orphan",
    )
