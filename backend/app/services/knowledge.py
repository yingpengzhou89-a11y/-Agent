import io
import re
from collections import defaultdict
from pathlib import Path
from uuid import UUID, uuid4

import fitz
import httpx
from docx import Document
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.models.knowledge import DocumentChunk, KnowledgeDocument
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import KnowledgeSearchResult


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}


def extract_text(filename: str, raw: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise AppError("FILE_PARSE_ERROR", "仅支持 PDF、DOCX、Markdown 和 TXT 文件", status_code=422)
    if suffix in {".md", ".txt"}:
        return raw.decode("utf-8", errors="replace").strip()
    try:
        if suffix == ".docx":
            document = Document(io.BytesIO(raw))
            return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
        with fitz.open(stream=raw, filetype="pdf") as pdf:
            return "\n".join(page.get_text() for page in pdf).strip()
    except Exception as exc:
        raise AppError("FILE_PARSE_ERROR", "文件无法解析，请确认它没有损坏或加密", status_code=422) from exc


def chunk_text(text: str, max_chars: int = 3000, overlap: int = 400) -> list[tuple[str, dict]]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    chunks: list[tuple[str, dict]] = []
    heading = ""
    buffer = ""
    for line in lines:
        if line.lstrip().startswith("#"):
            heading = line.lstrip("# ").strip()
        candidate = f"{buffer}\n{line}".strip()
        if len(candidate) > max_chars and buffer:
            chunks.append((buffer, {"heading": heading}))
            buffer = f"{buffer[-overlap:]}\n{line}".strip()
        else:
            buffer = candidate
    if buffer:
        chunks.append((buffer, {"heading": heading}))
    return chunks


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+#.]+|[\u4e00-\u9fff]{2,}", text.casefold())


def rrf_fuse(rankings: list[list[UUID]], k: int = 60) -> dict[UUID, float]:
    scores: dict[UUID, float] = defaultdict(float)
    for ranking in rankings:
        for position, identifier in enumerate(ranking, start=1):
            scores[identifier] += 1 / (k + position)
    return dict(scores)


class EmbeddingGateway:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not settings.embedding_base_url or not settings.embedding_api_key:
            raise AppError("EMBEDDING_NOT_CONFIGURED", "未配置 Embedding 服务", status_code=503)
        endpoint = f"{settings.embedding_base_url.rstrip('/')}/embeddings"
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds, trust_env=False) as client:
            response = await client.post(
                endpoint,
                headers={"Authorization": f"Bearer {settings.embedding_api_key}"},
                json={"model": settings.embedding_model, "input": texts},
            )
            try:
                response.raise_for_status()
                vectors = [item["embedding"] for item in response.json()["data"]]
            except (httpx.HTTPError, KeyError, TypeError) as exc:
                raise AppError("RETRIEVAL_ERROR", "Embedding 服务调用失败", retryable=True, status_code=502) from exc
        if any(len(vector) != settings.embedding_dimensions for vector in vectors):
            raise AppError("RETRIEVAL_ERROR", "Embedding 维度与配置不一致", status_code=502)
        return vectors


class KnowledgeService:
    def __init__(self, embeddings: EmbeddingGateway | None = None) -> None:
        self.repo = KnowledgeRepository()
        self.embeddings = embeddings or EmbeddingGateway()

    async def ingest_text(
        self, session: AsyncSession, user_id: UUID, name: str, source_type: str, text: str, file_path: str | None = None
    ) -> KnowledgeDocument:
        if not text.strip():
            raise AppError("FILE_PARSE_ERROR", "文档没有可索引的文本内容", status_code=422)
        document = await self.repo.create_document(
            session,
            KnowledgeDocument(
                user_id=user_id,
                name=name,
                source_type=source_type,
                file_path=file_path,
                parse_status="COMPLETED",
                index_status="PENDING",
            ),
        )
        chunks = [
            DocumentChunk(document_id=document.id, user_id=user_id, content=content, metadata_json=metadata)
            for content, metadata in chunk_text(text)
        ]
        await self.repo.replace_chunks(session, document, chunks)
        document.index_status = "KEYWORD_READY"
        await session.flush()
        return document

    async def ingest_file(
        self, session: AsyncSession, user_id: UUID, source_type: str, filename: str, raw: bytes
    ) -> KnowledgeDocument:
        if len(raw) > settings.max_upload_mb * 1024 * 1024:
            raise AppError("FILE_PARSE_ERROR", "上传文件超过大小限制", status_code=413)
        text = extract_text(filename, raw)
        storage_dir = Path(settings.storage_dir) / str(user_id)
        storage_dir.mkdir(parents=True, exist_ok=True)
        file_path = storage_dir / f"{uuid4().hex}{Path(filename).suffix.lower()}"
        file_path.write_bytes(raw)
        return await self.ingest_text(
            session, user_id, filename, source_type, text, file_path=str(file_path)
        )

    async def delete(self, session: AsyncSession, user_id: UUID, document_id: UUID) -> None:
        document = await self.repo.get_document(session, user_id, document_id)
        if document.file_path:
            path = Path(document.file_path)
            if path.is_file():
                path.unlink()
        await session.delete(document)

    async def reindex(self, session: AsyncSession, user_id: UUID, document_id: UUID) -> KnowledgeDocument:
        document = await self.repo.get_document(session, user_id, document_id)
        chunks = await self.repo.chunks_for_document(session, document.id)
        if not chunks:
            raise AppError("RETRIEVAL_ERROR", "文档没有可索引的片段", status_code=409)
        document.index_status = "INDEXING"
        vectors = await self.embeddings.embed([chunk.content for chunk in chunks])
        for chunk, vector in zip(chunks, vectors, strict=True):
            chunk.embedding = vector
        document.index_status = "INDEXED"
        await session.flush()
        return document

    async def search(
        self, session: AsyncSession, user_id: UUID, query: str, scope: list[str], top_k: int
    ) -> list[KnowledgeSearchResult]:
        candidates = await self.repo.chunks_for_user(session, user_id, scope)
        query_tokens = _tokens(query)
        keyword_ranked = sorted(
            candidates,
            key=lambda pair: self._keyword_score(query_tokens, pair[0].content),
            reverse=True,
        )
        keyword_ranked = [pair for pair in keyword_ranked if self._keyword_score(query_tokens, pair[0].content) > 0][:20]
        rankings = [[chunk.id for chunk, _ in keyword_ranked]]
        by_id = {chunk.id: (chunk, document) for chunk, document in candidates}
        if settings.embedding_base_url and settings.embedding_api_key:
            vector = (await self.embeddings.embed([query]))[0]
            vector_ranked = await self.repo.vector_chunks_for_user(session, user_id, scope, vector)
            rankings.append([chunk.id for chunk, _ in vector_ranked])
            by_id.update({chunk.id: (chunk, document) for chunk, document in vector_ranked})
        fused = rrf_fuse(rankings)
        return [
            KnowledgeSearchResult(
                document_id=by_id[chunk_id][1].id,
                chunk_id=chunk_id,
                content=by_id[chunk_id][0].content,
                source_type=by_id[chunk_id][1].source_type,
                source_name=by_id[chunk_id][1].name,
                score=score,
            )
            for chunk_id, score in sorted(fused.items(), key=lambda item: item[1], reverse=True)[:top_k]
        ]

    @staticmethod
    def _keyword_score(query_tokens: list[str], content: str) -> float:
        normalized = content.casefold()
        return sum(normalized.count(token) for token in query_tokens)
