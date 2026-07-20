from __future__ import annotations
import json
from pathlib import Path
from evaluation.ingestion.ocel_loader import load_ocel
from evaluation.handlers.category_1 import Category1Handler
from evaluation.templates.instantiation_engine import VariableInstantiationEngine
from evaluation.preconditions.engine import PreconditionEngine

class BenchmarkDryRun:
    def run(self, benchmark_path, ocel_path, templates, output_paths=(), write_outputs: bool = True):
        model=load_ocel(ocel_path)
        print("OCPM Benchmark Dry-Run Trace")
        print(f"benchmark JSON path: {benchmark_path}")
        print(f"OCEL path: {ocel_path}")
        print(f"number of templates loaded: {len(templates)}")
        print("loaded template IDs: [" + ", ".join(t.template_id for t in templates) + "]")
        print("loaded object types: [" + ", ".join(sorted(model.object_types)) + "]")
        print("loaded activities: [" + ", ".join(sorted(model.activities)) + "]")
        print("generated variable candidates:")
        engine=VariableInstantiationEngine(); preconditions=PreconditionEngine(); handler=Category1Handler()
        report={"benchmark_path": str(benchmark_path), "ocel_path": str(ocel_path), "template_count": len(templates), "templates": [t.template_id for t in templates]}
        for template in templates:
            instances=engine.instantiate_template(template, model)
            print(f"instantiated variables: {len(instances)}")
            if instances:
                status, results=preconditions.evaluate_all(template.preconditions, model, instances[0].runtime_variables_used)
                print("precondition evaluation outcomes: " + status)
                print("selected reference handler: Category1Handler")
                print("reference result: " + str(handler.execute(template.analyst_question_template, model, instances[0].runtime_variables_used)))
        print("final output paths: " + ", ".join(str(path) for path in output_paths))
        if write_outputs:
            for path in output_paths:
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                Path(path).write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        return report
