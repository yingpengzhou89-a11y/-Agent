from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.models.documents import Resume
from app.schemas.analysis import EvidenceQuote, ExtractedCandidateProfile, ExtractedProject
from app.services.analysis import ResumeAnalysisService


def make_resume(text: str) -> Resume:
    return Resume(
        id=uuid4(),
        user_id=uuid4(),
        name="resume.txt",
        file_type="txt",
        raw_text=text,
    )


def test_resume_analysis_binds_verified_project_evidence() -> None:
    resume = make_resume("项目 A：使用 FastAPI 构建 RAG 服务。")
    extracted = ExtractedCandidateProfile(
        skills=["FastAPI"],
        projects=[
            ExtractedProject(
                name="项目 A",
                summary="RAG 服务",
                evidence=[EvidenceQuote(quote="使用 FastAPI 构建 RAG 服务")],
            )
        ],
    )

    profile = ResumeAnalysisService._bind_and_validate_evidence(extracted, resume)

    assert profile.projects[0].evidence[0].document_id == resume.id
    assert profile.projects[0].evidence[0].source_type == "resume"


def test_resume_analysis_rejects_hallucinated_project_evidence() -> None:
    resume = make_resume("项目 A：使用 FastAPI 构建 RAG 服务。")
    extracted = ExtractedCandidateProfile(
        projects=[
            ExtractedProject(
                name="项目 B",
                summary="不存在的项目",
                evidence=[EvidenceQuote(quote="实现了 Kubernetes 集群")],
            )
        ]
    )

    with pytest.raises(AppError, match="无法在简历中验证"):
        ResumeAnalysisService._bind_and_validate_evidence(extracted, resume)


def test_resume_analysis_fallback_extracts_common_skills_without_a_model() -> None:
    profile = ResumeAnalysisService._fallback_profile("Python、FastAPI、Docker 和 RAG 项目经验")

    assert profile.skills == ["Python", "FastAPI", "Docker", "RAG"]
    assert profile.target_roles == ["AI 应用开发"]


@pytest.mark.asyncio
async def test_resume_analysis_persists_fallback_when_model_fails() -> None:
    resume = make_resume("Python、FastAPI 和 RAG 项目经验")

    class FailingGateway:
        async def complete_structured(self, **kwargs: object) -> object:
            raise AppError("MODEL_UNAVAILABLE", "unavailable", status_code=502)

    class ResumeLookup:
        async def get_for_user(self, *args: object) -> Resume:
            return resume

    class FlushSession:
        async def flush(self) -> None:
            return None

    service = ResumeAnalysisService(FailingGateway())  # type: ignore[arg-type]
    service.resumes = ResumeLookup()  # type: ignore[assignment]
    result = await service.analyze(FlushSession(), resume.user_id, resume.id)  # type: ignore[arg-type]

    assert result.candidate_profile.skills == ["Python", "FastAPI", "RAG"]
    assert resume.parsed_profile_json is not None
