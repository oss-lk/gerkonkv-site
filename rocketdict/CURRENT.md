# RocketDict — CURRENT authoritative continuation state

Date: 2026-09-05
Repository: `oss-lk/gerkonkv-site`
Branch: `main`

This file is the primary continuation boundary for the active Product line. Read it before older Stage8 notes or Stage6Y maintenance records.

## Non-negotiable rules

- Translation quality dominates speed/storage optimization.
- Never present fake/identity/mock/dictionary lookup as real MT.
- Never silently truncate a long source/corpus.
- Never infer an executable operation from parser strings, operation-looking names or historical behavior.
- Never interpret generic success/status text as a quality PASS unless the runtime publishes exact PASS semantics.
- Never reconstruct missing 0.30.40 source by silently mixing older Stage6Y/checkpoint bytes into Product lineage.
- Preserve failed experiments, immutable hashes and lineage boundaries.
- Public repository must remain project-only and contain no personal user information.

## Product implementation boundary

Workbench contains an evidence-driven resumable Product pipeline through Stage25.

Implemented sequence:

1. immutable Product preflight;
2. exact-runtime API/registry probe;
3. exact structured callable binding and execution proof;
4. Stage8 → Stage10 → Stage12 → Stage14;
5. Stage15 hard quality gates;
6. Stage16 finalization → Stage17 alignment → Workbench Stage18 aligned lexical extraction → Stage19 sense induction;
7. real OPUS-backed unified Stage20;
8. Stage20 lexical-primary arbitration → pinned CEFR-J → exact CMUdict pronunciation → Stage23 sense-scoped examples;
9. Stage24 card generation + set assembly;
10. Stage25 export.

Primary Product CLI:

`rocketdict-product-run`

Subcommands:

- `init`
- `advance`
- `status`

`advance` resumes all proven phases and stops on explicit runtime/asset/contract blockers. It does not weaken evidence requirements to keep progressing.

## Core Product identities

Product preflight schema: `rocketdict-workbench-product-preflight/2`.

Unified Product state schema: `rocketdict-workbench-product-run/1`.

API probe schema: `rocketdict-core-api-surface-probe/2`.

Product preflight freezes source SHA/bytes, durable `import_event_id`, durable `document_version_id`, source format, exact RocketDict/API identity, live registry identity, Product Profile identity, selected Stage8/10/12/14/16/17/19 implementation/descriptor/parameters/stage_key/required_inputs/execution contracts, exact Stage15 gate set and Product policy.

Observed parser/mapping strings are discovery evidence only. Exact binding needs live registry metadata plus exact callable module/qualname/source SHA and execution contract.

## Stage15 hard quality boundary

Required Product gates:

- `rocketdict-numeric-symbol-preservation`
- `rocketdict-punctuation-preservation`
- `rocketdict-length-ratio-proxy`

Before any gate call is dispatched, all three must publish:

1. a valid execution contract;
2. explicit quality PASS semantics.

`status="ok"` by itself is never PASS.

Only a complete aggregate Stage15 PASS fingerprint unlocks Stage16.

## Post-gate chain

Correct dependency chain:

`16 finalization → 17 alignment → Workbench 18 aligned extraction → 19 sense induction`

Do not shortcut Stage18. Stage19 depends on the real `extraction_run_id` produced by approved alignment-aware extraction.

Large occurrence output is hash-addressed instead of copied wholesale into Product JSON state.

## Real OPUS / Stage20

Accepted OPUS EN→RU evidence:

- URL: `https://object.pouta.csc.fi/OPUS-MT-models/en-ru/opus-2020-02-11.zip`
- official ZIP SHA-256: `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`
- CTranslate2 Marian
- acceptance compute type: `float32`

Unified Stage20 also hashes the exact local CT2 model directory tree. Same human-readable revision with different model bytes is rejected.

Historical real-model gate evidence remains valid model evidence:

- 120 representative sentences
- 4,488 representative words
- Opticks SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`
- Opticks regex words 104,275

Historical F96 challenge selector remains separate from ordinary Stage12 selection and must not be reconstructed from coincident counts.

## Stage20→25 durability

Downstream schema: `rocketdict-workbench-product-downstream/2`.

Important hardening checkpoint:

`a2313bd1b53aa600268577c30488224c6edb1577` — `Harden Stage20-23 downstream state integrity`

The runner binds exact SQLite path, full provider/stage20 hashes, ordered Stage20 durable identity, pinned CEFR-J hash and output-affecting settings. Completed arbitration/CEFR/pronunciation/example outputs are byte/canonical-hash verified sidecars. Ambiguous DB-mutating failures are not blindly replayed.

Stage24 success is stored in an append-only hash-chained JSONL journal with `fsync`. A truncated final record is physically removed to the last durable newline before future appends.

Stage24 set assembly uses exact mapping/callable identity; duplicate exact candidates cause ambiguity instead of first-match selection.

Stage25 consumes the exact hash-backed `set_revision_id`.

## Exact 0.30.40 recovery evidence

Evidence namespace:

`rocketdict/recovered/stage8-0.30.40/`

It is **not an active core checkout**.

Surviving Stage8 artifact prefix:

- artifact ID `9681838606`
- decompressed tar prefix bytes: 51,590
- SHA-256 `a6af982f442fdedadc6ba6bb9e91d7ca3b519e6d0f893b21537498741f7bf67a`
- `gzip_eof=false`

Exactly two complete 0.30.40 members are preserved byte-for-byte:

1. `src/rocketdict/__init__.py`
   - 502 bytes
   - SHA-256 `7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c`
   - proves `__version__ = "0.30.40"`
   - proves lazy public references to `rocketdict.api.contracts.API_VERSION` and `rocketdict.api.client.RocketDictAPI`.

2. `src/rocketdict/nlp/registry.py`
   - 29,072 bytes
   - SHA-256 `02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69`
   - proves registry `spacy-registry/1.0`, deterministic model tree SHA-256 and read-only inspection support.

Next tar member:

- `src/rocketdict/lab/stage12_pilot.py`
- declared bytes: 51,356
- incomplete.

Machine-readable recovery authority:

- `rocketdict/recovered/stage8-0.30.40/recovery.json`
- `rocketdict/recovered/stage8-0.30.40/core-recovery-history.json`

Both retain `promotion_allowed=false`.

## Important historical recovery conclusion

Historical ancestry/materializer analysis proved that the intended Stage8 overlay consisted of 19 research/translation files and **did not contain `rocketdict.api.*`**.

Therefore restoring the missing seven Stage8 overlay chunks alone would still not restore the complete base core/public API.

The public API/base-core dependencies remain missing as exact 0.30.40 bytes:

- `rocketdict.api.contracts`
- `rocketdict.api.client`
- `rocketdict.api.cli`

Also not recovered:

- full structured callable mappings;
- full required Stage8–19 implementation set.

No real Product Stage8 dispatch has been claimed from the recovered namespace.

## Recovery tooling now implemented

Operational guide:

`rocketdict-workbench/docs/CORE_RECOVERY.md`

Three CLI tools exist:

### `rocketdict-recover-core`

Inspects one source directory or ZIP checkpoint.

- directories can receive isolated subprocess import probing with module-origin verification;
- ZIPs are structural/read-only and are never executed/extracted by this verifier;
- validates Workbench bridge dependencies and available exact 0.30.40 anchors;
- never promotes a candidate by itself.

### `rocketdict-recover-plan`

Builds a deterministic read-only base→0.30.40 compatibility plan.

Current overlay recovery math:

- intended Stage8 overlay members: 19
- exact target bytes available: 2
- exact target bytes missing: 17

Historical/base files at the same paths cannot be accepted as 0.30.40 replacements without exact manifest-backed target SHA/size.

The recovered public API compatibility state remains `unproven_against_exact_0.30.40`.

### `rocketdict-recover-scan`

Batch screens a directory containing historical ZIP/checkouts.

- recursively discovers ZIP and canonical RocketDict source roots;
- does not execute directories unless `--probe-directories` is explicitly supplied;
- can persist hash-addressed full plans;
- ranking is recovery triage, never promotion proof;
- canonicalizes `root/src/rocketdict/__init__.py` to `root` so one checkout is not counted twice;
- corrupt ZIP is isolated as one candidate error and does not abort the remaining scan.

## Historical archive leads

Documented older full checkpoint lead:

- `RocketDict_CURRENT_COMPACT.zip`
- version `0.30.8`
- bytes `125875993`
- SHA-256 `f948a9b59e4deb7b00a606fdb88973dd9a435c087c132f32f03d2d0c863b51ac`
- manifest files 666

Its bytes are not currently recovered. It is only a base candidate.

Project history also contains later checkpoint names including 0.30.9, 0.30.19, 0.30.29, 0.30.32 and 0.30.34-era work. File Library currently exposes README/heavy evidence for 0.30.29 / Stage6T but not the checkpoint ZIP bytes.

The private historical `oss-lk/spacy-project-vault` is not a full base-core source. Its checked `rocketdict-stage06-spacy-model` branch contains no RocketDict source package.

## Separate Stage6Y maintenance lineage

RocketDict 0.30.34 / LAB Stage6Y remains a verified maintenance lineage, not Product source replacement.

Key evidence:

- working SQLite bytes 881,905,664
- working SHA-256 `a0128b802930d350679c7d135bea9197fb9e202d863260c31a68d49681fbeafb`
- canonical heavy SHA-256 `3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274`
- SQLite quick_check ok
- FK violations 0
- Alembic head `8b4e7c2a91d0`
- lexical entries 35,743
- 301 packaged runtime files matched source byte-for-byte.

Do not overwrite Product with Stage6Y. Exact source-level compatibility + full regression would be required.

## Latest verified recovery checkpoint

Current code checkpoint:

`d1e94eced4deaeec9e9a9a3a70fecdee48572e12` — `Fix canonical recovery candidate discovery and ZIP isolation`

GitHub Actions:

- workflow `RocketDict Workbench`
- run `33964578578`
- job `101302315173`
- Ubuntu 24.04
- Python 3.13.15
- compile success
- **153 passed, 1 skipped in 1.53s**

The immediately preceding batch-scan run was red with four failures and is intentionally preserved as failed-experiment evidence. It exposed duplicate checkout discovery (`root` and `root/src`) and uncaught corrupt ZIP handling; both were fixed in `d1e94ece...`.

## Immediate next Product task

Do not build another orchestration abstraction. The Product pipeline already reaches Stage25.

Next hard milestone: recover a **complete historical RocketDict core/checkpoint byte source** and feed it to the new recovery tools.

Priority order:

1. continue exact-byte recovery searches only where provenance can be verified;
2. when any old ZIP/checkpoint/source checkout is obtained, run `rocketdict-recover-scan` / `rocketdict-recover-core` / `rocketdict-recover-plan` immediately;
3. prefer the strongest complete base candidate, but never infer missing 0.30.40 replacement/API bytes;
4. if a complete exact-compatible runtime is recovered, run real Workbench doctor + import + Product preflight;
5. run live registry/API probe and exact binding/execution-contract proof;
6. perform the first genuine `rocketdict-product-run advance` dispatch;
7. continue the same immutable Product state through Stage25 using real OPUS + pinned CEFR-J;
8. finally run the full 90k+ public-domain corpus without truncation and retain the complete translation/research evidence database.

If exact core/API bytes cannot be recovered, keep `exact_core_incomplete` explicit. Do not synthesize missing 0.30.40 modules from older checkpoints, Stage6Y, old research overlays or inferred signatures.
