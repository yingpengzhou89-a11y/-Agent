from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.interview import EvaluationRubric, InterviewConfig, InterviewDecision
from app.schemas.sessions import EvaluationRead


def test_interview_config_requires_weights_to_sum_to_one() -> None:
    with pytest.raises(ValidationError):
        InterviewConfig(technical_weight=0.4, project_weight=0.4, behavioral_weight=0.4)


def test_question_action_requires_question_payload() -> None:
    with pytest.raises(ValidationError):
        InterviewDecision(action="ask", reason="开始面试")


def test_default_rubric_is_normalized() -> None:
    rubric = EvaluationRubric()
    assert rubric.correctness + rubric.completeness + rubric.relevance + rubric.depth + rubric.clarity + rubric.project_grounding + rubric.credibility == pytest.approx(1)


def test_evaluation_response_allows_rubric_version_metadata() -> None:
    evaluation = EvaluationRead(
        answer_id=uuid4(),
        overall_score=80,
        dimension_scores={
            "correctness": 80,
            "completeness": 80,
            "relevance": 80,
            "depth": 80,
            "clarity": 80,
            "project_grounding": None,
            "credibility": 80,
        },
        improved_answer="结构化说明方案、验证方式与结果。",
        confidence=0.9,
        rubric={"version": "v1", "correctness": 0.25},
        created_at=datetime.now(timezone.utc),
    )

    assert evaluation.rubric == {"version": "v1", "correctness": 0.25}
