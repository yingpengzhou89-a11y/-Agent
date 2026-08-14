from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import extract_user_id
from app.db.session import get_db_session
from app.models.user import User
from app.repositories.users import UserRepository


bearer_scheme = HTTPBearer(auto_error=False)
users = UserRepository()


async def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            "UNAUTHORIZED",
            "需要登录后才能访问该接口",
            status_code=401,
        )

    user_id = extract_user_id(credentials.credentials)

    if user_id is None:
        raise AppError(
            "UNAUTHORIZED",
            "登录凭证无效或已过期",
            status_code=401,
        )

    user = await users.get(session, user_id)

    if user is None:
        raise AppError(
            "UNAUTHORIZED",
            "登录用户不存在或已失效",
            status_code=401,
        )

    return user


async def current_user_id(
    user: User = Depends(current_user),
) -> UUID:
    return user.id
