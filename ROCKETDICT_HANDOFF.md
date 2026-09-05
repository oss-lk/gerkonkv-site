# RocketDict public handoff

This repository is the public, project-only continuation point for RocketDict.

## Authoritative entrypoint

**Start with [`rocketdict/CURRENT.md`](rocketdict/CURRENT.md).**

Then use:

- [`rocketdict-workbench/docs/CORE_RECOVERY.md`](rocketdict-workbench/docs/CORE_RECOVERY.md) — operational exact-core/checkpoint recovery workflow;
- [`rocketdict/START_HERE.md`](rocketdict/START_HERE.md) — Stage8 / real-OPUS research context;
- [`rocketdict/HANDOFF_HEALTH.md`](rocketdict/HANDOFF_HEALTH.md) — original public payload-materialization health record;
- [`rocketdict/recovered/stage8-0.30.40/recovery.json`](rocketdict/recovered/stage8-0.30.40/recovery.json) — exact recovered 0.30.40 byte evidence and blocker;
- [`rocketdict/recovered/stage8-0.30.40/core-recovery-history.json`](rocketdict/recovered/stage8-0.30.40/core-recovery-history.json) — machine-readable historical recovery map;
- [`rocketdict/STATE.json`](rocketdict/STATE.json) — historical Stage8 snapshot;
- [`rocketdict/checkpoints/stage6y/`](rocketdict/checkpoints/stage6y/) — verified 0.30.34 / LAB Stage6Y maintenance-hardening checkpoint.

## Current repository frontier

The active Workbench/Product implementation is already resumable through Stage25. The main blocker is **not missing orchestration**: it is the absence of a complete exact-compatible runnable RocketDict core/public API.

Exact 0.30.40 recovery currently preserves only two complete source members from a truncated Stage8 artifact prefix. Historical materializer/ancestry analysis proves that the intended 19-file Stage8 overlay did not include `rocketdict.api.*`; recovering the remaining overlay chunks alone therefore cannot reconstruct the complete base core.

Workbench now contains three fail-closed recovery tools:

- `rocketdict-recover-core` — inspect one source directory/ZIP candidate;
- `rocketdict-recover-plan` — deterministic read-only base→0.30.40 compatibility plan;
- `rocketdict-recover-scan` — batch screening/ranking of old ZIP/checkouts.

Current recovery math for the historical Stage8 overlay contract is 19 intended members, 2 exact target bytes available, 17 exact target bytes missing. The exact 0.30.40 public API bytes remain unrecovered and unproven.

Latest verified recovery code checkpoint:

- commit `d1e94eced4deaeec9e9a9a3a70fecdee48572e12`
- `RocketDict Workbench` run `33964578578`
- job `101302315173`
- Python 3.13.15
- compile success
- **153 passed, 1 skipped**.

A separate verified maintenance-hardening lineage reached RocketDict 0.30.34 / LAB Stage6Y. That checkpoint must not be assumed source-level merged into the active Product lineage unless exact source comparison and regression prove it.

## Immediate continuation

1. Recover any complete historical RocketDict checkpoint/source bytes from old uploads, machines, archives or another provenance-verifiable source.
2. Run `rocketdict-recover-scan` over the recovered collection.
3. Run `rocketdict-recover-core` and `rocketdict-recover-plan` on the strongest candidate.
4. Do not manufacture missing 0.30.40 overlay/API bytes.
5. Only after a complete exact-compatible runtime exists: Workbench doctor → import → immutable Product preflight → live registry/API probe → exact binding/execution proof → genuine Stage8 dispatch → continue through Stage25.
6. After runtime continuity is proven, run the full 90k+ public-domain validation corpus without truncation and retain the complete translation/research evidence database.

## Non-negotiable continuation rules

- Never replace real MT with fake/identity/dictionary translation and call it success.
- Never silently truncate the 104k+ *Opticks* corpus or another required long corpus.
- Preserve immutable hashes, failed experiments and audit evidence.
- Do not weaken quality gates merely to obtain a green run.
- Do not overwrite the newer active lineage with an older checkpoint; verified parallel checkpoints remain explicit lineages until compatibility is proven.
- This repository is public: keep it project-only. Do not add personal profile, location, account data, credentials, private conversations or unrelated files.
