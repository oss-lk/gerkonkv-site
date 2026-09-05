# RocketDict exact-core recovery workflow

Date: 2026-09-05

Recovery is deliberately fail-closed. No historical candidate can promote itself into Product execution.

## Current blocker

Workbench already implements the Product pipeline through Stage25. The missing prerequisite is a complete exact-compatible RocketDict core/public API runtime.

Exact 0.30.40 evidence currently preserves only:

- `src/rocketdict/__init__.py` — 502 bytes — SHA-256 `7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c`
- `src/rocketdict/nlp/registry.py` — 29,072 bytes — SHA-256 `02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69`

The next tar member is truncated. Historical materializer evidence proves the intended Stage8 overlay contained 19 research/translation files and no `rocketdict.api.*`.

Current exact-target math:

- intended overlay members: 19
- exact target members available: 2
- exact target members missing: 17
- exact recovered 0.30.40 public API modules: 0

Machine-readable authority:

- `rocketdict/recovered/stage8-0.30.40/recovery.json`
- `rocketdict/recovered/stage8-0.30.40/core-recovery-history.json`
- `rocketdict/recovered/checkpoint-catalog.json`
- `rocketdict/recovered/late-stage6-artifact-identities-2026-09-05.json`
- `rocketdict/recovered/recovery-frontier-2026-09-05.json`
- `rocketdict/recovered/search-exhaustion-2026-09-05.json`

## Preferred historical recovery input — corrected

The best known historical input is a **full checkpoint ZIP**, not merely the wheel:

`RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip`

Exact SHA-256:

`3cd150c012c28d0e8c458ba25bff56a8e9c17789d2c6986d8b6b72e202d5c387`

The old byte-size record is unavailable and must not be guessed.

Historical project output proves:

- the ZIP was created at `/mnt/data/RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip`;
- `unzip -t` passed;
- `7/7` new fault-injection tests passed;
- `34/34` targeted regressions passed;
- compileall passed;
- wheel installation check passed;
- source↔wheel parity passed;
- the archive was explicitly handed off.

A previous recovery record said Stage6Y ZIP packaging did not finish. That statement is superseded by the recovered historical output; no unknown metadata was fabricated while correcting it.

Alternate packaged-core input:

`rocketdict-0.30.34-py3-none-any.whl`

SHA-256:

`76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`

## Archive identity rule

For historical checkpoint ZIPs:

- filename equality alone is never identity;
- exact SHA-256 is sufficient cryptographic identity when historical byte size is unavailable;
- when a historical size is known, observed size must also match;
- size without an exact SHA is not accepted;
- unknown size must never be guessed.

Lower-level ZIP scan schema:

`rocketdict-workbench-core-recovery-scan/3`

This allows the exact Stage6Y ZIP to be represented honestly even though its old byte-size record is lost.

## 1. Inspect one source directory or checkpoint ZIP

```bash
rocketdict-recover-core /path/to/checkpoint-or-source
```

Accepted inputs:

- source directory;
- checkpoint ZIP.

ZIP candidates are structural/read-only evidence. Directory runtime probing is isolated and module-origin checked.

Important bridge modules:

- `rocketdict.api.contracts`
- `rocketdict.api.client`
- `rocketdict.api.cli`
- `rocketdict.database`
- `rocketdict.importing.cli`
- `rocketdict.interpretation.cli`

Candidate status is never Product promotion.

## 2. Build deterministic historical-base → 0.30.40 plan

```bash
rocketdict-recover-plan /path/to/checkpoint-or-source
```

The planner does not materialize reconstructed source.

Per intended Stage8 overlay member it distinguishes:

- `exact_target_already_present`
- `exact_replacement_available`
- `replacement_required_but_target_missing`
- `target_missing_and_candidate_missing`

A same-path file from 0.30.34 does not become an exact 0.30.40 replacement without target-backed evidence.

Historical API modules remain `unproven_against_exact_0.30.40` until exact live compatibility is established.

## 3. Recover one wheel alternate

```bash
rocketdict-recover-wheel /path/to/rocketdict-X.Y.Z-py3-none-any.whl
```

Current wheel proof schemas:

- integrity `rocketdict-workbench-wheel-integrity/2`
- runtime `rocketdict-workbench-core-wheel-runtime-probe/2`
- full proof `rocketdict-workbench-core-wheel-recovery/5`

Default wheel recovery does not execute historical code.

Proof order:

1. ZIP CRC + package metadata/WHEEL/mandatory RECORD integrity;
2. exact historical catalog identity when basename is known;
3. packaged RocketDict structural inspection;
4. historical-base→0.30.40 plan;
5. optional runtime proof.

Integrity hard failures include:

- bad CRC;
- wrong distribution/name/version/tag;
- missing `RECORD`;
- failed RECORD hashes/sizes/inventory.

Known filename with wrong catalog SHA is blocked before historical code import.

Optional runtime:

```bash
rocketdict-recover-wheel /path/to/candidate.whl --probe-runtime
```

The runtime probe:

- uses a fresh Python process with `-I`;
- imports directly through zipimport, without installing/extracting the wheel;
- hashes the wheel before/after the subprocess;
- rejects byte drift;
- uses a Python audit hook to reject socket/DNS attempts;
- verifies required and transitively loaded `rocketdict.*` module origins stay inside the candidate wheel;
- separates missing external dependencies from candidate-module failures.

A green historical wheel runtime still does not prove exact 0.30.40 compatibility or Product readiness.

## 4. Batch recovery

```bash
rocketdict-recover-scan /path/to/recovery-directory
```

Unified scan schema remains:

`rocketdict-workbench-core-recovery-scan/7`

It discovers source roots, checkpoint ZIPs and wheels. Wheel runtime remains explicit:

```bash
rocketdict-recover-scan /path/to/recovery-directory --probe-wheels
```

Directory runtime remains separately opt-in through `--probe-directories`.

## Recovery priority

1. exact full 0.30.34 Stage6Y ZIP;
2. exact 0.30.34 wheel alternate;
3. exact 0.30.33 ZIP/wheel;
4. exact 0.30.32 ZIP/wheel;
5. 0.30.31;
6. 0.30.30;
7. 0.30.29;
8. exact 0.30.8 ZIP.

Priority means “inspect first”, not “promote”.

## Search-exhaustion boundary

Read:

`rocketdict/recovered/search-exhaustion-2026-09-05.json`

Current schema:

`rocketdict-core-recovery-search-exhaustion/3`

Already checked without recovering the Stage6Y bytes:

- reachable Git history/deleted refs/Stage6T–Y commit window;
- likely API paths and Releases;
- known Actions workflows/artifacts;
- historical Stage6 branch;
- File Library exact Stage6Y filename/SHA/date navigation;
- connected Google Drive;
- public exact filename/SHA search;
- current runtime workspace;
- retained Stage31 transcripts.

Do not repeat these surfaces without new evidence.

## Product promotion boundary

A recovered Stage6Y candidate still must pass:

1. exact recovery identity and structural checks;
2. deterministic base→0.30.40 compatibility analysis;
3. Workbench doctor;
4. real source import and durable IDs;
5. immutable Product preflight;
6. live registry/API probe;
7. exact callable binding + execution-contract proof;
8. genuine Stage8 dispatch;
9. Stage10/12/14;
10. Stage15 hard gates with explicit PASS semantics;
11. Stage16→17→Workbench18→19;
12. real OPUS Stage20;
13. CEFR-J / CMUdict / Stage23;
14. Stage24;
15. Stage25;
16. full 90k+ public-domain validation without truncation.

No recovery tool skips or weakens these steps.

## Latest verified corrected checkpoint

Commit:

`c3b96263914c890502215b4fac60ad0c3bd82c33`

GitHub Actions:

- workflow `RocketDict Workbench`
- run `33974220059`
- job `101327963291`
- Ubuntu 24.04.4
- Python 3.13.15
- compile success
- **193 passed, 1 skipped in 1.70s**

The run includes regression coverage for SHA-only archive identity, wrong SHA rejection, known-size enforcement and rejection of size-without-SHA.

## Next useful external input

Preferred:

`RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip`

SHA-256 `3cd150c012c28d0e8c458ba25bff56a8e9c17789d2c6986d8b6b72e202d5c387`.

Alternate:

`rocketdict-0.30.34-py3-none-any.whl`

SHA-256 `76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`.

Until exact candidate bytes appear, keep `exact_core_incomplete`. Do not synthesize missing 0.30.40 code and do not rebuild Product orchestration already implemented.
