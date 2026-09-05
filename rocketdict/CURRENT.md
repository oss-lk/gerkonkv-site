# CURRENT — RocketDict public continuation state

Last synchronized: **2026-09-05**.

## 0. Latest continuation increment — live registry execution contracts + Stage8 discovery

The active Product/Workbench line has moved beyond a hard-coded Stage8 input assumption. The current execution proof chain is now:

**live Lab Registry → Product Profile → immutable Product preflight → exact-runtime API probe → Stage8 discovery → verified binding → future execution**.

No historical stage contract, parser command, operation-looking string, or controlled unit-test callable is allowed to skip a link in that chain.

### New schema/contracts

- Product Profile: `rocketdict-workbench-product-profile/6`;
- Product preflight: `rocketdict-workbench-product-preflight/2`;
- unified Product run root remains `rocketdict-workbench-product-run/1`;
- runtime API probe remains `rocketdict-core-api-surface-probe/2`;
- Stage8 discovery: `rocketdict-workbench-stage8-binding-discovery/1`;
- verified upstream binding: `rocketdict-workbench-upstream-binding/2`.

### Live execution-input contract is now authoritative

`product_profile.py` now copies explicit `required_inputs` from the **current live registry** for every selected Product stage. Implementation-level metadata wins when explicitly published; an explicit stage-level field is accepted as a fallback. Missing metadata remains unknown (`None`) rather than being inferred from a stage number or old runner behavior.

`product_preflight.py` now requires every selected upstream core stage **8, 10, 12, 14, 16, 17 and 19** to expose:

- non-empty `stage_key`;
- selected implementation;
- adapter descriptor identity;
- Product parameters;
- explicit ordered `required_inputs` list.

For each stage, immutable preflight identity stores:

- `stage_key`;
- implementation;
- adapter descriptor hash;
- parameters SHA-256;
- exact `required_inputs`;
- `execution_contract_sha256` over stage number/key, implementation, descriptor, complete Product parameters and required inputs.

Changing `required_inputs` changes both the stage execution-contract hash and the overall Product preflight fingerprint. Missing, malformed or duplicate required-input metadata is a hard stop before execution.

Historical heavy-run evidence did show `required_inputs` as a real RocketDict runner concept, including `document_version_id` for its historical Stage8. That evidence motivated recovering the contract from the live registry, but **its historical values are not copied into current Product identity and are not proof of the newer core**.

### Read-only exact Stage8 binding discovery

New CLI:

```text
rocketdict-workbench product-run-discover-stage8 <project> --state <product-run.json>
```

It reads the immutable preflight + probe-v2 evidence and compares every structured callable against the frozen current Stage8 contract.

The discovery record reports:

- frozen Stage8 stage key;
- Product implementation;
- descriptor hash;
- parameter hash;
- `required_inputs`;
- `execution_contract_sha256`;
- every structured callable candidate;
- exact match count;
- per-candidate mismatch reasons such as stage, implementation, descriptor or required-input drift.

Statuses are:

- `unique_exact_match`;
- `no_exact_match`;
- `ambiguous_exact_matches`.

Discovery is read-only. Parser paths and bare mapping strings are explicitly not execution proof.

### Stage8 binding v2

`product-run-bind-stage8` now promotes a callable only when three independent evidence layers agree exactly:

1. live registry → Product Profile/preflight execution contract;
2. immutable preflight hashes including `execution_contract_sha256`;
3. exact-runtime callable metadata/source SHA from API probe v2.

The first Workbench Stage8 resolver currently knows how to bind only the already frozen Product source `document_version_id`. Therefore the **current live registry itself** must say `required_inputs=["document_version_id"]` for the selected Stage8 adapter before binding can proceed. If the live registry says something different, Workbench stops with an explicit unsupported-input-contract error. This is a Workbench resolver limitation, not a claim copied from history.

Binding proof mode is now:

`live-registry-plus-exact-runtime-callable-v1`

and the persisted record uses `rocketdict-workbench-upstream-binding/2`.

Obsolete `/1` binding evidence is intentionally rejected rather than silently reused.

### Verified CI evidence

Code/test checkpoint:

- commit: `38cbd47663fa40802e25555dc0adeb0f29712b0c` — `Test live registry execution input propagation`;
- workflow: `RocketDict Workbench`;
- run: `33957485543`;
- Python: 3.13.15;
- package compile: success;
- tests: **63 passed, 1 skipped**.

The dependency-light skipped test is the real-core smoke path gated by `ROCKETDICT_TEST_CORE`; this CI run does **not** contain the missing exact newer RocketDict runtime.

Relevant commits in this increment:

- `6e918fafadac22803b0f509e6d8cc50cd93beef9` — `Freeze registry execution inputs in Product profile`;
- `c9ecac4b94eb8f4bb283415cf941d9871ec22f01` — `Freeze live stage execution contracts in Product preflight`;
- `747b0a465798123e8751b86e58cc93c2b79154cc` — `Bind Stage8 verification to frozen live registry contract`;
- `3a732e1ba94f461c643c60de5f07f50283d09915` — `Expose Stage8 exact binding discovery in Workbench CLI`;
- `19100373bb1c60b2e49c3c6f3a1d632bf13d5989` — `Test immutable live execution contracts in Product preflight`;
- `be83900a3a55aa454c94698072979b2ace8187f4` — `Test live-registry Stage8 binding discovery and proof`;
- `38cbd47663fa40802e25555dc0adeb0f29712b0c` — `Test live registry execution input propagation`;
- `a1c09c6a214a460b667fe337570644ef40a69589` — `Document live-registry Stage8 execution contract discovery`;
- `cc34e437bbb4bbf799af0b2ad2afdb00c7917f41` — `Document live-registry Stage8 binding proof chain`.

### Critical current boundary

**A real newer-core Stage8 callable is still not proven or executed.**

The public Stage8 payload remains incomplete, so the current CI can validate the Workbench proof machinery but cannot legitimately claim a specific newer RocketDict Stage8 callable. Controlled test operations such as `product.stage8.run` are fixtures only.

Do not mark Stage8 executed until an exact newer/recovered runtime has produced all of the following in one Product run:

1. live registry with explicit Stage8 `required_inputs`;
2. successful Product preflight `/2`;
3. API probe v2 from the same core/API identity;
4. Stage8 discovery with one exact structured callable;
5. persisted binding `/2` for that callable;
6. only then a real Stage8 invocation with durable output revision/run identities and hashes.

### Exact continuation from here

Do **not** build another abstract orchestration layer. The next task is concrete:

1. recover/obtain the exact newer RocketDict core runtime compatible with the active Product line;
2. run live Product Profile/preflight `/2`; if current registry does not expose `required_inputs`, add/recover that public core registry contract first;
3. run `product-run-init` to produce probe v2 from the same runtime;
4. run `product-run-discover-stage8`;
5. if and only if it returns one unique exact match, persist it with `product-run-bind-stage8`;
6. inspect/prove the exact API invocation envelope and result identity for that callable;
7. implement one resumable real Stage8 execution step bound to `document_version_id`, Product parameters, binding fingerprint and execution-contract hash;
8. persist/validate Stage8 result IDs and output/content hashes before advancing;
9. repeat the same proof pattern through real MT → hard integrity gates → approved translation revision → alignment → lexical/sense induction;
10. join the resulting real Stage20 inputs to the existing Stage20→Stage23 downstream runner;
11. add Stage24 cards and Stage25 export last.

If the exact newer core cannot be recovered, record that limitation explicitly. Do not use Stage6Y source, historical heavy-run contracts or guessed operation names as if they were newer Product-runtime proof.

## 1. Unified Product run root and API evidence

The unified state schema is:

`rocketdict-workbench-product-run/1`

Ordered steps remain:

1. `preflight`;
2. `upstream_contract_probe`;
3. `upstream_execution`;
4. `stage20_downstream`;
5. `cards`;
6. `export`.

The root identity is fail-closed and contains the Product preflight fingerprint, immutable source SHA-256, durable `import_event_id`, durable `document_version_id`, selected source format, live registry hash and real RocketDict/API identity.

API probe v2 observes only the exact runtime's public `rocketdict.api` surface and records:

- RocketDict/API version;
- API modules and inspectable module SHA-256;
- argparse command paths;
- callable mapping keys;
- structured callable rows with mapping/module/qualname/signature/parameters/source SHA-256;
- only explicit binding metadata published by that callable/runtime.

Completed probe evidence is persisted atomically and mutation-checked. A changed preflight root or core/API identity fails closed.

## 2. Existing resumable Product downstream runner

A strict/resumable downstream Product runner exists in `rocketdict-workbench/src/rocketdict_workbench/product_runner.py` and is exposed through:

```text
rocketdict-workbench lexical-opus ... --apply-stage20 --continue-product
```

Current executable downstream order:

1. Stage20 `lexical-primary-arbitration-v1`;
2. pinned CEFR-J Vocabulary Profile 1.5 assessment;
3. exact CMUdict pronunciation with generated fallback forbidden;
4. Stage23 sense-scoped document examples.

The downstream runner is fail-closed and evidence-preserving:

- atomic `rocketdict-workbench-product-downstream/1` state;
- successful steps reused on resume;
- immutable provider hash and exact Stage20 sense/entry/generation/selection identities;
- pinned CEFR-J identity;
- output-affecting settings in fingerprint;
- exact Stage20 arbitration evidence;
- exact CEFR/pronunciation/example coverage and order checks;
- generated pronunciation fallback forbidden;
- Stage23 `stage23-sense-scope-v2` required;
- every Stage23 row bound to the exact approved Stage20 selection revision from arbitration.

Verified downstream checkpoint:

- commit `cc43068b052761c0e1be66cfc9c5202732a241f5`;
- workflow run `33872151299`;
- **34 passed, 1 skipped**.

## 3. Product policy that must not regress

Hard quality gates:

- `rocketdict-numeric-symbol-preservation`;
- `rocketdict-punctuation-preservation`;
- `rocketdict-length-ratio-proxy`.

Current Product preferences include:

- Stage8: full offline English NLP, preferred `en-sm` / `en_core_web_sm` 3.8.0;
- Stage10: `structural-entity-term-discourse-pronoun-v1`;
- Stage12: real `opus-en-ru-ct2`, CTranslate2, `float32` quality acceptance;
- Stage14: `glossary_refinement-current`;
- Stage16: `approve-if-clean-finalization`;
- Stage17: `deterministic-structural-global`;
- Stage19: `deterministic-context-target-graph`;
- Workbench Stage18: `workbench-aligned-content-pos-v4`;
- Workbench Stage20 provider: `contextual-lexical-opus-v3`;
- Stage21: pinned CEFR-J Vocabulary Profile 1.5;
- Stage22: exact CMUdict, no generated fallback;
- Stage23: sense-scoped reviewed examples;
- Stage24: cards;
- Stage25: export JSON.

Never allow:

- fake/identity/mock MT in Product Mode;
- silent source loss/truncation;
- generated pronunciation presented as exact evidence;
- smoke CEFR as Product assessment;
- code-only/tokenizer NLP as final Product NLP;
- alignment to override lexical headword-form evidence;
- automatic quality-gate weakening;
- research results overwriting approved Product output.

## 4. Active real-OPUS / Stage8 research evidence

Public Stage8 research context remains useful but is not a complete source runtime:

- development snapshot version: **0.30.40**;
- official model: `opus-2020-02-11.zip`;
- observed official ZIP SHA-256: `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`;
- backend: CTranslate2 Marian;
- accepted compute type: `float32`;
- successful real-model GitHub gate: 120 representative sentences / 4,488 words;
- Stage8 DOE frontier in `STATE.json`: F96, snapshot failed only zero-numeric-loss with 3 numeric mismatches;
- do not restart DOE from variant A.

A surviving Stage8 diagnostic proves ordinary Stage12 pilot selection and historical F96 challenge selection are distinct. Aggregate similarity does not prove F96 identity. Do not reconstruct missing selector/source by coincidence.

## 5. Separate verified Stage6Y maintenance lineage

Preserved under `rocketdict/checkpoints/stage6y/`:

**RocketDict 0.30.34 / LAB Stage6Y**.

Verified maintenance contracts:

- `translation-offline-sqlite-compaction-v1`;
- `translation-offline-sqlite-compaction-recovery-v1`;
- `translation-offline-sqlite-compaction-io-fault-safety-v1`.

Heavy facts:

- baseline working SQLite: 881,905,664 bytes;
- baseline working SHA-256: `a0128b802930d350679c7d135bea9197fb9e202d863260c31a68d49681fbeafb`;
- canonical immutable heavy SHA-256: `3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274`;
- forced backup-copy ENOSPC recovery restored DB byte-for-byte;
- `quick_check=ok`, FK=0, Alembic head `8b4e7c2a91d0`;
- lexical entries = 35,743;
- translation runs/candidates/batch metrics/inference results/leases = 0/0/0/0/0;
- 301 packaged runtime files matched source byte-for-byte.

**Do not source-overwrite the active Product line with Stage6Y.** Exact source-level merge/regression is required before claiming compatibility.

To continue that separate maintenance lineage specifically, read `rocketdict/checkpoints/stage6y/CONTINUE_STAGE6Z.md`.

## 6. Payload health / recovery rule

The public Stage8 binary/text payload is incomplete. `HANDOFF_HEALTH.md` remains authoritative for what survives and what cannot be materialized bit-for-bit.

Do not invent missing Stage8 source files, Research Vault rows, adapter code, callable names or invocation semantics.

Historical repositories/archives may be used to understand old contracts or recovery possibilities, but never as proof that the active newer Product runtime has the same source/API/descriptor identity.

## 7. Do not regress repository lineage

The active `main` contains Product/Workbench work newer than old LAB checkpoints and old Stage8 handoff snapshots. Do not reset it to an older complete ZIP merely because that archive is self-contained.

The old `oss-lk/spacy-project-vault` heavy branches are historical evidence, not the active development branch.

## 8. Privacy boundary

This repository is public. Persist only project technical/research state. Do not add personal user data, private chats, credentials, unrelated account information, local personal paths or private datasets.
