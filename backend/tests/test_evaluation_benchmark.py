"""Recorded-answer benchmark for the reproducible parts of answer evaluation.

The model's qualitative judgment is intentionally injected in workflow tests. These
fixtures protect the deterministic checks and the server-side score aggregation
from accidental drift when prompts or providers change.
"""

import pytest

from app.schemas.interview import (
    AnswerEvaluation,
    DimensionScores,
    EvaluationAgentInput,
    EvaluationRubric,
    InterviewQuestionDraft,
)
from app.schemas.profiles import CandidateProfile
from app.services.interviews import EvaluationWorkflowService


@pytest.mark.parametrize(
    ("answer", "expected_hits", "minimum_length_met"),
    [
        ("", [], False),
        ("检索后把上下文交给模型生成。", ["检索", "生成"], False),
        (
            "我会先检索并过滤相关文档，再将带来源的上下文交给模型生成回答，"
            "最后通过命中率和人工抽检验证生成质量。",
            ["检索", "生成"],
            True,
        ),
    ],
)
def test_recorded_answers_keep_deterministic_checks_stable(
    answer: str, expected_hits: list[str], minimum_length_met: bool
) -> None:
    payload = EvaluationAgentInput(
        question=InterviewQuestionDraft(
            text="请解释 RAG 的检索与生成流程。",
            type="technical",
            difficulty="medium",
            skill_tags=["RAG"],
            expected_points=["检索", "生成"],
        ),
        user_answer=answer or " ",
        candidate_profile=CandidateProfile(),
    )

    checks = EvaluationWorkflowService._deterministic_checks(payload)

    assert checks.expected_point_hits == expected_hits
    assert checks.minimum_length_met is minimum_length_met
    assert checks.expected_point_coverage == len(expected_hits) / 2


def test_recorded_dimension_scores_have_a_stable_server_side_aggregate() -> None:
    recorded_model_output = AnswerEvaluation(
        overall_score=0,
        dimension_scores=DimensionScores(
            correctness=80,
            completeness=70,
            relevance=90,
            depth=70,
            clarity=80,
            project_grounding=60,
            credibility=80,
        ),
        improved_answer="先说明检索、上下文组装与生成，再补充质量验证。",
        confidence=0.9,
    )

    scores = [recorded_model_output.recompute_score(EvaluationRubric()) for _ in range(3)]

    assert scores == [76, 76, 76]
