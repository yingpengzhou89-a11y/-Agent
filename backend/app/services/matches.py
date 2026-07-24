import re
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.matches import MatchAnalysis
from app.repositories.documents import JobRepository, ResumeRepository
from app.repositories.matches import MatchRepository
from app.schemas.matches import MatchReport, SkillCoverage
from app.schemas.profiles import CandidateProfile, JobProfile


ALIASES = {
    "lang chain": "langchain",
    "lang graph": "langgraph",
    "fast api": "fastapi",
    "postgre sql": "postgresql",
    "large language model": "llm",
    "大语言模型": "llm",
    "检索增强生成": "rag",
}


def normalize_skill(skill: str) -> str:
    normalized = re.sub(r"[^\w+#.]", "", skill.casefold())
    return ALIASES.get(normalized, normalized)


class MatchService:
    MATCHING_RULE_VERSION = "matching_rules/v2"
    WEIGHTS = {"must_have": 0.70, "nice_to_have": 0.20, "project_evidence": 0.10}
    def __init__(self) -> None:
        self.resumes = ResumeRepository()
        self.jobs = JobRepository()
        self.matches = MatchRepository()

    async def create_report(
        self, session: AsyncSession, user_id: UUID, resume_id: UUID, job_id: UUID
    ) -> MatchAnalysis:
        resume = await self.resumes.get_for_user(session, user_id, resume_id)
        job = await self.jobs.get_for_user(session, user_id, job_id)
        if resume.parsed_profile_json is None:
            raise AppError("ANALYSIS_REQUIRED", "请先完成简历结构化分析", status_code=409)
        if job.parsed_requirements_json is None:
            raise AppError("ANALYSIS_REQUIRED", "请先完成 JD 结构化分析", status_code=409)

        candidate = CandidateProfile.model_validate(resume.parsed_profile_json)
        job_profile = JobProfile.model_validate(job.parsed_requirements_json)
        report = self._build_report(candidate, job_profile)
        return await self.matches.create(
            session,
            MatchAnalysis(
                user_id=user_id,
                resume_id=resume_id,
                job_id=job_id,
                report_json=report.model_dump(mode="json"),
            ),
        )

    @staticmethod
    def _build_report(candidate: CandidateProfile, job: JobProfile) -> MatchReport:
        candidate_skills = {normalize_skill(skill) for skill in candidate.skills}

        coverage: list[SkillCoverage] = []
        missing: list[str] = []
        evidence_gaps: list[str] = []
        must_total = len(job.must_have_skills)
        nice_total = len(job.nice_to_have_skills)
        must_covered = 0
        nice_covered = 0
        evidence_covered = 0
        total_requirements = must_total + nice_total

        for requirement, skills in (
            ("must_have", job.must_have_skills),
            ("nice_to_have", job.nice_to_have_skills),
        ):
            for skill in skills:
                normalized = normalize_skill(skill)
                if normalized not in candidate_skills:
                    coverage.append(
                        SkillCoverage(
                            skill=skill,
                            requirement=requirement,
                            status="missing",
                            score=0,
                            reason="候选人画像中没有识别到该技能。",
                        )
                    )
                    if requirement == "must_have":
                        missing.append(skill)
                    continue

                evidence_refs = MatchService._evidence_refs_for_skill(candidate, normalized)
                status = "covered" if evidence_refs else "evidence_insufficient"
                coverage.append(
                    SkillCoverage(
                        skill=skill,
                        requirement=requirement,
                        status=status,
                        score=1,
                        evidence_refs=evidence_refs,
                        reason=(
                            "候选人技能与项目证据均覆盖该要求。"
                            if evidence_refs
                            else "候选人画像包含该技能，但尚未找到可验证的项目证据。"
                        ),
                    )
                )
                if requirement == "must_have":
                    must_covered += 1
                else:
                    nice_covered += 1
                if evidence_refs:
                    evidence_covered += 1
                if status == "evidence_insufficient":
                    evidence_gaps.append(skill)

        must_rate = must_covered / must_total if must_total else 1.0
        nice_rate = nice_covered / nice_total if nice_total else 1.0
        evidence_rate = evidence_covered / total_requirements if total_requirements else 1.0
        readiness = round(
            (
                must_rate * MatchService.WEIGHTS["must_have"]
                + nice_rate * MatchService.WEIGHTS["nice_to_have"]
                + evidence_rate * MatchService.WEIGHTS["project_evidence"]
            )
            * 100
        )
        priorities = [*missing, *evidence_gaps]
        recommendation = [
            "先补齐必备技能缺口",
            "为已具备技能补充可验证的项目证据",
            "最后准备加分技能与表达练习",
        ]
        return MatchReport(
            readiness_index=readiness,
            matching_rule_version=MatchService.MATCHING_RULE_VERSION,
            weight_config=MatchService.WEIGHTS,
            score_breakdown={
                "must_have_score": round(must_rate, 4),
                "nice_to_have_score": round(nice_rate, 4),
                "project_evidence_score": round(evidence_rate, 4),
            },
            skill_coverage=coverage,
            missing_skills=missing,
            evidence_gaps=evidence_gaps,
            priority_topics=priorities,
            recommended_order=recommendation,
        )

    @staticmethod
    def _evidence_refs_for_skill(candidate: CandidateProfile, normalized_skill: str):
        refs = []
        for project in candidate.projects:
            summary_matches = normalized_skill in normalize_skill(project.summary)
            for ref in project.evidence:
                if summary_matches or normalized_skill in normalize_skill(ref.quote):
                    refs.append(ref)
        return refs
