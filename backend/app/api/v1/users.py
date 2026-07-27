from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.users import UserCreate, UserRead

router = APIRouter(prefix="/api/v1/users", tags=["users"])
users = UserRepository()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, session: AsyncSession = Depends(get_db_session)) -> User:
    user = await users.create(session, User(display_name=payload.display_name, email=payload.email))
    return user
