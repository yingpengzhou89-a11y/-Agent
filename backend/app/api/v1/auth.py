from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.errors import AppError
from app.core.rate_limit import limiter
from app.core.request_context import (
    get_client_ip,
    get_request_id,
    get_user_agent,
)
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db_session
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
)
from app.schemas.users import UserRead
from app.services.audit import audit_service


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)

users = UserRepository()


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(
    "5/hour",
    error_message="注册请求过于频繁，请稍后再试",
)
async def register(
    request: Request,
    response: Response,
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    request_id = get_request_id(request)
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    email = str(payload.email).strip().lower()

    existing = await users.get_by_email(
        session,
        email,
    )

    if existing is not None:
        raise AppError(
            "CONFLICT",
            "该邮箱已经注册",
            status_code=409,
        )

    user = User(
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(
            payload.password,
        ),
    )

    try:
        user = await users.create(
            session,
            user,
        )

        # Commit the user before creating the independent audit record.
        # This prevents an audit failure from turning a successful
        # registration into an HTTP 500.
        await session.commit()

    except IntegrityError:
        await session.rollback()

        raise AppError(
            "CONFLICT",
            "该邮箱已经注册",
            status_code=409,
        )

    access_token = create_access_token(
        user.id,
    )

    try:
        await audit_service.log_in_new_transaction(
            action="REGISTER_SUCCESS",
            actor_user_id=user.id,
            resource_type="USER",
            resource_id=user.id,
            success=True,
            status_code=status.HTTP_201_CREATED,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "auth_method": "password",
            },
        )
    except Exception:
        # Authentication must not fail just because audit persistence
        # is temporarily unavailable.
        pass

    return AuthResponse(
        access_token=access_token,
        user=UserRead.model_validate(user),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
)
@limiter.limit(
    "10/minute",
    error_message="登录尝试过于频繁，请稍后再试",
)
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    request_id = get_request_id(request)
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    email = str(payload.email).strip().lower()

    user = await users.get_by_email(
        session,
        email,
    )

    password_valid = False

    if (
        user is not None
        and user.password_hash is not None
    ):
        password_valid = verify_password(
            payload.password,
            user.password_hash,
        )

    if not password_valid:
        try:
            await audit_service.log_in_new_transaction(
                action="LOGIN_FAILED",
                actor_user_id=(
                    user.id
                    if user is not None
                    else None
                ),
                resource_type="USER",
                resource_id=(
                    user.id
                    if user is not None
                    else None
                ),
                success=False,
                status_code=status.HTTP_401_UNAUTHORIZED,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "auth_method": "password",
                    "reason": "invalid_credentials",
                },
            )
        except Exception:
            # Audit failure must never turn an expected 401 into a 500.
            pass

        raise AppError(
            "UNAUTHORIZED",
            "邮箱或密码错误",
            status_code=401,
        )

    access_token = create_access_token(
        user.id,
    )

    try:
        await audit_service.log_in_new_transaction(
            action="LOGIN_SUCCESS",
            actor_user_id=user.id,
            resource_type="USER",
            resource_id=user.id,
            success=True,
            status_code=status.HTTP_200_OK,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                "auth_method": "password",
            },
        )
    except Exception:
        # Do not break a successful login because of an audit
        # persistence problem.
        pass

    return AuthResponse(
        access_token=access_token,
        user=UserRead.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserRead,
)
async def me(
    user: User = Depends(current_user),
) -> UserRead:
    return UserRead.model_validate(user)
