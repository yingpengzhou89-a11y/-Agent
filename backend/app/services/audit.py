from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.models.audit import AuditLog
from app.repositories.audit import AuditRepository


class AuditService:
    """Centralized service for security and business audit logging."""

    def __init__(
        self,
        repository: AuditRepository | None = None,
    ) -> None:
        self.repository = repository or AuditRepository()

    async def log(
        self,
        *,
        session: AsyncSession,
        action: str,
        actor_user_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        success: bool,
        status_code: int | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            status_code=status_code,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=metadata or {},
        )

        return await self.repository.create(
            session,
            audit_log,
        )

    async def log_in_new_transaction(
        self,
        *,
        action: str,
        actor_user_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        success: bool,
        status_code: int | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Persist an audit event using an independent database transaction.

        This must be used for events that happen immediately before
        returning/raising an HTTP error, so the audit record survives
        rollback of the original request transaction.
        """
        async with SessionLocal() as session:
            try:
                audit_log = await self.log(
                    session=session,
                    action=action,
                    actor_user_id=actor_user_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    success=success,
                    status_code=status_code,
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata=metadata,
                )

                await session.commit()

                return audit_log

            except Exception:
                await session.rollback()
                raise


audit_service = AuditService()
