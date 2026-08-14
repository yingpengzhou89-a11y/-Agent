from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models.audit import AuditLog
from app.models.user import User
from app.repositories.audit import AuditRepository
from app.services.audit import AuditService


@pytest_asyncio.fixture
async def sqlite_session_factory(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'audit.db'}",
    )

    async with engine.begin() as connection:
        await connection.run_sync(User.__table__.create)
        await connection.run_sync(AuditLog.__table__.create)

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_audit_repository_creates_audit_log(
    sqlite_session_factory,
) -> None:
    user_id = uuid4()

    async with sqlite_session_factory() as session:
        user = User(
            id=user_id,
            email="audit@example.com",
            display_name="Audit User",
            password_hash="test-hash",
        )

        session.add(user)
        await session.commit()

        repository = AuditRepository()

        audit = AuditLog(
            actor_user_id=user_id,
            action="LOGIN_SUCCESS",
            resource_type="USER",
            resource_id=user_id,
            success=True,
            status_code=200,
            request_id="request-123",
            ip_address="127.0.0.1",
            user_agent="pytest",
            metadata_json={
                "auth_method": "password",
            },
        )

        created = await repository.create(
            session,
            audit,
        )

        await session.commit()

        assert created.id is not None
        assert created.actor_user_id == user_id
        assert created.action == "LOGIN_SUCCESS"
        assert created.resource_type == "USER"
        assert created.resource_id == user_id
        assert created.success is True
        assert created.status_code == 200
        assert created.request_id == "request-123"
        assert created.ip_address == "127.0.0.1"
        assert created.user_agent == "pytest"
        assert created.metadata_json == {
            "auth_method": "password",
        }


@pytest.mark.asyncio
async def test_audit_service_log_persists_event(
    sqlite_session_factory,
) -> None:
    user_id = uuid4()

    async with sqlite_session_factory() as session:
        user = User(
            id=user_id,
            email="service@example.com",
            display_name="Service User",
            password_hash="test-hash",
        )

        session.add(user)
        await session.commit()

        service = AuditService()

        audit = await service.log(
            session=session,
            action="LOGIN_FAILED",
            actor_user_id=user_id,
            resource_type="USER",
            resource_id=user_id,
            success=False,
            status_code=401,
            request_id="request-456",
            ip_address="192.168.1.10",
            user_agent="pytest-agent",
            metadata={
                "auth_method": "password",
                "reason": "invalid_credentials",
            },
        )

        await session.commit()

        assert audit.action == "LOGIN_FAILED"
        assert audit.success is False
        assert audit.status_code == 401
        assert audit.metadata_json["reason"] == "invalid_credentials"

        stored = await session.scalar(
            select(AuditLog).where(
                AuditLog.id == audit.id,
            )
        )

        assert stored is not None
        assert stored.request_id == "request-456"


@pytest.mark.asyncio
async def test_independent_audit_transaction_survives_outer_rollback(
    sqlite_session_factory,
    monkeypatch,
) -> None:
    user_id = uuid4()

    async with sqlite_session_factory() as session:
        user = User(
            id=user_id,
            email="rollback@example.com",
            display_name="Rollback User",
            password_hash="test-hash",
        )

        session.add(user)
        await session.commit()

    import app.services.audit as audit_module

    monkeypatch.setattr(
        audit_module,
        "SessionLocal",
        sqlite_session_factory,
    )

    service = AuditService()

    async with sqlite_session_factory() as outer_session:
        await service.log_in_new_transaction(
            action="LOGIN_FAILED",
            actor_user_id=user_id,
            resource_type="USER",
            resource_id=user_id,
            success=False,
            status_code=401,
            request_id="rollback-request",
            ip_address="127.0.0.1",
            user_agent="pytest",
            metadata={
                "reason": "invalid_credentials",
            },
        )

        await outer_session.rollback()

    async with sqlite_session_factory() as verify_session:
        stored = await verify_session.scalar(
            select(AuditLog).where(
                AuditLog.request_id == "rollback-request",
            )
        )

        assert stored is not None
        assert stored.action == "LOGIN_FAILED"
        assert stored.success is False
