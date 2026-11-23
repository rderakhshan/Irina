# Irina Governance Evaluation Lab

Additive, synthetic-first evaluation lab for Irina. It does not change the
harness, providers, memory, sessions, sandbox, or production policy path.

## What works now (offline, no network)

- Typed metric dictionary and deterministic calculators
  (`configs/metric_dictionary.yaml`, `metrics/`).
- Versioned evaluation contracts and evidence levels (`contracts/`).
- Seeded synthetic finance world (`worlds/factory.py`):
  fictional companies, filings, amendments, future/confidential documents,
  chunks, memories, policy rules, and time semantics.
- Independent oracles (`oracles/`): Decimal finance, retrieval IR metrics,
  point-in-time filtering, memory transitions, policy decisions, effect ledger.
- Disposable RAG fixture (`rag_fixture/`): in-memory BM25-style retrieval with
  time and ACL filtering. Test-only; delete the folder to remove it.
- Core datasets DS01, DS02, DS04, DS05, DS11, DS12 (`datasets/catalog.py`).
- Deterministic checks (`checks/core.py`) and reference runner
  (`runners/reference.py`).
- L2 harness runner with a scripted model (`runners/harness_runner.py`).
- JSON + Markdown reports and a 12-concern coverage matrix
  (`reporting/`, `governance/`).
- Best-effort local Opik adapter (`opik_adapter/`).

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
  tests.test_eval_rag tests.test_eval_suite tests.test_eval_harness
```

## Evidence honesty

- Reference-responder results are `L1_simulated_workflow`, not model behavior.
- The scripted harness run is `L2_irina_integrated` with a mocked model.
- The RAG fixture is not production retrieval.
- `blocked` and `not_applicable` items are never counted as passes.
- No report claims legal or regulatory compliance.

## Not implemented yet

- DS03 claims, DS06 tools, DS07/DS08 memory, DS09 injection, DS10 fairness,
  DS13 resilience, DS14 calibration, DS15 audit telemetry, DS16 benchmarks.
- Runtime policy gate, approvals/identity, retention, tenancy.
- DeepEval adapters and benchmark lane (not installed/verified).
- Online evaluation, guardrails, and alerts (deployment-gated).

See `implementation_manifest.yaml` for checkpoints, blockers, and next tasks.

## Runtime span tracing

When `IRINA_OPIK_ENABLED=1` and the local Opik stack is reachable, each
`Harness.run` creates per-pillar traces under one thread:

- `irina:llm` — model routing and `llm` spans (usage/model/provider).
- `irina:memory` — retrieval, update, compaction spans.
- `irina:tools` — tool spans with args/results/failures.
- `irina:environment` — setup, policy checks, run end.

Thread id = session id, or `IRINA_TRACE_THREAD`, or `Irina`.
Spans are written after the run with explicit start/end times, so input,
output, duration, errors, and usage populate without the create/update race.

### Runtime span coverage (current)

- `irina:environment`: `env.setup`, `policy.check`, `approval.request`,
  `sandbox.start|exec|read_file|write_file|upload_file|list_files|grep|download|delete`,
  `run.end`.
- `irina:memory`: `memory.retrieve` (item IDs/content/scores),
  `memory.update`, `memory.compaction` (summary text).
- `irina:tools`: `tool.<name>` with args/result/failure, `model.routing`.
- `irina:llm`: `assistant.turn.<n>`, `llm` provider spans with usage/model.
- Subagent traces include `parent_run_id` metadata for linkage.

Still uninstrumented: exports/artifact transfer, skills sync, session JSONL
writes, provider internal retries, direct OpenAI calls inside vendored memory,
CLI startup/banner/shutdown.
