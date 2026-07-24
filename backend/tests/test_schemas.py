import pytest
from pydantic import ValidationError

from app.schemas.interview import EvaluationRubric, InterviewConfig, InterviewDecision


def test_interview_config_requires_weights_to_sum_to_one() -> None:
    with pytest.raises(ValidationError):
        InterviewConfig(technical_weight=0.4, project_weight=0.4, behavioral_weight=0.4)


def test_question_action_requires_question_payload() -> None:
    with pytest.raises(ValidationError):
        InterviewDecision(action="ask", reason="开始面试")


def test_default_rubric_is_normalized() -> None:
    rubric = EvaluationRubric()
    assert rubric.correctness + rubric.completeness + rubric.relevance + rubric.depth + rubric.clarity + rubric.project_grounding + rubric.credibility == pytest.approx(1)
