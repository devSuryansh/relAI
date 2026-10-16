"""Tool-calling agent for any OpenAI-compatible chat completions endpoint.

Works with OpenAI, Groq, Together, vLLM, and Ollama (http://localhost:11434/v1).
Tool calls go through a relai ToolEnv, so injected faults, cost, latency, and
token usage all land in the trajectory like they do for offline agents.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from collections.abc import Callable
from typing import Any

from relai.env import ToolEnv
from relai.types import Task, TokenUsage, Trajectory

Transport = Callable[[str, dict[str, Any], dict[str, str]], dict[str, Any]]
"""(url, json payload, headers) -> decoded json response."""

DEFAULT_SYSTEM_PROMPT = (
    "You are a careful assistant with tools. Use a tool whenever the answer depends "
    "on data you do not have. If a tool times out or is unavailable, try it again. "
    "When you are done, reply with only the final answer, with no extra words."
)


def http_transport(timeout_s: float = 60.0) -> Transport:
    def post(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return json.loads(response.read().decode("utf-8"))

    return post


class OpenAICompatAgent:
    """A ReAct-style loop: ask the model, run the tools it calls, repeat until it answers."""

    def __init__(
        self,
        name: str,
        env: ToolEnv,
        *,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_turns: int = 8,
        temperature: float = 0.0,
        usd_per_1k_prompt: float = 0.0,
        usd_per_1k_completion: float = 0.0,
        transport: Transport | None = None,
    ) -> None:
        self.name = name
        self.env = env
        self.model = model
        self.base_url = (
            base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        ).rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.temperature = temperature
        self.usd_per_1k_prompt = usd_per_1k_prompt
        self.usd_per_1k_completion = usd_per_1k_completion
        self._post = transport or http_transport()

    def run(self, task: Task) -> Trajectory:
        rec = self.env.recorder(task)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task.prompt},
        ]
        tools = self.env.specs(task.allowed_tools or None)
        for _ in range(self.max_turns):
            started = time.perf_counter()
            try:
                response = self._post(
                    f"{self.base_url}/chat/completions",
                    self._payload(messages, tools),
                    self._headers(),
                )
                message = response["choices"][0]["message"]
            except Exception as exc:
                rec.error(f"model call failed: {type(exc).__name__}: {exc}")
                rec.recovery("ask the model again")
                continue
            latency_ms = (time.perf_counter() - started) * 1000
            tokens = _usage(response)
            cost = self._cost(tokens)
            text = (message.get("content") or "").strip()
            calls = message.get("tool_calls") or []
            if not calls:
                return rec.final(text, tokens=tokens, cost_usd=cost, latency_ms=latency_ms)
            rec.plan(
                text or "call " + ", ".join(_call_name(call) for call in calls),
                tokens=tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
            )
            messages.append(
                {"role": "assistant", "content": message.get("content"), "tool_calls": calls}
            )
            for call in calls:
                result = rec.call(_call_name(call), _call_args(call))
                messages.append(
                    {"role": "tool", "tool_call_id": call.get("id", ""), "content": result.output}
                )
        return rec.stop()

    def _payload(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if tools:
            payload["tools"] = tools
        return payload

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def _cost(self, tokens: TokenUsage) -> float:
        return (
            tokens.prompt * self.usd_per_1k_prompt + tokens.completion * self.usd_per_1k_completion
        ) / 1000


def _usage(response: dict[str, Any]) -> TokenUsage:
    usage = response.get("usage") or {}
    return TokenUsage(
        prompt=int(usage.get("prompt_tokens") or 0),
        completion=int(usage.get("completion_tokens") or 0),
    )


def _call_name(call: dict[str, Any]) -> str:
    return str((call.get("function") or {}).get("name", ""))


def _call_args(call: dict[str, Any]) -> dict[str, Any]:
    raw = (call.get("function") or {}).get("arguments") or "{}"
    try:
        args = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {"_unparsed": str(raw)}
    return args if isinstance(args, dict) else {"_value": args}
