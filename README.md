## Motivation

LLM-based assistants can make process-mining systems easier to use by allowing users to ask questions in natural language. However, this is only useful in practice if their answers remain grounded in the actual process data.

In process mining, small factual errors are not harmless. A wrong frequency, an incorrect reachability statement, or a fabricated bottleneck can lead to wrong operational conclusions. For this reason, benchmark questions should be tied to deterministic graph properties rather than evaluated only by subjective judgement.

This benchmark therefore uses mathematical OC-DFG/OCPM structures as its foundation. Each template describes a graph-based query pattern that can be instantiated for a concrete OCEL log and checked against a deterministic reference value.

The goal is to create a reusable reference layer for later evaluation of LLM or agent responses.

---

## Core Idea

The benchmark separates two concerns:

1. **Reference generation**  
   Compute deterministic ground-truth values from OCEL/OC-DFG data.

2. **Agent evaluation**  
   Later compare LLM or agent answers and tool traces against those deterministic reference values.

The current repository focuses on the first part: deterministic reference generation.

---

## Why Mathematical Templates?

Free-form analyst questions are useful for user studies, but they are difficult to evaluate systematically. Similar questions can be phrased in many different ways, and it is often unclear which exact graph property should be used as the reference.

This benchmark starts from graph-structure templates instead.

A template is an abstract mathematical query pattern, for example:

```text
Which directed transitions have positive $SIGMA waiting time for object type $OT_A?

For a concrete OCEL log, runtime variables are replaced with values from the log:

```text
$OT_A = orders
$SIGMA = avg
```

This produces a concrete benchmark question:

> Which directed transitions have positive avg waiting time for object type orders?

Because the underlying reference target is explicit, the expected answer can be computed deterministically from the graph representation.

## Benchmark Structure

The benchmark contains 100 templates.

Each template may contain:

- a stable template identifier
- a benchmark category
- a formal graph pattern
- runtime variables
- preconditions
- an analyst-facing question template
- an expected tool-chain specification for future agent evaluation
- a deterministic mathematical assertion
- a symbolic lookup path for the reference value

## Evaluation Dimensions

The templates are organized along three evaluation dimensions.

### Factual Correctness

The benchmark should make it possible to check whether an answer contains the correct numerical or structural value.

### Completeness

The benchmark should make it possible to check whether the relevant object type, activity, edge, path, or multi-object context is included.

### Robustness

The benchmark should include structurally different cases, edge cases, and variants that test whether a system remains stable under different graph situations.

## Benchmark Categories

The 100 templates are grouped according to the mathematical structure of the underlying OC-DFG/OCPM question.

### Category 1: Local Node and Activity Metrics

These templates test local properties of individual activities from the perspective of a selected object type.

Typical metrics include:

- in-degree
- out-degree
- node weight
- start frequency
- end frequency
- object frequency

Example question pattern:

> What is the end frequency of activity $ACT_X for object type $OT_A?

### Category 2: Edge and Temporal Metrics

These templates focus on directly-follows relations between activities.

Typical metrics include:

- edge weight
- edge duration
- waiting time
- lead time
- aggregated temporal values such as sum, avg, min, and max

Example question pattern:

> Which directed transitions have positive $SIGMA waiting time for object type $OT_A?

### Category 3: Path Structures and Reachability

These templates test graph-theoretic reasoning over the OC-DFG beyond single nodes or direct edges.

Typical structures include:

- path existence
- direct reachability
- indirect reachability
- transitive closure
- shortest path distance
- loops
- reachable activity sets

Example question pattern:

> Is activity $ACT_Y reachable from activity $ACT_X for object type $OT_A?

### Category 4: Multi-Object Interaction Patterns

These templates address the object-centric part of the benchmark.

Typical structures include:

- object-type co-occurrence
- activity-level co-occurrence
- convergence patterns
- divergence patterns
- synchronization-related structures
- multi-object interaction counts

Example question pattern:

> Which activities involve multiple object types or show object-type interaction patterns?

## Template Instantiation

Templates are abstract. They become concrete benchmark instances only after their runtime variables are replaced with values from an OCEL-derived reference model.

Common runtime variables include:

| Variable | Meaning | Domain |
| --- | --- | --- |
| `$OT_A`, `$OT_B` | object types | object types found in the OCEL |
| `$ACT_X`, `$ACT_Y`, `$ACT_Z` | activities | activity labels found in the OCEL |
| `$SIGMA` | aggregation function | supported aggregations such as sum, avg, min, max |
| `$NET_ATT` | numerical attribute | numerical event or edge attributes, if available |

A single template can generate many concrete candidate questions.

For example, a template with one object-type variable and two activity variables can generate:

```text
|object_types| x |activities| x |activities|
```

candidate instances before precondition filtering.

## Preconditions

Preconditions ensure that only meaningful template instances are evaluated.

Examples of preconditions include:

- the selected object type exists
- the selected activity exists
- the selected object type has related events
- enough activities exist for edge or path queries
- timestamps exist for temporal metrics
- numerical attributes exist for attribute-based metrics

If a precondition fails, the candidate should not be interpreted as a wrong answer. It is simply not a valid benchmark instance for the current OCEL log.

## Reference-Only Evaluation

The current implementation focuses on deterministic reference generation.

In reference-only mode, the system does not call an LLM or an agent. Instead, it computes the expected value directly from the OCEL/OC-DFG representation.

The reference-only path can be summarized as:

```text
Load benchmark templates
-> load OCEL/reference model
-> instantiate runtime variables
-> evaluate preconditions
-> select category-specific handler
-> compute reference value
-> write result row
```

The output can be used later as the ground-truth layer for agent evaluation.

## Current Status

Implemented or documented:

- 100-template benchmark catalog
- mathematical template structure
- runtime-variable instantiation concept
- precondition-based validation
- deterministic reference-value generation concept
- graph-based benchmark categories

Not claimed as complete yet:

- real LLM or agent endpoint execution
- factual answer comparison against LLM output
- tool-trace capture
- formal G_factual implementation
- formal F_tool implementation
- complete real-agent benchmark execution

## Planned Extensions

Future work may include:

- connecting the benchmark runner to a real FastAPI/LangGraph agent endpoint
- storing real LLM or agent responses
- capturing actual tool traces
- implementing factual correctness scoring
- implementing tool-chain alignment scoring
- running full end-to-end agent evaluations against the deterministic reference layer

## Authorship and Reuse

This repository documents the initial OCPM 100 Template Benchmark concept, template catalog, and reference-generation approach by Stephanie Motz.

If you reuse the template structure, benchmark categories, runtime-variable instantiation approach, reference-generation logic, documentation, or code, please cite this repository.
