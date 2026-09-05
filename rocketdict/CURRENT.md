# CURRENT — RocketDict public continuation state

Last synchronized: **2026-09-05**.

## 0. Latest continuation increment — structured runtime proof and fail-closed Stage8 binding gate

The active Workbench/Product line has advanced from a discovery-only API probe to a proof-oriented binding gate for the first upstream Product stage.

The unified Product state remains:

`rocketdict-workbench-product-run/1`

with ordered steps:

1. `preflight`;
2. `upstream_contract_probe`;
3. `upstream_execution`;
4. `stage20_downstream`;
5. `cards`;
6. `export`.

### API probe v2

`product-run-init` now produces `rocketdict-core-api-surface-probe/2`. It no longer records only parser paths and string keys. For each callable found in a public callable mapping under `rocketdict.api`, it records structured evidence:

- mapping module and mapping name;
- exact operation key;
- callable module and qualname;
- `inspect.signature` text;
- structured parameter names, kinds and required flags;
- SHA-256 of inspectable callable source;
- explicit binding metadata published by that callable when present:
  - `stage_number`;
  - `stage_key`;
  - `implementation_key`;
  - `adapter_descriptor_hash` / `descriptor_hash`;
  - `required_inputs`.

The probe fingerprint covers these observations. Persisted probe output is also protected by the Product-run state's result hash.

Parser paths and mapping-key strings remain discovery evidence only. They are never treated as proof that an operation may execute Product work.

### Stage8 binding verifier

New module:

`rocketdict-workbench/src/rocketdict_workbench/upstream_binding.py`

New durable binding schema:

`rocketdict-workbench-upstream-binding/1`

New CLI command:

```text
rocketdict-workbench product-run-bind-stage8 <project> --state <product-run.json> --operation <exact-operation-key>
```

`verify_stage8_binding(...)` fails closed unless all exact identities agree:

- completed Product preflight is present and unmodified;
- Product-run root still matches that preflight fingerprint;
- completed probe-v2 evidence is present and unmodified;
- the probe's own fingerprint recomputes exactly;
- probed RocketDict/API versions equal the frozen preflight versions;
- the requested operation occurs exactly once as structured callable evidence;
- parser/candidate strings alone are insufficient;
- callable module, qualname, structured signature and inspectable source SHA-256 exist;
- frozen Product Stage8 implementation and adapter descriptor identities are internally consistent;
- callable metadata explicitly identifies Stage **8**;
- callable `stage_key`, implementation and descriptor hash exactly equal the frozen Product profile/preflight;
- required inputs are exactly `document_version_id`;
- the exact frozen `document_version_id` is written into binding evidence.

The binding additionally freezes:

- Product preflight fingerprint;
- Product-run root fingerprint;
- registry hash;
- RocketDict version/API version;
- API-probe fingerprint;
- operation/mapping/callable identities;
- callable signature and source SHA-256;
- Product implementation, adapter descriptor and parameter hash;
- proof mode `exact-runtime-callable-metadata-v1`.

Repeated verification of identical immutable evidence is idempotent. Mutation of a persisted binding is detected; a different Stage8 binding cannot silently replace an already verified one in the same immutable Product run.

When a real callable passes this verifier, state advances to:

`ready_for_stage8_execution`

while `upstream_execution` remains explicitly `binding_verified` / `verified_stage8_binding_not_yet_executed`. Binding verification therefore does **not** masquerade as actual Stage8 execution.

### Critical evidence boundary

The verifier and state transition are implemented and tested, but an exact Stage8 callable from the newer Product core has **not yet been observed** in the incomplete public handoff/runtime payload.

The dependency-light CI uses controlled callable evidence to test the verifier. That proves the Workbench contract, not the existence of a particular callable in the missing newer core.

Historical LAB evidence confirms that Stage8 execution was bound to `document_version_id` in that older lineage. It does **not** prove that its old Stage8 implementation or API surface is identical to the current Product line. In particular, do not substitute the historical `nltk-whitespace-en` implementation for the current registry-derived Product Stage8 choice.

Relevant commits in this increment:

- `34981e80d1f87cb78622cdca557afc25554f69a1` — `Strengthen Product API probe with callable contract evidence`;
- `6870a20161d7bb52b505e6e347b6dbd119300c70` — `Add fail-closed Stage8 upstream binding verifier`;
- `0a0081ae6844bb94d29d4f19034868c413d4d378` — `Make verified Stage8 bindings resumably idempotent`;
- `522e64b724a0941042075a4da667b8304415cbe2` — `Test structured callable evidence in Product API probe`;
- `e84dc9c3d8a536deb7d361d078dde57d07eb22d5` — `Test fail-closed Stage8 upstream binding verification`;
- `98d0bbc3d15456422acf3932323997312f16375d` — `Expose verified Stage8 binding promotion in Workbench CLI`;
- `95bd198f76a0d42eb84579f776d529142eba95dc` — `Test Stage8 binding CLI exposure`;
- `0e57b4a5aa3ada0c047d008eb933bd3a14204c51` — `Document exact-runtime Stage8 binding proof contract`;
- `f90543754f0aae9e61ec5ff41a20775de2ac568c` — `Document structured Stage8 binding verification`.

Verified GitHub Actions evidence for the complete code/CLI checkpoint:

- commit: `95bd198f76a0d42eb84579f776d529142eba95dc`;
- workflow: `RocketDict Workbench`, run `33952044681`;
- Python: 3.13.15;
- package compile: success;
- tests: **54 passed, 1 skipped**.

Detailed proof rules are documented in:

`rocketdict-workbench/docs/PRODUCT_STAGE8_BINDING.md`

### Exact next continuation

Do not invent an operation name and do not write Stage8 execution around a fake fixture.

The next active Product task is:

1. obtain/recover the exact newer RocketDict core runtime compatible with the Product preflight;
2. run `product-run-init` against that exact runtime to create real probe-v2 evidence;
3. inspect its structured `callable_operations`;
4. if a unique callable publishes the exact Stage8/Product metadata, promote it with `product-run-bind-stage8`;
5. if no callable passes, recover/add the missing **public core execution contract** first rather than infer it from names/history;
6. only after a real binding is persisted, implement resumable Stage8 invocation;
7. bind Stage8 invocation to exact `document_version_id`, Product parameters and binding fingerprint;
8. validate and persist the real Stage8 output revision/run IDs plus content/result hashes;
9. then continue the same proof pattern through real MT → hard integrity gates → approved translation → alignment → lexical extraction/sense induction;
10. reuse the existing Stage20→Stage23 downstream runner and add Stage24/25 only after upstream continuity is proven.

## 1. Unified Product root and immutable preflight

`product-run-init` rebuilds `rocketdict-workbench-product-preflight/1` and anchors the unified run to it.

The root freezes:

- source SHA-256;
- `import_event_id`;
- `document_version_id`;
- selected source format;
- source kind;
- real RocketDict/API identity;
- live registry hash;
- selected required Product stages **8, 10, 12, 14, 16, 17, 19**;
- selected implementation keys, adapter descriptor hashes and parameter hashes;
- exact Stage15 hard-gate set;
- Product profile hash;
- preflight/root fingerprints.

The hard Stage15 gates remain:

- `rocketdict-numeric-symbol-preservation`;
- `rocketdict-punctuation-preservation`;
- `rocketdict-length-ratio-proxy`.

Product Mode forbids fake/identity MT and requires the accepted real OPUS float32 path when Stage12 is selected.

## 2. Existing executable downstream Product slice

The downstream Product runner already executes and resumes:

1. Stage20 `lexical-primary-arbitration-v1`;
2. pinned CEFR-J Vocabulary Profile 1.5;
3. exact CMUdict pronunciation with generated fallback forbidden;
4. Stage23 sense-scoped document examples.

It preserves exact provider/Stage20 revision identity, validates coverage/order and requires Stage23 to reference the exact approved Stage20 revision produced/validated by arbitration.

Do not duplicate this logic in the upstream runner.

## 3. Active Product profile facts

Current Workbench Product profile schema:

`rocketdict-workbench-product-profile/5`

Important preferred implementations include:

- Stage10: `structural-entity-term-discourse-pronoun-v1`;
- Stage14: `glossary_refinement-current`;
- Stage16: `approve-if-clean-finalization`;
- Stage17: `deterministic-structural-global`;
- Stage19: `deterministic-context-target-graph`;
- Stage21: `cefrj-vocabulary-1.5`;
- Stage22: `cmudict-production`;
- Stage23: `examples-current`;
- Stage24: `cards-current`;
- Stage25: `export-json`.

Workbench-specific contracts remain:

- Stage18: `workbench-aligned-content-pos-v4`;
- Stage20 provider: `contextual-lexical-opus-v3`;
- generated pronunciation fallback forbidden;
- smoke/frequency-only CEFR forbidden for Product output;
- fake/identity MT forbidden;
- network dependency during processing forbidden.

## 4. Do not regress the repository

The active `main` line is newer than archived LAB checkpoints. Older complete ZIPs or maintenance branches must not overwrite current Product/Workbench work merely because they are self-contained.

Historical repositories/checkpoints may be used as evidence to recover contracts, but compatibility with the newer Product source must be proved explicitly.

## 5. Active real-OPUS / Stage8 research evidence

The public Stage8 research handoff remains important context:

- Stage8 development snapshot: **0.30.40**;
- official model: `opus-2020-02-11.zip`;
- official ZIP SHA-256 observed in successful GitHub execution: `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`;
- backend: CTranslate2 Marian;
- quality acceptance compute type: `float32`;
- successful real-model gate: 120 representative sentences / 4,488 words;
- Stage8 DOE F96 snapshot: roughly 5k challenge words, 3 numeric mismatches, zero critical-symbol mismatches, zero length-ratio mismatches, zero empty outputs and no backend-error units; at that snapshot the remaining gate failure was zero-numeric-loss.

Do not restart DOE from variant A and do not reconstruct the missing F96 selector merely from aggregate similarity.

## 6. Payload health

The Stage8 public payload is incomplete. Exact newer core source/runtime and exact Research Vault material cannot currently be assumed to exist in `rocketdict/payload/`.

`HANDOFF_HEALTH.md` remains authoritative for payload survivability.

Never invent missing Stage8 source files, API calls or Research Vault rows.

## 7. Separate verified Stage6Y maintenance lineage

A separate verified maintenance checkpoint is preserved under `checkpoints/stage6y/`:

**RocketDict 0.30.34 / LAB Stage6Y**.

It proves, on its own lineage:

- `translation-offline-sqlite-compaction-v1`;
- `translation-offline-sqlite-compaction-recovery-v1`;
- `translation-offline-sqlite-compaction-io-fault-safety-v1`.

Heavy challenge facts retained for continuity:

- baseline working SQLite: 881,905,664 bytes;
- baseline working SHA-256: `a0128b802930d350679c7d135bea9197fb9e202d863260c31a68d49681fbeafb`;
- canonical immutable heavy SHA-256: `3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274`;
- recovery restored the working DB byte-for-byte after forced backup-copy ENOSPC;
- `quick_check=ok`, FK=0, Alembic head `8b4e7c2a91d0`;
- lexical entries: 35,743;
- translation runs/candidates/batch metrics/inference results/leases: 0/0/0/0/0;
- 301 packaged runtime files matched source byte-for-byte.

Do not assume these maintenance changes are source-merged into Stage8/Product. An exact source-level comparison/merge plus regression is required.

## 8. Privacy boundary

This is a public repository. Persist only project technical/research state. Do not add personal user data, private chats, credentials, unrelated account information, local personal paths or private datasets.
