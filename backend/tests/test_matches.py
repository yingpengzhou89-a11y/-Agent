from uuid import uuid4

from app.schemas.profiles import CandidateProfile, CandidateProject, JobProfile, SourceRef
from app.services.matches import MatchService


def source(quote: str) -> SourceRef:
    return SourceRef(
        document_id=uuid4(),
        chunk_id=uuid4(),
        source_type="resume",
        source_name="resume.md",
        quote=quote,
        score=1,
    )


def test_match_report_separates_skill_gap_from_evidence_gap() -> None:
    candidate = CandidateProfile(
        skills=["FastAPI", "RAG"],
        projects=[
            CandidateProject(
                name="检索服务",
                summary="服务端项目",
                evidence=[source("使用 FastAPI 提供 API")],
            )
        ],
    )
    job = JobProfile(
        must_have_skills=["FastAPI", "RAG", "PostgreSQL"],
        nice_to_have_skills=["LangGraph"],
    )

    report = MatchService._build_report(candidate, job)

    assert report.readiness_index == 49
    assert report.missing_skills == ["PostgreSQL"]
    assert report.evidence_gaps == ["RAG"]
    assert "PostgreSQL" in report.priority_topics
    assert report.matching_rule_version == "matching_rules/v2"
    assert report.weight_config["must_have"] == 0.70
    assert report.skill_coverage[0].evidence_refs[0].source_type == "resume"
    assert report.disclaimer.endswith("不代表真实录取概率。")
