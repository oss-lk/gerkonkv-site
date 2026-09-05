# RocketDict core recovery workflow

Date: 2026-09-05

This document is the operational recovery path for the active Product line. It is intentionally fail-closed: none of these tools can promote a recovered candidate into a Product runtime by themselves.

## Why recovery is still required

The active Workbench already implements the Product pipeline through Stage25, but the exact public RocketDict 0.30.40 core is incomplete in the repository.

Exact bytes currently recovered from the 0.30.40 Stage8 artifact prefix:

- `src/rocketdict/__init__.py`
  - 502 bytes
  - SHA-256 `7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c`
- `src/rocketdict/nlp/registry.py`
  - 29,072 bytes
  - SHA-256 `02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69`

The next tar member, `src/rocketdict/lab/stage12_pilot.py`, is truncated.

Historical reconstruction also proved an important boundary: the intended Stage8 overlay contained 19 research/translation files and **did not contain `rocketdict.api.*`**. Therefore recovering the missing seven overlay chunks alone could never restore the complete base core/public API.

The exact historical reconstruction evidence is machine-readable in:

- `rocketdict/recovered/stage8-0.30.40/recovery.json`
- `rocketdict/recovered/stage8-0.30.40/core-recovery-history.json`

Both retain `promotion_allowed=false`.

## Recovery commands

Workbench installs three recovery commands.

### 1. Inspect one candidate

```bash
rocketdict-recover-core /path/to/checkpoint-or-source
```

Accepted inputs:

- source directory;
- ZIP checkpoint.

Directory candidates can receive an isolated subprocess runtime probe. The probe verifies that imported RocketDict modules originate from the candidate tree rather than another installed package.

ZIP candidates are read-only structural evidence. They are not extracted or executed by the verifier.

The candidate verifier checks the Workbench bridge dependencies including:

- `rocketdict.api.contracts`
- `rocketdict.api.client`
- `rocketdict.api.cli`
- `rocketdict.database`
- `rocketdict.importing.cli`
- `rocketdict.interpretation.cli`

It also compares any available 0.30.40 exact hash anchors.

A candidate status such as `exact_version_structural_candidate` is **not** Product promotion.

### 2. Build a deterministic base→0.30.40 compatibility plan

```bash
rocketdict-recover-plan /path/to/checkpoint-or-source
```

The planner is read-only. It never creates a reconstructed source tree.

Current exact Stage8 overlay contract:

- total intended overlay members: 19;
- exact target bytes currently available: 2;
- exact target bytes currently missing: 17.

For each intended overlay member the plan distinguishes:

- `exact_target_already_present`
- `exact_replacement_available`
- `replacement_required_but_target_missing`
- `target_missing_and_candidate_missing`

A historical/base file at the correct path does **not** become accepted 0.30.40 target evidence merely because it exists. Replacement bytes must be backed by the exact recovery manifest with size and SHA-256.

Likewise, the public API is treated as a base-core dependency. Because exact 0.30.40 API bytes are not recovered, candidate API modules remain `unproven_against_exact_0.30.40`.

### 3. Screen a directory of old checkpoints

```bash
rocketdict-recover-scan /path/to/archive-directory
```

The scanner recursively discovers:

- ZIP files;
- canonical RocketDict source roots.

By default it does not execute discovered directory candidates. Runtime probing is explicit:

```bash
rocketdict-recover-scan /path/to/archive-directory --probe-directories
```

Optional full compatibility plans can be persisted under hash-derived names:

```bash
rocketdict-recover-scan /path/to/archive-directory \
  --reports-dir ./recovery-reports \
  --output ./recovery-scan.json
```

Ranking is only recovery triage. It prioritizes useful leads such as a documented archive identity or exact-version structural candidate. It does not mean the candidate is compatible or promotable.

The scanner canonicalizes `root/src/rocketdict/__init__.py` to `root`, so a single checkout is not double-counted as both `root` and `root/src`. A corrupt ZIP becomes an isolated candidate error and does not abort analysis of the remaining candidates.

## Historical archive leads

One documented older full checkpoint is known:

- archive: `RocketDict_CURRENT_COMPACT.zip`
- version: `0.30.8`
- bytes: `125875993`
- SHA-256: `f948a9b59e4deb7b00a606fdb88973dd9a435c087c132f32f03d2d0c863b51ac`
- manifest files: 666

Its bytes are not currently recovered. It is a historical **base candidate only**, not a substitute for 0.30.40.

Project history also records later checkpoints including 0.30.9, 0.30.19, 0.30.29, 0.30.32 and 0.30.34-era work. File Library searches currently recover README/heavy evidence for 0.30.29/Stage6T, but not the corresponding ZIP bytes.

The private historical repository `oss-lk/spacy-project-vault` is not a source for the missing full base core. Its surviving RocketDict branches are research/model/evidence lineages; the checked `rocketdict-stage06-spacy-model` tree contains no RocketDict source package.

## Promotion boundary

Even a strong recovery candidate must still pass the normal Product chain:

1. exact source/runtime candidate recovery;
2. Workbench doctor;
3. real source import + durable IDs;
4. immutable Product preflight;
5. live registry/API probe;
6. exact callable binding and execution-contract proof;
7. first genuine Stage8 dispatch;
8. Stage10/12/14;
9. Stage15 hard quality gates with explicit PASS semantics;
10. Stage16→17→Workbench18→19;
11. real OPUS-backed Stage20;
12. CEFR-J / CMUdict / Stage23;
13. Stage24 cards;
14. Stage25 export;
15. full 90k+ public-domain corpus validation without truncation.

No recovery tool can skip or weaken those steps.

## Latest recovery CI checkpoint

Commit:

`d1e94eced4deaeec9e9a9a3a70fecdee48572e12` — `Fix canonical recovery candidate discovery and ZIP isolation`

GitHub Actions:

- workflow: `RocketDict Workbench`
- run: `33964578578`
- job: `101302315173`
- Ubuntu 24.04
- Python 3.13.15
- compile success
- **153 passed, 1 skipped in 1.53s**

The preceding red run was retained as evidence: it found the duplicate-root and corrupt-ZIP isolation defects. The fixed checkpoint does not hide that failed experiment.
