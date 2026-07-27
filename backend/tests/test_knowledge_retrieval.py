from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.knowledge import KnowledgeSearchEvent
from app.models.user import User
from app.services.knowledge import chunk_text, rrf_fuse
from app.services.knowledge import KnowledgeService


def test_chunker_preserves_heading_metadata() -> None:
    chunks = chunk_text("# 架构\n第一段内容\n第二段内容", max_chars=100)

    assert len(chunks) == 1
    assert chunks[0][1]["heading"] == "架构"


def test_rrf_fusion_rewards_results_found_by_multiple_retrievers() -> None:
    shared = uuid4()
    keyword_only = uuid4()
    vector_only = uuid4()

    scores = rrf_fuse([[keyword_only, shared], [vector_only, shared]])

    assert scores[shared] > scores[keyword_only]
    assert scores[shared] > scores[vector_only]


@pytest.mark.asyncio
async def test_retrieval_quality_aggregates_feedback_and_latency(tmp_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'knowledge-quality.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        user = User(display_name="Candidate")
        session.add(user)
        await session.flush()
        first_chunk, second_chunk = uuid4(), uuid4()
        session.add_all(
            [
                KnowledgeSearchEvent(
                    user_id=user.id,
                    query="RAG 评估",
                    scope_json=["project_docs"],
                    top_k=8,
                    result_chunk_ids_json=[str(first_chunk), str(second_chunk)],
                    retrieval_config_json={"lexical_retriever": "postgres_fts"},
                    result_count=2,
                    latency_ms=120,
                ),
                KnowledgeSearchEvent(
                    user_id=user.id,
                    query="不存在的内容",
                    scope_json=["project_docs"],
                    top_k=8,
                    result_chunk_ids_json=[],
                    retrieval_config_json={"lexical_retriever": "keyword_fallback"},
                    result_count=0,
                    latency_ms=80,
                ),
            ]
        )
        await session.flush()
        event = next(
            item
            for item in await KnowledgeService().repo.list_search_events(session, user.id)
            if item.result_count == 2
        )
        await KnowledgeService().record_feedback(session, user.id, event.id, first_chunk, "helpful")
        quality = await KnowledgeService().quality_overview(session, user.id)

        assert quality.search_count == 2
        assert quality.zero_result_rate == pytest.approx(0.5)
        assert quality.average_latency_ms == pytest.approx(100)
        assert quality.feedback_coverage_rate == pytest.approx(0.5)
        assert quality.helpful_rate == 1
    await engine.dispose()
