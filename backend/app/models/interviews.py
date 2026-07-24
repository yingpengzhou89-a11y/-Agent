from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InterviewPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interview_plans"

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resume_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    plan_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="READY")


class InterviewSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interview_sessions"

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("interview_plans.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="CREATED", index=True)
    current_question_index: Mapped[int] = mapped_column(Integer, default=0)
    follow_up_count: Mapped[int] = mapped_column(Integer, default=0)
    last_valid_state: Mapped[str | None] = mapped_column(String(30), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InterviewQuestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interview_questions"

    session_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True
    )
    parent_question_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("interview_questions.id", ondelete="SET NULL"), nullable=True
    )
    question_text: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(String(30))
    difficulty: Mapped[str] = mapped_column(String(20))
    skill_tags_json: Mapped[list[str]] = mapped_column(JSON)
    expected_points_json: Mapped[list[str]] = mapped_column(JSON)
    source_refs_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    question_fingerprint: Mapped[str] = mapped_column(String(128), index=True)
    order_index: Mapped[int] = mapped_column(Integer)

    __table_args__ = (UniqueConstraint("session_id", "order_index", name="uq_question_session_order"),)


class InterviewAnswer(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "interview_answers"

    question_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("interview_questions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    answer_text: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hint_used: Mapped[bool] = mapped_column(default=False)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (UniqueConstraint("question_id", "idempotency_key", name="uq_answer_idempotency"),)
