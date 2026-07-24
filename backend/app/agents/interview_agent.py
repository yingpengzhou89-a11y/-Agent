from app.agents.base import AgentContext, BaseAgent
from app.schemas.interview import (
    InterviewAgentInput,
    InterviewDecision,
    InterviewPlanDraft,
    InterviewPlanningInput,
)
from app.services.model_gateway import StructuredModelGateway


class InterviewAgent(BaseAgent[InterviewAgentInput, InterviewDecision]):
    def __init__(self, gateway: StructuredModelGateway):
        self.gateway = gateway

    async def run(self, ctx: AgentContext, payload: InterviewAgentInput) -> InterviewDecision:
        return await self.gateway.complete_structured(
            context=ctx,
            prompt_key="interview_agent/v1",
            payload=payload,
            output_model=InterviewDecision,
        )

    async def create_plan(
        self, ctx: AgentContext, payload: InterviewPlanningInput
    ) -> InterviewPlanDraft:
        return await self.gateway.complete_structured(
            context=ctx,
            prompt_key="interview_plan/v1",
            payload=payload,
            output_model=InterviewPlanDraft,
        )
