from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_audits import AgentDecisionLog


class AgentDecisionRepository:
    async def create(self, session: AsyncSession, decision: AgentDecisionLog) -> AgentDecisionLog:
        session.add(decision)
        await session.flush()
        return decision
