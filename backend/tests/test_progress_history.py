from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.progress import ProgressService


def test_history_calculates_recent_average_and_score_change() -> None:
    rows = [
        (
            SimpleNamespace(
                summary_json={"overall_score": 82, "evaluated_question_count": 6},
                weak_topics_json=["系统设计"],
                created_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            ),
            SimpleNamespace(id=uuid4(), completed_at=datetime(2026, 7, 29, tzinfo=timezone.utc)),
        ),
        (
            SimpleNamespace(
                summary_json={"overall_score": 70, "evaluated_question_count": 5},
                weak_topics_json=["RAG"],
                created_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
            ),
            SimpleNamespace(id=uuid4(), completed_at=datetime(2026, 7, 28, tzinfo=timezone.utc)),
        ),
    ]

    history = ProgressService._build_history(rows)

    assert history.score_change == 12
    assert history.recent_average_score == 76
    assert history.history[0].weak_topics == ["系统设计"]
