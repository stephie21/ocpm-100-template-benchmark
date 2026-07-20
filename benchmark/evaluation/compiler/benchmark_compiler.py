from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from evaluation.handlers.category_1 import Category1Handler
from evaluation.handlers.category_2 import Category2Handler
from evaluation.handlers.category_3 import Category3Handler
from evaluation.handlers.category_4 import Category4Handler
from evaluation.handlers.dispatch import execute_reference_metric
from evaluation.ingestion.ocel_loader import load_ocel
from evaluation.preconditions.engine import PreconditionEngine
from evaluation.schemas.benchmark import BenchmarkTemplate
from evaluation.templates.instantiation_engine import BenchmarkInstance, VariableInstantiationEngine

class BenchmarkDataset(BaseModel):
    source_log_path: str
    template_count: int
    instance_count: int
    object_types: list[str]
    activities: list[str]
    instances: list[BenchmarkInstance]

    @classmethod
    def model_validate(cls, data):
        if isinstance(data, cls): return data
        instances=[]
        for item in data.get("instances", []):
            if isinstance(item, BenchmarkInstance): instances.append(item)
            else: instances.append(BenchmarkInstance(**item))
        return cls(source_log_path=data["source_log_path"], template_count=data["template_count"], instance_count=data["instance_count"], object_types=list(data["object_types"]), activities=list(data["activities"]), instances=instances)

class EvaluationRecord(BaseModel):
    template_id: str
    category: str
    instantiated_question: str
    runtime_variables_used: dict[str, str]
    precondition_status: str
    handler_status: str
    value: Any
    messages: list[str]

class EvaluationReport(BaseModel):
    summary: dict[str, int]
    details: list[EvaluationRecord]

    @classmethod
    def model_validate(cls, data):
        if isinstance(data, cls): return data
        return cls(summary=dict(data["summary"]), details=[EvaluationRecord.model_validate(item) for item in data["details"]])

def load_templates_from_file(path: Path) -> list[BenchmarkTemplate]:
    raw=json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict): raw=[raw]
    return [BenchmarkTemplate.model_validate(item) for item in raw]

class BenchmarkCompiler:
    def __init__(self):
        self.instantiator=VariableInstantiationEngine()
        self.preconditions=PreconditionEngine()
        self.handlers={"Category_1": Category1Handler(), "Category_2": Category2Handler(), "Category_3": Category3Handler(), "Category_4": Category4Handler()}

    def compile(self, log_path: Path, templates: list[BenchmarkTemplate]) -> BenchmarkDataset:
        model=load_ocel(log_path)
        instances=[]
        for template in templates:
            instances.extend(self.instantiator.instantiate_template(template, model))
        return BenchmarkDataset(source_log_path=Path(log_path).as_posix(), template_count=len(templates), instance_count=len(instances), object_types=list(model.object_types), activities=list(model.activities), instances=instances)

    def write_dataset(self, dataset: BenchmarkDataset, output_path: Path) -> None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(dataset.model_dump_json()+"\n", encoding="utf-8")

    def evaluate(self, log_path: Path, templates: list[BenchmarkTemplate]) -> EvaluationReport:
        model=load_ocel(log_path)
        records=[]
        for template in templates:
            try:
                instances=self.instantiator.instantiate_template(template, model)
            except Exception as exc:
                records.append(EvaluationRecord(template_id=template.template_id, category=template.category, instantiated_question=template.analyst_question_template, runtime_variables_used={}, precondition_status="unsupported", handler_status="skipped", value=None, messages=[str(exc)]))
                continue
            for instance in instances or [BenchmarkInstance(template.template_id, template.category, template.analyst_question_template, {}, tuple(template.preconditions), template.evaluation_logic.mathematical_assertion.lookup_path, template.evaluation_logic.mathematical_assertion.model_dump())]:
                status, results=self.preconditions.evaluate_all(template.preconditions, model, instance.runtime_variables_used)
                if status != "passed":
                    records.append(EvaluationRecord(template_id=template.template_id, category=template.category, instantiated_question=instance.analyst_question, runtime_variables_used=instance.runtime_variables_used, precondition_status=status, handler_status="skipped", value=None, messages=[r.explanation for r in results]))
                    continue
                handler=self.handlers.get(template.category)
                if not handler:
                    records.append(EvaluationRecord(template_id=template.template_id, category=template.category, instantiated_question=instance.analyst_question, runtime_variables_used=instance.runtime_variables_used, precondition_status=status, handler_status="unsupported", value=None, messages=["No handler for category"]))
                    continue
                result=execute_reference_metric(template, model, instance.runtime_variables_used, self.handlers)
                if result["status"] == "success" and result["value"] is None:
                    result = {"status": "skipped", "value": None, "message": result["message"]}
                records.append(EvaluationRecord(template_id=template.template_id, category=template.category, instantiated_question=instance.analyst_question, runtime_variables_used=instance.runtime_variables_used, precondition_status=status, handler_status=result["status"], value=result["value"], messages=[result["message"]]))
        summary={"total_templates": len(templates), "total_records": len(records), "passed": sum(1 for r in records if r.precondition_status=="passed" and r.handler_status=="success" and r.value is not None), "failed": sum(1 for r in records if r.handler_status=="error"), "skipped": sum(1 for r in records if r.precondition_status!="passed" or r.handler_status in {"skipped", "unsupported"} or (r.handler_status=="success" and r.value is None))}
        return EvaluationReport(summary=summary, details=records)
