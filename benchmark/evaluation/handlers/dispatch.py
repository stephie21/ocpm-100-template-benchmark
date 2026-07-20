from __future__ import annotations

from typing import Any, Mapping

from evaluation.handlers.category_1 import Category1Handler
from evaluation.handlers.category_2 import Category2Handler
from evaluation.handlers.category_3 import Category3Handler

MetricResult = dict[str, Any]

_TEMPLATE_DISPATCH = {
    "OCPM_GEN_001": Category1Handler.NODE_OUT_DEGREE_QUESTION,
    "OCPM_GEN_002": Category1Handler.NODE_IN_DEGREE_QUESTION,
    "OCPM_GEN_003": Category1Handler.START_FREQUENCY_QUESTION,
    "OCPM_GEN_004": Category1Handler.ACTIVITY_FREQUENCY_QUESTION,
    "OCPM_GEN_005": Category1Handler.END_FREQUENCY_QUESTION,
    "OCPM_GEN_006": Category1Handler.OBJECTS_BY_TYPE_QUESTION,
    "OCPM_GEN_011": Category1Handler.ZERO_IN_QUESTION,
    "OCPM_GEN_012": Category1Handler.ZERO_OUT_QUESTION,
    "OCPM_GEN_026": Category2Handler.EDGE_EXISTS_QUESTION,
    "OCPM_GEN_027": Category2Handler.EDGE_COUNT_QUESTION,
    "OCPM_GEN_031": Category2Handler.OUTGOING_EDGES_QUESTION,
    "OCPM_GEN_033": Category2Handler.EDGE_DURATION_QUESTION,
    "OCPM_GEN_046": Category2Handler.BRANCHING_RATIO_QUESTION,
    "OCPM_GEN_052": Category3Handler.REACHABLE_QUESTION,
    "OCPM_GEN_054": Category3Handler.SHORTEST_PATH_QUESTION,
    "OCPM_GEN_055": Category3Handler.PATH_LENGTH_QUESTION,
    "OCPM_GEN_056": Category3Handler.DOWNSTREAM_QUESTION,
    "OCPM_GEN_062": Category3Handler.ACTIVITY_COUNT_QUESTION,
    "OCPM_GEN_067": Category3Handler.EDGE_LIST_QUESTION,
}

_METRIC_DISPATCH = {
    "node_out_degree": Category1Handler.NODE_OUT_DEGREE_QUESTION,
    "node_in_degree": Category1Handler.NODE_IN_DEGREE_QUESTION,
    "start_frequency": Category1Handler.START_FREQUENCY_QUESTION,
    "node_weight": Category1Handler.ACTIVITY_FREQUENCY_QUESTION,
    "end_frequency": Category1Handler.END_FREQUENCY_QUESTION,
    "object_frequency": Category1Handler.OBJECTS_BY_TYPE_QUESTION,
    "zero_in_degree_activities": Category1Handler.ZERO_IN_QUESTION,
    "zero_out_degree_activities": Category1Handler.ZERO_OUT_QUESTION,
    "edge_exists": Category2Handler.EDGE_EXISTS_QUESTION,
    "edge_weight": Category2Handler.EDGE_COUNT_QUESTION,
    "outgoing_edges": Category2Handler.OUTGOING_EDGES_QUESTION,
    "avg_edge_duration": Category2Handler.EDGE_DURATION_QUESTION,
    "edge_weight_share": Category2Handler.BRANCHING_RATIO_QUESTION,
    "eventual_reachability": Category3Handler.REACHABLE_QUESTION,
    "shortest_path": Category3Handler.SHORTEST_PATH_QUESTION,
    "shortest_path_length": Category3Handler.PATH_LENGTH_QUESTION,
    "downstream_activity_set": Category3Handler.DOWNSTREAM_QUESTION,
    "downstream_activity_count": Category3Handler.ACTIVITY_COUNT_QUESTION,
    "shortest_path_edge_list": Category3Handler.EDGE_LIST_QUESTION,
}

def _metric_name(template: Any) -> str:
    return str(template.evaluation_logic.mathematical_assertion.target_metric)

def dispatch_question(template: Any) -> str | None:
    return _TEMPLATE_DISPATCH.get(str(template.template_id)) or _METRIC_DISPATCH.get(_metric_name(template))

def execute_reference_metric(template: Any, model: Any, bindings: Mapping[str, str] | None, handlers: Mapping[str, Any]) -> MetricResult:
    handler = handlers.get(str(template.category))
    if handler is None:
        return {"status": "unsupported", "value": None, "message": f"Unsupported category: {template.category}"}
    question = dispatch_question(template)
    if question is None:
        return {"status": "unsupported", "value": None, "message": f"Unsupported target metric: {_metric_name(template)}"}
    return handler.execute(question, model, dict(bindings or {}))
