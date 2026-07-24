from uuid import uuid4

from app.services.knowledge import chunk_text, rrf_fuse


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
