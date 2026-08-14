from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditRepository:
    async def create(
        self,
        session: AsyncSession,
        audit_log: AuditLog,
    ) -> AuditLog:
        session.add(audit_log)
        await session.flush()
        await session.refresh(audit_log)
        return audit_log
