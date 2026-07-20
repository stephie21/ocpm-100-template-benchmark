from __future__ import annotations
import re
from typing import Any


def _tool_f1_score(actual, expected) -> float:
    actual=list(actual); expected=list(expected)
    if not actual and not expected: return 1.0
    if not actual or not expected: return 0.0
    matches=sum(1 for item in actual if item in expected)
    return matches / max(len(actual), len(expected))

def _factual_grounding_score(reference_value: Any, response: str) -> float:
    text=str(response or "")
    if reference_value is None:
        return 1.0 if "none" in text.lower() or "keine" in text.lower() else 0.0
    if isinstance(reference_value, (list, tuple, set)):
        if not reference_value:
            return 1.0 if "none" in text.lower() or "keine" in text.lower() else 0.0
        return 1.0 if all(str(item) in text for item in reference_value) else 0.0
    if isinstance(reference_value, str):
        return 1.0 if reference_value in text else 0.0
    return 1.0 if re.search(rf"(?<!\d){re.escape(str(reference_value))}(?!\d)", text) else 0.0

class AgentRunner:
    def __init__(self, api_base_url: str | None = None, ocdfg_id: str | None = None, timeout_seconds: float = 180.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.api_base_url=api_base_url.rstrip("/") if api_base_url else None
        self.ocdfg_id=ocdfg_id
        self.timeout_seconds=timeout_seconds

    async def enrich(self, row: dict[str, Any], expected_tools: tuple[str, ...]) -> dict[str, Any]:
        if row.get("final_status") != "computed":
            row.update({"agent_status":"skipped","actual_tool_chain":[],"tool_chain_alignment_score":0.0,"mode":"agent-comparison"})
            return row
        if not self.api_base_url:
            row.update({"agent_status":"skipped","actual_tool_chain":[],"tool_chain_alignment_score":0.0,"mode":"agent-comparison"})
            return row
        if not self.ocdfg_id:
            raise ValueError("ocdfg_id is required for computed agent-comparison rows")
        endpoint=f"{self.api_base_url}/api/v1/eval"
        answer, tools = await self._post_eval_answer(endpoint, row["instantiated_question"])
        row.update({"agent_status":"completed","llm_response":answer,"used_llm":True,"used_agent":True,"actual_tool_chain":tools,"tool_chain_alignment_score":_tool_f1_score(tools, expected_tools),"response_contains_reference": bool(_factual_grounding_score(row.get("reference_value"), answer)),"mode":"agent-comparison"})
        return row

    async def _post_eval_answer(self, endpoint: str, question: str) -> tuple[str, list[str]]:
        import httpx
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(endpoint, json={"message": question, "ocdfg_id": self.ocdfg_id, "context": {"mode":"tools"}})
            response.raise_for_status()
            data=response.json()
        if not isinstance(data, dict):
            raise ValueError("Expected JSON object from eval endpoint")
        return str(data.get("answer", "")), [str(tool) for tool in data.get("tools_used", [])]
