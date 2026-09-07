# RocketDict memory index — L2 router

This file is a **router**, not a second specification. Normal recovery starts at [`../../PROJECT_STATE.md`](../../PROJECT_STATE.md), follows [`../../AGENTS.md`](../../AGENTS.md), then uses this index to open only task-relevant durable context. Everything else remains L3 and is unrestricted when evidence is needed.

## Authority order

- **Requirements:** [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md) — current authoritative Product target.
- **Current operational cache:** [`../../PROJECT_STATE.md`](../../PROJECT_STATE.md) — small replace-in-place L1; may be stale and must be checked against HEAD/L3.
- **Durable reasoning:** [`DECISIONS.md`](DECISIONS.md), [`TRANSLATION_QUALITY.md`](TRANSLATION_QUALITY.md), plus the existing domain documents linked below.
- **Actual behavior/evidence:** source, tests, CI, Git history, artifacts, experiment JSON/SQLite and external primary sources (L3). When memory conflicts with them, L3 wins for factual current behavior and memory must be updated.

No separate current full technical-specification file exists in the audited tree beyond `rocketdict/PRODUCT_TARGET.md`; do not invent or route to a nonexistent `rocketdict/rocketdict.md`.

## Task router

| Need | Open first | Expand to L3 when needed |
| --- | --- | --- |
| Product requirements / release contract | [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md) | Product source/tests/CI |
| Maintained Product Core architecture, Stage8→25 ownership | [`../../rocketdict-product-core/README.md`](../../rocketdict-product-core/README.md), [`DECISIONS.md`](DECISIONS.md) | `../../rocketdict-product-core/src/rocketdict/`, `../../rocketdict-product-core/tests/` |
| Workbench / unified Product orchestration | [`../../rocketdict-workbench/README.md`](../../rocketdict-workbench/README.md), [`DECISIONS.md`](DECISIONS.md) | `../../rocketdict-workbench/src/rocketdict_workbench/`, `../../rocketdict-workbench/tests/` |
| Stage8 Product binding | [`../../rocketdict-workbench/docs/PRODUCT_STAGE8_BINDING.md`](../../rocketdict-workbench/docs/PRODUCT_STAGE8_BINDING.md) | corresponding Workbench code/tests |
| Current maintained translation quality / Stage12 planner / numeric gates / R1 & heavy DOE | [`TRANSLATION_QUALITY.md`](TRANSLATION_QUALITY.md) | `../../rocketdict-product-core/src/rocketdict/translation_stage.py`; `numeric_integrity.py`; maintained R1/full-Opticks workflows, tests and artifacts |
| Product CI / real acceptance gate | [`../../.github/workflows/rocketdict-product-core.yml`](../../.github/workflows/rocketdict-product-core.yml) | Actions runs/logs/artifacts; `../../rocketdict-product-core/tests/real_runtime_smoke.py`; `../../rocketdict-workbench/tests/real_product_run_smoke.py` |
| Quality/research history and expensive historical Stage8 findings | [`../../rocketdict/START_HERE.md`](../../rocketdict/START_HERE.md), [`../../rocketdict/RESEARCH_STATUS.md`](../../rocketdict/RESEARCH_STATUS.md), [`DECISIONS.md`](DECISIONS.md) | `../../rocketdict/research/`, `../../rocketdict-ci/`, Git history/artifacts |
| Historical core/checkpoint recovery | [`../../rocketdict-workbench/docs/CORE_RECOVERY.md`](../../rocketdict-workbench/docs/CORE_RECOVERY.md) | `../../rocketdict/recovered/`, `../../rocketdict/checkpoints/`, recovery code/tests/workflows |
| Privacy / public-repository constraints | [`../../rocketdict/PRIVACY.md`](../../rocketdict/PRIVACY.md), [`../../AGENTS.md`](../../AGENTS.md) | repository diff/history when auditing leakage |
| Durable architectural decisions / rejected approaches | [`DECISIONS.md`](DECISIONS.md) | linked commits, source, tests, research evidence |

## Legacy status/handoff paths

Older chats/commits may refer to [`../../rocketdict/CURRENT.md`](../../rocketdict/CURRENT.md), `rocketdict/CURRENT_STATE.json`, `rocketdict/STATE.json`, or [`../../ROCKETDICT_HANDOFF.md`](../../ROCKETDICT_HANDOFF.md). These paths are retained only as compatibility pointers. They are **not parallel live state stores**. Historical contents remain available through Git history.

`rocketdict/CURRENT_STAGE8.md`, `rocketdict/HANDOFF_HEALTH.md`, checkpoints, recovered data and research JSON are L3 historical/provenance material. Load them only when the task requires their evidence.

## L3 rule

L3 is deliberately not enumerated exhaustively here. Do not interpret this index as an allowlist. If a correct decision requires a wider source scan, full Git history, CI logs, artifacts, external documentation, or a large experiment corpus, inspect it fully.
