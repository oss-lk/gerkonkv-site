# RocketDict — CURRENT authoritative continuation state

Date: 2026-09-05
Repository: `oss-lk/gerkonkv-site`
Branch: `main`

This file is the primary continuation boundary for the active Product line. Read it before older Stage8 notes or Stage6Y maintenance records.

## Non-negotiable rules

- Translation quality dominates speed and storage optimization.
- Never present fake/identity/mock/dictionary lookup as real MT.
- Never silently truncate a long source/corpus.
- Never infer an executable operation from a parser string, operation-looking name or historical behavior.
- Never treat generic success/status text as a quality PASS unless the runtime publishes exact PASS semantics.
- Never reconstruct missing 0.30.40 source by mixing older Stage6Y files into Product lineage.
- Preserve failed experiments, hashes and lineage boundaries.
- Public repository must contain project-only information and no personal user data.

## Active Product implementation boundary

Workbench now contains an evidence-driven resumable Product pipeline through Stage25. The active code is no longer at the old “discover Stage8 and implement an executor next” boundary.

Implemented sequence:

1. immutable Product preflight;
2. exact-runtime API/registry probe;
3. exact structured callable binding and execution proof;
4. pre-gate Stage8 → Stage10 → Stage12 → Stage14;
5. Stage15 hard quality gates;
6. Stage16 finalization → Stage17 alignment → Workbench Stage18 aligned lexical extraction → Stage19 sense induction;
7. real OPUS-backed unified Stage20;
8. Stage20 lexical-primary arbitration → CEFR-J → exact CMUdict pronunciation → Stage23 sense-scoped examples;
9. Stage24 card generation + set assembly;
10. Stage25 export.

Primary Product CLI:

`rocketdict-product-run`

Subcommands:

- `init`
- `advance`
- `status`

`advance` resumes all proven phases and stops only on explicit asset/runtime/contract blockers. It does not weaken evidence requirements to keep progressing.

## Product preflight and run identity

Product preflight schema: `rocketdict-workbench-product-preflight/2`.

It freezes:

- source SHA-256/bytes;
- durable `import_event_id`;
- durable `document_version_id`;
- selected source format;
- exact RocketDict/core API identity;
- live Lab Registry identity;
- Product Profile identity;
- exact Stage8/10/12/14/16/17/19 implementation, descriptor, parameters, `stage_key`, `required_inputs` and execution-contract identity;
- exact required Stage15 quality-gate set;
- Product policy including real OPUS float32 and fake-MT prohibition.

Unified state schema: `rocketdict-workbench-product-run/1`.

API probe schema: `rocketdict-core-api-surface-probe/2`.

Observed parser/mapping names are discovery evidence only. Exact binding requires live registry metadata + exact callable mapping/module/qualname/source SHA + execution contract.

## Stage15 quality boundary

Required gates:

- `rocketdict-numeric-symbol-preservation`
- `rocketdict-punctuation-preservation`
- `rocketdict-length-ratio-proxy`

Before any gate call is dispatched, all three must publish:

1. a valid public execution contract;
2. a valid explicit quality PASS-semantics contract.

`status="ok"` alone is never PASS.

Only a complete aggregate Stage15 PASS fingerprint unlocks Stage16.

## Post-gate chain

Correct dependency chain is:

`16 finalization → 17 alignment → Workbench 18 aligned extraction → 19 sense induction`

Do not shortcut Stage18. Stage19 depends on the real `extraction_run_id` produced from approved alignment-aware lexical extraction.

Large occurrence output is hash-addressed instead of copied wholesale into Product-run JSON state.

## Unified real OPUS / Stage20

Accepted OPUS evidence:

- official release URL: `https://object.pouta.csc.fi/OPUS-MT-models/en-ru/opus-2020-02-11.zip`
- official ZIP SHA-256: `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`
- CTranslate2 Marian
- acceptance compute type: `float32`

Unified Stage20 also hashes the exact local CT2 model directory tree. Same revision label + different local bytes is rejected.

Historical real-OPUS gate evidence remains real model evidence, not fake/identity translation:

- 120 representative sentences
- 4,488 representative words
- Opticks SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`
- Opticks regex words 104,275

Historical F96 selection remains a separate challenge selector and must not be reconstructed from coincident counts.

## Stage20→23 state hardening

Current downstream schema: `rocketdict-workbench-product-downstream/2`.

Important commit:

`a2313bd1b53aa600268577c30488224c6edb1577` — `Harden Stage20-23 downstream state integrity`

The runner now binds:

- exact SQLite path;
- full provider payload SHA-256;
- full Stage20 payload SHA-256;
- provider entries SHA-256;
- ordered durable Stage20 identity;
- pinned CEFR-J SHA-256;
- output-affecting settings.

Completed arbitration/CEFR/pronunciation/example results are stored as byte+canonical-hash verified sidecar artifacts.

An ambiguous DB-mutating failure is not blindly replayed on resume.

## Stage24/25 durability

Stage24 card success records use an append-only hash-chained JSONL journal with `fsync`.

A real crash-recovery defect was found by CI: an incomplete final JSONL record could be glued to the next append. This was fixed by physically truncating the journal to the last durable newline before a later append.

Set assembly does not select the first matching operation key. Mapping module/name, callable module/qualname and callable source SHA are part of identity; duplicate exact candidates produce ambiguity.

Stage25 consumes exact hash-backed `set_revision_id` from completed Stage24 set assembly.

## Exact 0.30.40 recovery evidence

Evidence namespace:

`rocketdict/recovered/stage8-0.30.40/`

This is **not an active core checkout**.

Surviving Actions artifact:

- artifact ID: `9681838606`
- artifact name: `stage8-overlay-prefix`

Downloaded artifact proves a decompressed tar prefix of exactly 51,590 bytes, SHA-256:

`a6af982f442fdedadc6ba6bb9e91d7ca3b519e6d0f893b21537498741f7bf67a`

`gzip_eof=false`; therefore it is truncated evidence.

Exactly two complete source members survive and are now preserved byte-for-byte in the repository:

1. `src/rocketdict/__init__.py`
   - 502 bytes
   - SHA-256 `7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c`
   - proves `__version__ = "0.30.40"`
   - proves lazy public references to `rocketdict.api.contracts.API_VERSION` and `rocketdict.api.client.RocketDictAPI`.

2. `src/rocketdict/nlp/registry.py`
   - 29,072 bytes
   - SHA-256 `02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69`
   - proves `spacy-registry/1.0`, deterministic model tree SHA-256 and read-only inspection support.

Next member:

- `src/rocketdict/lab/stage12_pilot.py`
- declared 51,356 bytes
- incomplete in the surviving prefix.

Current machine-readable recovery authority:

`rocketdict/recovered/stage8-0.30.40/recovery.json`

It intentionally states:

- `promotion_allowed=false`
- `active_product_core_recovered=false`
- `runtime_blocker.status="exact_core_incomplete"`
- `runtime_blocker.runnable_product_core=false`

Exact public modules still missing from the recovered evidence, as proven/required by the package root and Workbench bridge:

- `rocketdict.api.contracts`
- `rocketdict.api.client`
- `rocketdict.api.cli`

Also not recovered:

- structured callable mappings;
- full required Stage8–19 implementation set.

Therefore **no real Product Stage8 dispatch has been claimed from this recovered namespace**.

The separately recoverable offline OPUS runtime artifact:

- artifact ID `9614728610`
- ZIP bytes 343,401,002
- includes official OPUS archive + CT2 4.8.1 + sentencepiece 0.2.2 + numpy 2.5.2 etc.
- contains no RocketDict core source.

The real-OPUS gate artifact:

- artifact ID `9614725980`
- gate schema `rocketdict-github-real-opus-gate/4`
- real model true
- fake/identity translation false.

These artifacts solve model/runtime evidence, not the missing core/API problem.

## Recovery evidence CI

Workbench CI now verifies exact hashes/byte sizes of both recovered 0.30.40 source members and verifies the fail-closed promotion boundary.

Latest verified Workbench run after adding that guard:

- run `33961885064`
- job `101295068804`
- Ubuntu 24.04
- Python 3.13.15
- compile success
- **131 passed, 1 skipped**

Earlier full pipeline integrity checkpoint:

- commit `a2313bd1b53aa600268577c30488224c6edb1577`
- run `33961181952`
- **129 passed, 1 skipped**

The increase to 131 is the two exact recovery-boundary tests.

## Separate Stage6Y maintenance lineage

RocketDict 0.30.34 / LAB Stage6Y remains a verified maintenance lineage, not Product source replacement.

Key evidence:

- working SQLite bytes: 881,905,664
- working SHA-256 `a0128b802930d350679c7d135bea9197fb9e202d863260c31a68d49681fbeafb`
- canonical heavy SHA-256 `3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274`
- SQLite quick_check ok
- FK violations 0
- Alembic head `8b4e7c2a91d0`
- lexical entries 35,743
- 301 packaged runtime files matched source byte-for-byte.

Do not overwrite the Product line with Stage6Y source. Exact source-level merge + regression would be required.

## Immediate next Product task

Do **not** implement another orchestration abstraction. The Workbench pipeline already reaches Stage25.

The next hard milestone is obtaining an **exact compatible runnable RocketDict core** and executing the existing Product machinery against it.

Priority order:

1. continue exact-source recovery only where bytes can be provenance-verified;
2. search surviving Actions/Git objects/artifacts specifically for complete `rocketdict.api` package and required Product stage modules;
3. if a compatible complete runtime is found, run real Workbench doctor + import + preflight;
4. run live API/registry probe and exact binding/execution-contract proof;
5. perform the first genuine `rocketdict-product-run advance` dispatch;
6. then continue the same immutable Product state through Stage25 using real OPUS + pinned CEFR-J;
7. finally run the large 90k+ public-domain corpus validation without truncation and retain the complete translation/research evidence database.

If exact core/API bytes cannot be recovered, keep `exact_core_incomplete` explicit. Do not synthesize missing 0.30.40 modules from 0.30.34, old research overlays or inferred signatures.
