from app.schemas.interview import EvaluationAgentInput, InterviewConfig, InterviewPlanningInput, InterviewQuestionDraft
from app.schemas.profiles import CandidateProfile, JobProfile
from app.services.interviews import EvaluationWorkflowService, InterviewPlanService


def test_fallback_plan_is_valid_without_project_evidence() -> None:
    draft = InterviewPlanService._fallback_plan(
        InterviewPlanningInput(
            candidate_profile=CandidateProfile(skills=["Python", "FastAPI"]),
            job_profile=JobProfile(job_title="AI 应用开发工程师", must_have_skills=["Python", "RAG"]),
            interview_config=InterviewConfig(),
        )
    )

    assert len(draft.question_blueprints) == 3
    assert sum(section.question_count for section in draft.sections) == 3
    assert sum(section.weight for section in draft.sections) == 1


def test_fallback_evaluation_is_valid() -> None:
    result = EvaluationWorkflowService._fallback_evaluation(
        EvaluationAgentInput(
            question=InterviewQuestionDraft(
                text="请说明 FastAPI 的依赖注入。",
                type="technical",
                difficulty="medium",
                skill_tags=["FastAPI"],
                expected_points=["概念解释", "使用场景"],
            ),
            user_answer="我会先解释概念，再给出使用场景。",
            candidate_profile=CandidateProfile(),
        )
    )

    assert 0 <= result.overall_score <= 100
    assert result.confidence == 0.35
