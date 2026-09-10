# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`
- Engineering branch: `chatgpt/product-core-forward`
- Current frontier includes Product Core, Workbench orchestration and quality research workflows.
- `MetricX QE` is an evaluation component, not a development blocker.

## Recovery protocol

Follow `AGENTS.md`:
1. Check HEAD and changes after this checkpoint.
2. Use `docs/memory/INDEX.md` as L2 router.
3. Use source/tests/CI/artifacts as L3 authority.

## Implemented quality contracts

- Real EN→RU translation through pinned OPUS/CTranslate2 path.
- Stage12 protected planning and replay-safe Product execution.
- Narrow source-owned structural preservation only for proven non-linguistic classes.
- Numeric integrity gate and fail-closed quality rules.
- Structural labels, block identifiers and table handling have dedicated evidence-backed contracts.
- Bounded Stage12 batching is an execution contract.

## Research frontier

The repository already contains research branches for:

- clause-boundary feasibility;
- long-unit boundary feasibility;
- whole-context/content-loss investigation;
- n-best rescue experiments;
- MetricX semantic QE;
- prime notation;
- formula corruption;
- large integer corruption.

Existing experiments must be inspected before creating new implementations. Prefer result analysis and new evidence-driven hypotheses over duplicate mechanisms.

## Active investigation

Primary remaining quality problem:

**Long-unit content loss**

Current evidence path:

- `.github/workflows/rocketdict-full-opticks-long-unit-boundary-feasibility.yml`
- `.github/workflows/rocketdict-full-opticks-whole-context-rescue.yml`
- immutable full-Opticks artifacts and experiment outputs

Requirements:
- preserve immutable source coverage;
- avoid target-side repair;
- compare planner/context strategies on full failure classes;
- promote only after regression evidence.

Separate branches remain:
- prime ambiguity;
- formula/fraction corruption;
- large integer corruption.

## Forbidden shortcuts

Never promote:
- target literal insertion;
- corpus-specific patches;
- identity/dictionary substitution as translation;
- evaluator weakening;
- broad n-best fallback without semantic evidence.

## Before each development report

Synchronize:
- this file;
- `docs/memory/TRANSLATION_QUALITY.md`;
- `docs/memory/DECISIONS.md`;

against actual HEAD, CI and artifacts.

## Hot paths

- `rocketdict-product-core/src/rocketdict/translation_stage.py`
- `rocketdict-product-core/src/rocketdict/numeric_integrity.py`
- `rocketdict-workbench/tests/real_translation_full_opticks_*`
- `.github/workflows/`
