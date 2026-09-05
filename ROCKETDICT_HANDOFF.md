# RocketDict public handoff

This repository is the public, project-only continuation point for RocketDict.

## Authoritative entrypoint

Start with [`rocketdict/CURRENT.md`](rocketdict/CURRENT.md).

Then read:

- [`rocketdict-workbench/docs/CORE_RECOVERY.md`](rocketdict-workbench/docs/CORE_RECOVERY.md) — operational recovery commands and promotion boundary;
- [`rocketdict/recovered/checkpoint-catalog.json`](rocketdict/recovered/checkpoint-catalog.json) — machine-readable historical checkpoint identities/names with explicit evidence levels;
- [`rocketdict/recovered/search-exhaustion-2026-09-05.json`](rocketdict/recovered/search-exhaustion-2026-09-05.json) — sources already searched so they are not redundantly repeated;
- [`rocketdict/recovered/stage8-0.30.40/recovery.json`](rocketdict/recovered/stage8-0.30.40/recovery.json) — exact recovered 0.30.40 bytes and blocker;
- [`rocketdict/recovered/stage8-0.30.40/core-recovery-history.json`](rocketdict/recovered/stage8-0.30.40/core-recovery-history.json) — historical payload/Actions recovery map;
- [`rocketdict/START_HERE.md`](rocketdict/START_HERE.md) and [`rocketdict/STATE.json`](rocketdict/STATE.json) for older Stage8 research context;
- [`rocketdict/checkpoints/stage6y/`](rocketdict/checkpoints/stage6y/) for the separate verified 0.30.34 maintenance lineage.

## Current frontier

The Workbench Product pipeline already reaches resumable Stage25. The hard blocker is the absence of a complete exact-compatible RocketDict core/public API, not missing orchestration.

Exact 0.30.40 recovery currently preserves two complete Stage8 overlay source members. Historical reconstruction proves the intended 19-file Stage8 overlay did not contain `rocketdict.api.*`; seven missing overlay chunks alone cannot reconstruct the base core.

Recovery tools:

- `rocketdict-recover-core`
- `rocketdict-recover-plan`
- `rocketdict-recover-scan`

Current scanner schema: `rocketdict-workbench-core-recovery-scan/2`.

It distinguishes exact archive SHA/size identity from historical filename-only matching. Known checkpoints without a proven filename do not receive guessed patterns.

Current recovery math:

- intended Stage8 overlay members: 19
- exact target bytes available: 2
- exact target bytes missing: 17
- exact 0.30.40 public API modules recovered: 0
- complete core candidate found in currently accessible recovery sources: 0

Latest verified checkpoint before this documentation update:

- commit `ff9018516d924d56de6e6c4d267a91e5b920a5a6`
- Workbench run `33965240536`
- job `101304088386`
- Python 3.13.15
- compile success
- **159 passed, 1 skipped**.

## Immediate continuation

Do not repeat already exhausted Git/deleted-ref/Release/current-workspace scans unless new objects become available.

The next useful input is new provenance-verifiable historical RocketDict checkpoint/core bytes, preferably a later 0.30.x full checkpoint. When bytes appear:

1. `rocketdict-recover-scan <directory>`;
2. `rocketdict-recover-core <candidate>`;
3. `rocketdict-recover-plan <candidate>`;
4. only if a complete exact-compatible runtime is proven: Workbench doctor → import → Product preflight → live registry/API probe → exact binding/execution proof → genuine Stage8 dispatch → continue through Stage25;
5. finally run the full 90k+ public-domain corpus without truncation and retain the complete translation/research evidence database.

## Non-negotiable rules

- Never replace real MT with fake/identity/dictionary translation and call it success.
- Never silently truncate required long corpora.
- Preserve immutable hashes, failed experiments and audit evidence.
- Do not weaken quality gates merely to obtain a green run.
- Do not overwrite Product with an older checkpoint without exact compatibility proof and regression.
- Keep this public repository project-only and free of personal/account/private-conversation data.
