# CURRENT — RocketDict public continuation state

Last synchronized: **2026-09-02**.

## 1. Do not regress the repository

The active `main` history is newer than several archived LAB checkpoints. At synchronization, HEAD before this update was:

`e9124f57698ebb1e36e1708f27be23374215560c` — **Add resumable Stage20 lexical primary arbitration**.

Recent repository work after the original Stage 8 handoff includes Product/Workbench alignment-aware lexical extraction, dictionary-shaped lexical OPUS, exact pronunciation policy, pinned CEFR-J policy and Stage20 lexical-primary arbitration.

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

### Continue the Stage 6 maintenance-hardening line

Start from **0.30.34 / Stage 6Y**, read `checkpoints/stage6y/CONTINUE_STAGE6Z.md`, and execute Stage 6Z. If this line is to be merged into the active Stage 8/Product source, first recover/materialize the exact newer source and perform an explicit source-level merge plus full affected regressions; do not infer compatibility from version numbers.

## 6. Privacy boundary

This is a public repository. Persist only project technical/research state. Do not add personal user data, private chats, credentials, unrelated account information, local personal paths or private datasets.
