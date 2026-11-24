"""Thin wrapper around the official Groq SDK.

Each task (extraction | insight | chat) has a primary and a fallback model from settings.
A call tries the primary; on any API error or unusable reply it retries once on the fallback.
The API key is only handed to the SDK — never logged or returned.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from functools import lru_cache
from typing import Annotated, Any, Literal, TypeVar

import groq
from fastapi import Depends

from backend.app.config import Settings, get_settings

log = logging.getLogger(__name__)

Task = Literal["extraction", "insight", "chat"]
T = TypeVar("T")

# Chat is warmer so replies read naturally; numbers stay pinned by the prompt + grounding check.
TEMPERATURE: dict[Task, float] = {"extraction": 0.0, "insight": 0.0, "chat": 0.5}
TIMEOUT_SECONDS = 12.0  # x2 (primary + fallback) stays inside Vercel's 30 s function limit


class LLMUnavailable(Exception):
    """No GROQ_API_KEY is configured."""


class LLMError(Exception):
    """Both the primary and the fallback model failed."""

    def __init__(self, message: str, rate_limited: bool = False) -> None:
        super().__init__(message)
        self.rate_limited = rate_limited  # the last failure was Groq's per-minute limit


class GroqLLM:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.models: dict[Task, tuple[str, str]] = {
            "extraction": (settings.groq_extraction_model, settings.groq_extraction_fallback_model),
            "insight": (settings.groq_insight_model, settings.groq_insight_fallback_model),
            "chat": (settings.groq_chat_model, settings.groq_chat_fallback_model),
        }
        if client is None and settings.groq_api_key:
            # max_retries=0: our own fallback model is the retry.
            client = groq.Groq(api_key=settings.groq_api_key, timeout=TIMEOUT_SECONDS, max_retries=0)
        self._client = client  # None -> AI is off

    def complete_json(self, task: Task, messages: list[dict[str, str]]) -> tuple[dict[str, Any], str]:
        """JSON-mode completion parsed into a dict. Returns (data, model_used)."""

        def call(model: str) -> dict[str, Any]:
            data = json.loads(self._create(task, model, messages, json_mode=True))
            if not isinstance(data, dict):
                raise ValueError("expected a JSON object")
            return data

        return self._with_fallback(task, call)

    def complete_text(self, task: Task, messages: list[dict[str, str]]) -> tuple[str, str]:
        """Plain-text completion. Returns (text, model_used)."""
        return self._with_fallback(task, lambda model: self._create(task, model, messages, json_mode=False))

    def _create(self, task: Task, model: str, messages: list[dict[str, str]], json_mode: bool) -> str:
        extra: dict[str, Any] = {"response_format": {"type": "json_object"}} if json_mode else {}
        if task == "chat" and model.startswith("openai/gpt-oss"):
            extra["reasoning_effort"] = "low"  # quicker replies, fewer tokens against the per-minute limit
        response = self._client.chat.completions.create(  # type: ignore[union-attr]
            model=model, messages=messages, temperature=TEMPERATURE[task], **extra
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("empty reply")
        return content

    def _with_fallback(self, task: Task, call: Callable[[str], T]) -> tuple[T, str]:
        if self._client is None:
            raise LLMUnavailable()
        primary, fallback = self.models[task]
        try:
            return call(primary), primary
        except (groq.GroqError, ValueError) as exc:  # ValueError covers bad/empty JSON
            log.warning("Groq %s on %s failed (%s); retrying on %s", task, primary, type(exc).__name__, fallback)
        try:
            return call(fallback), fallback
        except (groq.GroqError, ValueError) as exc:
            log.warning("Groq %s on %s failed (%s)", task, fallback, type(exc).__name__)
            rate_limited = isinstance(exc, groq.RateLimitError)
            raise LLMError(f"{task}: {primary} and {fallback} both failed", rate_limited) from exc


@lru_cache
def _llm_for(settings: Settings) -> GroqLLM:
    return GroqLLM(settings)  # one SDK client (and its connection pool) per configuration


def get_llm(settings: Annotated[Settings, Depends(get_settings)]) -> GroqLLM:
    """FastAPI dependency (tests override it with a fake)."""
    return _llm_for(settings)
