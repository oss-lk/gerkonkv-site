# RocketDict 0.30.34 — LAB Stage 6Y

## Цель

Закрыть I/O/ENOSPC failure semantics для Stage 6W/6X offline SQLite compaction/recovery. Disk-full, short-write, ambiguous rename error и cleanup I/O failure не должны удалять последнюю verified primary или единственную доказанно корректную rollback-копию. Неоднозначный residue должен блокировать автоматическое продолжение, а не разрешаться догадкой.

## Новый контракт

`translation-offline-sqlite-compaction-io-fault-safety-v1`

### Journal write

- atomic JSON journal проверяет полный размер записи;
- покрыты ENOSPC, short-write и I/O error на journal path;
- временный journal-файл удаляется best-effort;
- partial `.compaction-recovery.json.tmp-*` без durable journal считается неоднозначным evidence: recovery fail-closed и не удаляет его автоматически;
- audit публикует `journal_temp_count`, `journal_temp_bytes` и `ambiguous_partial_recovery_journal`.

### VACUUM destination

`database or disk is full` с частично созданным compact-temp оставляет verified primary неизменной. Пока journal доказывает original primary, partial temp может быть безопасно удалён; journal после normal exception снимается только после доказанного recovery/cleanup.

### Rollback backup

Hardlink→copy fallback отдельно проверен с partial backup + ENOSPC. Partial copy не считается backup evidence. Recovery видит verified original primary и journal fingerprint, удаляет только доказанно неполный temp/backup и сохраняет primary.

### Atomic replace

Критическое исправление Stage 6Y: exception вокруг `os.replace(temp, primary)` больше **никогда** не удаляет rollback backup на предположении, что rename не состоялся.

Проверены два режима:

- `atomic_replace_eio_before`: namespace transition не произошёл → recovery сохраняет verified original primary;
- `atomic_replace_eio_after`: `os.replace` уже произошёл, но caller получает EIO → recovery по primary+backup+fingerprints обнаруживает фактический replacement и принимает verified compacted primary.

Ambiguous syscall outcome разрешается доказательствами, а не веткой исключения.

### Recovery cleanup

I/O failure при удалении temp/backup/journal не считается завершённым recovery. Verified primary остаётся на месте, journal и неубранное evidence сохраняются. Следующий `recover` без fault повторяет cleanup идемпотентно.

## Source fault matrix

10/10 individual clean-exit:

1. journal ENOSPC;
2. journal short-write;
3. VACUUM destination ENOSPC;
4. backup copy-fallback ENOSPC;
5. atomic replace EIO before transition;
6. atomic replace EIO after transition;
7. recovery temp cleanup EIO;
8. recovery backup cleanup EIO;
9. recovery journal cleanup EIO;
10. ambiguous partial journal fail-closed.

Selected Stage 6W regressions: 5/5. LAB runner: 7/7.

## Installed wheel evidence

Representative installed-wheel paths passed:

- journal ENOSPC;
- backup copy ENOSPC;
- atomic replace EIO-after;
- ambiguous partial journal fail-closed;
- crash + recovery backup-cleanup EIO preserving primary+backup+journal, then second recovery accepting the verified compacted primary.

All **301 packaged runtime files** matched source byte-for-byte in this checkpoint.

## Heavy ENOSPC challenge

On a fresh mutable working copy of the canonical heavy SQLite through the installed 0.30.34 wheel:

- baseline working bytes: **881,905,664**;
- baseline working SHA-256: `a0128b802930d350679c7d135bea9197fb9e202d863260c31a68d49681fbeafb`;
- full `VACUUM INTO` reached verified temp;
- hardlink was deliberately forced into copy fallback;
- copy created a partial backup and received `OSError errno=28`;
- recovery removed temp/partial backup/journal;
- working SHA after recovery was exactly the same `a0128b...`;
- canonical source SHA before/after remained `3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274`;
- residue temp/backup/journal = 0/0/false;
- `quick_check=ok`; FK=0; Alembic head `8b4e7c2a91d0`;
- lexical entries = 35,743;
- translation runs/candidates/batch metrics/inference results/leases = 0/0/0/0/0.

Installed-wheel LAB audit reported `offline_compaction_ready=true`; recovery, I/O safety, retention, storage and translation-lease checks were visible.

## Translation identity

This I/O safety work concerns offline maintenance and does not change model/runtime/tokenizer/generation/checkpoint semantics. The checkpoint therefore retained:

- configuration: `dc8e07c493b733bc14a6c9fcbb425539525cbfcf1632c25d8652687a9c33fbbf`;
- adapter catalog: `3f62a9a0ce463ee1505cd05ac70f77896820a28823e71beac86d07ab5782d25a`;
- execution policy: `75d9b29f72f2f87844db916c4b445cb3282fb9814329ee097bc84c4b64f6384b`;
- Stage 12/13 exact contract: `b6f2d5b9dfb1b0e5a0372977e585fc1f013dd7565bc633c7fd1bfb83a69755e5`.

## Real OPUS status in this checkpoint

The Stage 6Y execution environment could not acquire official OPUS bytes: DNS/TCP/TLS failed and model files remained absent. Fake/identity/dictionary/third-party weights were not used.

This is a historical environment fact for the Stage 6Y lineage. The newer Stage 8 repository line later succeeded in running the official OPUS model through GitHub Actions; do not confuse the two execution environments.

## Следующий этап maintenance-линии — Stage 6Z

See [`CONTINUE_STAGE6Z.md`](CONTINUE_STAGE6Z.md).

If this maintenance lineage is merged into the newer Stage 8/Product source, first recover exact source snapshots and prove the merge with source comparison + affected regressions. Do not infer merge status from version numbers.
