# RocketDict durable decisions — L2

Store only conclusions that are expensive or risky to rediscover. This is not a changelog. Git history and L3 evidence contain the chronology and raw detail.

## Quality is a release invariant, not an optimization variable

**Decision.** Speed, storage and context-cost optimizations may not reduce Product quality or evidence. Real EN→RU MT is mandatory; fake/identity/mock/dictionary substitution is never Product translation. Hard gates must not be weakened merely to pass CI, and source/corpus truncation must never be silent.

**Why.** The Product is explicitly quality-first and past research found failures that can look superficially successful (translation compression, numeric corruption, structural table failures).

**Evidence.** `rocketdict/PRODUCT_TARGET.md`; `rocketdict/START_HERE.md`; Stage8 research under `rocketdict/research/`.

## Maintained Product Core is the forward implementation; recovery is evidence, not the critical path

**Decision.** New Product work targets `rocketdict-product-core` plus the Workbench unified orchestration. Historical 0.30.x/checkpoint recovery remains available for provenance, compatibility and evidence, but must not block or replace the maintained Product path without a specific evidence-based reason.

**Why.** Stage20→25 was migrated into the maintained core and the direct maintained-core real runtime path now reaches Stage25.

**Evidence.** `rocketdict-product-core/README.md`; commits `fae37f5`, `2b5e1a6`, `2e3b016`, `759f484`, `8319e91`, `1235dab`; `rocketdict-product-core/tests/real_runtime_smoke.py`.

## Product assets and downstream evidence are pinned and fail-closed

**Decision.** Use the official OPUS EN→RU `opus-2020-02-11` asset with ZIP SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677` and `float32` for quality acceptance. Stage21 uses the pinned POS-aware CEFR-J source, Stage22 uses exact CMUdict evidence without generated pronunciation fallback, Stage23 examples are sense-scoped, and Stage24/25 identities are immutable/replayable.

**Why.** These constraints distinguish reproducible Product evidence from heuristics or silent degradation.

**Evidence.** `rocketdict/PRODUCT_TARGET.md`; `rocketdict-product-core/src/rocketdict/downstream.py`; `rocketdict-workbench/src/rocketdict_workbench/maintained_product_pipeline.py`; Product Core real smoke/workflow.

## Unified runs must be resumable and replay-safe

**Decision.** The user-facing Product workflow must resume from durable identities/cache rather than reconstructing synthetic state. Re-entry after completion must preserve the immutable Stage25 export identity/content for the same inputs/configuration.

**Why.** The eventual 90k+ acceptance run is too expensive and failure-prone to require all-or-nothing reruns, and reproducibility is part of the Product/research contract.

**Evidence.** `rocketdict-workbench/src/rocketdict_workbench/product_run_state.py`; `maintained_product_pipeline.py`; `rocketdict-workbench/tests/real_product_run_smoke.py`; commits `2b5e1a6`, `8319e91`, `4c941715`.

## Acceptance order is unified smoke → full corpus → distributable Product

**Decision.** First prove the complete user-facing real source→Stage25 workflow and replay. Then run the full public-domain 90k+ corpus acceptance/research matrix with no source truncation and audit output quality/evidence. Only after that should the Windows installable artifact be treated as the release frontier.

**Why.** A green direct core smoke does not prove the user-facing orchestration; packaging before end-to-end acceptance would freeze an unproven path.

**Evidence.** `rocketdict/PRODUCT_TARGET.md`; `.github/workflows/rocketdict-product-core.yml`; `rocketdict-workbench/tests/real_product_run_smoke.py`.

## Translation-quality promotion requires contiguous evidence, not checker gaming

**Decision.** A maintained translation-quality change may be promoted only when the failure class is correctly identified (planner vs evaluator vs source-selection artifact vs model), the candidate remains raw/evidence-backed rather than synthetically repaired, and evidence extends beyond a frozen discontinuous stress excerpt when that discontinuity can affect the result. Mechanical hard-gate success alone is insufficient if target-language review exposes semantic or structural degradation.

Raw OPUS n-best hypotheses are legitimate research candidates; post-hoc insertion of missing numbers/structure is not. Broad n-best fallback, arbitrary punctuation-boundary splitting and wholesale structural-island splitting are not current Product policies. Detailed maintained findings and current contracts live in [`TRANSLATION_QUALITY.md`](TRANSLATION_QUALITY.md).

**Why.** The maintained R1 campaign demonstrated all four confounders: evaluator false positives, real Stage12 planning defects, artificial joins at frozen-selection boundaries, and model hypotheses that satisfy a narrow invariant while worsening useful translation text. Without this separation a green metric can represent a worse Product.

**Evidence.** `docs/memory/TRANSLATION_QUALITY.md`; `rocketdict-product-core/src/rocketdict/translation_stage.py`; `numeric_integrity.py`; maintained R1/full-Opticks workflows and artifacts.

## Stage8 negative results must not be rediscovered by default

**Decision.** Historical F96/Stage8 research is reusable evidence, not an instruction to restart the DOE. In particular, `numeric-islands-v1` remains an experimental/fail-closed negative branch unless new evidence justifies reopening it; long atomic units require careful splitting; table structure requires distinct handling; evaluator failures must be separated from model failures.

**Why.** These conclusions came from expensive real-model/corpus experiments and repeating them without new grounds wastes compute/context and risks reintroducing known defects.

**Evidence.** `rocketdict/START_HERE.md`; `rocketdict/RESEARCH_STATUS.md`; `rocketdict/research/`; Git history.

## Project memory uses progressive disclosure

**Decision.** Recovery is L1 `PROJECT_STATE.md` → HEAD diff → L2 `docs/memory/INDEX.md`/relevant durable docs → unrestricted L3 as evidence requires. Exhaustively rereading the repository/history/spec is not the default reconstruction mechanism.

**Why.** Repeated context reconstruction consumes model effort without adding engineering value. The policy changes only what is loaded first, never how deeply the model may reason or investigate.

**Evidence.** `AGENTS.md`. If this rule ever hides relevant evidence or reduces verification depth, the implementation of the rule is wrong and L3 must be expanded immediately.
