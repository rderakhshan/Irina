# Irina Governance Evaluation Lab

Additive, synthetic-first evaluation lab for Irina. It does not change the
harness, providers, memory, sessions, sandbox, or production policy path.

## What works now (offline, no network)

- Typed metric dictionary and deterministic calculators
  (`configs/metric_dictionary.yaml`, `metrics/`): 46 registered metrics,
  undefined-value contract, boundary tests.
- Versioned evaluation contracts and evidence levels (`contracts/`).
- Seeded synthetic finance world (`worlds/factory.py`):
  fictional companies, filings, amendments, future/confidential documents,
  chunks, memories, policy rules, and time semantics.
- Independent oracles (`oracles/`): Decimal finance, retrieval IR metrics,
  point-in-time filtering, memory transitions, policy decisions, effect ledger.
- Disposable RAG fixture (`rag_fixture/`): in-memory BM25-style retrieval with
  time and ACL filtering. Test-only; delete the folder to remove it.
- Core datasets: **DS01, DS02, DS03, DS04, DS05, DS10, DS11, DS12**
  (`datasets/catalog.py`).
- Deterministic checks (`checks/`):
  - answers/abstention, numerics, policy decisions, extraction, lookahead;
  - claim-level: `claim_citation_coverage`, `citation_resolution_rate`,
    `claim_support_rate`, `contradicted_claim_rate`,
    `unsupported_material_claim_rate`;
  - approval: `approval_compliance_rate`, `unauthorized_execution_count`;
  - fairness: `fairness_pair_disparity`;
  - audit: `governance_event_completeness`, `trace_correlation_rate`,
    `evidence_integrity_version_binding`.
- Reference runner (`runners/reference.py`) and L2 harness runner with a
  scripted model (`runners/harness_runner.py`).
- JSON + Markdown reports and a 12-concern coverage matrix
  (`reporting/`, `governance/`).
- Best-effort local Opik adapter (`opik_adapter/`): traces with input/output,
  dataset attempt. Experiments/feedback scores are not wired yet.

## Calculated metrics (core suite)

- `llm.task_completion`, `llm.abstention_accuracy`,
  `llm.refusal_escalation_correctness`, `llm.numeric_exact_accuracy`
- `llm.claim_citation_coverage`, `llm.citation_resolution_rate`,
  `llm.claim_support_rate`, `llm.contradicted_claim_rate`,
  `llm.unsupported_material_claim_rate`
- `llm.fairness_pair_disparity`
- `tools.retrieval_precision_at_k`, `tools.retrieval_recall_at_k`,
  `tools.retrieval_mrr`, `tools.retrieval_ndcg`,
  `tools.lookahead_violation_count`
- `tools.approval_compliance_rate`, `tools.unauthorized_execution_count`
- `environment.historical_snapshot_accuracy`,
  `environment.extraction_field_accuracy`
- Audit helpers: `environment.governance_event_completeness`,
  `environment.trace_correlation_rate`,
  `environment.evidence_integrity_version_binding`

## Run

```powershell
python -m src.back.evaluations.run_core --seed 7 --out reports/core
# optional mirror to local Opik (traces + dataset attempt)
python -m src.back.evaluations.run_core --seed 7 --out reports/core --opik
```

Reports:
- `evaluation_report.json`
- `evaluation_report.md`
- `coverage.json`

## Tests

```powershell
$env:IRINA_MEMORY_ENABLED="0"
python -m unittest tests.test_eval_metrics tests.test_eval_world `
  tests.test_eval_rag tests.test_eval_suite tests.test_eval_harness `
  tests.test_eval_opik_adapter
```

## Evidence honesty

- Reference-responder results are `L1_simulated_workflow`, not model behavior.
- The scripted harness run is `L2_irina_integrated` with a mocked model.
- The RAG fixture is not production retrieval.
- `blocked` and `not_applicable` items are never counted as passes.
- No report claims legal or regulatory compliance.

## Not implemented yet

- DS06 tools, DS07/DS08 memory, DS09 injection, DS13 resilience,
  DS14 calibration, DS15 full audit telemetry, DS16 benchmarks.
- Opik experiments and feedback scores (dataset-backed metrics are not yet
  dashboard columns).
- Real runtime policy gate, approval workflow/identity, retention, tenancy.
- DeepEval adapters and benchmark lane (not installed/verified).
- Online evaluation, guardrails, and alerts (deployment-gated).

See `implementation_manifest.yaml` for checkpoints, blockers, and next tasks.

## Runtime span tracing

When `IRINA_OPIK_ENABLED=1` and the local Opik stack is reachable, each
`Harness.run` creates per-pillar traces under one thread:

- `irina:llm` - model routing, assistant turns, and `llm` spans
  (usage/model/provider).
- `irina:memory` - retrieval items, update, compaction summary.
- `irina:tools` - tool spans with args/results/failures.
- `irina:environment` - setup, policy checks, approvals, sandbox operations,
  exports, skills sync, session writes, run end.

Thread id = session id, or `IRINA_TRACE_THREAD`, or `Irina`.
Spans are written after the run with explicit start/end times, so input,
output, duration, errors, and usage populate without the create/update race.

### Runtime span coverage (current)

- `irina:environment`: `env.setup`, `policy.check`, `approval.request`,
  `export.artifacts`, `skills.sync`, `session.append`,
  `sandbox.start|exec|read_file|write_file|upload_file|list_files|grep|download|delete`,
  `run.end`.
- `irina:memory`: `memory.retrieve` (item IDs/content/scores),
  `memory.update`, `memory.compaction` (summary text).
- `irina:tools`: `tool.<name>` with args/result/failure, `model.routing`.
- `irina:llm`: `assistant.turn.<n>`, `llm` provider spans with usage/model.
- Subagent traces include `parent_run_id` metadata for linkage.

Still uninstrumented: provider internal retries, direct OpenAI calls inside
vendored memory, OS/library internals, and CLI startup/banner/shutdown.
