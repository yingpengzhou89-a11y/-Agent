from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.documents import JobDescription, Resume
from app.core.config import settings
from app.core.errors import AppError
from app.repositories.documents import JobRepository, ResumeRepository
from app.repositories.users import UserRepository
from app.schemas.documents import JobCreate, ResumeCreate
from app.services.knowledge import ALLOWED_EXTENSIONS, extract_text


class ResumeService:
    def __init__(self) -> None:
        self.users = UserRepository()
        self.resumes = ResumeRepository()

    async def create(self, session: AsyncSession, user_id: UUID, payload: ResumeCreate) -> Resume:
        await self.users.require(session, user_id)
        resume = Resume(
            user_id=user_id,
            name=payload.name,
            file_type=payload.file_type,
            raw_text=payload.raw_text,
            is_current=payload.is_current,
        )
        return await self.resumes.create(session, resume)

    async def create_from_file(
        self, session: AsyncSession, user_id: UUID, filename: str, raw: bytes, name: str | None = None
    ) -> Resume:
        """Parse and persist a candidate's source resume while retaining its original file."""
        await self.users.require(session, user_id)
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise AppError("FILE_PARSE_ERROR", "简历仅支持 PDF、DOCX、Markdown 和 TXT 文件", status_code=422)
        if len(raw) > settings.max_upload_mb * 1024 * 1024:
            raise AppError("FILE_PARSE_ERROR", "上传简历超过大小限制", status_code=413)
        text = extract_text(filename, raw)
        if not text.strip():
            raise AppError("FILE_PARSE_ERROR", "简历中没有可解析的文本内容", status_code=422)

        storage_dir = Path(settings.storage_dir) / "resumes" / str(user_id)
        storage_dir.mkdir(parents=True, exist_ok=True)
        file_path = storage_dir / f"{uuid4().hex}{suffix}"
        file_path.write_bytes(raw)
        resume = Resume(
            user_id=user_id,
            name=(name or Path(filename).stem).strip() or "我的简历",
            file_path=str(file_path),
            file_type=suffix.removeprefix("."),
            raw_text=text,
            is_current=True,
        )
        return await self.resumes.create(session, resume)


class JobService:
    def __init__(self) -> None:
        self.users = UserRepository()
        self.jobs = JobRepository()

    async def create(self, session: AsyncSession, user_id: UUID, payload: JobCreate) -> JobDescription:
        await self.users.require(session, user_id)
        job = JobDescription(
            user_id=user_id,
            title=payload.title,
            company=payload.company,
            raw_text=payload.raw_text,
            is_current=payload.is_current,
        )
        return await self.jobs.create(session, job)
