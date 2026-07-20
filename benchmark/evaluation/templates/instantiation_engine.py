from __future__ import annotations
from dataclasses import dataclass
from itertools import product

class VariableResolutionError(ValueError):
    pass

@dataclass(frozen=True)
class VariableDefinition:
    name: str
    values: tuple[str, ...]

@dataclass(frozen=True)
class BenchmarkInstance:
    template_id: str
    category: str
    analyst_question: str
    runtime_variables_used: dict[str, str]
    preconditions: tuple[str, ...]
    lookup_path: str
    mathematical_assertion: dict[str, object]

class VariableInstantiationEngine:
    def resolve_variable(self, variable: str, model) -> VariableDefinition:
        if variable in {"$OT_A", "$OT_B"}:
            return VariableDefinition(variable, tuple(model.object_types))
        if variable in {"$ACT_X", "$ACT_Y"}:
            return VariableDefinition(variable, tuple(model.activities))
        if variable == "$SIGMA":
            return VariableDefinition(variable, ("avg", "min", "max", "sum", "none"))
        raise VariableResolutionError(f"Unsupported runtime variable {variable}")

    def instantiate_template(self, template, model):
        variables=list(template.runtime_variables)
        definitions=[self.resolve_variable(variable, model) for variable in variables]
        if not definitions:
            combos=[()]
        else:
            combos=product(*(definition.values for definition in definitions))
        instances=[]
        for combo in combos:
            bindings=dict(zip(variables, combo))
            if "$OT_A" in bindings and "$OT_B" in bindings and bindings["$OT_A"] == bindings["$OT_B"]:
                continue
            question=template.analyst_question_template
            lookup=template.evaluation_logic.mathematical_assertion.lookup_path
            preconditions=list(template.preconditions)
            for key, value in bindings.items():
                question=question.replace(key, value)
                lookup=lookup.replace(key, value)
                preconditions=[expr.replace(key, value) for expr in preconditions]
            assertion=template.evaluation_logic.mathematical_assertion.model_dump()
            assertion["lookup_path"]=lookup
            instances.append(BenchmarkInstance(template.template_id, template.category, question, bindings, tuple(preconditions), lookup, assertion))
        return instances
