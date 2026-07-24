from app.agents.base import AgentContext, BaseAgent
from app.schemas.interview import AnswerEvaluation, EvaluationAgentInput
from app.services.model_gateway import StructuredModelGateway


class EvaluationAgent(BaseAgent[EvaluationAgentInput, AnswerEvaluation]):
    def __init__(self, gateway: StructuredModelGateway):
        self.gateway = gateway

    async def run(self, ctx: AgentContext, payload: EvaluationAgentInput) -> AnswerEvaluation:
        result = await self.gateway.complete_structured(
            context=ctx,
            prompt_key="evaluation_agent/v1",
            payload=payload,
            output_model=AnswerEvaluation,
        )
        # The workflow recalculates the persisted total from the saved rubric.
        return result

