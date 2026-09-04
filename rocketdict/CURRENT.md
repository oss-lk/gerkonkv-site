# CURRENT — RocketDict public continuation state

Last synchronized: **2026-09-04**.

## 0. Latest continuation increment — unified Product run root and real-core API surface probe

The active Workbench/Product line now has a single durable Product-run root above the previously separate preflight and downstream slices.

`rocketdict-workbench product-run-init` rebuilds the strict Product preflight, binds the run to that immutable fingerprint and captures evidence about the exact `rocketdict.api` surface present in the selected real runtime.

The new state schema is:

`rocketdict-workbench-product-run/1`

Its initial ordered steps are:

1. `preflight`;
2. `upstream_contract_probe`;
3. `upstream_execution`;
4. `stage20_downstream`;
5. `cards`;
6. `export`.

The root identity is fail-closed and contains:

- the Product preflight fingerprint;
- immutable source SHA-256;
- durable `import_event_id`;
- durable `document_version_id`;
- selected source format;
- live registry hash;
- real RocketDict version/API identity;
- a canonical root fingerprint over those values.

The Product preflight was hardened at the same time: it now refuses a source record that lacks positive `import_event_id`, positive `document_version_id` or selected interpretation format. These IDs are no longer represented only indirectly by payload hashes; the upstream runner can address the exact imported/interpreted document revision without guessing.

### Real-core API surface probe

`upstream_contract_probe` executes inside the exact real RocketDict runtime selected by Workbench. It observes only the `rocketdict.api` package and records evidence rather than importing guessed Stage8–19 internal services.

The probe records:

- RocketDict version and API version;
- direct modules exposed under `rocketdict.api`;
- source SHA-256 for those modules when source introspection is available;
- discoverable argparse parser command paths;
- string keys from public callable mappings;
- a canonical fingerprint over the observed surface.

Completed probe evidence is persisted atomically, reused on resume, and revalidated. Mutation of persisted probe output is detected by a separate canonical result hash. A changed Product preflight root or changed real core/API identity also fails closed.

**Critical boundary:** parser paths and callable mapping keys are only observed operation candidates. Their presence is **not** treated as proof that they are valid Product Stage8–19 execution calls. Therefore `upstream_execution` deliberately remains `pending` with:

`no_verified_stage8_19_operation_binding`

until a concrete registry/API binding has been demonstrated against the exact runtime.

CLI addition:

`rocketdict-workbench product-run-init <project> [--source-sha256 ...] [--source-kind subtitle|text] [--state ...]`

Relevant commits in this increment:

- `71899cc66356892c7f0923e22a7d53052c91476a` — `Expose durable source revision identities in Product preflight`;
- `58cf7b571639aba1999059f8072b790cc2795580` — `Add unified Product run state and API surface probe`;
- `7cda9528f0aee0bc18b9de23c530a6eaba323e28` — `Test unified Product run state and API surface probe`;
- `8639f1664a13322f4a3689a89814172827c6d4b8` — `Test durable source revision identities in Product preflight`;
- `1f844d1a021dea1229047cc60bcea161b6fca444` — `Expose unified Product run initialization in Workbench CLI`;
- `4bd4e438c4a5767d686bdc8332755edf36d6aea1` — `Test Product run initialization CLI contract`;
- `26c0bcbc7dac3d0c6a1a9c66e3ab5b76f6cc784a` — `Document unified Product run root and API probe`.

Verified GitHub Actions evidence for the code/test checkpoint:

- commit: `4bd4e438c4a5767d686bdc8332755edf36d6aea1`;
- workflow: `RocketDict Workbench`, run `33876212769`;
- Python: 3.13.15;
- package compile: success;
- tests: **47 passed, 1 skipped**.

### Exact continuation after this increment

Do **not** spend the next stage designing another orchestration abstraction. The next active Product task is concrete:

1. run/use the persisted `upstream_contract_probe` evidence from an exact real RocketDict runtime;
2. identify one specific public registry/API operation path that can execute the first upstream Product slice for the frozen `document_version_id` and Product profile;
3. prove its input/output contract and bind it by exact operation name/API version/implementation descriptor identity rather than by guessed imports;
4. add that proven operation as the first resumable `upstream_execution` step with durable input/result hashes and revision IDs;
5. only then expand through source preparation → real MT → hard integrity gates → approved translation revision → alignment → lexical extraction/sense induction;
6. join the resulting real Stage20 inputs to the existing Stage20→Stage23 downstream runner;
7. add Stage24 cards and Stage25 export last.

Do not promote a parser/mapping string merely because the probe observed it. Evidence of actual invocation semantics is required before Product execution may advance.

## 1. Immutable Product source/runtime preflight

`rocketdict-workbench product-preflight` creates a durable `rocketdict-workbench-product-preflight/1` record and refuses to declare the Product run ready unless the exact source and current real runtime are compatible with the Product Profile.

The preflight freezes and validates:

- selected imported source SHA-256, byte size, suffix and project-relative immutable-copy path;
- a fresh SHA-256 of the copied source, rejecting mutation after import;
- durable `import_event_id`, `document_version_id` and selected format plus canonical import/interpretation payload hashes;
- source kind (`subtitle`/`text`), with optional explicit assertion;
- real RocketDict core version and API identity;
- live Lab Registry hash with runtime probing enabled;
- Product Profile rebuilt from that live registry;
- locally available selected implementations for required upstream core stages **8, 10, 12, 14, 16, 17 and 19**;
- exact implementation keys, adapter descriptor hashes and parameter hashes;
- exact Stage15 hard-gate set: numeric/symbol preservation, punctuation preservation and length-ratio proxy;
- Product policy validation including fake/identity MT prohibition and accepted OPUS float32 rule;
- one immutable preflight fingerprint.

Projects with multiple imported sources must supply the exact `--source-sha256`; Product Mode does not guess. Source-path escape, missing/mutated source, missing durable document identity, missing registry hash, changed gate identity, unavailable required implementation or incompatible Product policy all fail closed before expensive processing.

Previous preflight checkpoint CI:

- commit `50afdd84ec99f55ca0fb940de517034419014c49`;
- workflow run `33872766481`;
- **40 passed, 1 skipped**.

## 2. Existing resumable Product downstream runner

A strict/resumable downstream Product runner exists in `rocketdict-workbench/src/rocketdict_workbench/product_runner.py` and is exposed through `rocketdict-workbench lexical-opus --apply-stage20 --continue-product`.

Current executable downstream order:

1. Stage20 `lexical-primary-arbitration-v1`;
2. pinned CEFR-J Vocabulary Profile 1.5 assessment;
3. exact CMUdict pronunciation with generated fallback forbidden;
4. Stage23 sense-scoped document examples.

The downstream runner is fail-closed and evidence-preserving:

- every step is persisted atomically in `rocketdict-workbench-product-downstream/1` state;
- successful steps are reused on resume;
- immutable input identity includes lexical-provider `entries_sha256`, exact Stage20 sense/entry/generation/selection revision identities, pinned CEFR-J SHA-256 and output-affecting settings;
- changed immutable inputs/settings reject state reuse;
- Stage20 arbitration requires the desired dictionary headword to already exist as an accepted model-evidenced candidate;
- CEFR coverage/order and pinned source identity are checked;
- pronunciation coverage/order is checked and generated fallback is forbidden;
- Stage23 coverage/order and `stage23-sense-scope-v2` are checked;
- every Stage23 row must reference exactly the approved Stage20 selection revision validated by lexical-primary arbitration;
- failed steps are recorded and remain resumable.

Previous verified downstream checkpoint:

- commit `cc43068b052761c0e1be66cfc9c5202732a241f5`;
- workflow run `33872151299`;
- **34 passed, 1 skipped**.

## 3. Do not regress the repository

The active `main` history is newer than several archived LAB checkpoints. At the 2026-09-02 synchronization, HEAD before the handoff update was:

`e9124f57698ebb1e36e1708f27be23374215560c` — **Add resumable Stage20 lexical primary arbitration**.

Recent repository work after the original Stage 8 handoff includes Product/Workbench alignment-aware lexical extraction, dictionary-shaped lexical OPUS, exact pronunciation policy, pinned CEFR-J policy, Stage20 lexical-primary arbitration, the resumable downstream Product runner, immutable Product preflight, and the unified Product-run/API-probe root described above.

Therefore an older LAB archive/version number must never overwrite this active line merely because it is a complete ZIP.

## 4. Active real-OPUS / experimental line

The public Stage 8 handoff remains the active real-model research context:

- development version recorded by the Stage 8 snapshot: **0.30.40**;
- official model: `opus-2020-02-11.zip`;
- official ZIP SHA-256 observed in successful GitHub execution: `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`;
- backend: CTranslate2 Marian, quality acceptance compute type `float32`;
- successful real-model GitHub gate: 120 representative sentences / 4,488 words;
- Stage 8 DOE frontier in `STATE.json`: F96, failing only the zero-numeric-loss gate with 3 numeric mismatches at that snapshot;
- current commits extend Product/Workbench dictionary work beyond that snapshot.

Read `START_HERE.md`, `STATE.json` and `RESEARCH_STATUS.md` for this line. Do not restart its DOE from variant A.

A surviving Stage8 diagnostic proves that the ordinary source-proven Stage12 pilot selector and historical F96 challenge selector are distinct. Aggregate similarity to old ~5k-word/occurrence counts is not proof of F96 identity. Do not reconstruct the missing F96 selector by coincidence.

## 5. Verified maintenance-hardening lineage

A separate fully verified maintenance checkpoint is preserved under `checkpoints/stage6y/`:

**RocketDict 0.30.34 / LAB Stage 6Y**.

It proves on its own lineage:

- `translation-offline-sqlite-compaction-v1`;
- `translation-offline-sqlite-compaction-recovery-v1`;
- `translation-offline-sqlite-compaction-io-fault-safety-v1`.

Stage 6Y covers journal ENOSPC/short-write, VACUUM disk-full, hardlink→copy backup ENOSPC, ambiguous atomic-replace I/O before/after namespace transition, recovery-cleanup I/O faults and ambiguous partial-journal fail-closed behavior.

Heavy challenge facts:

- baseline working SQLite: 881,905,664 bytes;
- baseline working SHA-256: `a0128b802930d350679c7d135bea9197fb9e202d863260c31a68d49681fbeafb`;
- after forced backup-copy ENOSPC, recovery restored the working DB byte-for-byte;
- canonical immutable heavy SHA-256 remained `3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274`;
- `quick_check=ok`, FK=0, Alembic head `8b4e7c2a91d0`;
- lexical entries = 35,743;
- translation runs/candidates/batch metrics/inference results/leases = 0/0/0/0/0;
- 301 packaged runtime files matched source byte-for-byte.

**Important:** the public repository does not contain enough exact source payload to prove these Stage 6Y maintenance changes are merged into newer 0.30.40/Stage8/Product source. Treat Stage 6Y as verified parallel evidence until an exact source merge/comparison is performed.

## 6. Payload health

The Stage 8 public binary/text payload is still incomplete. `HANDOFF_HEALTH.md` is authoritative for what survives in `rocketdict/payload/` and what cannot be materialized bit-for-bit.

Do not invent missing Stage 8 source files or Research Vault rows. Mechanism experiments may continue only when clearly labelled non-promotional and evidence-backed.

## 7. Exact continuation choices

### Continue the active Stage 8/Product line

Use current GitHub HEAD, Workbench/Product commits, `START_HERE.md`, `STATE.json` and `RESEARCH_STATUS.md`. Preserve official OPUS identity and existing DOE/evidence rules. Do not reset to an older LAB ZIP.

Immediate continuation after the unified Product-run/API-probe checkpoint:

- obtain actual `product-run-init` probe evidence from the exact real runtime available for Product work;
- prove one concrete Stage8–19 public operation binding from that evidence/runtime;
- encode that binding with exact API/core/registry/adapter identities and durable input/output hashes;
- execute only proven real-core calls and preserve exact revision/content identities across boundaries;
- enforce zero hard-quality failures before translation approval/alignment;
- reuse `workbench-aligned-content-pos-v4`, lexical OPUS, Stage20 arbitration and current downstream runner rather than duplicating them;
- add Stage24 cards and Stage25 export only after upstream/downstream continuity is proven;
- keep one-button Product UI disabled until the full path is executable and validated without synthetic fallbacks.

### Continue the Stage 6 maintenance-hardening line

Start from **0.30.34 / Stage 6Y**, read `checkpoints/stage6y/CONTINUE_STAGE6Z.md`, and execute Stage 6Z. To merge this line into active Stage8/Product source, first recover/materialize exact newer source and perform an explicit source-level merge plus full affected regressions; do not infer compatibility from version numbers.

## 8. Privacy boundary

This is a public repository. Persist only project technical/research state. Do not add personal user data, private chats, credentials, unrelated account information, local personal paths or private datasets.
