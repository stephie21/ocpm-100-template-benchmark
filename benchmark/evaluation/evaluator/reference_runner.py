from __future__ import annotations

RESULT_FIELDS = (
    "question_id","template_id","category","formal_pattern","instantiated_question","runtime_variables_used","preconditions_status","precondition_messages","expected_tool_chain","target_metric","lookup_path","metric_definition","reference_value","reference_status","reference_message","reference_source","graph_source","used_graph","used_pm4py","final_status","error_or_skip_reason","agent_status","llm_response","used_llm","used_agent","actual_tool_chain","tool_chain_alignment_score","response_contains_reference","mode","ocel_path","benchmark_path",
)

def empty_row():
    return {field: None for field in RESULT_FIELDS}
