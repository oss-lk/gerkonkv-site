# RocketDict exact-core recovery workflow

Date: 2026-09-05

This is the operational recovery path for the active Product line. Recovery tools are deliberately fail-closed: none can promote a candidate into Product execution by themselves.

## Current blocker

Workbench already implements the Product pipeline through Stage25. The missing prerequisite is a complete exact-compatible RocketDict core/public API.

Exact 0.30.40 evidence currently preserves only:

- `src/rocketdict/__init__.py` — 502 bytes — SHA-256 `7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c`
- `src/rocketdict/nlp/registry.py` — 29,072 bytes — SHA-256 `02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69`

The next tar member, `src/rocketdict/lab/stage12_pilot.py`, is truncated.

Historical materializer analysis proves the intended Stage8 overlay contained 19 research/translation files and no `rocketdict.api.*`. Therefore restoring the missing seven overlay chunks alone cannot restore the complete base core.

Machine-readable evidence:

- `rocketdict/recovered/stage8-0.30.40/recovery.json`
- `rocketdict/recovered/stage8-0.30.40/core-recovery-history.json`
- `rocketdict/recovered/checkpoint-catalog.json`
- `rocketdict/recovered/search-exhaustion-2026-09-05.json`

## 1. Inspect one candidate

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

## 2. Build deterministic base→0.30.40 plan

```bash
rocketdict-recover-plan /path/to/checkpoint-or-source
```

The planner never writes reconstructed source.

Current Stage8 overlay contract:

- intended members: 19
- exact target bytes available: 2
- exact target bytes missing: 17

Per member it emits one of:

- `exact_target_already_present`
- `exact_replacement_available`
- `replacement_required_but_target_missing`
- `target_missing_and_candidate_missing`

A same-path file from an older base is not accepted as 0.30.40 target evidence without exact manifest-backed size/SHA.

Exact 0.30.40 public API bytes remain unrecovered, so candidate API modules remain `unproven_against_exact_0.30.40`.

## 3. Screen a directory of historical checkpoints

```bash
rocketdict-recover-scan /path/to/archive-directory
```

Current schema: `rocketdict-workbench-core-recovery-scan/2`.

Scanner behavior:

- recursively finds ZIPs and canonical RocketDict source roots;
- ZIPs are structural-only;
- directories are not executed by default;
- use `--probe-directories` for explicit runtime probes;
- corrupt ZIPs become isolated candidate errors;
- `root/src/rocketdict/__init__.py` is canonicalized to `root`, avoiding duplicate checkouts;
- optional full plans are written under fingerprint-derived names with `--reports-dir`.

Example:

```bash
rocketdict-recover-scan /path/to/archive-directory \
  --reports-dir ./recovery-reports \
  --output ./recovery-scan.json
```

## Historical checkpoint catalog

Default catalog:

`rocketdict/recovered/checkpoint-catalog.json`

Override only when deliberately testing another validated catalog:

```bash
rocketdict-recover-scan /path/to/archive-directory \
  --checkpoint-catalog /path/to/checkpoint-catalog.json
```

Catalog semantics are strict:

- exact archive SHA-256 + byte size is cryptographic identity evidence;
- a historical archive-name match is only triage evidence;
- a name-only match never becomes byte identity;
- a known checkpoint without a proven archive filename receives no guessed pattern;
- catalog and every entry must retain `promotion_allowed=false`.

Known exact historical archive identity:

- `RocketDict_CURRENT_COMPACT.zip`
- version `0.30.8`
- 125,875,993 bytes
- SHA-256 `f948a9b59e4deb7b00a606fdb88973dd9a435c087c132f32f03d2d0c863b51ac`
- 666 manifest files.

Later catalog records preserve historical evidence for 0.30.9, 0.30.19, 0.30.29, 0.30.32 and the separate 0.30.34 Stage6Y lineage without inventing unknown SHA values or filenames.

## Search-exhaustion boundary

Read:

`rocketdict/recovered/search-exhaustion-2026-09-05.json`

Already checked:

- reachable Git history + parentless upload root;
- observed deleted RocketDict refs;
- likely historical API source paths;
- GitHub Releases in both RocketDict-related repositories;
- historical `spacy-project-vault` Stage6 branch;
- File Library recovery evidence;
- two currently retained Stage31 transcripts;
- ten ZIPs in the current ephemeral recovery workspace.

Current workspace result:

- 10 ZIPs
- 1 ZIP with any RocketDict package root (`stage8-overlay-prefix.zip`)
- 0 with required public API source modules
- 0 with RocketDict wheel
- 0 with nested RocketDict full checkpoint
- 0 complete core candidates.

Do not repeat these surfaces unless new refs/files/objects appear.

## Promotion boundary

A recovered candidate still must pass:

1. recovery identity/compatibility checks;
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

No recovery tool skips these steps.

## Latest verified recovery checkpoint

- commit `ff9018516d924d56de6e6c4d267a91e5b920a5a6`
- Workbench run `33965240536`
- job `101304088386`
- Ubuntu 24.04
- Python 3.13.15
- compile success
- **159 passed, 1 skipped in 2.11s**

The next useful recovery input is new provenance-verifiable full historical RocketDict checkpoint/core bytes. Until those bytes exist, retain `exact_core_incomplete` and do not synthesize the missing implementation.
