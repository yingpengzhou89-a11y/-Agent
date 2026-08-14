from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.user import User


class UserRepository:
    async def create(self, session: AsyncSession, user: User) -> User:
        session.add(user)
        await session.flush()
        await session.refresh(user)
        return user

    async def get(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> User | None:
        return await session.scalar(
            select(User).where(
                User.id == user_id,
                User.deleted_at.is_(None),
            )
        )

    async def get_by_email(
        self,
        session: AsyncSession,
        email: str,
    ) -> User | None:
        return await session.scalar(
            select(User).where(
                User.email == email,
                User.deleted_at.is_(None),
            )
        )

    async def require(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> User:
        user = await self.get(session, user_id)

        if user is None:
            raise AppError(
                "NOT_FOUND",
                "未找到用户",
                status_code=404,
            )

        return user
