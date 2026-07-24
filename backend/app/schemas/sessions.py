from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.interview import InterviewConfig, InterviewPlanDraft
from app.schemas.interview import AnswerEvaluation


class InterviewPlanCreate(BaseModel):
    resume_id: UUID
    job_id: UUID
    config: InterviewConfig = Field(default_factory=InterviewConfig)


class InterviewPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    resume_id: UUID
    job_id: UUID
    config: InterviewConfig
    plan: InterviewPlanDraft
    status: str
    created_at: datetime


class InterviewSessionCreate(BaseModel):
    plan_id: UUID


class InterviewQuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_text: str
    question_type: str
    difficulty: str
    skill_tags: list[str]
    order_index: int


class InterviewSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plan_id: UUID
    status: str
    current_question_index: int
    follow_up_count: int
    started_at: datetime | None
    paused_at: datetime | None
    completed_at: datetime | None


class AnswerCreate(BaseModel):
    answer_text: str = Field(min_length=1, max_length=20_000)
    idempotency_key: str = Field(min_length=8, max_length=128)
    duration_seconds: int | None = Field(default=None, ge=0, le=14_400)
    hint_used: bool = False


class AnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_id: UUID
    answer_text: str
    duration_seconds: int | None
    hint_used: bool
    submitted_at: datetime


class EvaluationRead(AnswerEvaluation):
    answer_id: UUID
    rubric: dict[str, float] | None = None
    generation_config: dict[str, object] | None = None
    created_at: datetime
