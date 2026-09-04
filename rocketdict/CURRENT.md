# CURRENT — RocketDict public continuation state

Last synchronized: **2026-09-04**.

## 0. Latest continuation increment — immutable Product source/runtime preflight

The active Workbench/Product line now has an executable fail-closed gate before the still-unwired upstream Stage8–19 production path.

`rocketdict-workbench product-preflight` creates a durable `rocketdict-workbench-product-preflight/1` record and refuses to declare the Product run ready unless the exact source and current real runtime are proven compatible with the Product Profile.

The preflight freezes and validates:

- the selected imported source SHA-256, byte size, suffix and project-relative immutable-copy path;
- a fresh SHA-256 of the copied source, rejecting mutation after import;
- import-event and interpretation identities as canonical hashes;
- source kind (`subtitle`/`text`), with optional explicit assertion;
- real RocketDict core version and API identity;
- the live Lab Registry hash obtained with runtime probing enabled;
- the Product Profile rebuilt from that live registry;
- locally available selected implementations for required upstream core stages **8, 10, 12, 14, 16, 17 and 19**;
- exact selected implementation keys, adapter descriptor hashes and parameter hashes;
- the exact Stage15 hard-gate set: numeric/symbol preservation, punctuation preservation and length-ratio proxy;
- Product policy validation, including fake/identity MT prohibition and the accepted OPUS float32 rule;
- one immutable preflight fingerprint over all of the above.

Projects with multiple imported sources must supply the exact `--source-sha256`; Product Mode does not guess. A copied path escaping the Workbench root, missing/mutated source, missing registry hash, changed gate identity, unavailable required implementation or incompatible Product policy all fail closed before expensive processing.

CLI additions:

- `product-preflight <project>`;
- `--source-sha256`;
- `--source-kind subtitle|text` as an optional assertion;
- `--output` for durable preflight evidence.

Relevant commits in this increment:

- `2380607d2e3fa5f1365e52132385ab046f345b6e` — `Add immutable Product source and runtime preflight`;
- `871b38ea41583b4329c75503f92dcde84af4fd59` — `Test immutable Product preflight contract`;
- `394b217dd4c917fea2b1d1eb884cdd588f6568b2` — `Expose immutable Product preflight in Workbench CLI`;
- `50afdd84ec99f55ca0fb940de517034419014c49` — `Test Product preflight CLI exposure`;
- `bf8b527b4b1f89f04adf41cb7c5422df62abd561` — `Document immutable Product preflight gate`.

Verified GitHub Actions evidence for the code/test checkpoint:

- commit: `50afdd84ec99f55ca0fb940de517034419014c49`;
- workflow: `RocketDict Workbench`, run `33872766481`;
- Python: 3.13.15;
- package compile: success;
- tests: **40 passed, 1 skipped**.

### Exact boundary after this increment

This preflight does **not** claim Stage8–19 execution is wired. The public handoff still does not contain enough exact newer-core source to safely invent internal service/module calls. The next active Product milestone is therefore:

1. bind this immutable preflight fingerprint into one unified resumable Product-run state;
2. recover or probe the exact real-core registry/API execution contract for Stage8–19 from surviving authoritative runtime/evidence;
3. only then execute source preparation → real MT → hard integrity gates → approved translation revision → alignment → lexical extraction/sense induction;
4. feed the resulting real Stage20 inputs into the already-working downstream runner;
5. add Stage24 cards and Stage25 export last.

Do not replace the missing upstream execution contract with a simplified parallel implementation or guessed Python imports.

## 1. Existing resumable Product downstream runner

A strict/resumable downstream Product runner already exists in `rocketdict-workbench/src/rocketdict_workbench/product_runner.py` and is exposed through `rocketdict-workbench lexical-opus --apply-stage20 --continue-product`.

Current executable downstream order:

1. Stage20 `lexical-primary-arbitration-v1`;
2. pinned CEFR-J Vocabulary Profile 1.5 assessment;
3. exact CMUdict pronunciation with generated fallback forbidden;
4. Stage23 sense-scoped document examples.

The downstream runner is deliberately fail-closed and evidence-preserving:

- every step is persisted atomically in `rocketdict-workbench-product-downstream/1` state;
- successful steps are reused on resume instead of being blindly repeated;
- immutable run identity includes lexical-provider `entries_sha256`, exact Stage20 sense/entry/generation/selection revision identities, pinned CEFR-J SHA-256 and output-affecting Product settings;
- changing those immutable inputs/settings rejects state reuse instead of mixing evidence from different runs;
- Stage20 arbitration requires the desired dictionary headword to already exist as an accepted model-evidenced candidate;
- CEFR coverage/order and pinned source identity are checked;
- pronunciation coverage/order is checked and generated fallback remains forbidden;
- Stage23 coverage/order and `stage23-sense-scope-v2` are checked;
- every Stage23 row must reference exactly the approved Stage20 selection revision produced/validated by lexical-primary arbitration; a newer/unrelated approved revision is treated as review-identity drift and stops the run;
- failed steps are recorded with error type/message and remain resumable; completed earlier steps remain durable.

Previous verified checkpoint for this downstream slice:

- commit: `cc43068b052761c0e1be66cfc9c5202732a241f5` — `Document resumable Product downstream pipeline`;
- workflow: `RocketDict Workbench`, run `33872151299`;
- tests: **34 passed, 1 skipped**.

## 2. Do not regress the repository

The active `main` history is newer than several archived LAB checkpoints. At the 2026-09-02 synchronization, HEAD before the handoff update was:

`e9124f57698ebb1e36e1708f27be23374215560c` — **Add resumable Stage20 lexical primary arbitration**.

Recent repository work after the original Stage 8 handoff includes Product/Workbench alignment-aware lexical extraction, dictionary-shaped lexical OPUS, exact pronunciation policy, pinned CEFR-J policy, Stage20 lexical-primary arbitration, the resumable downstream Product runner and the immutable Product preflight described above.

Therefore an older LAB archive/version number must never be used to overwrite this active line merely because it is a complete ZIP.

## 3. Active real-OPUS / experimental line

The public Stage 8 handoff remains the active real-model research context:

- development version recorded by the Stage 8 snapshot: **0.30.40**;
- official model: `opus-2020-02-11.zip`;
- official ZIP SHA-256 observed in successful GitHub execution: `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`;
- backend: CTranslate2 Marian, quality acceptance compute type `float32`;
- successful real-model GitHub gate: 120 representative sentences / 4,488 words;
- Stage 8 DOE frontier recorded in `STATE.json`: F96, failing only the zero-numeric-loss gate with 3 numeric mismatches at that snapshot;
- current repository commits subsequently extend Product/Workbench dictionary work beyond that snapshot.

Read `START_HERE.md`, `STATE.json` and `RESEARCH_STATUS.md` for this line. Do not restart its DOE from variant A.

A surviving Stage8 diagnostic also proves that the ordinary source-proven Stage12 pilot selector and the historical F96 challenge selector are distinct. Aggregate similarity to the old ~5k-word/occurrence counts is not proof of F96 identity. Do not reconstruct the missing F96 selector by coincidence.

## 4. Verified maintenance-hardening lineage

A separate fully verified maintenance checkpoint is preserved under `checkpoints/stage6y/`:

**RocketDict 0.30.34 / LAB Stage 6Y**.

It proves the following contracts on its own lineage:

- `translation-offline-sqlite-compaction-v1`;
- `translation-offline-sqlite-compaction-recovery-v1`;
- `translation-offline-sqlite-compaction-io-fault-safety-v1`.

Stage 6Y covers journal ENOSPC/short-write, VACUUM disk-full, hardlink→copy backup ENOSPC, ambiguous atomic replace I/O failures before/after namespace transition, recovery cleanup I/O faults and ambiguous partial-journal fail-closed behavior.

Heavy challenge facts:

- baseline working SQLite: 881,905,664 bytes;
- baseline working SHA-256: `a0128b802930d350679c7d135bea9197fb9e202d863260c31a68d49681fbeafb`;
- after forced backup-copy ENOSPC, recovery restored the working DB byte-for-byte;
- canonical immutable heavy SHA-256 remained `3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274`;
- `quick_check=ok`, FK=0, Alembic head `8b4e7c2a91d0`;
- lexical entries = 35,743;
- translation runs/candidates/batch metrics/inference results/leases = 0/0/0/0/0;
- 301 packaged runtime files matched source byte-for-byte in that checkpoint.

**Important:** the public repository does not currently contain enough exact source payload to prove that these Stage 6Y maintenance changes are merged into the newer 0.30.40/Stage8/Product source. Treat Stage 6Y as verified parallel evidence until an exact source merge/comparison is performed.

## 5. Payload health

The Stage 8 public binary/text payload is still incomplete. `HANDOFF_HEALTH.md` is authoritative for what survives in `rocketdict/payload/` and what cannot yet be materialized bit-for-bit.

Do not invent missing Stage 8 source files or Research Vault rows. Mechanism experiments can continue only when clearly labelled non-promotional and evidence-backed.

## 6. Exact continuation choices

### Continue the active Stage 8/Product line

Use the current GitHub HEAD, Workbench/Product commits, `START_HERE.md`, `STATE.json` and `RESEARCH_STATUS.md`. Preserve the official OPUS identity and the existing DOE/evidence rules. Do not reset to an older LAB ZIP.

Immediate continuation after the Product preflight checkpoint:

- create a unified Product-run state whose immutable root identity is the preflight fingerprint;
- recover/probe the real core's exact registry-backed Stage8–19 execution surface instead of guessing internal services;
- extend the state machine upstream only through proven real-core calls;
- enforce exact stage/revision/content identities and zero hard-quality failures before translation approval/alignment;
- reuse `workbench-aligned-content-pos-v4`, existing lexical OPUS/Stage20 arbitration and current downstream runner instead of duplicating them;
- add Stage24 cards and Stage25 export after upstream/downstream continuity is proven;
- do not enable the one-button Product UI until the full path is executable and validated without synthetic fallbacks.

### Continue the Stage 6 maintenance-hardening line

Start from **0.30.34 / Stage 6Y**, read `checkpoints/stage6y/CONTINUE_STAGE6Z.md`, and execute Stage 6Z. If this line is to be merged into the active Stage 8/Product source, first recover/materialize the exact newer source and perform an explicit source-level merge plus full affected regressions; do not infer compatibility from version numbers.

## 7. Privacy boundary

This is a public repository. Persist only project technical/research state. Do not add personal user data, private chats, credentials, unrelated account information, local personal paths or private datasets.
