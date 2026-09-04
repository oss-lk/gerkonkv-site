# CURRENT — RocketDict public continuation state

Last synchronized: **2026-09-04**.

## 0. Latest continuation increment — resumable Product downstream runner

The active Workbench/Product line has advanced beyond the standalone Stage20 arbitration checkpoint.

A first strict/resumable Product runner slice now exists in `rocketdict-workbench/src/rocketdict_workbench/product_runner.py` and is exposed through `rocketdict-workbench lexical-opus --apply-stage20 --continue-product`.

Current executable downstream order:

1. Stage20 `lexical-primary-arbitration-v1`;
2. pinned CEFR-J Vocabulary Profile 1.5 assessment;
3. exact CMUdict pronunciation with generated fallback forbidden;
4. Stage23 sense-scoped document examples.

The runner is deliberately fail-closed and evidence-preserving:

- every step is persisted atomically in `rocketdict-workbench-product-downstream/1` state;
- successful steps are reused on resume instead of being blindly repeated;
- immutable run identity includes lexical-provider `entries_sha256`, exact Stage20 sense/entry/generation/selection revision identities, pinned CEFR-J SHA-256 and output-affecting Product settings;
- changing those immutable inputs/settings rejects state reuse instead of mixing evidence from different runs;
- Stage20 arbitration still requires the desired dictionary headword to already exist as an accepted model-evidenced candidate;
- CEFR coverage/order and pinned source identity are checked;
- pronunciation coverage/order is checked and generated fallback remains forbidden;
- Stage23 coverage/order and `stage23-sense-scope-v2` are checked;
- critically, every Stage23 row must reference exactly the approved Stage20 selection revision produced/validated by lexical-primary arbitration; a newer/unrelated approved revision is treated as review-identity drift and stops the run;
- failed steps are recorded with error type/message and remain resumable; completed earlier steps remain durable.

CLI additions:

- `--continue-product`;
- `--cefrj-asset`;
- `--product-state`;
- `--include-russian-pronunciation-hint` (included in immutable run fingerprint).

Verified GitHub Actions evidence for the complete code/test/documentation checkpoint:

- commit: `cc43068b052761c0e1be66cfc9c5202732a241f5` — `Document resumable Product downstream pipeline`;
- workflow: `RocketDict Workbench`, run `33872151299`;
- Python: 3.13.15;
- package compile: success;
- tests: **34 passed, 1 skipped**.

This is not yet the complete one-button dictionary pipeline. The next active Product milestone is to extend the same runner **upward** through source preparation → real MT → hard integrity gates → approved translation revision → alignment → lexical extraction/sense induction, and **downward** from Stage23 through cards/export. Existing real stage implementations and evidence contracts must be orchestrated, not reimplemented in a parallel simplified stack.

## 1. Do not regress the repository

The active `main` history is newer than several archived LAB checkpoints. At the 2026-09-02 synchronization, HEAD before the handoff update was:

`e9124f57698ebb1e36e1708f27be23374215560c` — **Add resumable Stage20 lexical primary arbitration**.

Recent repository work after the original Stage 8 handoff includes Product/Workbench alignment-aware lexical extraction, dictionary-shaped lexical OPUS, exact pronunciation policy, pinned CEFR-J policy, Stage20 lexical-primary arbitration and the resumable downstream Product runner described above.

Therefore an older LAB archive/version number must never be used to overwrite this active line merely because it is a complete ZIP.

## 2. Active real-OPUS / experimental line

The public Stage 8 handoff remains the active real-model research context:

- development version recorded by the Stage 8 snapshot: **0.30.40**;
- official model: `opus-2020-02-11.zip`;
- official ZIP SHA-256 observed in successful GitHub execution: `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`;
- backend: CTranslate2 Marian, quality acceptance compute type `float32`;
- successful real-model GitHub gate: 120 representative sentences / 4,488 words;
- Stage 8 DOE frontier recorded in `STATE.json`: F96, failing only the zero-numeric-loss gate with 3 numeric mismatches at that snapshot;
- current repository commits subsequently extend Product/Workbench downstream dictionary work beyond that snapshot.

Read `START_HERE.md`, `STATE.json` and `RESEARCH_STATUS.md` for this line. Do not restart its DOE from variant A.

## 3. Verified maintenance-hardening lineage

A separate fully verified maintenance checkpoint is now preserved under `checkpoints/stage6y/`:

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

## 4. Payload health

The Stage 8 public binary/text payload is still incomplete. `HANDOFF_HEALTH.md` is authoritative for what survives in `rocketdict/payload/` and what cannot yet be materialized bit-for-bit.

Do not invent missing Stage 8 source files or Research Vault rows. Mechanism experiments can continue only when clearly labelled non-promotional and evidence-backed.

## 5. Exact continuation choices

### Continue the active Stage 8/Product line

Use the current GitHub HEAD, Workbench/Product commits, `START_HERE.md`, `STATE.json` and `RESEARCH_STATUS.md`. Preserve the official OPUS identity and the existing DOE/evidence rules. Do not reset to an older LAB ZIP.

Immediate continuation after the resumable downstream runner checkpoint:

- inspect/reuse the existing core contracts for source preparation, Stage12 real MT, Stage15 hard reference-free integrity gates, translation approval/finalization, Stage17/19 alignment/context and Stage18 lexical extraction/sense induction;
- extend the same immutable/resumable state machine upward until it can produce the Stage20 inputs itself;
- then add Stage24 cards and Stage25 export as the final downstream tail;
- require exact stage/revision/content identities across boundaries, just as Stage20→Stage23 is now enforced;
- do not enable the one-button Product UI until the full path is executable and validated without synthetic fallbacks.

### Continue the Stage 6 maintenance-hardening line

Start from **0.30.34 / Stage 6Y**, read `checkpoints/stage6y/CONTINUE_STAGE6Z.md`, and execute Stage 6Z. If this line is to be merged into the active Stage 8/Product source, first recover/materialize the exact newer source and perform an explicit source-level merge plus full affected regressions; do not infer compatibility from version numbers.

## 6. Privacy boundary

This is a public repository. Persist only project technical/research state. Do not add personal user data, private chats, credentials, unrelated account information, local personal paths or private datasets.
