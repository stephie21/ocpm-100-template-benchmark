from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from evaluation.evaluator.agent_runner import AgentRunner, _factual_grounding_score, _tool_f1_score


def _computed_row(reference_value: Any = 5) -> dict[str, Any]:
    return {
        "final_status": "computed",
        "instantiated_question": "How many events exist?",
        "reference_value": reference_value,
        "agent_status": "not_run",
        "actual_tool_chain": [],
        "tool_chain_alignment_score": None,
        "llm_response": None,
        "response_contains_reference": None,
        "used_llm": False,
        "used_agent": False,
        "mode": "reference-only",
    }


class StubAgentRunner(AgentRunner):
    def __init__(self, answer: str, tools: list[str]) -> None:
        super().__init__(api_base_url="http://agent.example/base/", ocdfg_id="configured-id")
        self.posted_endpoint: str | None = None
        self.posted_question: str | None = None
        self._answer = answer
        self._tools = tools

    async def _post_eval_answer(self, endpoint: str, question: str) -> tuple[str, list[str]]:
        self.posted_endpoint = endpoint
        self.posted_question = question
        return self._answer, self._tools


def test_enrich_posts_question_and_updates_row_in_place() -> None:
    row = _computed_row()
    runner = StubAgentRunner("The total is exactly 5.", ["fetch_metadata", "7"])

    enriched = asyncio.run(runner.enrich(row, ("fetch_metadata", "compute_total")))

    assert enriched is row
    assert runner.posted_endpoint == "http://agent.example/base/api/v1/eval"
    assert runner.posted_question == "How many events exist?"
    assert row["llm_response"] == "The total is exactly 5."
    assert row["agent_status"] == "completed"
    assert row["actual_tool_chain"] == ["fetch_metadata", "7"]
    assert row["tool_chain_alignment_score"] == 0.5
    assert row["response_contains_reference"] is True
    assert row["used_llm"] is True
    assert row["used_agent"] is True
    assert row["mode"] == "agent-comparison"


def test_enrich_scores_empty_json_result() -> None:
    row = _computed_row(reference_value=None)
    row["instantiated_question"] = "What is absent?"
    row["actual_tool_chain"] = ["previous"]
    runner = StubAgentRunner("", [])

    enriched = asyncio.run(runner.enrich(row, ("fetch_metadata",)))

    assert enriched["llm_response"] == ""
    assert enriched["actual_tool_chain"] == []
    assert enriched["tool_chain_alignment_score"] == 0.0
    assert enriched["response_contains_reference"] is False


def test_enrich_requires_ocdfg_id_only_for_computed_rows() -> None:
    computed = _computed_row()
    runner = AgentRunner(api_base_url="http://agent.example/base/")

    with pytest.raises(ValueError, match="ocdfg_id is required"):
        asyncio.run(runner.enrich(computed, ()))

    skipped = _computed_row()
    skipped["final_status"] = "skipped"

    enriched = asyncio.run(runner.enrich(skipped, ()))

    assert enriched["agent_status"] == "skipped"
    assert enriched["actual_tool_chain"] == []


def test_post_eval_answer_posts_exact_payload_and_parses_json(monkeypatch: Any) -> None:
    fake_client = FakeAsyncClient(
        {
            "answer": "The total is 5.",
            "tools_used": ["fetch_metadata", 7, "compute_total"],
            "ocdfg_cached": True,
            "usage": {"prompt_tokens": 1},
        }
    )
    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(AsyncClient=fake_client.build_client))
    runner = AgentRunner(api_base_url="http://agent.example/base/", ocdfg_id="configured-id")

    answer, tools = asyncio.run(
        runner._post_eval_answer(
            "http://agent.example/base/api/v1/eval",
            "How many events exist?",
        )
    )

    assert fake_client.timeout == 180.0
    assert fake_client.post_url == "http://agent.example/base/api/v1/eval"
    assert fake_client.post_json == {
        "message": "How many events exist?",
        "ocdfg_id": "configured-id",
        "context": {"mode": "tools"},
    }
    assert fake_client.response.raise_for_status_called is True
    assert answer == "The total is 5."
    assert tools == ["fetch_metadata", "7", "compute_total"]


def test_post_eval_answer_requires_json_object(monkeypatch: Any) -> None:
    fake_client = FakeAsyncClient(["not", "an", "object"])
    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(AsyncClient=fake_client.build_client))
    runner = AgentRunner(api_base_url="http://agent.example/base/", ocdfg_id="configured-id")

    with pytest.raises(ValueError, match="JSON object"):
        asyncio.run(runner._post_eval_answer("http://agent.example/base/api/v1/eval", "Question?"))


def test_agent_runner_accepts_custom_positive_timeout(monkeypatch: Any) -> None:
    fake_client = FakeAsyncClient({"answer": "ok", "tools_used": []})
    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(AsyncClient=fake_client.build_client))
    runner = AgentRunner(api_base_url="http://agent.example/base/", ocdfg_id="configured-id", timeout_seconds=42.5)

    asyncio.run(runner._post_eval_answer("http://agent.example/base/api/v1/eval", "Question?"))

    assert fake_client.timeout == 42.5


def test_agent_runner_rejects_non_positive_timeout() -> None:
    with pytest.raises(ValueError, match="timeout_seconds must be positive"):
        AgentRunner(timeout_seconds=0)


class FakeAsyncClient:
    def __init__(self, response_json: Any) -> None:
        self.response = FakeJsonResponse(response_json)
        self.post_url: str | None = None
        self.post_json: dict[str, Any] | None = None
        self.timeout: float | None = None

    def build_client(self, *, timeout: float) -> "FakeAsyncClient":
        self.timeout = timeout
        return self

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        return None

    async def post(self, url: str, *, json: dict[str, Any]) -> "FakeJsonResponse":
        self.post_url = url
        self.post_json = json
        return self.response


class FakeJsonResponse:
    def __init__(self, response_json: Any) -> None:
        self._response_json = response_json
        self.raise_for_status_called = False

    def raise_for_status(self) -> None:
        self.raise_for_status_called = True

    def json(self) -> Any:
        return self._response_json


def test_factual_grounding_obeys_atomic_semantics() -> None:
    assert _factual_grounding_score(["alpha", "beta"], "alpha and beta are present") == 1.0
    assert _factual_grounding_score(["alpha", "beta"], "alpha is present") == 0.0
    assert _factual_grounding_score(12, "The value is 112.") == 0.0
    assert _factual_grounding_score(12, "The value is 12.") == 1.0
    assert _factual_grounding_score([], "There are keine matching cases.") == 1.0
    assert _factual_grounding_score(None, "none were found") == 1.0
    assert _factual_grounding_score("Case A", "case a") == 0.0


def test_tool_f1_uses_ordered_lcs() -> None:
    assert _tool_f1_score((), ()) == 1.0
    assert _tool_f1_score(("a",), ()) == 0.0
    assert _tool_f1_score(("b", "a"), ("a", "b")) == 0.5
    assert _tool_f1_score(("a", "x", "c"), ("a", "b", "c")) == 2 / 3
