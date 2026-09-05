# RocketDict public handoff

This repository is the public, project-only continuation point for RocketDict.

## Authoritative entrypoint

Start with [`rocketdict/CURRENT.md`](rocketdict/CURRENT.md).

Then read:

- [`rocketdict-workbench/docs/CORE_RECOVERY.md`](rocketdict-workbench/docs/CORE_RECOVERY.md);
- [`rocketdict/recovered/recovery-frontier-2026-09-05.json`](rocketdict/recovered/recovery-frontier-2026-09-05.json) — current machine-readable frontier, schema `/4`;
- [`rocketdict/recovered/checkpoint-catalog.json`](rocketdict/recovered/checkpoint-catalog.json);
- [`rocketdict/recovered/late-stage6-artifact-identities-2026-09-05.json`](rocketdict/recovered/late-stage6-artifact-identities-2026-09-05.json);
- [`rocketdict/recovered/search-exhaustion-2026-09-05.json`](rocketdict/recovered/search-exhaustion-2026-09-05.json) — searches already exhausted;
- [`rocketdict/recovered/stage8-0.30.40/recovery.json`](rocketdict/recovered/stage8-0.30.40/recovery.json) and [`core-recovery-history.json`](rocketdict/recovered/stage8-0.30.40/core-recovery-history.json);
- [`rocketdict/checkpoints/stage6y/`](rocketdict/checkpoints/stage6y/) for the separate maintenance lineage.

## Current frontier

Workbench Product orchestration already reaches resumable Stage25. The hard blocker is a complete exact-compatible RocketDict core/public API runtime, not missing pipeline code.

Exact 0.30.40 recovery still has only two complete Stage8 overlay members out of 19; 17 exact targets and the exact public API bytes remain missing.

Best historical recovery target:

`RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip`

SHA-256 `3cd150c012c28d0e8c458ba25bff56a8e9c17789d2c6986d8b6b72e202d5c387`.

Historical size is unknown and must never be guessed. Historical output proves the full archive existed, passed unzip/regression/package checks and was handed off.

Alternate:

`rocketdict-0.30.34-py3-none-any.whl`

SHA-256 `76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`.

Neither exact artifact's bytes are currently recovered.

## Recovery commands and proof

Installed commands:

- `rocketdict-recover-core`
- `rocketdict-recover-plan`
- `rocketdict-recover-checkpoint`
- `rocketdict-recover-wheel`
- `rocketdict-recover-scan`
- `rocketdict-product-run`

Focused full-checkpoint proof schema: `rocketdict-workbench-full-checkpoint-recovery/2`.

Unified scan schema: `rocketdict-workbench-core-recovery-scan/8`.

For every discovered ZIP, unified scan automatically attaches the read-only checkpoint proof. The proof verifies:

1. outer ZIP safety/CRC and exact catalog SHA;
2. unique RocketDict source root and source version;
3. SHA-256 inventory of `api/contracts.py`, `api/client.py`, `api/cli.py` when present;
4. nested RocketDict wheel CRC/METADATA/WHEEL/RECORD;
5. nested wheel exact catalog SHA/optional-size identity;
6. source↔wheel package-byte parity;
7. README/report/manifest/state evidence inventory with explicit eligible/selected/limit/truncated counters;
8. historical-base→exact-0.30.40 compatibility plan.

It never extracts or executes checkpoint code. Wrong nested wheel SHA, corrupt RECORD or source↔wheel drift blocks the checkpoint. Exact historical 0.30.34 evidence still does not become exact 0.30.40 Product identity.

## Latest verified checkpoint

- commit `ed86467011efb5a680647e56007728d0cbb16157`
- Workbench run `33975530978`
- job `101331437743`
- Ubuntu 24.04.4
- Python 3.13.15
- compile success
- installed CLI smoke success
- **203 passed, 1 skipped in 2.46s**.

Preserve failed run `33975210119`: the new checkpoint logic passed and one stale test expected unified schema `/7`; it was corrected to `/8` without weakening recovery rules.

## Immediate continuation

Do not repeat recovery searches already closed in `search-exhaustion-2026-09-05.json` without new evidence.

When provenance-verifiable bytes appear:

1. prefer the exact full Stage6Y ZIP;
2. run `rocketdict-recover-scan` and retain `rocketdict-recover-checkpoint` output;
3. prove outer identity, source API hashes, nested exact wheel identity/RECORD and source↔wheel parity;
4. resolve base→exact-0.30.40 compatibility without fabricating the 17 missing exact targets;
5. only after an exact-compatible runtime exists: doctor → real import → Product preflight → live registry/API probe → exact binding/execution → genuine Stage8 → continue through Stage25;
6. run the full 90k+ public-domain corpus without truncation and retain the complete translation/research evidence database.

## Non-negotiable rules

- Never replace real MT with fake/identity/dictionary translation and call it success.
- Never silently truncate required corpora or evidence inventories.
- Preserve hashes, failed experiments and audit evidence.
- Do not weaken quality gates for a green run.
- Do not treat Stage6Y as Product source without exact compatibility proof and regression.
- Keep the public repository free of personal/account/private-conversation data.
