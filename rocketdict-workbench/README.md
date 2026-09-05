# RocketDict Workbench 0.1

Product-first, evidence-driven local control plane over the real RocketDict core.

The Workbench code now contains a resumable Product pipeline from immutable source import through Stage25 export. **That is an implementation claim, not a claim that the recovered public RocketDict 0.30.40 core has been executed end-to-end.** Current recovery evidence is intentionally fail-closed because the exact 0.30.40 public API implementation is incomplete.

## Product path implemented in Workbench

`rocketdict-product-run` is the primary Product entry point. The implemented sequence is:

1. immutable Product preflight;
2. exact-runtime API/registry probe;
3. pre-gate upstream Stage8 → Stage10 → Stage12 → Stage14;
4. Stage15 hard-quality gate set;
5. Stage16 finalization → Stage17 alignment → Workbench Stage18 aligned lexical extraction → Stage19 sense induction;
6. real OPUS-backed Stage20 lexical processing;
7. Stage20 lexical-primary arbitration → pinned CEFR-J → exact CMUdict pronunciation → Stage23 sense-scoped examples;
8. Stage24 card fan-out and card-set assembly;
9. Stage25 export.

The CLI is installed as:

```bash
rocketdict-product-run --core-pythonpath /path/to/exact-core init ./project
rocketdict-product-run --core-pythonpath /path/to/exact-core advance ./project \
  --state ./project/experiments/product-run/<fingerprint>.json \
  --model-path /path/to/opus-en-ru-ct2 \
  --cefrj-asset /path/to/cefrj-vocabulary-profile-1.5.csv
rocketdict-product-run status ./project --state ./project/experiments/product-run/<fingerprint>.json
```

`advance` resumes as far as immutable inputs and proven contracts allow. Missing external assets such as the OPUS model path or CEFR-J file are reported as explicit blockers. Missing or drifting runtime contracts are correctness failures and are not guessed around.

The older `rocketdict-workbench` CLI remains available for project/import/research/diagnostic operations.

## Core invariants

Product Mode is deliberately stricter than the research surface:

- never use fake, identity, mock or dictionary-lookup output as real MT;
- never silently truncate source text/subtitles;
- never infer a public operation from a promising command/mapping name;
- never execute a stage until its live registry identity and structured callable identity agree;
- never interpret generic `status="ok"` as a quality PASS unless the callable publishes explicit PASS semantics;
- never reuse completed evidence after immutable input, DB, runtime, implementation, parameter or output-affecting setting drift;
- never promote recovered source fragments into an active core merely because their hashes are exact.

## Immutable Product preflight and runtime probe

Preflight schema `rocketdict-workbench-product-preflight/2` freezes:

- source SHA-256 and byte size;
- durable `import_event_id`, `document_version_id` and selected source format;
- exact RocketDict version and API version;
- live Lab Registry identity;
- Product Profile identity;
- selected upstream implementation, descriptor, parameters, `stage_key` and `required_inputs`;
- exact hard-gate identity;
- Product policy including real OPUS float32 requirements and fake-MT prohibition.

The unified run state is `rocketdict-workbench-product-run/1`. Its root is bound to the immutable preflight fingerprint.

The runtime API probe `rocketdict-core-api-surface-probe/2` observes the exact `rocketdict.api` package and records module/source hashes, parser paths, callable mappings, callable signatures and explicit binding metadata. Observed names are only candidates. Promotion requires exact structured evidence.

## Upstream execution: Stage8–14

Workbench already implements exact binding, proof, planning and execution machinery rather than stopping at discovery. Stage execution is bound to:

- Product-run root fingerprint;
- preflight and API-probe fingerprints;
- core/API version;
- live registry contract and descriptor hashes;
- exact callable module/qualname/source SHA-256;
- exact operation name and structured request mapping;
- durable input identities such as `document_version_id`;
- canonical request/result hashes and durable result revision IDs.

Pre-gate orchestration advances Stage8 → 10 → 12 → 14 only when each public execution contract is proven. It does not import guessed internal service modules.

## Stage15 hard-quality boundary

The required Product gates are:

- `rocketdict-numeric-symbol-preservation`;
- `rocketdict-punctuation-preservation`;
- `rocketdict-length-ratio-proxy`.

Every gate needs two independently verified public contracts before the first gate invocation is dispatched:

1. an execution contract describing the request and durable result fields;
2. an explicit quality-semantics contract describing exactly which result field/value means PASS.

This two-phase proof prevents a database from being partially mutated by two gates before discovering that the third gate has no trustworthy PASS semantics. Stage16 is unlocked only by one complete aggregate Stage15 PASS fingerprint.

## Post-gate Stage16–19

The actual dependency chain implemented by Workbench is:

`Stage16 finalization → Stage17 alignment → Workbench Stage18 aligned extraction → Stage19 sense induction`.

Stage18 is not skipped: Stage19 requires the `extraction_run_id` produced from the approved alignment-aware lexical extraction path. Large occurrence payloads are kept in hash-addressed artifacts rather than duplicated into the unified JSON state.

## Real OPUS and unified Stage20

Accepted translation runtime evidence remains the official OPUS EN→RU release:

- release: `opus-2020-02-11`;
- official ZIP SHA-256: `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`;
- CTranslate2 Marian;
- CPU quality acceptance compute type: `float32`.

Unified Stage20 binds not only the release/archive identity but also a deterministic SHA-256 over the exact local CT2 model directory tree. Replacing local model bytes while retaining the same human-readable revision therefore fails closed.

The downstream state schema is now `rocketdict-workbench-product-downstream/2`. It binds:

- exact SQLite path;
- full provider payload SHA-256;
- full Stage20 payload SHA-256;
- provider entries SHA-256 and ordered Stage20 durable identity;
- pinned CEFR-J asset SHA-256;
- output-affecting settings.

Completed arbitration/CEFR/pronunciation/example outputs are persisted as byte- and canonical-hash-verified sidecar artifacts. An ambiguous database-mutating failure is not blindly replayed on resume.

Downstream order:

1. `lexical-primary-arbitration-v1`;
2. CEFR-J 1.5 exact source assessment;
3. exact CMUdict pronunciation, generated fallback forbidden;
4. `stage23-sense-scope-v2` examples bound to the exact approved Stage20 translation revision.

## Stage24/25 durability

Stage24 fans out over exact `lexical_sense_id` identities. Each successful card result is appended to a hash-chained JSONL journal and `fsync`ed. A power-loss-truncated tail is physically truncated to the last durable newline before any future append, preventing stale partial JSON from being glued to a new success record.

When all cards exist, Workbench produces a complete manifest and discovers a card-set assembly callable only from a public execution contract that consumes the exact `card_revision_ids` and exposes durable `set_revision_id`. Duplicate operation keys from different callable mappings remain distinct and cause ambiguity rather than first-match selection.

Stage25 consumes the exact hash-backed `set_revision_id`. Completed set/export evidence is validated on resume rather than silently regenerated.

## Exact 0.30.40 recovery boundary

The public repository still does **not** contain a complete runnable RocketDict 0.30.40 core.

Exact recovered evidence lives under:

`rocketdict/recovered/stage8-0.30.40/`

From surviving Actions artifact `9681838606`, two complete source members are preserved byte-for-byte:

- `src/rocketdict/__init__.py` — SHA-256 `7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c`;
- `src/rocketdict/nlp/registry.py` — SHA-256 `02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69`.

The next archive member, `src/rocketdict/lab/stage12_pilot.py`, is truncated. The surviving source does not include complete:

- `rocketdict.api.contracts`;
- `rocketdict.api.client`;
- `rocketdict.api.cli`;
- structured callable mappings;
- the complete required Stage8–19 implementation set.

Therefore `promotion_allowed=false` and `active_product_core_recovered=false` remain mandatory. The recovered package root proves version `0.30.40` and expected lazy public API exports, but it cannot be used as the active runtime.

The separately recoverable 343 MB offline OPUS runtime and successful real-OPUS gate preserve real-model evidence, not missing RocketDict core source.

Workbench CI now hashes the two recovered files and verifies the fail-closed recovery boundary so a future refactor cannot silently reinterpret this evidence namespace as a runnable core.

## Verification status

Latest verified dependency-light GitHub Actions run after recovery hardening:

- workflow: `RocketDict Workbench`;
- run: `33961885064`;
- Python: `3.13.15`;
- compile: success;
- tests: **131 passed, 1 skipped**.

These tests prove Workbench contracts, resumability and recovery guards with controlled evidence. They do **not** substitute for a real 0.30.40 runtime execution.

## Current hard boundary

Do not spend the next iteration rebuilding orchestration already present in Workbench. The next Product milestone is to obtain an **exact compatible runnable RocketDict core** and run:

1. real Workbench doctor/import/preflight;
2. live registry/API probe;
3. exact binding/execution-contract proof;
4. the first genuine `rocketdict-product-run advance` dispatch;
5. then continue the same unified state through the complete pipeline and large public-domain corpus validation.

If exact core/API bytes cannot be recovered, keep the blocker explicit. Do not synthesize missing 0.30.40 modules from older Stage6Y source or historical behavior.
