# RocketDict durable decisions — L2

Store only conclusions that are expensive or risky to rediscover. This is not a changelog. Git history and L3 evidence contain chronology and raw detail.

## Quality is a release invariant, not an optimization variable

**Decision.** Speed, storage and context-cost optimizations may not reduce Product quality or evidence. Real EN→RU MT is mandatory; fake/identity/mock/dictionary substitution is never Product translation. Hard gates must not be weakened merely to pass CI, and source/corpus truncation must never be silent.

**Why.** Full-corpus research repeatedly finds failures that can look superficially successful: semantic compression, numeric corruption, prime/unit corruption and document-structure loss.

**Evidence.** `rocketdict/PRODUCT_TARGET.md`; `docs/memory/TRANSLATION_QUALITY.md`; maintained R1/full-*Opticks* workflows/artifacts.

## Maintained Product Core is the forward implementation

**Decision.** New Product work targets `rocketdict-product-core` plus Workbench unified orchestration. Historical 0.30.x/checkpoint recovery remains provenance/compatibility evidence but is not the critical path without a specific evidence-based reason.

**Why.** Direct and unified real source→Stage25 paths are green and replay-safe under the current planner `/8` line.

**Evidence.** Product Core run `34250903497`; `rocketdict-product-core/README.md`; Workbench maintained pipeline/tests.

## Product assets and downstream evidence are pinned and fail-closed

**Decision.** Use official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian and `float32` acceptance compute. Stage21 uses pinned CEFR-J, Stage22 exact CMUdict without generated authoritative fallback, Stage23 examples are sense-scoped, and Stage24/25 identities are immutable/replayable.

**Why.** These constraints distinguish reproducible Product evidence from heuristics or silent degradation.

**Evidence.** `rocketdict/PRODUCT_TARGET.md`; maintained downstream code/tests; Product Core real smoke.

## Unified runs must be resumable and replay-safe

**Decision.** The user-facing Product workflow must resume from durable identities/cache rather than reconstructing synthetic state. Re-entry after completion must preserve immutable Stage25 export identity/content for the same inputs/configuration.

**Why.** Full-corpus runs are expensive/failure-prone and reproducibility is part of the Product contract.

**Evidence.** Workbench product run state/pipeline and `real_product_run_smoke.py`.

## Acceptance order is unified smoke → full corpus → distributable Product

**Decision.** Complete user-facing real source→Stage25 workflow/replay must be green before full-corpus acceptance; full public-domain acceptance/quality evidence must be stable before Windows distribution becomes the release frontier.

**Why.** Packaging an unproven quality path would freeze known translation defects into the distributable Product.

**Evidence.** `rocketdict/PRODUCT_TARGET.md`; Product Core/full-*Opticks* workflows.

## Translation-quality promotion requires contiguous evidence and semantic review

**Decision.** A maintained translation-quality change may be promoted only when the failure class is correctly identified (planner vs evaluator vs source-selection vs document structure vs execution resource vs model), the candidate remains raw/evidence-backed rather than synthetically repaired, and evidence extends to contiguous source when boundaries matter. Mechanical gate success is insufficient when target-language review exposes semantic degradation.

Raw OPUS n-best hypotheses are legitimate research candidates; post-hoc insertion of missing numbers/structure is not. Broad n-best fallback, arbitrary punctuation splitting, generic structural islands and evaluator weakening are not Product policies.

**Why.** R1 and full-*Opticks* research repeatedly produced mechanically green but semantically poor hypotheses.

**Evidence.** `docs/memory/TRANSLATION_QUALITY.md`; maintained Stage12/numeric source; R1/full-*Opticks* artifacts.

## Numeric prime notation is a Product hard-gate invariant

**Decision.** Stage15 numeric/symbol integrity uses `rocketdict-maintained-numeric-integrity/5`; prime/unit notation is fail-closed and must not be collapsed into apostrophe-decimal semantics.

**Why.** Current planner `/8` complete *Opticks* evidence still finds 17 prime-bearing units / 38 prime events and 11 rank0 prime corruptions. Numeric `/5` catches every one.

**Evidence.** `numeric_integrity.py`; `prime_notation.py`; full-*Opticks* run `34244876537`, artifact `10064356708`.

## Prime-fragment structural decomposition is rejected despite mechanical success

**Decision.** Do not promote the research branch that preserves numeric prime-expression fragments byte-exact while separately translating surrounding prose.

**Why.** It reaches 16/16 strict mechanical success on ordinary prime units, but removing local context produces semantically unacceptable Russian in real full-corpus examples (`53 deg.` → `53 балла`, `hundred Feet` → `сто ног`). Quality-first rules prohibit trading semantics for gate success.

Whole-unit Unicode prime normalization and semantic hints are also rejected as current Product preprocessing: the former yields 0/16 strict success; the latter rescues 0/11 baseline failures. Whole-unit beam6→12→16 rescues only 4/11 prime failures and does not justify a generic fallback.

**Evidence.** Prime feasibility run `34249764521`, artifact `10065557329`; staged n-best evidence in run `34248620999`, artifact `10065076540`.

## Structural Gutenberg labels require planner isolation plus narrow raw-OPUS selection

**Decision.** Supported block labels `_Exper._ N.`, `_Obs._ N.`, `_Qu._ N.` are a source-document structure class. Product planner isolates the 108 block labels byte-exact; the single inline occurrence remains ordinary prose. Only the abbreviation in model input may be expanded to `Experiment`, `Observation`, `Query`; beam6 is attempted first and beam12 only for unresolved labels; only strict raw `Эксперимент/Наблюдение/Вопрос N.` with the same number is accepted; failure is fail-closed.

**Why.** Exhaustive real-OPUS inventory gave acceptable raw candidates for 106/109 at beam6 and 109/109 after beam12. Current full-corpus evidence keeps the class numerically clean.

**Evidence.** `structural_labels.py`; structural-label tests; full-*Opticks* artifacts documented in `TRANSLATION_QUALITY.md`.

## Source-owned block section identifiers are a closed maintained class

**Decision.** Narrow block identifiers of form `digit.A.` or `digit.A.digit.` are source-owned Gutenberg document structure when they occur at block/paragraph start. They are isolated byte-exact and excluded from MT under `rocketdict-stage12-block-section-identifier/1`. Inline references remain ordinary linguistic prose.

**Why.** Planner `/7` lost or Cyrillicized 9/21 block identifiers. Planner `/8` full-corpus audit preserves 21/21 block identifiers exactly, performs zero model requests for them, and keeps all 5 inline identifiers on the ordinary MT path.

**Evidence.** `block_section_identifiers.py`; block-section tests; full-*Opticks* run `34244876537`, artifact `10064356708`.

## Stage12 backend batching is an execution contract, not a planner contract

**Decision.** Primary Stage12 OPUS requests use `rocketdict-stage12-bounded-request-batch/1`, default batch size `48`, maximum `128`. Backend batch boundaries must preserve request order/cardinality and must not alter planner spans, model inputs, generation settings or output assembly. Batch contract/size are part of Stage12 cache/config/output provenance.

**Why.** Monolithic full-corpus inference caused repeated hosted-runner `exit 143`. Bounded execution completed full Product Stage12 and preserves direct/unified real Product behavior.

**Evidence.** `translation_stage.py`; batching tests; Product/full-*Opticks* runs documented in `TRANSLATION_QUALITY.md`.

## Source-owned structure preservation is permitted only for exhaustively identified non-linguistic classes

**Decision.** Pre-MT passthrough is permitted only when bytes are demonstrably document structure rather than linguistic content, detection is narrow and source-derived, source spans stay immutable, and inline linguistic uses remain outside the rule. Current examples are ASCII table geometry/numeric cells and block section identifiers. Structural labels are different: their semantic heading text is translated by real OPUS rather than passed through.

**Why.** This boundary prevents structural preservation from becoming disguised target repair/identity translation.

**Evidence.** Stage12 table/structural-label/block-section contracts and full-corpus evidence.

## Large-integer grouping is rejected as Product preprocessing

**Decision.** Do not normalize ordinary long integers by inserting thousands separators or rewrite narrow multiplication `x` to `×` merely to improve OPUS numeric preservation.

**Why.** Complete planner `/8` inventory found 12 ordinary ≥7-digit units, four baseline hard failures. The research branch rescues 0/4 failures and regresses some previously strict-successful units.

**Evidence.** Run `34250592035`, artifact `10065848534`, `rocketdict-full-opticks-large-integer-feasibility/1`.

## Compact-formula operator spacing is rejected as Product preprocessing

**Decision.** Do not rely on adding whitespace around arithmetic operators / trailing algebraic `A` in whole-unit model input for the current compact formula class.

**Why.** The complete *Opticks* planner `/8` inventory has one investigated matching unit (`3/8A ... ((61-1/2)/8)A`); spacing does not rescue it even with staged raw n-best.

**Evidence.** Run `34250960739`, artifact `10065980547`, `rocketdict-full-opticks-formula-spacing-feasibility/1`.

## Structural handling does not license generic n-best or numeric islands

**Decision.** Narrow structural-label n-best is an exception for a source-defined class with exhaustive corpus inventory and strict semantic selection. It must not be generalized to ordinary translation units. Historical `numeric-islands-v1` remains negative unless genuinely new evidence justifies reopening it.

**Why.** Generic high-beam experiments produce semantically wrong hypotheses; numeric-island experiments created backend/empty failures and risk synthetic repair semantics.

**Evidence.** Full-*Opticks* generic n-best artifacts; historical Stage8/R1 research.

## Project memory uses progressive disclosure and mandatory pre-response synchronization

**Decision.** Recovery is L1 `PROJECT_STATE.md` → HEAD diff → L2 `docs/memory/INDEX.md`/relevant durable docs → unrestricted L3 as evidence requires. Before every user-facing development result after an iteration, `PROJECT_STATE.md`, `docs/memory/TRANSLATION_QUALITY.md` and `docs/memory/DECISIONS.md` must be checked and synchronized to actual HEAD/CI/evidence.

**Why.** Progressive disclosure saves repeated reconstruction cost only if its caches are current. Stale memory can redirect work toward already-closed blockers or obsolete contracts.

**Evidence.** `AGENTS.md`.
