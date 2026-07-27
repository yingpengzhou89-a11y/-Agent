from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.progress import ProgressService, ReportService


def test_dynamic_review_schedule_shortens_after_errors_and_extends_after_successes() -> None:
    now = datetime(2026, 7, 27, tzinfo=timezone.utc)

    assert ProgressService._next_review(now, 75, 0, 0) == datetime(2026, 7, 30, tzinfo=timezone.utc)
    assert ProgressService._next_review(now, 85, 1, 0) == datetime(2026, 8, 3, tzinfo=timezone.utc)
    assert ProgressService._next_review(now, 85, 2, 0) == datetime(2026, 8, 10, tzinfo=timezone.utc)
    assert ProgressService._next_review(now, 85, 0, 2) == datetime(2026, 7, 28, tzinfo=timezone.utc)


def test_score_streaks_reset_when_a_result_is_neither_correct_nor_incorrect() -> None:
    assert ProgressService._updated_streaks(90, 1, 0) == (2, 0)
    assert ProgressService._updated_streaks(45, 2, 0) == (0, 1)
    assert ProgressService._updated_streaks(70, 2, 1) == (0, 0)


def test_report_recommends_manual_review_for_low_confidence_evaluations() -> None:
    items = [
        (
            SimpleNamespace(skill_tags_json=["RAG"]),
            SimpleNamespace(),
            SimpleNamespace(
                overall_score=60,
                confidence=0.35,
                dimension_scores_json={"correctness": 60},
            ),
        )
    ]

    summary, _, actions, _ = ReportService._summarize(items)

    assert summary["manual_review_recommended"] is True
    assert summary["low_confidence_answer_count"] == 1
    assert "人工复核" in actions[-1]
