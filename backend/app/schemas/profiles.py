from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    document_id: UUID
    chunk_id: UUID
    source_type: Literal["resume", "job", "project_docs", "knowledge_base"]
    source_name: str = Field(min_length=1, max_length=255)
    quote: str = Field(min_length=1, max_length=2000)
    score: float = Field(ge=0, le=1)


class CandidateProject(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=2000)
    evidence: list[SourceRef] = Field(min_length=1)


class CandidateProfile(BaseModel):
    education: list[str] = []
    skills: list[str] = []
    projects: list[CandidateProject] = []
    experiences: list[str] = []
    certificates: list[str] = []
    target_roles: list[str] = []


class JobProfile(BaseModel):
    job_title: str | None = None
    responsibilities: list[str] = []
    must_have_skills: list[str] = []
    nice_to_have_skills: list[str] = []
    soft_skills: list[str] = []
    seniority: Literal["intern", "junior", "mid", "senior", "unknown"] = "unknown"
    interview_focus: list[str] = []

