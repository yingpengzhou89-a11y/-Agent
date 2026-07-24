from types import SimpleNamespace

from app.services.progress import ReportService


def test_report_summary_identifies_weak_topics_and_actions() -> None:
    items = [
        (
            SimpleNamespace(skill_tags_json=["RAG"]),
            SimpleNamespace(),
            SimpleNamespace(overall_score=50, dimension_scores_json={"correctness": 50, "clarity": 80}),
        ),
        (
            SimpleNamespace(skill_tags_json=["FastAPI"]),
            SimpleNamespace(),
            SimpleNamespace(overall_score=80, dimension_scores_json={"correctness": 80, "clarity": 70}),
        ),
    ]

    summary, weak_topics, actions, skill_scores = ReportService._summarize(items)

    assert summary["overall_score"] == 65
    assert weak_topics == ["RAG", "FastAPI"]
    assert actions[0] == "优先复习：RAG"
    assert skill_scores["FastAPI"] == [80]
