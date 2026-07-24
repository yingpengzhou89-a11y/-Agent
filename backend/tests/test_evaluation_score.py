from app.schemas.interview import AnswerEvaluation, DimensionScores, EvaluationRubric


def test_server_side_score_recalculation_ignores_model_total() -> None:
    evaluation = AnswerEvaluation(
        overall_score=1,
        dimension_scores=DimensionScores(
            correctness=80,
            completeness=70,
            relevance=90,
            depth=70,
            clarity=80,
            project_grounding=60,
            credibility=80,
        ),
        improved_answer="改进后的回答。",
        confidence=0.9,
    )

    assert evaluation.recompute_score(EvaluationRubric()) == 76


def test_score_recalculation_excludes_not_applicable_project_grounding() -> None:
    evaluation = AnswerEvaluation(
        overall_score=1,
        dimension_scores=DimensionScores(
            correctness=80,
            completeness=70,
            relevance=90,
            depth=70,
            clarity=80,
            project_grounding=None,
            credibility=80,
        ),
        improved_answer="改进后的回答。",
        confidence=0.9,
    )

    assert evaluation.recompute_score(EvaluationRubric()) == 78
