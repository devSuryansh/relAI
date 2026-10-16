import copy
import json
from typing import Any

from relai.adapters import OpenAICompatAgent
from relai.env import FaultPolicy, ToolEnv, lookup_tool
from relai.harness import evaluate
from relai.types import FailureMode, StepKind, Task

TASK = Task(id="capital", prompt="Capital of France?", expected="Paris", allowed_tools=["search"])


def _env(faults: FaultPolicy | None = None) -> ToolEnv:
    return ToolEnv([lookup_tool("search", {"capital of France": "Paris"})], faults)


def _tool_call(call_id: str, query: str) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {"name": "search", "arguments": json.dumps({"q": query})},
                        }
                    ],
                }
            }
        ],
        "usage": {"prompt_tokens": 50, "completion_tokens": 10},
    }


def _answer(text: str) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 80, "completion_tokens": 3},
    }


class FakeModel:
    def __init__(self, *responses: dict[str, Any] | Exception) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def __call__(self, url: str, payload: dict[str, Any], headers: dict[str, str]):
        self.requests.append(copy.deepcopy({"url": url, "payload": payload, "headers": headers}))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _agent(model: FakeModel, env: ToolEnv | None = None, **kwargs: Any) -> OpenAICompatAgent:
    return OpenAICompatAgent(
        "fake-llm",
        env or _env(),
        model="test-model",
        base_url="http://localhost:9/v1",
        api_key="sk-test",
        usd_per_1k_prompt=1.0,
        usd_per_1k_completion=2.0,
        transport=model,
        **kwargs,
    )


def test_tool_loop_records_tokens_cost_and_tool_messages() -> None:
    model = FakeModel(_tool_call("c1", "capital of France"), _answer("Paris"))
    report = evaluate(_agent(model), [TASK])
    (result,) = report.results
    assert result.metrics.success
    assert result.metrics.tokens.total == 143
    assert result.metrics.cost_usd == (50 + 80) / 1000 + (10 + 3) * 2 / 1000
    kinds = [step.kind for step in result.trajectory.steps]
    assert kinds == [StepKind.PLAN, StepKind.TOOL_CALL, StepKind.OBSERVATION, StepKind.FINAL]
    first, second = model.requests
    assert first["url"] == "http://localhost:9/v1/chat/completions"
    assert first["headers"] == {"Authorization": "Bearer sk-test"}
    assert first["payload"]["tools"][0]["function"]["name"] == "search"
    assert second["payload"]["messages"][-1] == {
        "role": "tool",
        "tool_call_id": "c1",
        "content": "Paris",
    }


def test_injected_fault_reaches_the_model_and_its_retry_is_credited() -> None:
    model = FakeModel(
        _tool_call("c1", "capital of France"),
        _tool_call("c2", "capital of France"),
        _answer("Paris"),
    )
    report = evaluate(_agent(model, _env(FaultPolicy(fail_first_n=1))), [TASK])
    (result,) = report.results
    assert result.metrics.success
    assert result.metrics.recovery_rate == 1.0
    assert "timed out" in model.requests[1]["payload"]["messages"][-1]["content"]


def test_model_errors_are_recorded_and_running_out_of_turns_has_no_final() -> None:
    model = FakeModel(ConnectionError("refused"), *[_tool_call(f"c{i}", "x") for i in range(3)])
    report = evaluate(_agent(model, max_turns=4), [TASK])
    (result,) = report.results
    assert not result.metrics.success
    assert "model call failed" in result.trajectory.steps[0].content
    assert result.trajectory.final_output is None
    assert FailureMode.HORIZON in result.failures.modes
