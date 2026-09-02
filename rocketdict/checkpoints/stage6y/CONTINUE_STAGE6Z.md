# Continue — LAB Stage 6Z maintenance lineage

Start from **RocketDict 0.30.34 / Stage 6Y** only when continuing the maintenance-hardening lineage.

Verified state:

- offline compaction contract: `translation-offline-sqlite-compaction-v1`;
- hard-crash recovery: `translation-offline-sqlite-compaction-recovery-v1`;
- ENOSPC/I/O safety: `translation-offline-sqlite-compaction-io-fault-safety-v1`;
- journal ENOSPC/short-write, VACUUM disk-full, copy-fallback ENOSPC, atomic replace EIO before/after and recovery cleanup I/O faults are covered;
- ambiguous partial journal without durable journal fails closed and is retained;
- atomic replace exceptions never delete rollback backup based on an assumption; recovery decides from verified candidates;
- representative installed-wheel faults and heavy backup-copy ENOSPC are verified;
- heavy fault restored the 881,905,664-byte primary byte-for-byte;
- canonical source SHA remains `3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274`;
- quality-first translation identity is unchanged within this maintenance lineage.

## If official OPUS is available in the execution environment

Use the original official `opus-2020-02-11.zip` → CTranslate2 `float32` → importer smoke → real bound pilot → full resumable 104,257-word Stage 12 → Stage 13 explicit skip-equivalent → Stage 14–30.

Note: the newer active Stage 8 repository line already has successful official-OPUS GitHub execution. Do not use that fact to claim the 0.30.34 maintenance source is merged with the newer source; merge status must be proven separately.

## If continuing Stage 6Z hardening

Inspect and prove **cross-process offline-maintenance coordination**.

Race:

1. two compaction processes;
2. compaction vs retention apply;
3. compaction vs recovery;
4. operations around pre-journal creation;
5. `VACUUM INTO` writer reservation;
6. post-lock WAL verification;
7. rollback-backup creation;
8. atomic namespace swap.

Required property: no process may mutate/delete another **live** maintenance operation's journal/temp/backup.

First prove existing journal-owner + SQLite writer-lock behavior with real subprocess race tests. Only if insufficient, add a durable sidecar maintenance lease/fencing contract with PID + process-start identity and stale-owner recovery.

Then run source + separately installed-wheel checks + representative heavy audit and package one checkpoint.

## Merge rule

If these changes are to enter the newer Stage 8/Product line, recover the exact newer source first and perform an explicit merge. Rerun all compaction/recovery/retention/storage/lease tests and relevant Stage 8/Product tests. Never replace the newer repository line wholesale with the older maintenance tree.
