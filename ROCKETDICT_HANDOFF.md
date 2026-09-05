# RocketDict public handoff

This repository is the public, project-only continuation point for RocketDict.

## Authoritative entrypoint

Start with [`rocketdict/CURRENT.md`](rocketdict/CURRENT.md).

Then read:

- [`rocketdict-workbench/docs/CORE_RECOVERY.md`](rocketdict-workbench/docs/CORE_RECOVERY.md) — operational exact-core recovery workflow;
- [`rocketdict/recovered/checkpoint-catalog.json`](rocketdict/recovered/checkpoint-catalog.json) — exact/name-only historical artifact identities;
- [`rocketdict/recovered/late-stage6-artifact-identities-2026-09-05.json`](rocketdict/recovered/late-stage6-artifact-identities-2026-09-05.json) — recovered 0.30.29→0.30.34 provenance;
- [`rocketdict/recovered/recovery-frontier-2026-09-05.json`](rocketdict/recovered/recovery-frontier-2026-09-05.json) — machine-readable current recovery priority;
- [`rocketdict/recovered/search-exhaustion-2026-09-05.json`](rocketdict/recovered/search-exhaustion-2026-09-05.json) — recovery surfaces already checked;
- [`rocketdict/recovered/stage8-0.30.40/recovery.json`](rocketdict/recovered/stage8-0.30.40/recovery.json) and [`core-recovery-history.json`](rocketdict/recovered/stage8-0.30.40/core-recovery-history.json) — exact surviving 0.30.40 evidence;
- [`rocketdict/checkpoints/stage6y/`](rocketdict/checkpoints/stage6y/) — separate verified Stage6Y maintenance evidence.

## Current frontier

The Workbench Product pipeline already reaches resumable Stage25. Missing orchestration is not the blocker; the blocker is a complete exact-compatible RocketDict core/public API runtime.

Exact 0.30.40 recovery preserves two complete Stage8 overlay members. The intended overlay had 19 members and did not include `rocketdict.api.*`, so missing overlay chunks alone cannot restore the public API.

Current exact-target state:

- intended overlay members: 19
- exact available: 2
- exact missing: 17
- exact 0.30.40 public API modules recovered: 0

## Corrected best historical recovery target

A previous handoff incorrectly said Stage6Y release ZIP packaging did not complete. Historical project output proves that a full verified ZIP was created and explicitly handed off.

Primary target:

`RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip`

SHA-256:

`3cd150c012c28d0e8c458ba25bff56a8e9c17789d2c6986d8b6b72e202d5c387`

Historical size is unknown and must not be guessed. Historical verification recorded `unzip -t` success, `7/7` new fault-injection tests, `34/34` targeted regressions, compileall/wheel install/source↔wheel parity success.

Alternate packaged-core target:

`rocketdict-0.30.34-py3-none-any.whl`

SHA-256:

`76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`

Neither artifact's bytes are currently present in the active recovery runtime.

## Recovery commands

- `rocketdict-recover-core`
- `rocketdict-recover-plan`
- `rocketdict-recover-wheel`
- `rocketdict-recover-scan`

Checkpoint ZIP identity is SHA-first: exact SHA-256 is sufficient when old byte size is unavailable; if a size is known, it must also match. Filename alone is never proof.

Wheel proof remains integrity/catalog/structure/plan gated before optional isolated runtime import.

## Latest verified corrected checkpoint

- commit `c3b96263914c890502215b4fac60ad0c3bd82c33`
- workflow `RocketDict Workbench`
- run `33974220059`
- job `101327963291`
- Ubuntu 24.04.4
- Python 3.13.15
- compile success
- **193 passed, 1 skipped in 1.70s**

## Immediate continuation

Do not repeat searches listed in `search-exhaustion-2026-09-05.json` without new evidence.

When provenance-verifiable bytes appear:

1. prefer the exact full 0.30.34 Stage6Y ZIP;
2. run `rocketdict-recover-scan`, `rocketdict-recover-core` and `rocketdict-recover-plan`;
3. use the exact 0.30.34 wheel as alternate packaged-core recovery if the ZIP remains unavailable;
4. never manufacture missing 0.30.40 bytes;
5. only after exact-compatible runtime proof: doctor → import → Product preflight → live registry/API probe → exact binding/execution proof → genuine Stage8 → continue through Stage25;
6. finally run the full 90k+ public-domain corpus without truncation and retain the complete translation/research evidence database.

## Non-negotiable rules

- Never replace real MT with fake/identity/dictionary translation and call it success.
- Never silently truncate required long corpora.
- Preserve hashes, failed experiments and audit evidence.
- Do not weaken quality gates for a green run.
- Do not treat Stage6Y as Product source without exact compatibility proof and regression.
- Keep the public repository free of personal/account/private-conversation data.
