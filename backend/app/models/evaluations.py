from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin, utcnow


class AnswerEvaluation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "answer_evaluations"

    answer_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("interview_answers.id", ondelete="CASCADE"), unique=True, index=True
    )
    overall_score: Mapped[int] = mapped_column(Integer)
    dimension_scores_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    strengths_json: Mapped[list[str]] = mapped_column(JSON)
    errors_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    missing_points_json: Mapped[list[str]] = mapped_column(JSON)
    advice_json: Mapped[list[str]] = mapped_column(JSON)
    answer_framework_json: Mapped[list[str]] = mapped_column(JSON)
    improved_answer: Mapped[str] = mapped_column(Text)
    practice_questions_json: Mapped[list[str]] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float)
    model_name: Mapped[str] = mapped_column(String(255))
    prompt_version: Mapped[str] = mapped_column(String(50))
    rubric_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    generation_config_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    deterministic_checks_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
