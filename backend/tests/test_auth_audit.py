from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.rate_limit import limiter
from app.db.session import get_db_session
from app.main import create_app
from app.models.audit import AuditLog
from app.models.user import User
from app.services import audit as audit_module


@pytest_asyncio.fixture
async def test_database(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'auth_audit.db'}",
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


@pytest_asyncio.fixture
async def app_with_test_database(
    test_database,
    monkeypatch,
):
    app = create_app()

    async def override_get_db_session():
        async with test_database() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = (
        override_get_db_session
    )

    monkeypatch.setattr(
        audit_module,
        "SessionLocal",
        test_database,
    )

    # IMPORTANT:
    # Keep SlowAPI enabled in these tests.
    #
    # Previously this fixture set:
    #
    #     limiter.enabled = False
    #
    # which meant the authentication tests did not exercise the real
    # SlowAPI decorator. That allowed the production bug where the
    # endpoint was missing `response: Response` to escape the tests.
    #
    # We now run the real limiter and reset its in-memory counters before
    # and after every test so tests do not affect one another.
    original_enabled = limiter.enabled
    limiter.enabled = True

    try:
        limiter.reset()
    except AttributeError:
        pass

    try:
        yield app
    finally:
        try:
            limiter.reset()
        except AttributeError:
            pass

        limiter.enabled = original_enabled
        app.dependency_overrides.clear()


async def fetch_audit_logs(
    session_factory,
) -> list[AuditLog]:
    async with session_factory() as session:
        result = await session.scalars(
            select(AuditLog).order_by(
                AuditLog.created_at.asc(),
            )
        )

        return list(result.all())


@pytest.mark.asyncio
async def test_register_success_creates_audit_log(
    app_with_test_database,
    test_database,
) -> None:
    async with AsyncClient(
        transport=ASGITransport(
            app=app_with_test_database,
        ),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "register@example.com",
                "password": "12345678",
                "display_name": "Register User",
            },
            headers={
                "X-Request-ID": "register-request-1",
            },
        )

    assert response.status_code == 201

    body = response.json()

    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "register@example.com"

    # This is important for the real SlowAPI integration.
    # The route is configured with headers_enabled=True, so a successful
    # request should receive the rate-limit headers.
    assert response.headers["X-RateLimit-Limit"] == "5"
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers

    logs = await fetch_audit_logs(
        test_database,
    )

    assert len(logs) == 1

    audit = logs[0]

    assert audit.action == "REGISTER_SUCCESS"
    assert audit.success is True
    assert audit.status_code == 201
    assert audit.request_id == "register-request-1"
    assert audit.resource_type == "USER"
    assert audit.resource_id is not None
    assert audit.actor_user_id == audit.resource_id
    assert audit.metadata_json == {
        "auth_method": "password",
    }


@pytest.mark.asyncio
async def test_login_success_creates_audit_log(
    app_with_test_database,
    test_database,
) -> None:
    async with AsyncClient(
        transport=ASGITransport(
            app=app_with_test_database,
        ),
        base_url="http://testserver",
    ) as client:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "login-success@example.com",
                "password": "12345678",
                "display_name": "Login User",
            },
        )

        assert register_response.status_code == 201

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login-success@example.com",
                "password": "12345678",
            },
            headers={
                "X-Request-ID": "login-success-request",
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["access_token"]
    assert body["token_type"] == "bearer"

    # This assertion specifically protects against the production bug
    # that was caused by the missing `response: Response` parameter in
    # the login endpoint.
    assert response.headers["X-RateLimit-Limit"] == "10"
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers

    logs = await fetch_audit_logs(
        test_database,
    )

    login_logs = [
        item
        for item in logs
        if item.action == "LOGIN_SUCCESS"
    ]

    assert len(login_logs) == 1

    audit = login_logs[0]

    assert audit.success is True
    assert audit.status_code == 200
    assert audit.request_id == "login-success-request"
    assert audit.resource_type == "USER"
    assert audit.actor_user_id is not None
    assert audit.resource_id == audit.actor_user_id
    assert audit.metadata_json == {
        "auth_method": "password",
    }


@pytest.mark.asyncio
async def test_login_failed_creates_audit_log_and_returns_401(
    app_with_test_database,
    test_database,
) -> None:
    async with AsyncClient(
        transport=ASGITransport(
            app=app_with_test_database,
        ),
        base_url="http://testserver",
    ) as client:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "login-failed@example.com",
                "password": "12345678",
                "display_name": "Failed Login User",
            },
        )

        assert register_response.status_code == 201

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login-failed@example.com",
                "password": "wrong-password",
            },
            headers={
                "X-Request-ID": "login-failed-request",
            },
        )

    assert response.status_code == 401

    body = response.json()

    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["message"] == "邮箱或密码错误"
    assert body["error"]["request_id"] == "login-failed-request"
    assert body["error"]["retryable"] is False

    logs = await fetch_audit_logs(
        test_database,
    )

    failed_logs = [
        item
        for item in logs
        if item.action == "LOGIN_FAILED"
    ]

    assert len(failed_logs) == 1

    audit = failed_logs[0]

    assert audit.success is False
    assert audit.status_code == 401
    assert audit.request_id == "login-failed-request"
    assert audit.resource_type == "USER"
    assert audit.actor_user_id is not None
    assert audit.resource_id == audit.actor_user_id
    assert audit.metadata_json == {
        "auth_method": "password",
        "reason": "invalid_credentials",
    }


@pytest.mark.asyncio
async def test_login_nonexistent_user_creates_audit_log(
    app_with_test_database,
    test_database,
) -> None:
    async with AsyncClient(
        transport=ASGITransport(
            app=app_with_test_database,
        ),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "does-not-exist@example.com",
                "password": "12345678",
            },
            headers={
                "X-Request-ID": "missing-user-request",
            },
        )

    assert response.status_code == 401

    body = response.json()

    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["message"] == "邮箱或密码错误"
    assert body["error"]["request_id"] == "missing-user-request"
    assert body["error"]["retryable"] is False

    logs = await fetch_audit_logs(
        test_database,
    )

    failed_logs = [
        item
        for item in logs
        if item.action == "LOGIN_FAILED"
    ]

    assert len(failed_logs) == 1

    audit = failed_logs[0]

    assert audit.actor_user_id is None
    assert audit.resource_id is None
    assert audit.resource_type == "USER"
    assert audit.status_code == 401
    assert audit.success is False
    assert audit.request_id == "missing-user-request"
    assert audit.metadata_json == {
        "auth_method": "password",
        "reason": "invalid_credentials",
    }


@pytest.mark.asyncio
async def test_invalid_password_hash_returns_401_instead_of_500(
    app_with_test_database,
    test_database,
) -> None:
    user_id = uuid4()

    async with test_database() as session:
        session.add(
            User(
                id=user_id,
                email="broken-hash@example.com",
                display_name="Broken Hash User",
                password_hash="this-is-not-a-valid-password-hash",
            )
        )

        await session.commit()

    async with AsyncClient(
        transport=ASGITransport(
            app=app_with_test_database,
        ),
        base_url="http://testserver",
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "broken-hash@example.com",
                "password": "12345678",
            },
            headers={
                "X-Request-ID": "broken-hash-request",
            },
        )

    assert response.status_code == 401

    body = response.json()

    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["request_id"] == "broken-hash-request"
    assert body["error"]["retryable"] is False

    logs = await fetch_audit_logs(
        test_database,
    )

    failed_logs = [
        item
        for item in logs
        if item.action == "LOGIN_FAILED"
    ]

    assert len(failed_logs) == 1

    audit = failed_logs[0]

    assert audit.success is False
    assert audit.status_code == 401
    assert audit.request_id == "broken-hash-request"
    assert audit.actor_user_id == user_id
    assert audit.resource_id == user_id
    assert audit.resource_type == "USER"
    assert audit.metadata_json == {
        "auth_method": "password",
        "reason": "invalid_credentials",
    }


@pytest.mark.asyncio
async def test_login_rate_limit_is_enforced_and_creates_audit_log(
    app_with_test_database,
    test_database,
) -> None:
    """
    Exercise the real SlowAPI login decorator.

    The login route is limited to 10 requests/minute per client IP.

    The first ten requests should reach the login endpoint and return
    the normal 401 invalid-credentials response.

    The eleventh request must be rejected by SlowAPI with 429 before
    the login endpoint executes, and the global rate-limit exception
    handler must create a RATE_LIMITED audit event.
    """

    async with AsyncClient(
        transport=ASGITransport(
            app=app_with_test_database,
        ),
        base_url="http://testserver",
    ) as client:
        for attempt in range(1, 11):
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "rate-limit@example.com",
                    "password": "wrong-password",
                },
                headers={
                    "X-Request-ID": (
                        f"rate-limit-login-{attempt}"
                    ),
                },
            )

            # The first ten requests are allowed through SlowAPI and
            # therefore reach the login endpoint.
            assert response.status_code == 401

            body = response.json()

            assert body["error"]["code"] == "UNAUTHORIZED"
            assert body["error"]["retryable"] is False

            assert body["error"]["request_id"] == (
                f"rate-limit-login-{attempt}"
            )

        # The eleventh request must be blocked by the real SlowAPI
        # decorator before the login endpoint is executed.
        limited_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "rate-limit@example.com",
                "password": "wrong-password",
            },
            headers={
                "X-Request-ID": "rate-limit-login-11",
            },
        )

    assert limited_response.status_code == 429

    body = limited_response.json()

    assert body["error"]["code"] == "RATE_LIMITED"
    assert body["error"]["request_id"] == (
        "rate-limit-login-11"
    )
    assert body["error"]["retryable"] is True
    assert body["error"]["message"] == (
        "登录尝试过于频繁，请稍后再试"
    )

    # These headers are explicitly part of the project's current
    # rate-limit contract.
    assert limited_response.headers["Retry-After"] == "60"
    assert limited_response.headers["X-Request-ID"] == (
        "rate-limit-login-11"
    )

    logs = await fetch_audit_logs(
        test_database,
    )

    failed_logs = [
        item
        for item in logs
        if item.action == "LOGIN_FAILED"
    ]

    rate_limit_logs = [
        item
        for item in logs
        if item.action == "RATE_LIMITED"
    ]

    # The first ten requests reached the login endpoint.
    assert len(failed_logs) == 10

    # The eleventh request was rejected by SlowAPI before login()
    # executed, so it must not create another LOGIN_FAILED event.
    assert len(rate_limit_logs) == 1

    audit = rate_limit_logs[0]

    assert audit.success is False
    assert audit.status_code == 429
    assert audit.request_id == "rate-limit-login-11"
    assert audit.resource_type == "HTTP_ENDPOINT"
    assert audit.actor_user_id is None
    assert audit.resource_id is None
    assert audit.metadata_json == {
        "method": "POST",
        "path": "/api/v1/auth/login",
    }
