# RocketDict exact-core recovery workflow

Date: 2026-09-05

Recovery is deliberately fail-closed. No historical candidate can promote itself into Product execution.

## Current blocker

Workbench already implements the Product pipeline through Stage25. The missing prerequisite is a complete exact-compatible RocketDict core/public API runtime.

Exact 0.30.40 evidence currently preserves only:

- `src/rocketdict/__init__.py` — 502 bytes — SHA-256 `7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c`
- `src/rocketdict/nlp/registry.py` — 29,072 bytes — SHA-256 `02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69`.

The intended Stage8 overlay contained 19 members and no `rocketdict.api.*`. Seventeen exact targets remain missing; exact recovered 0.30.40 public API modules remain zero.

Machine-readable authority:

- `rocketdict/recovered/recovery-frontier-2026-09-05.json` — `/4`
- `rocketdict/recovered/search-exhaustion-2026-09-05.json` — `/3`
- `rocketdict/recovered/checkpoint-catalog.json`
- `rocketdict/recovered/late-stage6-artifact-identities-2026-09-05.json`
- `rocketdict/recovered/stage8-0.30.40/`.

## Preferred historical input

Primary:

`RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip`

SHA-256:

`3cd150c012c28d0e8c458ba25bff56a8e9c17789d2c6986d8b6b72e202d5c387`

Historical size is unknown and must not be guessed. Historical output proves this full ZIP was created, unzip-tested, regression-tested, package-checked and explicitly handed off.

Alternate packaged core:

`rocketdict-0.30.34-py3-none-any.whl`

SHA-256:

`76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`.

Neither exact artifact's bytes are currently recovered.

## Archive identity rule

For historical checkpoint ZIPs:

- filename equality alone is never identity;
- exact SHA-256 is sufficient if historical byte size is unavailable;
- a known historical size must also match;
- size without SHA is invalid;
- unknown size is never guessed.

Lower-level ZIP scan: `rocketdict-workbench-core-recovery-scan/3`.

## 1. Inspect generic source/ZIP structure

```bash
rocketdict-recover-core /path/to/checkpoint-or-source
```

This is the generic structural verifier. It does not replace the richer full-checkpoint proof below.

## 2. Build historical-base → exact-0.30.40 plan

```bash
rocketdict-recover-plan /path/to/checkpoint-or-source
```

The planner never materializes reconstructed source. Older same-path files do not become exact 0.30.40 evidence without exact target provenance.

## 3. Prove one full checkpoint ZIP

```bash
rocketdict-recover-checkpoint \
  /path/to/RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip \
  --output checkpoint-proof.json
```

Schema:

`rocketdict-workbench-full-checkpoint-recovery/2`

The command is read-only: it never extracts or executes checkpoint code.

Proof order:

1. outer ZIP path safety, duplicate names and CRC;
2. exact historical checkpoint catalog identity;
3. unique RocketDict source root and source version;
4. source SHA-256 inventory for:
   - `src/rocketdict/api/contracts.py`
   - `src/rocketdict/api/client.py`
   - `src/rocketdict/api/cli.py`;
5. nested RocketDict wheel CRC/METADATA/WHEEL/mandatory RECORD;
6. independent nested wheel historical catalog SHA/optional-size identity;
7. source↔wheel package-byte parity;
8. README/report/manifest/state evidence inventory;
9. historical-base→exact-0.30.40 compatibility plan.

Fail-closed examples:

- wrong exact outer ZIP SHA;
- missing/ambiguous source root;
- bad nested-wheel CRC/metadata/RECORD;
- exact nested-wheel catalog SHA mismatch;
- source↔wheel file-set or byte mismatch;
- generic compatibility-plan failure.

### Evidence inventory is never silently truncated

Diagnostic evidence selection is deliberately bounded, but the report always publishes:

- `evidence_inventory_eligible_count`
- `evidence_inventory_count`
- `evidence_inventory_limit` = 200
- `evidence_inventory_truncated`.

Selected evidence members up to 8 MiB are SHA-256 hashed. A larger selected member explicitly reports `hash_skipped`; it is not silently treated as hashed.

### Nested wheel identity is independent

An exact outer Stage6Y ZIP match does not excuse a different wheel hidden inside it. If a nested basename matches a catalog wheel identity, the nested wheel SHA-256 and any known size must independently match. Source↔wheel parity is then checked byte-for-byte across the RocketDict package.

Even a perfect historical checkpoint proof remains non-promotional: it is evidence about 0.30.34, not proof that missing exact 0.30.40 bytes are equal.

## 4. Recover one standalone wheel

```bash
rocketdict-recover-wheel /path/to/rocketdict-X.Y.Z-py3-none-any.whl
```

Schemas:

- integrity `rocketdict-workbench-wheel-integrity/2`
- full wheel recovery `rocketdict-workbench-core-wheel-recovery/5`
- runtime probe `rocketdict-workbench-core-wheel-runtime-probe/2`.

Proof order:

1. ZIP CRC + METADATA/WHEEL/RECORD;
2. exact historical catalog identity for known basename;
3. packaged RocketDict structure;
4. base→0.30.40 plan;
5. optional isolated runtime proof.

Runtime remains explicit:

```bash
rocketdict-recover-wheel /path/to/candidate.whl --probe-runtime
```

It uses isolated direct zipimport, hashes the wheel before/after, denies socket/DNS via audit hook and verifies transitively loaded `rocketdict.*` origins stay inside the exact wheel. A green import does not prove exact 0.30.40 compatibility or Product readiness.

## 5. Unified batch recovery

```bash
rocketdict-recover-scan /path/to/recovery-directory
```

Current schema:

`rocketdict-workbench-core-recovery-scan/8`

For every discovered checkpoint ZIP, `/8` automatically attaches the full-checkpoint `/2` proof. For wheels it preserves the existing integrity/catalog/plan pipeline. Wheel runtime remains disabled unless:

```bash
rocketdict-recover-scan /path/to/recovery-directory --probe-wheels
```

Directory runtime probing remains independently opt-in with `--probe-directories`.

Useful checkpoint counters include:

- `checkpoint_pipeline_count`
- `checkpoint_exact_identity_match_count`
- `checkpoint_blocked_count`
- `checkpoint_source_api_complete_count`
- `checkpoint_nested_wheel_count`
- `checkpoint_nested_wheel_integrity_ok_count`
- `checkpoint_nested_wheel_catalog_exact_match_count`
- `checkpoint_nested_wheel_catalog_exact_mismatch_count`
- `checkpoint_source_wheel_parity_complete_count`.

Use `--reports-dir` to retain focused checkpoint/wheel proof sidecars alongside the unified report.

## Installed CLI verification

The Workbench CI installs the package and smoke-checks:

- `rocketdict-recover-core`
- `rocketdict-recover-plan`
- `rocketdict-recover-checkpoint`
- `rocketdict-recover-wheel`
- `rocketdict-recover-scan`
- `rocketdict-product-run`.

Latest verified code checkpoint:

- commit `ed86467011efb5a680647e56007728d0cbb16157`
- run `33975530978`
- job `101331437743`
- Ubuntu 24.04.4
- Python 3.13.15
- compile success
- installed CLI smoke success
- **203 passed, 1 skipped in 2.46s**.

Preserved red evidence: run `33975210119` had `1 failed, 200 passed, 1 skipped`; new checkpoint logic passed and a stale wheel regression still expected unified scan `/7`. It was corrected to `/8` without weakening proof semantics.

## Recovery priority

1. exact full 0.30.34 Stage6Y ZIP;
2. exact 0.30.34 wheel alternate;
3. exact 0.30.33 ZIP/wheel;
4. exact 0.30.32 ZIP/wheel;
5. 0.30.31;
6. 0.30.30;
7. 0.30.29;
8. exact 0.30.8 ZIP.

Priority means inspect first, never promote.

## Search-exhaustion boundary

Before searching again, read `rocketdict/recovered/search-exhaustion-2026-09-05.json`.

Already closed without recovering Stage6Y bytes: reachable/deleted Git refs, Stage6T–Y commit window, Releases, likely API paths, known Actions artifacts, historical Stage6 branch, exact File Library search, connected Google Drive, public exact-name/SHA search, current runtime artifacts, Stage31 transcript recovery and the three-file public Stage6Y mirror.

The Stage6Y mirror confirms 301 packaged runtime files matched source but explicitly is not a complete source/wheel mirror and does not provide their individual paths/hashes/API source bytes.

Do not repeat these surfaces without new evidence.

## Product promotion boundary

A recovered Stage6Y candidate still must pass:

1. exact historical artifact proof;
2. base→exact-0.30.40 compatibility resolution;
3. Workbench doctor;
4. real source import/durable IDs;
5. immutable Product preflight;
6. live registry/API probe;
7. exact callable binding + execution contract;
8. genuine Stage8;
9. Stage10/12/14;
10. Stage15 hard PASS gates;
11. Stage16→17→Workbench18→19;
12. real OPUS Stage20;
13. CEFR-J / CMUdict / Stage23;
14. Stage24;
15. Stage25;
16. full 90k+ public-domain validation without truncation.

No recovery tool skips these steps. Historical source/API hashes are not exact 0.30.40 identity merely because they are complete inside 0.30.34.

## Next useful external input

Preferred exact input:

`RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip`

SHA-256 `3cd150c012c28d0e8c458ba25bff56a8e9c17789d2c6986d8b6b72e202d5c387`.

Alternate:

`rocketdict-0.30.34-py3-none-any.whl`

SHA-256 `76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`.

When the ZIP appears, `rocketdict-recover-scan` automatically performs the full checkpoint proof; retain a focused `rocketdict-recover-checkpoint` report too. Until provenance-verifiable bytes appear, keep `exact_core_incomplete`, do not synthesize missing 0.30.40 code, and do not rebuild Product orchestration already implemented.
