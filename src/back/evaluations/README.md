# Irina Governance Evaluation Lab

A synthetic-first, evidence-producing evaluation lab for Irina. It evaluates
Irina's LLM, Memory, Tools, and Environment behavior against twelve governance
concerns without needing external datasets, live financial feeds, confidential
corpora, or production user data.

The lab is **additive**. It does not replace or modify Irina's harness,
providers, memory, sessions, sandbox, policy path, or Opik tracing. Production
authorization remains outside this package.

---

## 1. What problem this solves

A model answer that looks correct can hide unauthorized actions, stale
evidence, fabricated citations, or failed controls. This lab therefore evaluates
three levels:

1. **Final output** - was the answer correct, relevant, grounded, and safe?
2. **Trajectory** - which tools, memory operations, approvals, and policy
   decisions led to the answer?
3. **Controls** - did the enforcement layer actually deny, escalate, retrieve,
   preserve, or delete what it claimed?

It produces evidence, not a compliance certificate. Reports distinguish
`implemented`, `partial`, `blocked`, and `not_applicable`; a blocked item is
never counted as a pass.

---

## 2. High-level architecture

```text
WorldFactory(seed)
    |
    +--> fictional companies, filings, amendments, future/confidential docs
    +--> time machine (published / available / effective / ingested / as_of)
    +--> retrieval corpus (chunks, relevance, ACLs, hard negatives)
    +--> memories, policy rules, tool mocks, fault fixtures
    |
    v
Datasets DS01..DS16  (candidate -> validated -> reviewed -> frozen)
    |
    v
IrinaRunner
    +--> L1 reference responder (deterministic, no model)
    +--> L2 real Harness + ScriptedProvider / synthetic inputs
    |
    v
Checks + oracles
    +--> deterministic math, retrieval IR, temporal filter, memory reducer,
         policy table, effect ledger
    +--> Opik-native / custom judges where no deterministic oracle exists
    |
    v
EvaluationResult (value | undefined_reason, numerator, denominator, level)
    |
    +--> JSON + Markdown report
    +--> coverage matrix (12 concerns x 4 pillars)
    +--> Opik traces/datasets (experiments/feedback scores not wired yet)
```

The evaluator never lets a model write its own answer key. Expected outcomes
come from deterministic oracles or human review.

---

## 3. Directory map

```text
src/back/evaluations/
  configs/metric_dictionary.yaml   registered metrics and semantics
  metrics/                         MetricValue, calculators, dictionary loader
  contracts/                       versioned records and evidence levels
  worlds/                          deterministic synthetic finance world
  oracles/                         independent answer keys
  datasets/                        DS catalog and case generation
  checks/                          deterministic checks + claim/audit helpers
  runners/                         L1 reference runner, L2 Harness runner
  reporting/                       JSON / Markdown report builder
  governance/                      12-concern coverage matrix
  opik_adapter/                    local Opik trace/dataset integration
  rag_fixture/                     disposable retrieval tool (test-only)
  run_core.py                      CLI entry point for the core suite
  implementation_manifest.yaml     checkpoints, blockers, rollback
  README.md                        this document
```

---

## 4. Evidence model

### Evidence levels

| Level | Meaning | Allowed claim |
|---|---|---|
| `L0_oracle_unit` | Pure world/oracle tests | Oracle/fixture behavior only |
| `L1_simulated_workflow` | Scripted or reference response | Simulated behavior only |
| `L2_irina_integrated` | Real Harness path, synthetic inputs/mocked effects | Tested Irina path |
| `L3_production_observed` | Real runtime telemetry | Observed behavior, not correctness |

### Status vocabulary

- `implemented` - runnable and tested.
- `partial` - some checks run; gaps documented.
- `blocked` - depends on a missing control/policy/identity/API.
- `not_applicable` - architecture does not have the capability (e.g. tenancy).
- `planned` - designed but not implemented.

### Dataset dependency

- **D** - needs labeled cases/expected outcomes to compute the metric.
- **C** - can score without labels, but needs reviewed calibration data before
  its thresholds are trusted.
- **N** - needs only traces, config, events, or metadata; no gold dataset.
- **B** - standard benchmark test set and scorer.

Timing: `OFF` (offline/CI), `ON-S` (synchronous runtime gate), `ON-A`
(asynchronous sampled judge), `ON-T` (runtime telemetry).

---

## 5. Metric math

Every metric stores value **or** an explicit undefined reason, plus numerator,
denominator, sample size, versions, and evidence level. Undefined is never 0 or
1.

| Family | Formula / meaning | Undefined when |
|---|---|---|
| `RATE` | matching / eligible | eligible = 0 |
| `P_AT_K` | hits in top-k / k | k = 0 |
| `R_AT_K` | hits in top-k / relevant | no relevant items |
| `MRR` | mean 1/rank of first relevant | no answerable queries |
| `NDCG` | DCG@k / IDCG@k | ideal gain = 0 |
| `COUNT` | qualifying events | telemetry incomplete |
| `PAIR` | unjustified pair differences / pairs | no matched pairs |
| `COMP_RATIO` | tokens_after / tokens_before | before = 0 |
| `JUDGE` | rubric-defined score | rubric/judge unverified |
| `BINARY` / `LABEL` | predicate / categorical outcome | missing policy or field |
| `HASH` | canonical SHA-256 equality | missing digest |
| `ACCURACY` / `P/R/F1/FNR` | classification counts | denominator = 0 |

Claim-specific rules:

- `claim_citation_coverage = cited material claims / material claims`; zero
  material claims → undefined.
- `citation_resolution_rate = resolvable citations / cited refs`; zero
  citations → undefined.
- `claim_support_rate`, `contradicted_claim_rate`,
  `unsupported_material_claim_rate`; zero material claims → undefined.
- `numeric_exact_accuracy` uses Decimal tolerance; wrong unit or period is
  incorrect regardless of numeric closeness.

---

## 6. Registered metrics (49)

`implemented` means the metric is computed by the current core suite or helper
with tests. `planned`/`blocked` are honest gaps.

| Metric ID | Pillar | Formula | Dep | Datasets | Status |
|---|---|---|---|---|---|
| `llm.answer_relevance` | llm | JUDGE | C | DS01, DS14 | planned |
| `llm.task_completion` | llm | RATE | C | DS01, DS06, DS14 | implemented |
| `llm.hallucination_faithfulness` | llm | JUDGE | C | DS03, DS14 | planned |
| `llm.abstention_accuracy` | llm | RATE | D | DS01 | implemented |
| `llm.claim_citation_coverage` | llm | RATE | N | DS03 | implemented |
| `llm.citation_resolution_rate` | llm | RATE | N | DS03 | implemented |
| `llm.claim_support_rate` | llm | RATE | C | DS03, DS14 | implemented |
| `llm.unsupported_material_claim_rate` | llm | RATE | C | DS03, DS14 | implemented |
| `llm.contradicted_claim_rate` | llm | RATE | C | DS03, DS14 | implemented |
| `llm.numeric_exact_accuracy` | llm | RATE | D | DS04 | implemented |
| `llm.refusal_escalation_correctness` | llm | RATE | D | DS05 | implemented |
| `llm.required_disclosure_presence` | llm | BINARY | N | DS05 | planned |
| `llm.prompt_injection_success_rate` | llm | RATE | D | DS09 | planned |
| `llm.bias_judge` | llm | JUDGE | C | DS10, DS14 | planned |
| `llm.fairness_pair_disparity` | llm | PAIR | D | DS10 | implemented |
| `memory.retrieval_precision_at_k` | memory | P_AT_K | D | DS07 | planned |
| `memory.retrieval_recall_at_k` | memory | R_AT_K | D | DS07 | planned |
| `memory.retrieval_mrr` | memory | MRR | D | DS07 | planned |
| `memory.retrieval_ndcg` | memory | NDCG | D | DS07 | planned |
| `memory.write_accuracy` | memory | RATE | D | DS08 | planned |
| `memory.preservation_recall` | memory | RATE | D | DS08 | planned |
| `memory.compaction_ratio` | memory | COMP_RATIO | N | DS08 | planned |
| `tools.tool_selection_accuracy` | tools | RATE | D | DS06 | planned |
| `tools.parameter_correctness` | tools | RATE | D | DS06 | planned |
| `tools.trajectory_validity` | tools | RATE | D | DS06 | planned |
| `tools.tool_schema_validity` | tools | BINARY | N | DS06 | planned |
| `tools.approval_compliance_rate` | tools | RATE | N | DS05 | implemented |
| `tools.unauthorized_execution_count` | tools | COUNT | N | DS05 | implemented |
| `tools.policy_bypass_success_rate` | tools | RATE | D | DS05, DS09 | planned |
| `tools.retrieval_precision_at_k` | tools | P_AT_K | D | DS02 | implemented |
| `tools.retrieval_recall_at_k` | tools | R_AT_K | D | DS02 | implemented |
| `tools.retrieval_mrr` | tools | MRR | D | DS02 | implemented |
| `tools.retrieval_ndcg` | tools | NDCG | D | DS02 | implemented |
| `tools.lookahead_violation_count` | tools | COUNT | N | DS12 | implemented |
| `environment.extraction_field_accuracy` | environment | RATE | D | DS11 | implemented |
| `environment.index_coverage` | environment | RATE | D | DS11 | planned |
| `environment.historical_snapshot_accuracy` | environment | RATE | D | DS12 | implemented |
| `environment.availability_violation_count` | environment | COUNT | N | DS12 | planned |
| `environment.corpus_index_reproducibility` | environment | HASH | N | DS12 | planned |
| `environment.fault_recovery_rate` | environment | RATE | D | DS13 | planned |
| `environment.safe_degradation_correctness` | environment | RATE | D | DS13 | planned |
| `environment.governance_event_completeness` | environment | RATE | N | DS15 | implemented |
| `environment.trace_correlation_rate` | environment | LABEL | N | DS15 | implemented |
| `environment.evidence_integrity_version_binding` | environment | HASH | N | DS15 | implemented |
| `environment.pii_redaction_detection_accuracy` | environment | RATE | D | DS09, DS14 | planned |
| `calibration.judge_precision` | llm | PRECISION | D | DS14 | planned |
| `calibration.judge_recall` | llm | RECALL | D | DS14 | planned |
| `calibration.judge_fnr` | llm | FNR | D | DS14 | planned |
| `calibration.agreement_rate` | llm | ACCURACY | D | DS14 | planned |

---

## 7. Datasets

| ID | Purpose | Current state |
|---|---|---|
| DS01 | Financial Q&A gold | implemented |
| DS02 | RAG relevance gold | implemented |
| DS03 | Atomic claim gold | implemented |
| DS04 | Financial calculation gold | implemented |
| DS05 | Policy/authorization gold | implemented (fixture approvals) |
| DS06 | Tool choice/trajectory gold | planned |
| DS07 | Memory retrieval gold | planned |
| DS08 | Memory lifecycle gold | planned |
| DS09 | Injection/adversarial gold | planned |
| DS10 | Fairness paired gold | implemented |
| DS11 | Ingestion/index gold | implemented (core extraction only) |
| DS12 | Temporal RAG gold | implemented (core cases) |
| DS13 | Resilience/security gold | planned |
| DS14 | Judge calibration gold | planned (no human labels yet) |
| DS15 | Synthetic runtime telemetry | helpers implemented; full suite planned |
| DS16 | Benchmark cache | planned/blocked (no verified local benchmark cache) |

Each case records provenance, seed, dataset version, expected behavior, severity,
oracle type, and review status. Generated expectations never enter release gates
without human review.

---

## 8. Implemented checks

Deterministic (`checks/`):

- Answer correctness and abstention (`DS01`).
- Retrieval precision/recall/MRR/NDCG (`DS02`).
- Claim support/citation coverage/resolution/contradiction (`DS03`).
- Decimal numeric accuracy (`DS04`).
- Policy allow/reject/escalate (`DS05`).
- Approval-before-effect and unauthorized execution (`DS05` fixtures).
- Fairness matched-pair disparity (`DS10`).
- Field extraction (`DS11`).
- Point-in-time snapshot and lookahead (`DS12`).
- Audit completeness, trace correlation, evidence hash.

The L2 runner executes the real `Harness` with a `ScriptedProvider`; it proves
the harness path without calling a model or external system.

---

## 9. Runtime span tracing

When `IRINA_OPIK_ENABLED=1` and local Opik is reachable, each `Harness.run`
creates per-pillar traces under one thread:

| Trace | Spans |
|---|---|
| `irina:llm` | `model.routing`, `assistant.turn.<n>`, `llm` (usage/model/provider) |
| `irina:memory` | `memory.retrieve` (items/scores), `memory.update`, `memory.compaction` (summary) |
| `irina:tools` | `tool.<name>` with args, result, failure |
| `irina:environment` | `env.setup`, `policy.check`, `approval.request`, `sandbox.*`, `export.artifacts`, `skills.sync`, `session.append`, `run.end` |

Thread id = session id, `IRINA_TRACE_THREAD`, or `Irina`. Spans are written after
the run with explicit start/end times, avoiding Opik's create/update race.
Subagent traces carry `parent_run_id` metadata.

Still uninstrumented: provider internal retries, direct OpenAI calls in vendored
memory, OS/library internals, CLI startup/banner/shutdown.

---

## 10. Opik integration

Implemented:

- Flat evaluation traces (`eval:<case_id>`) with input/output/metadata.
- Dataset creation attempt (`irina-core-<dataset_version>`).
- Runtime per-pillar traces and spans.

Not implemented yet:

- **Experiments** and **feedback scores**, so dataset metrics are not yet
  dashboard columns.
- Online evaluation, guardrails, alerts (deployment-gated).
- DeepEval metric adapter and benchmark lane.

---

## 11. Run and test

```powershell
uv run python -m src.back.evaluations.run_core --seed 7 --out reports/core
uv run python -m src.back.evaluations.run_core --seed 7 --out reports/core --opik

$env:IRINA_MEMORY_ENABLED="0"
uv run python -m unittest tests.test_eval_metrics tests.test_eval_world `
  tests.test_eval_rag tests.test_eval_suite tests.test_eval_harness `
  tests.test_eval_opik_adapter
```

Outputs: `evaluation_report.json`, `evaluation_report.md`, `coverage.json`.

---

## 12. Adding a metric, dataset, or check

1. **Metric**: add one atomic entry to `configs/metric_dictionary.yaml`; include
   dependency, formula, datasets, modes, undefined rule, owner, status.
2. **Dataset**: add cases in `datasets/catalog.py` with provenance and expected
   behavior; never invent gold answers without an oracle or reviewer.
3. **Check**: implement in `checks/`, return `MetricValue` with numerator,
   denominator, undefined reason, and evidence level.
4. **Runner**: add a branch in `runners/reference.py` (or a new runner).
5. **Tests**: add positive, negative, undefined, and mutation cases.
6. **Checkpoint**: update `implementation_manifest.yaml`; commit only that slice.

---

## 13. Honest limitations

- Synthetic fixtures are fictional; they do not prove real-market accuracy,
  legal compliance, population fairness, or production enforcement.
- Reference-responder results are L1 evidence.
- RAG is a disposable fixture, not Irina's production retrieval.
- No approval identity/workflow, runtime policy gate, retention system, or
  tenancy exists yet; related metrics remain `blocked` or `not_applicable`.
- No human calibration set (DS14); judge-based thresholds are not trustworthy.
- No experiments/feedback scores in Opik yet.
- No benchmark lane; no benchmark result is used for governance passes.
