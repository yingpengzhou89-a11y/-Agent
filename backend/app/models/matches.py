from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MatchAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "match_analyses"

    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resume_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True
    )
    report_json: Mapped[dict[str, Any]] = mapped_column(JSON)

