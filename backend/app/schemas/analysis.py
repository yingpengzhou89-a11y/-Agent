from pydantic import BaseModel, Field

from app.schemas.profiles import CandidateProfile, JobProfile


class EvidenceQuote(BaseModel):
    quote: str = Field(min_length=1, max_length=1000)


class ExtractedProject(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=2000)
    evidence: list[EvidenceQuote] = Field(min_length=1, max_length=8)


class ExtractedCandidateProfile(BaseModel):
    education: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[ExtractedProject] = Field(default_factory=list)
    experiences: list[str] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)


class ResumeExtractionOutput(BaseModel):
    candidate_profile: ExtractedCandidateProfile
    resume_issues: list[str] = Field(default_factory=list, max_length=20)


class ResumeAnalysisOutput(BaseModel):
    candidate_profile: CandidateProfile
    resume_issues: list[str] = Field(default_factory=list, max_length=20)


class JobAnalysisOutput(BaseModel):
    job_profile: JobProfile
