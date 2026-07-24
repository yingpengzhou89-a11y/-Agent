import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeVar

import httpx

from pydantic import BaseModel

from app.agents.base import AgentContext
from app.core.config import settings
from app.core.errors import AppError

OutputT = TypeVar("OutputT", bound=BaseModel)


class StructuredModelGateway(ABC):
    """Only boundary where an OpenAI-compatible client may be introduced."""

    @abstractmethod
    async def complete_structured(
        self,
        *,
        context: AgentContext,
        prompt_key: str,
        payload: BaseModel,
        output_model: type[OutputT],
    ) -> OutputT:
        """Return a schema-validated result or raise a typed application error."""
        raise NotImplementedError


class OpenAICompatibleGateway(StructuredModelGateway):
    """OpenAI-compatible JSON gateway with bounded schema-repair retries."""

    def _load_prompt(self, prompt_key: str) -> str:
        path = Path(__file__).parents[1] / "prompts" / f"{prompt_key}.md"
        if not path.is_file():
            raise AppError("PROMPT_NOT_FOUND", f"未找到 Prompt: {prompt_key}", status_code=500)
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _extract_json(content: str) -> object:
        fenced = re.search(r"```(?:json)?\s*(.*?)```", content, flags=re.DOTALL | re.IGNORECASE)
        candidate = fenced.group(1) if fenced else content
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end < start:
            raise ValueError("响应中未找到 JSON 对象")
        return json.loads(candidate[start : end + 1])

    async def complete_structured(
        self,
        *,
        context: AgentContext,
        prompt_key: str,
        payload: BaseModel,
        output_model: type[OutputT],
    ) -> OutputT:
        if not settings.chat_base_url or not settings.chat_api_key or not settings.chat_model:
            raise AppError(
                "MODEL_NOT_CONFIGURED",
                "请在 .env 中配置 CHAT_BASE_URL、CHAT_API_KEY 和 CHAT_MODEL",
                status_code=503,
            )

        system_prompt = self._load_prompt(prompt_key)
        schema = json.dumps(output_model.model_json_schema(), ensure_ascii=False)
        user_prompt = (
            "输入数据：\n"
            f"{payload.model_dump_json()}\n\n"
            "输出必须是严格 JSON，不要使用 Markdown。请符合以下 JSON Schema：\n"
            f"{schema}"
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        endpoint = f"{settings.chat_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {settings.chat_api_key}"}

        # The local desktop environment may expose an incomplete SOCKS proxy
        # configuration. Model traffic should use the explicitly configured API URL.
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds, trust_env=False) as client:
            for attempt in range(settings.llm_max_retries + 1):
                try:
                    response = await client.post(
                        endpoint,
                        headers=headers,
                        json={
                            "model": context.model_name,
                            "messages": messages,
                            "temperature": 0.2,
                            "max_tokens": context.token_budget,
                            "response_format": {"type": "json_object"},
                        },
                    )
                    response.raise_for_status()
                    content = response.json()["choices"][0]["message"]["content"]
                    if not isinstance(content, str):
                        raise ValueError("模型响应未包含文本内容")
                    return output_model.model_validate(self._extract_json(content))
                except (httpx.HTTPError, ImportError, KeyError, IndexError, TypeError, AttributeError, ValueError) as exc:
                    if attempt == settings.llm_max_retries:
                        raise AppError(
                            "MODEL_OUTPUT_INVALID",
                            "模型响应无法通过结构化校验",
                            retryable=True,
                            status_code=502,
                        ) from exc
                    messages.append({"role": "assistant", "content": "请修复为符合 Schema 的严格 JSON。"})

        raise AssertionError("unreachable")
