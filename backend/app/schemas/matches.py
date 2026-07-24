from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.profiles import SourceRef


class MatchCreate(BaseModel):
    resume_id: UUID
    job_id: UUID


class SkillCoverage(BaseModel):
    skill: str
    requirement: Literal["must_have", "nice_to_have"]
    status: Literal["covered", "missing", "evidence_insufficient"]
    score: float = Field(ge=0, le=1)
    evidence_refs: list[SourceRef] = Field(default_factory=list)
    reason: str


class MatchReport(BaseModel):
    readiness_index: int = Field(ge=0, le=100)
    matching_rule_version: str
    weight_config: dict[str, float]
    score_breakdown: dict[str, float]
    skill_coverage: list[SkillCoverage]
    missing_skills: list[str]
    evidence_gaps: list[str]
    priority_topics: list[str]
    recommended_order: list[str]
    disclaimer: str = "该指数仅用于安排面试准备优先级，不代表真实录取概率。"


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    resume_id: UUID
    job_id: UUID
    report: MatchReport
    created_at: datetime
