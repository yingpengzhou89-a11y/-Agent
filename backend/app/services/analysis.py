import re
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentContext
from app.core.config import settings
from app.core.errors import AppError
from app.models.documents import Resume
from app.repositories.documents import JobRepository, ResumeRepository
from pydantic import BaseModel

from app.schemas.analysis import (
    ExtractedCandidateProfile,
    JobAnalysisOutput,
    ResumeAnalysisOutput,
    ResumeExtractionOutput,
)
from app.schemas.profiles import CandidateProfile, CandidateProject, SourceRef
from app.services.model_gateway import StructuredModelGateway


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


class ResumeAnalysisService:
    def __init__(self, gateway: StructuredModelGateway) -> None:
        self.gateway = gateway
        self.resumes = ResumeRepository()

    async def analyze(self, session: AsyncSession, user_id: UUID, resume_id: UUID) -> ResumeAnalysisOutput:
        resume = await self.resumes.get_for_user(session, user_id, resume_id)
        try:
            result = await self.gateway.complete_structured(
                context=AgentContext(
                    request_id=resume.id,
                    user_id=user_id,
                    model_name=settings.chat_model or "unconfigured",
                    prompt_name="resume_extract",
                    prompt_version="v1",
                    token_budget=2500,
                ),
                prompt_key="resume_extract/v1",
                payload=ResumeAnalysisInput(resume_text=resume.raw_text),
                output_model=ResumeExtractionOutput,
            )
            profile = self._bind_and_validate_evidence(result.candidate_profile, resume)
            analysis = ResumeAnalysisOutput(
                candidate_profile=profile,
                resume_issues=result.resume_issues,
            )
        except Exception:
            analysis = ResumeAnalysisOutput(
                candidate_profile=self._fallback_profile(resume.raw_text),
                resume_issues=["模型结构化分析暂不可用，当前使用本地基础解析；请检查模型配置后重新分析。"],
            )
        profile = analysis.candidate_profile
        resume.parsed_profile_json = profile.model_dump(mode="json")
        resume.evidence_map_json = {
            project.name: [ref.model_dump(mode="json") for ref in project.evidence]
            for project in profile.projects
        }
        await session.flush()
        return analysis

    @staticmethod
    def _fallback_profile(text: str) -> CandidateProfile:
        normalized = text.casefold()
        skill_map = {
            "Python": ("python",),
            "FastAPI": ("fastapi",),
            "Django": ("django",),
            "SQL": ("sql", "postgresql", "mysql"),
            "Docker": ("docker",),
            "Git": ("git",),
            "Redis": ("redis",),
            "RAG": ("rag", "检索增强"),
            "LangChain": ("langchain",),
            "LangGraph": ("langgraph",),
            "LLM": ("llm", "大语言模型"),
            "React": ("react",),
        }
        skills = [name for name, terms in skill_map.items() if any(term in normalized for term in terms)]
        target_roles = ["AI 应用开发"] if any(term in normalized for term in ("rag", "llm", "agent", "大语言模型")) else []
        return CandidateProfile(skills=skills, target_roles=target_roles)

    @staticmethod
    def _bind_and_validate_evidence(
        profile: ExtractedCandidateProfile, resume: Resume
    ) -> CandidateProfile:
        source_text = _compact(resume.raw_text)
        projects: list[CandidateProject] = []
        for project in profile.projects:
            refs: list[SourceRef] = []
            for evidence_quote in project.evidence:
                if _compact(evidence_quote.quote) not in source_text:
                    raise AppError(
                        "MODEL_OUTPUT_INVALID",
                        f"项目“{project.name}”包含无法在简历中验证的证据",
                        retryable=True,
                        status_code=502,
                    )
                refs.append(
                    SourceRef(
                        document_id=resume.id,
                        chunk_id=resume.id,
                        source_type="resume",
                        source_name=resume.name,
                        quote=evidence_quote.quote,
                        score=1.0,
                    )
                )
            if not refs:
                raise AppError(
                    "MODEL_OUTPUT_INVALID",
                    f"项目“{project.name}”缺少来源证据",
                    retryable=True,
                    status_code=502,
                )
            projects.append(
                CandidateProject(name=project.name, summary=project.summary, evidence=refs)
            )
        return CandidateProfile(
            education=profile.education,
            skills=profile.skills,
            projects=projects,
            experiences=profile.experiences,
            certificates=profile.certificates,
            target_roles=profile.target_roles,
        )


class JobAnalysisService:
    def __init__(self, gateway: StructuredModelGateway) -> None:
        self.gateway = gateway
        self.jobs = JobRepository()

    async def analyze(self, session: AsyncSession, user_id: UUID, job_id: UUID) -> JobAnalysisOutput:
        job = await self.jobs.get_for_user(session, user_id, job_id)
        result = await self.gateway.complete_structured(
            context=AgentContext(
                request_id=job.id,
                user_id=user_id,
                model_name=settings.chat_model or "unconfigured",
                prompt_name="job_extract",
                prompt_version="v1",
                token_budget=2000,
            ),
            prompt_key="job_extract/v1",
            payload=JobAnalysisInput(job_text=job.raw_text),
            output_model=JobAnalysisOutput,
        )
        job.parsed_requirements_json = result.job_profile.model_dump(mode="json")
        await session.flush()
        return result


class ResumeAnalysisInput(BaseModel):
    resume_text: str


class JobAnalysisInput(BaseModel):
    job_text: str
