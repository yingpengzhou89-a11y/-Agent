"""Run a labelled retrieval benchmark against one local user's knowledge base."""

import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID

from app.db.session import SessionLocal
from app.services.retrieval_evaluation import RetrievalBenchmarkDataset, RetrievalBenchmarkService


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate knowledge retrieval with labelled citations.")
    parser.add_argument("--user-id", required=True, type=UUID)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--top-k", default=5, type=int, choices=range(1, 21))
    args = parser.parse_args()
    dataset = RetrievalBenchmarkDataset.model_validate_json(args.dataset.read_text(encoding="utf-8"))
    async with SessionLocal() as session:
        report = await RetrievalBenchmarkService().run(session, args.user_id, dataset, args.top_k)
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
