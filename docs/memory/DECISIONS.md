# RocketDict durable decisions — L2

Store only conclusions that are expensive or risky to rediscover. This is not a changelog. Git history and L3 evidence contain the chronology and raw detail.

## Quality is a release invariant, not an optimization variable

**Decision.** Speed, storage and context-cost optimizations may not reduce Product quality or evidence. Real EN→RU MT is mandatory; fake/identity/mock/dictionary substitution is never Product translation. Hard gates must not be weakened merely to pass CI, and source/corpus truncation must never be silent.

**Why.** The Product is explicitly quality-first and past research found failures that can look superficially successful: translation compression, numeric corruption, prime/unit corruption and document-structure loss.

**Evidence.** `rocketdict/PRODUCT_TARGET.md`; `docs/memory/TRANSLATION_QUALITY.md`; maintained R1/full-Opticks workflows and artifacts.

## Maintained Product Core is the forward implementation; recovery is evidence, not the critical path

**Decision.** New Product work targets `rocketdict-product-core` plus the Workbench unified orchestration. Historical 0.30.x/checkpoint recovery remains available for provenance, compatibility and evidence, but must not block or replace the maintained Product path without a specific evidence-based reason.

**Why.** The maintained direct and unified user-facing real source→Stage25 paths are green and replay-safe.

**Evidence.** `rocketdict-product-core/README.md`; `rocketdict-workbench/src/rocketdict_workbench/maintained_product_pipeline.py`; Product Core run `34207018066`.

## Product assets and downstream evidence are pinned and fail-closed

**Decision.** Use the official OPUS EN→RU `opus-2020-02-11` asset with ZIP SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677` and `float32` for quality acceptance. Stage21 uses pinned CEFR-J evidence, Stage22 exact CMUdict evidence without generated pronunciation fallback, Stage23 examples are sense-scoped, and Stage24/25 identities are immutable/replayable.

**Why.** These constraints distinguish reproducible Product evidence from heuristics or silent degradation.

**Evidence.** `rocketdict/PRODUCT_TARGET.md`; maintained downstream source/tests and Product Core real smoke.

## Unified runs must be resumable and replay-safe

**Decision.** The user-facing Product workflow must resume from durable identities/cache rather than reconstructing synthetic state. Re-entry after completion must preserve the immutable Stage25 export identity/content for the same inputs/configuration.

**Why.** Full-corpus runs are too expensive and failure-prone to require all-or-nothing reruns, and reproducibility is part of the Product/research contract.

**Evidence.** `rocketdict-workbench/src/rocketdict_workbench/product_run_state.py`; `maintained_product_pipeline.py`; `rocketdict-workbench/tests/real_product_run_smoke.py`.

## Acceptance order is unified smoke → full corpus → distributable Product

**Decision.** The complete user-facing real source→Stage25 workflow and replay must be green before full-corpus acceptance; full public-domain acceptance/quality evidence must be stable before treating Windows distribution as the release frontier.

**Why.** Packaging an unproven quality path would freeze known translation defects into the distributable Product.

**Evidence.** `rocketdict/PRODUCT_TARGET.md`; `.github/workflows/rocketdict-product-core.yml`; full-*Opticks* workflows.

## Translation-quality promotion requires contiguous evidence, not checker gaming

**Decision.** A maintained translation-quality change may be promoted only when the failure class is correctly identified (planner vs evaluator vs source-selection artifact vs document structure vs model), the candidate remains raw/evidence-backed rather than synthetically repaired, and evidence extends to contiguous source when selection boundaries can affect the result. Mechanical gate success alone is insufficient if target-language review exposes semantic degradation.

Raw OPUS n-best hypotheses are legitimate research candidates; post-hoc insertion of missing numbers/structure is not. Broad n-best fallback, arbitrary punctuation-boundary splitting and wholesale structural-island splitting are not Product policies.

**Why.** R1 and full-*Opticks* research demonstrated evaluator blind spots, planning defects, artificial joins and hypotheses that pass narrow invariants while worsening useful translation.

**Evidence.** `docs/memory/TRANSLATION_QUALITY.md`; maintained Stage12/numeric source; R1/full-*Opticks* artifacts.

## Numeric prime notation is a Product hard-gate invariant

**Decision.** Stage15 numeric/symbol integrity uses `rocketdict-maintained-numeric-integrity/5`; prime/unit notation is fail-closed and must not be collapsed into apostrophe-decimal semantics.

**Why.** Complete *Opticks* evidence found 17 prime-bearing Stage12 units and 11 rank0 prime corruptions; seven had falsely passed numeric `/4`. Examples included prime marks becoming feet or losing prime count. `/5` closes proven false passes rather than weakening thresholds.

**Evidence.** `rocketdict-product-core/src/rocketdict/numeric_integrity.py`; `prime_notation.py`; full-*Opticks* run `34205049701`, artifact `10047696652`; Product Core real smoke after promotion.

## Structural Gutenberg labels require planner isolation plus narrow raw-OPUS selection

**Decision.** Supported block labels `_Exper._ N.`, `_Obs._ N.`, `_Qu._ N.` are a source-document structure class. Product handling may use a narrow source-side canonicalization + raw OPUS selector only after the planner isolates each supported **block** label into a byte-exact standalone Stage12 unit. The one supported inline occurrence remains on the ordinary text path.

The maintained structural-label contract is `rocketdict-stage12-block-structural-label-opus/1`:

- immutable source bytes/spans remain unchanged;
- only the abbreviation in model input is literally expanded to `Experiment`, `Observation`, or `Query`;
- beam6 is attempted first; beam12 is permitted only for unresolved structural-label units;
- only raw target `Эксперимент/Наблюдение/Вопрос N.` with the same number and numeric `/5` pass may be selected;
- if no such raw candidate exists, Stage12 must fail closed;
- no target-side injection, placeholders, fabricated punctuation or broad n-best fallback is licensed.

**Why.** Full-*Opticks* inventory found 109 supported labels. Source-side canonicalized real OPUS contains an acceptable raw candidate for 106/109 at beam6 and 109/109 after beam12; the only beam6 gap is `Observation 1.`. Current planner `/4` is structurally inadequate: 48/109 labels cross planned-unit boundaries, so execution-only special handling would operate after source structure has already been damaged. Exactly one supported occurrence is inline; the other 108 are block labels.

**Evidence.** `rocketdict-product-core/src/rocketdict/structural_labels.py`; structural-label tests; runs `34208337952`, `34209680326`, `34210312015`; artifacts `10048735151`, `10049272284`, `10049542652`; `docs/memory/TRANSLATION_QUALITY.md`.

## Structural-label handling does not license generic n-best

**Decision.** The structural-label mechanism is an exception for a source-defined document token class with exhaustive corpus inventory and strict semantic selection. It must not be generalized to ordinary translation units.

**Why.** Generic high-beam experiments produced mechanically acceptable but semantically wrong hypotheses (including prime/unit corruption), while structural-label canonicalization has explicit source identity, exact expected semantic term and complete 109-event evidence.

**Evidence.** Full-*Opticks* generic n-best escalation and structural-label inventory/escalation artifacts.

## Stage8 negative results must not be rediscovered by default

**Decision.** Historical F96/Stage8 research is reusable evidence, not an instruction to restart the DOE. In particular, `numeric-islands-v1` remains negative unless new evidence justifies reopening it; long atomic units require careful splitting; table structure requires distinct handling; evaluator failures must be separated from model failures.

**Why.** These conclusions came from expensive real-model/corpus experiments and repeating them without new grounds wastes compute/context and risks reintroducing known defects.

**Evidence.** `rocketdict/START_HERE.md`; `rocketdict/RESEARCH_STATUS.md`; `rocketdict/research/`; Git history.

## Project memory uses progressive disclosure and mandatory pre-response synchronization

**Decision.** Recovery is L1 `PROJECT_STATE.md` → HEAD diff → L2 `docs/memory/INDEX.md`/relevant durable docs → unrestricted L3 as evidence requires. Before every user-facing development result after an iteration, `PROJECT_STATE.md`, `docs/memory/TRANSLATION_QUALITY.md` and `docs/memory/DECISIONS.md` must be checked and synchronized to actual HEAD/CI/evidence.

**Why.** Progressive disclosure saves repeated reconstruction cost only if its caches are current. A stale L1/L2 can redirect development toward already-closed blockers or obsolete contracts.

**Evidence.** `AGENTS.md`.
