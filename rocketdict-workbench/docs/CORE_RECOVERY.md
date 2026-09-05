# RocketDict exact-core recovery workflow

Date: 2026-09-05

This is the operational recovery path for the active Product line. Recovery tools are deliberately fail-closed: none can promote a historical candidate into Product execution by themselves.

## Current blocker

Workbench already implements the Product pipeline through Stage25. The missing prerequisite is a complete exact-compatible RocketDict core/public API.

Exact 0.30.40 evidence currently preserves only:

- `src/rocketdict/__init__.py` — 502 bytes — SHA-256 `7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c`
- `src/rocketdict/nlp/registry.py` — 29,072 bytes — SHA-256 `02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69`

The next tar member, `src/rocketdict/lab/stage12_pilot.py`, is truncated.

Historical materializer analysis proves the intended Stage8 overlay contained 19 research/translation files and no `rocketdict.api.*`. Therefore restoring the missing overlay bytes alone cannot restore the complete base core/public API.

Current exact-target math:

- intended overlay members: 19
- exact target members available: 2
- exact target members missing: 17
- exact recovered 0.30.40 public API modules: 0

Machine-readable evidence:

- `rocketdict/recovered/stage8-0.30.40/recovery.json`
- `rocketdict/recovered/stage8-0.30.40/core-recovery-history.json`
- `rocketdict/recovered/checkpoint-catalog.json`
- `rocketdict/recovered/late-stage6-artifact-identities-2026-09-05.json`
- `rocketdict/recovered/recovery-frontier-2026-09-05.json`
- `rocketdict/recovered/search-exhaustion-2026-09-05.json`

## Preferred historical packaged-core lead

The strongest known historical recovery target is:

- version `0.30.34`
- wheel `rocketdict-0.30.34-py3-none-any.whl`
- exact SHA-256 `76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`

Stage6Y engineering completed historically, but the final release ZIP packaging did not complete. No 0.30.34 release ZIP identity may be invented.

This wheel identity is a recovery lead, not exact 0.30.40 identity and not Product proof.

## 1. Inspect one source directory or checkpoint ZIP

```bash
rocketdict-recover-core /path/to/checkpoint-or-source
```

Accepted inputs:

- source directory;
- ZIP checkpoint.

Directory candidates may receive an isolated subprocess import probe with module-origin verification. ZIP candidates are read-only structural evidence and are never extracted/executed by this verifier.

Required Workbench bridge modules include:

- `rocketdict.api.contracts`
- `rocketdict.api.client`
- `rocketdict.api.cli`
- `rocketdict.database`
- `rocketdict.importing.cli`
- `rocketdict.interpretation.cli`

Candidate status is recovery evidence only, never promotion.

## 2. Build deterministic historical-base → 0.30.40 plan

```bash
rocketdict-recover-plan /path/to/checkpoint-or-source
```

The planner never writes reconstructed source.

Per overlay member it emits one of:

- `exact_target_already_present`
- `exact_replacement_available`
- `replacement_required_but_target_missing`
- `target_missing_and_candidate_missing`

A same-path file from an older base is not accepted as 0.30.40 target evidence without exact manifest-backed bytes/SHA.

Exact 0.30.40 public API bytes remain unrecovered, so historical API modules remain `unproven_against_exact_0.30.40`.

## 3. Recover one historical wheel

```bash
rocketdict-recover-wheel /path/to/rocketdict-X.Y.Z-py3-none-any.whl
```

Current full-wheel schema:

`rocketdict-workbench-core-wheel-recovery/5`

The default is read-only and does **not** import historical code. It performs the following strict sequence:

1. wheel container/package integrity;
2. known historical checkpoint identity when the basename matches the catalog;
3. packaged RocketDict structural inspection;
4. deterministic historical-base→0.30.40 compatibility plan;
5. optional runtime proof.

### Wheel integrity

Schema:

`rocketdict-workbench-wheel-integrity/2`

The verifier checks without extraction or import:

- ZIP CRC;
- exactly one `.dist-info/METADATA`;
- exactly one `.dist-info/WHEEL`;
- mandatory `.dist-info/RECORD`;
- RECORD member inventory;
- RECORD hashes and sizes;
- duplicate or unrecorded paths;
- metadata distribution must be RocketDict;
- filename distribution/version must agree with METADATA;
- filename Python/ABI/platform tag must be present in WHEEL `Tag:`.

The following are hard failures:

- `zip_crc_failure`
- `metadata_distribution_is_not_rocketdict`
- `filename_metadata_name_mismatch`
- `filename_metadata_version_mismatch`
- `filename_wheel_tag_mismatch`
- `wheel_record_missing`
- `wheel_record_verification_failed`

A failed integrity layer prevents runtime import even if runtime was explicitly requested.

### Historical catalog identity

Default catalog:

`rocketdict/recovered/checkpoint-catalog.json`

For a known wheel basename with a cataloged exact identity, filename equality is **not** enough. SHA-256 and any cataloged byte size must match.

In particular, a file named:

`rocketdict-0.30.34-py3-none-any.whl`

is accepted as the recovered Stage6Y packaged-core artifact only if its SHA-256 is exactly:

`76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`

A known basename with wrong bytes gets:

- wheel recovery status `blocked_historical_catalog_identity`
- runtime status `blocked_by_historical_catalog_identity`
- blocker `historical_catalog_exact_identity_mismatch`
- `runtime_probe.attempted=false`

An unknown but internally valid wheel may still be explored as an unverified historical base candidate. It receives no known-checkpoint identity claim.

Override the catalog only for deliberate, provenance-aware testing:

```bash
rocketdict-recover-wheel /path/to/candidate.whl \
  --checkpoint-catalog /path/to/checkpoint-catalog.json
```

### Optional wheel runtime proof

```bash
rocketdict-recover-wheel /path/to/candidate.whl --probe-runtime
```

Runtime schema:

`rocketdict-workbench-core-wheel-runtime-probe/2`

Runtime proof is reached only after integrity, catalog identity where applicable, structural inspection and cross-layer artifact/version checks pass.

The probe:

- never installs the wheel;
- never extracts the wheel;
- launches a fresh Python subprocess with `-I`;
- imports the package directly via zipimport;
- hashes the wheel before and after the subprocess;
- rejects artifact drift during the probe;
- installs a Python audit hook that denies socket connect and name-resolution events;
- also sets common offline environment flags;
- verifies required module origins;
- verifies every transitively loaded `rocketdict.*` module with a file origin remains inside the exact candidate wheel;
- distinguishes missing external dependencies, missing candidate modules, network attempts and module-origin escape.

A successful runtime proof means only that this exact historical wheel imports successfully in the selected isolated Python environment. It does **not** prove:

- exact 0.30.40 compatibility;
- exact 0.30.40 public API bytes;
- live Product registry contracts;
- DB compatibility;
- Product dispatch readiness.

## 4. Batch recovery scan

```bash
rocketdict-recover-scan /path/to/recovery-directory
```

Current schema:

`rocketdict-workbench-core-recovery-scan/7`

The scanner finds RocketDict source roots, checkpoint ZIPs and Python wheels. For every wheel it creates the full read-only proof chain automatically. Runtime remains disabled unless explicitly requested:

```bash
rocketdict-recover-scan /path/to/recovery-directory --probe-wheels
```

`--probe-wheels` does **not** bypass earlier gates. A corrupt wheel or known historical filename with the wrong SHA remains visible in the report, but historical code is not executed.

Useful scan counters include:

- `wheel_pipeline_count`
- `wheel_integrity_ok_count`
- `wheel_catalog_exact_match_count`
- `wheel_catalog_exact_mismatch_count`
- `wheel_runtime_attempted_count`
- `wheel_runtime_proven_count`

Directory runtime probes remain independently opt-in through `--probe-directories`.

Example:

```bash
rocketdict-recover-scan /path/to/recovery-directory \
  --probe-wheels \
  --reports-dir ./recovery-reports \
  --output ./recovery-scan.json
```

## Historical checkpoint priority

Current recovery triage priority is:

1. 0.30.34 exact wheel;
2. 0.30.33 exact ZIP or wheel;
3. 0.30.32 exact ZIP or wheel;
4. 0.30.31;
5. 0.30.30;
6. 0.30.29;
7. 0.30.8 exact ZIP.

This priority means “inspect first”, never “promote”.

Known exact identities are recorded machine-readably. Notable examples:

- 0.30.33 ZIP SHA `405d4339fc12b8046da4f5cb73c799b2d5c957a9b53dffdf8e2ed9a79cbeb152`
- 0.30.33 wheel SHA `4c64deb9cc48b68be1408ad52b4458b843453f89f60c84a72c688b5cb3f042c1`
- 0.30.32 ZIP SHA `c86bf534f78dfb84b7b2ecb9acb7fb03ab89ee4c9933cd393df7cdd2c5a9ddf6`
- 0.30.32 wheel SHA `16c8a6015328ad623f008fc30f8ba13c7eb97de09ac60c6219be5f7f8d946013`
- 0.30.29 ZIP SHA `199e44f5ef1584565d2c57d771e5723423f274131f686024c541754802a09fa3`
- 0.30.8 ZIP SHA `f948a9b59e4deb7b00a606fdb88973dd9a435c087c132f32f03d2d0c863b51ac`

## Search-exhaustion boundary

Read `rocketdict/recovered/search-exhaustion-2026-09-05.json` before repeating recovery searches. Already checked include reachable Git history, deleted refs, likely historical API paths, Releases, historical Stage6 branch, File Library evidence, retained Stage31 transcripts and ten ZIPs in the current ephemeral workspace.

Current ephemeral workspace does not contain a complete historical core candidate or RocketDict wheel. Do not repeat exhausted surfaces unless new refs/files/objects appear.

## Product promotion boundary

A recovered historical candidate still must pass:

1. exact recovery identity/compatibility checks;
2. Workbench doctor;
3. real source import and durable IDs;
4. immutable Product preflight;
5. live registry/API probe;
6. exact callable binding + execution-contract proof;
7. genuine Stage8 dispatch;
8. Stage10/12/14;
9. Stage15 hard gates with explicit PASS semantics;
10. Stage16→17→Workbench18→19;
11. real OPUS Stage20;
12. CEFR-J / CMUdict / Stage23;
13. Stage24;
14. Stage25;
15. full 90k+ public-domain validation without truncation.

No recovery tool skips these steps. Full wheel/scan reports retain `promotion_allowed=false` and `product_execution_allowed=false`.

## Latest verified recovery checkpoint

Latest verified code checkpoint:

- commit `202fbf58b450f35ef631009f65356d5cdf562547`
- Workbench run `33968651171`
- job `101313136601`
- Ubuntu 24.04.4
- Python 3.13.15
- compile success
- **187 passed, 1 skipped in 3.29s**

This regression run proves unknown intact wheels remain exploratory; a known 0.30.34 basename with wrong SHA is blocked before runtime import; explicit exact catalog identity permits runtime proof; corrupt RECORD blocks runtime; and batch scan preserves rejected candidates and exact reasons.

Preserved failed evidence includes the earlier 63-character historical SHA rejection and the wheel-integrity test-fixture SyntaxError; both were corrected without weakening the recovery rules.

## Next useful external input

Preferred exact input:

`rocketdict-0.30.34-py3-none-any.whl`

SHA-256:

`76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`

Until provenance-verifiable core bytes appear, retain `exact_core_incomplete`. Do not synthesize missing 0.30.40 implementation/API bytes and do not rebuild Product orchestration that is already implemented.
