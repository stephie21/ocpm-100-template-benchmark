from __future__ import annotations
import asyncio, csv, json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evaluation.compiler.benchmark_compiler import load_templates_from_file
from evaluation.evaluator.agent_runner import AgentRunner
from evaluation.evaluator.reference_runner import RESULT_FIELDS, empty_row
from evaluation.handlers.category_1 import Category1Handler
from evaluation.handlers.category_2 import Category2Handler
from evaluation.handlers.category_3 import Category3Handler
from evaluation.handlers.category_4 import Category4Handler
from evaluation.handlers.dispatch import execute_reference_metric
from evaluation.ingestion.ocel_loader import load_ocel
from evaluation.preconditions.engine import PreconditionEngine
from evaluation.templates.instantiation_engine import VariableInstantiationEngine

@dataclass(frozen=True)
class OrchestratorResult:
    rows: list[dict[str, Any]]
    jsonl_path: Path
    csv_path: Path
    summary_path: Path

class BenchmarkOrchestrator:
    def __init__(self, agent_runner: AgentRunner | None = None) -> None:
        self.agent_runner=agent_runner
        self.instantiator=VariableInstantiationEngine()
        self.preconditions=PreconditionEngine()
        self.handlers={"Category_1":Category1Handler(),"Category_2":Category2Handler(),"Category_3":Category3Handler(),"Category_4":Category4Handler()}

    def run(self, benchmark_json: Path, ocel_path: Path, mode: str = "reference-only", output_dir: Path | None = None, api_base_url: str | None = None, verbose: bool = False) -> OrchestratorResult:
        model=load_ocel(ocel_path); templates=load_templates_from_file(benchmark_json)
        rows=[]
        for template in templates:
            try: instances=self.instantiator.instantiate_template(template, model)
            except Exception: instances=[]
            if not instances:
                continue
            for index, instance in enumerate(instances, start=1):
                row=empty_row(); row.update({"question_id": f"{template.template_id}-{index}","template_id":template.template_id,"category":template.category,"formal_pattern":template.formal_pattern,"instantiated_question":instance.analyst_question,"runtime_variables_used":instance.runtime_variables_used,"expected_tool_chain":"|".join(tool.tool for tool in template.evaluation_logic.expected_tool_chain),"target_metric":template.evaluation_logic.mathematical_assertion.target_metric,"lookup_path":instance.lookup_path,"metric_definition":template.evaluation_logic.mathematical_assertion.target_metric,"reference_source":"clean-room ReferenceModel","graph_source":"directly_follows_edges","used_graph":True,"used_pm4py":False,"error_or_skip_reason":None,"ocel_path":Path(ocel_path).as_posix(),"benchmark_path":Path(benchmark_json).as_posix(),"agent_status":"not_run","actual_tool_chain":[],"tool_chain_alignment_score":None,"llm_response":None,"response_contains_reference":None,"used_llm":False,"used_agent":False,"mode":mode})
                status, precondition_results=self.preconditions.evaluate_all(template.preconditions, model, instance.runtime_variables_used)
                row["preconditions_status"]=status; row["precondition_messages"]="|".join(r.explanation for r in precondition_results)
                if status != "passed":
                    row.update({"final_status":"skipped","reference_status":"skipped","reference_value":None,"reference_message":"preconditions did not pass"})
                else:
                    handler=self.handlers.get(template.category)
                    if instance.runtime_variables_used.get("$SIGMA") == "none":
                        result={"status":"unsupported","value":None,"message":"Unsupported aggregation 'none'"}
                        final_status="skipped_unsupported_metric"
                        row["error_or_skip_reason"]="Unsupported aggregation 'none'"
                    else:
                        result=execute_reference_metric(template, model, instance.runtime_variables_used, self.handlers)
                        if result["status"] == "success" and result["value"] is not None:
                            final_status="computed"
                        elif result["status"] == "success":
                            result["status"]="failed"
                            final_status="skipped_no_valid_variables"
                            row["error_or_skip_reason"]=result["message"]
                        else:
                            final_status="skipped"
                            row["error_or_skip_reason"]=result["message"]
                    row.update({"reference_status":result["status"],"reference_value":result["value"],"reference_message":result["message"],"final_status":final_status})
                if mode == "agent-comparison":
                    runner=self.agent_runner or AgentRunner(api_base_url=api_base_url, ocdfg_id="standalone")
                    expected=tuple(tool.tool for tool in template.evaluation_logic.expected_tool_chain)
                    asyncio.run(runner.enrich(row, expected))
                rows.append(row)
        output_dir=Path(output_dir or "evaluation/reports"); output_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path=output_dir/"benchmark_results.jsonl"; csv_path=output_dir/"benchmark_results.csv"; summary_path=output_dir/"benchmark_summary.json"
        jsonl_path.write_text("".join(json.dumps(row, sort_keys=True)+"\n" for row in rows), encoding="utf-8")
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer=csv.DictWriter(handle, fieldnames=RESULT_FIELDS); writer.writeheader(); writer.writerows(rows)
        summary={"row_count":len(rows),"jsonl_line_count":len(rows),"csv_data_line_count":len(rows),"mode":mode}
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        if verbose:
            print(f"terminal status rows: {len(rows)}")
        return OrchestratorResult(rows, jsonl_path, csv_path, summary_path)
