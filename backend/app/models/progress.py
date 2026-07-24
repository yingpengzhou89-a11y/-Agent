from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin, utcnow


class InterviewReport(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "interview_reports"

    session_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("interview_sessions.id", ondelete="CASCADE"), unique=True, index=True
    )
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    weak_topics_json: Mapped[list[str]] = mapped_column(JSON)
    recommended_actions_json: Mapped[list[str]] = mapped_column(JSON)
    model_name: Mapped[str] = mapped_column(String(255), default="deterministic")
    prompt_version: Mapped[str] = mapped_column(String(50), default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SkillMastery(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "skill_mastery"

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skill_name: Mapped[str] = mapped_column(String(255))
    mastery_score: Mapped[float] = mapped_column(Float)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_score: Mapped[float] = mapped_column(Float)
    last_practiced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (UniqueConstraint("user_id", "skill_name", name="uq_skill_mastery_user_skill"),)
