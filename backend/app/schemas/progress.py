from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InterviewReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    summary: dict
    weak_topics: list[str]
    recommended_actions: list[str]
    created_at: datetime


class SkillMasteryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    skill_name: str
    mastery_score: float = Field(ge=0, le=100)
    attempt_count: int
    consecutive_correct_count: int = Field(ge=0)
    consecutive_incorrect_count: int = Field(ge=0)
    last_score: float
    last_practiced_at: datetime
    next_review_at: datetime


class ProgressOverview(BaseModel):
    completed_interviews: int
    evaluated_answers: int
    weakest_topics: list[str]
    next_reviews: list[SkillMasteryRead]
