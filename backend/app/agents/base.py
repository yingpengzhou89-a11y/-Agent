from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class AgentContext(BaseModel):
    request_id: UUID
    user_id: UUID
    session_id: UUID | None = None
    model_name: str
    prompt_name: str
    prompt_version: str
    token_budget: int = Field(gt=0)


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """LLM-facing role; storage and workflow control remain outside this class."""

    @abstractmethod
    async def run(self, ctx: AgentContext, payload: InputT) -> OutputT:
        raise NotImplementedError

