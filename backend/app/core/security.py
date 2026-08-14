from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()


def _get_secret_key() -> str:
    """
    Return the JWT signing secret.

    The default development secret is intentionally rejected in production.
    """
    if settings.app_env.lower() in {"production", "prod"}:
        if settings.app_secret_key == "dev-only-change-me":
            raise RuntimeError(
                "生产环境必须通过 APP_SECRET_KEY 配置真实的 JWT secret"
            )

    return settings.app_secret_key


def hash_password(password: str) -> str:
    """Hash a plaintext password using the recommended pwdlib algorithm."""
    return password_hash.hash(password)


def verify_password(
    password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a plaintext password against a stored hash.

    A missing/corrupted/legacy hash must never cause the login
    endpoint to return HTTP 500. It is treated as invalid credentials.
    """
    try:
        return password_hash.verify(
            password,
            hashed_password,
        )
    except Exception:
        return False


def create_access_token(
    user_id: UUID,
    expires_minutes: int | None = None,
) -> str:
    """
    Create a signed JWT access token.

    The user UUID is stored in the standard `sub` claim.
    """
    now = datetime.now(timezone.utc)

    expires_at = now + timedelta(
        minutes=(
            expires_minutes
            if expires_minutes is not None
            else settings.access_token_expire_minutes
        )
    )

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        _get_secret_key(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.
    """
    return jwt.decode(
        token,
        _get_secret_key(),
        algorithms=[settings.jwt_algorithm],
    )


def extract_user_id(
    token: str,
) -> UUID | None:
    """
    Extract the authenticated user's UUID from the JWT `sub` claim.
    """
    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
        return None

    subject = payload.get("sub")

    if not isinstance(subject, str):
        return None

    try:
        return UUID(subject)
    except ValueError:
        return None
