# RocketDict public handoff health

Last checked: 2026-08-28 UTC.

## Status

The public handoff metadata and research narrative are usable, but the binary/text payload materialization is **not yet self-contained**.

`rocketdict/materialize_handoff.py` is authoritative about the intended payload contract:

- Stage 8 source overlay: 8 canonical files `rocketdict/payload/stage8-overlay/part-000.b64` through `part-007.b64`;
- Research Vault: 11 canonical files `rocketdict/payload/research-vault/part-000.b85` through `part-010.b85`;
- overlay tar.gz SHA-256: `ddf5f409a5690fa4d2141c8a3bd30ef73f82cc9e75c27b66716791afbc6f97b7`;
- Research Vault xz SHA-256: `394ffcfe399deb1f83ad445cc3ac2e727c8f684a29fd06c757eee16612cfe4ab`;
- uncompressed Research Vault SQLite SHA-256: `106fc9d7bee42a53b34412267923d17b3331019d2eef16300b539de8929927a1`.

At this check, `main` contains only:

- `rocketdict/payload/stage8-overlay/part-000.b64`.

The remaining 7 overlay chunks and all 11 Research Vault chunks are absent. Therefore `python rocketdict/materialize_handoff.py` cannot currently succeed from a fresh clone, and no continuation session should claim otherwise.

## Verified recovery from the surviving overlay prefix

The surviving `part-000.b64` has now been decoded and decompressed fail-closed in GitHub Actions run `33183643328` (artifact `9690741914`, digest `sha256:78d8414641cf70465427d9a09671510050579aec7dd640a6c3be9c969fb49ea9`). It recovers two complete 0.30.40 source files plus the first 20,358 bytes of the real `src/rocketdict/lab/stage12_pilot.py` member.

This prefix proves that the 0.30.40 Stage12 sampling policy still uses `coverage-stratified-v1` with default 8 position / 8 numeric / 8 critical-symbol / 8 long challenge quotas and `long_unit_min_words=24`. The visible selector algorithm is unchanged from the recovered 0.30.34 parent except that numeric eligibility changed from the old local regex to `rocketdict.translation.integrity.contains_numeric_literal()`; the same helper is used for coverage accounting. Pilot and journal formats advance to 7.0 / 5.0 and the module imports `compare_numeric_integrity` from the same missing integrity module.

Therefore earlier recovery experiments that obtained matching aggregate counts by changing the sampling quotas are **diagnostic only**, not the recovered 0.30.40 configuration. The next exact source dependency is specifically `src/rocketdict/translation/integrity.py`; `src/rocketdict/research/integrity_doe.py` is also still required to recover the late Stage8 challenge clipping/execution layer. See `research/stage8-overlay-prefix-exact-recovery-2026-08-28.json`.

## What remains durable and usable

The following are present and sufficient to recover the research direction and continue independent mechanism experiments without inventing prior results:

- `ROCKETDICT_HANDOFF.md`;
- `rocketdict/START_HERE.md`;
- `rocketdict/STATE.json`;
- `rocketdict/RESEARCH_STATUS.md`;
- exact canonical heavy/source-stream recovery evidence under `rocketdict/research/`;
- exact surviving Stage8 overlay-prefix evidence under `rocketdict/research/`;
- official OPUS real-model GitHub gate and its still-live Actions artifacts;
- Stage 8 G/H/I standalone mechanism probes added under `rocketdict-ci/`;
- durable compact probe results under `rocketdict/research/` as they are completed.

The exact F96 full-pipeline implementation and the append-only Research Vault cannot be reconstructed bit-for-bit until the missing payload chunks are restored from the original prepared payload or an equivalent verified source snapshot.

## Continuation rule while payload is incomplete

1. Do not restart DOE from A; F96 remains the measured parent frontier.
2. Do not fabricate missing source implementation or Research Vault rows.
3. Do not replace the source-proven 8/8/8/8 Stage12 sampling defaults with parameter-fitted alternatives merely because aggregate counts match.
4. Prioritize recovery of `translation/integrity.py`, then `research/integrity_doe.py` / exact challenge clipping identity.
5. Mechanism probes may continue in GitHub Actions when they are explicitly labelled non-promotional and use the same official OPUS identity.
6. Do not promote G/H/I to the 10k screen until the real Stage 8 source overlay is restored, the mechanisms are integrated, and the identical ~5k challenge set passes `rocketdict-numeric-integrity/3.2` with numeric=0, critical=0, length=0, empty=0, backend_errors=0.
7. Once the payload is restored, run `python rocketdict/materialize_handoff.py`; treat its SHA/inventory/integrity checks as mandatory before full-pipeline work.

## Privacy

This health record is project-only technical information for the public repository. Do not add personal/user/account/private-conversation information.
