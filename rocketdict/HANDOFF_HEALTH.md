# RocketDict public handoff health

Last synchronized: **2026-09-02**.

## Overall status

The repository is **usable for continuation as a technical/research handoff**, but it contains two distinct kinds of evidence that must not be conflated:

1. a newer active Stage 8/Product/Workbench repository line with real official OPUS GitHub execution and downstream lexical/product commits;
2. a separately verified RocketDict **0.30.34 / LAB Stage 6Y** maintenance-hardening checkpoint whose report/continuation evidence is mirrored under `rocketdict/checkpoints/stage6y/`.

The exact source-level merge status between those lineages is **not proven** by the public payload. Do not overwrite one with the other based on version numbering alone.

## Stage 8 payload health

`rocketdict/materialize_handoff.py` remains authoritative about the intended Stage 8 payload contract. The public payload is still not bit-for-bit self-contained.

Known intended payloads include the Stage 8 source overlay and Research Vault chunks. The surviving repository material is sufficient to recover research direction, official OPUS identity, several source fragments and mechanism evidence, but not sufficient to reconstruct every exact Stage 8 source file and Research Vault row from a fresh clone.

Therefore:

- do not claim full Stage 8 source materialization from this repository alone;
- do not fabricate missing source or vault rows;
- keep standalone mechanism probes non-promotional until integrated into recovered exact source;
- retain the existing F96/Stage8 evidence and do not restart DOE from A.

## Stage 6Y checkpoint health

The mirrored Stage 6Y report is a complete verified **evidence/handoff record**, not a source-code mirror.

Verified checkpoint facts include:

- RocketDict 0.30.34 / LAB Stage 6Y;
- I/O/ENOSPC-safe offline compaction/recovery contracts;
- 10/10 individual source fault-matrix checks;
- selected Stage 6W regressions 5/5 and LAB runner 7/7;
- representative installed-wheel fault paths passed;
- 301 packaged runtime files byte-for-byte matched source in that checkpoint;
- heavy backup-copy ENOSPC challenge restored the 881,905,664-byte working primary byte-for-byte;
- canonical heavy source SHA-256 remained `3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274`;
- `quick_check=ok`, FK=0, Alembic head `8b4e7c2a91d0`.

The actual 0.30.34 source tree/wheel/heavy DB are deliberately **not** copied into this public repository by this synchronization because the currently accessible handoff material is documentary/evidence-level and the repo is public.

## Continuation rule

Read `rocketdict/CURRENT.md` first.

- For active Stage 8/Product work: continue from current GitHub HEAD and existing Workbench/Product history.
- For Stage 6 maintenance hardening: use `rocketdict/checkpoints/stage6y/CONTINUE_STAGE6Z.md`.
- If merging lineages: recover exact source snapshots first, perform an explicit source merge, and rerun all affected tests/evidence. Never declare the merge from documentation similarity alone.

## Privacy

This health record is intentionally project-only. Do not add personal profile, location, account data, credentials, private conversations or unrelated artifacts to this public repository.
