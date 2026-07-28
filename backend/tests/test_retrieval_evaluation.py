from uuid import uuid4

import pytest

from app.schemas.knowledge import KnowledgeSearchResult
from app.services.retrieval_evaluation import (
    RetrievalBenchmarkCase,
    RetrievalBenchmarkDataset,
    calculate_retrieval_metrics,
)


def _result(name: str) -> KnowledgeSearchResult:
    return KnowledgeSearchResult(
        document_id=uuid4(),
        chunk_id=uuid4(),
        content="资料片段",
        source_type="project_docs",
        source_name=name,
        score=0.02,
    )


def test_retrieval_benchmark_calculates_ranking_and_citation_metrics() -> None:
    dataset = RetrievalBenchmarkDataset(
        name="test-set",
        cases=[
            RetrievalBenchmarkCase(
                id="architecture",
                query="系统架构",
                expected_source_names=["architecture.md", "api.md"],
            ),
            RetrievalBenchmarkCase(
                id="missing",
                query="不存在",
                expected_source_names=["missing.md"],
            ),
        ],
    )
    report = calculate_retrieval_metrics(
        dataset,
        {"architecture": [_result("wrong.md"), _result("architecture.md")], "missing": []},
        top_k=2,
    )

    assert report.recall_at_k == pytest.approx(0.25)
    assert report.mrr == pytest.approx(0.25)
    assert report.ndcg_at_k == pytest.approx(0.1934)
    assert report.citation_correct_rate == pytest.approx(0.5)
    assert report.zero_result_rate == pytest.approx(0.5)
    assert report.case_details[0]["first_relevant_rank"] == 2
