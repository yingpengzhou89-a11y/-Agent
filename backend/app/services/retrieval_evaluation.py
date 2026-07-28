"""Offline, reproducible evaluation for the personal knowledge retriever."""

from __future__ import annotations

import math
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.knowledge import KnowledgeSearchResult
from app.services.knowledge import KnowledgeService


class RetrievalBenchmarkCase(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    query: str = Field(min_length=1, max_length=2000)
    expected_chunk_ids: list[UUID] = []
    expected_source_names: list[str] = []

    @model_validator(mode="after")
    def requires_expected_citation(self) -> "RetrievalBenchmarkCase":
        if not self.expected_chunk_ids and not self.expected_source_names:
            raise ValueError("每个评测问题至少需要一个期望片段 ID 或文档名")
        return self


class RetrievalBenchmarkDataset(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    cases: list[RetrievalBenchmarkCase] = Field(min_length=1, max_length=200)


class RetrievalMetrics(BaseModel):
    dataset_name: str
    evaluated_case_count: int
    top_k: int
    recall_at_k: float = Field(ge=0, le=1)
    mrr: float = Field(ge=0, le=1)
    ndcg_at_k: float = Field(ge=0, le=1)
    citation_correct_rate: float = Field(ge=0, le=1)
    zero_result_rate: float = Field(ge=0, le=1)
    case_details: list[dict[str, object]]


def _is_relevant(case: RetrievalBenchmarkCase, result: KnowledgeSearchResult) -> bool:
    return (
        result.chunk_id in case.expected_chunk_ids
        or result.source_name.casefold() in {name.casefold() for name in case.expected_source_names}
    )


def calculate_retrieval_metrics(
    dataset: RetrievalBenchmarkDataset,
    rankings: dict[str, list[KnowledgeSearchResult]],
    top_k: int,
) -> RetrievalMetrics:
    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    ndcgs: list[float] = []
    details: list[dict[str, object]] = []
    all_returned = 0
    all_correct = 0
    zero_results = 0

    for case in dataset.cases:
        results = rankings.get(case.id, [])[:top_k]
        matches = [_is_relevant(case, result) for result in results]
        expected_count = len(case.expected_chunk_ids or case.expected_source_names)
        hit_count = sum(matches)
        recalls.append(min(hit_count / expected_count, 1))
        first_rank = next((index for index, matched in enumerate(matches, start=1) if matched), None)
        reciprocal_ranks.append(1 / first_rank if first_rank else 0)
        dcg = sum(1 / math.log2(index + 1) for index, matched in enumerate(matches, start=1) if matched)
        ideal_dcg = sum(1 / math.log2(index + 1) for index in range(1, min(expected_count, top_k) + 1))
        ndcgs.append(dcg / ideal_dcg if ideal_dcg else 0)
        all_returned += len(results)
        all_correct += hit_count
        zero_results += int(not results)
        details.append(
            {
                "id": case.id,
                "query": case.query,
                "returned_chunk_ids": [str(result.chunk_id) for result in results],
                "returned_source_names": [result.source_name for result in results],
                "first_relevant_rank": first_rank,
                "recall_at_k": round(recalls[-1], 4),
            }
        )

    count = len(dataset.cases)
    return RetrievalMetrics(
        dataset_name=dataset.name,
        evaluated_case_count=count,
        top_k=top_k,
        recall_at_k=round(sum(recalls) / count, 4),
        mrr=round(sum(reciprocal_ranks) / count, 4),
        ndcg_at_k=round(sum(ndcgs) / count, 4),
        citation_correct_rate=round(all_correct / all_returned, 4) if all_returned else 0,
        zero_result_rate=round(zero_results / count, 4),
        case_details=details,
    )


class RetrievalBenchmarkService:
    def __init__(self, knowledge: KnowledgeService | None = None) -> None:
        self.knowledge = knowledge or KnowledgeService()

    async def run(
        self,
        session: AsyncSession,
        user_id: UUID,
        dataset: RetrievalBenchmarkDataset,
        top_k: int = 5,
    ) -> RetrievalMetrics:
        rankings = {
            case.id: await self.knowledge.search(
                session, user_id, case.query, ["project_docs", "knowledge_base"], top_k
            )
            for case in dataset.cases
        }
        return calculate_retrieval_metrics(dataset, rankings, top_k)
