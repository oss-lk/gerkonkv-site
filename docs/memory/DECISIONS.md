# RocketDict durable decisions — L2

Store only conclusions that are expensive or risky to rediscover. This is not a changelog. Git history and L3 evidence contain chronology and raw detail.

## Quality is a release invariant, not an optimization variable

**Decision.** Speed, storage and context-cost optimizations may not reduce Product quality or evidence. Real EN→RU MT is mandatory; fake/identity/mock/dictionary substitution is never Product translation. Hard gates must not be weakened merely to pass CI, and source/corpus truncation must never be silent.

**Why.** The Product is explicitly quality-first and full-corpus research repeatedly found failures that can look superficially successful: translation compression, numeric corruption, prime/unit corruption and document-structure loss.

**Evidence.** `rocketdict/PRODUCT_TARGET.md`; `docs/memory/TRANSLATION_QUALITY.md`; maintained R1/full-*Opticks* workflows/artifacts.

## Maintained Product Core is the forward implementation; recovery is evidence, not the critical path

**Decision.** New Product work targets `rocketdict-product-core` plus Workbench unified orchestration. Historical 0.30.x/checkpoint recovery remains provenance/compatibility evidence but does not block the maintained Product path without a specific evidence-based reason.

**Why.** Direct and unified real source→Stage25 paths are green and replay-safe.

**Evidence.** Product Core run `34225159869`; `rocketdict-product-core/README.md`; Workbench maintained pipeline/tests.

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

## Translation-quality promotion requires contiguous evidence, not checker gaming

**Decision.** A maintained translation-quality change may be promoted only when the failure class is correctly identified (planner vs evaluator vs source-selection vs document structure vs execution resource vs model), the candidate remains raw/evidence-backed rather than synthetically repaired, and evidence extends to contiguous source when boundaries matter. Mechanical gate success alone is insufficient if target-language review exposes semantic degradation.

Raw OPUS n-best hypotheses are legitimate research candidates; post-hoc insertion of missing numbers/structure is not. Broad n-best fallback, arbitrary punctuation splitting and wholesale structural-island splitting are not Product policies.

**Why.** R1 and full-*Opticks* research demonstrated evaluator blind spots, planning defects, artificial joins and mechanically green but semantically poor hypotheses.

**Evidence.** `docs/memory/TRANSLATION_QUALITY.md`; maintained Stage12/numeric source; R1/full-*Opticks* artifacts.

## Numeric prime notation is a Product hard-gate invariant

**Decision.** Stage15 numeric/symbol integrity uses `rocketdict-maintained-numeric-integrity/5`; prime/unit notation is fail-closed and must not be collapsed into apostrophe-decimal semantics.

**Why.** Complete *Opticks* evidence found 17 prime-bearing units / 38 prime events and 11 rank0 prime corruptions. Numeric `/5` catches all prime failures under current planner evidence.

**Evidence.** `numeric_integrity.py`; `prime_notation.py`; full-*Opticks* runs `34205049701` and `34224998708`.

## Structural Gutenberg labels require planner isolation plus narrow raw-OPUS selection

**Decision.** Supported block labels `_Exper._ N.`, `_Obs._ N.`, `_Qu._ N.` are a source-document structure class. Product planner isolates the 108 block labels byte-exact; the single inline occurrence remains ordinary prose. Only the abbreviation in model input may be expanded to `Experiment`, `Observation`, `Query`; beam6 is attempted first and beam12 only for unresolved labels; only strict raw `Эксперимент/Наблюдение/Вопрос N.` with the same number is accepted; failure is fail-closed.

**Why.** Planner `/4` fragmented 48/109 labels. Exhaustive real-OPUS inventory gave acceptable raw candidates for 106/109 at beam6 and 109/109 after beam12. Planner `/7` full-corpus evidence then produced 108 structural-label units with zero label numeric failures.

**Evidence.** `structural_labels.py`; structural-label tests; runs/artifacts documented in `TRANSLATION_QUALITY.md`; full-*Opticks* run `34224998708`.

## Source-owned block section identifiers are preserved, inline references are translated

**Decision.** Narrow block identifiers of form `digit.A.` or `digit.A.digit.` are source-owned Gutenberg document structure when they occur at paragraph/block start. They may be isolated byte-exact and excluded from MT under `rocketdict-stage12-block-section-identifier/1`. Inline references such as `paragraph 1.F.3` remain ordinary linguistic prose and must not be captured.

**Why.** Planner `/7` full-corpus evidence showed repeated omission/Cyrillicization of block IDs inside prose units. Corpus inventory found 26 narrow occurrences, 21 block-level; only 12/21 block IDs were preserved exactly under `/7`. Preserving the block token pre-MT removes a genuine document-structure defect without inventing target text or changing inline prose semantics.

**Evidence.** `block_section_identifiers.py`; `test_block_section_identifiers.py`; planner `/8` migration run `34236048593`; full-*Opticks* `/7` artifact `10056028661`. Independent `/8` real/full-corpus acceptance is required before treating promotion as fully verified.

## Stage12 backend batching is an execution contract, not a planner contract

**Decision.** Primary Stage12 OPUS requests use `rocketdict-stage12-bounded-request-batch/1`, default batch size `48`, maximum `128`. Backend batch boundaries must preserve request order/cardinality and must not alter planner spans, model inputs, generation settings or output assembly. Batch contract/size are part of Stage12 cache/config/output provenance.

**Why.** Two full-corpus attempts terminated with hosted-runner `exit 143` while ~3.3k requests were submitted in one `translate_batch`. Bounded execution passed focused/full dependency-light regressions, direct/unified real Product smoke, and completed full Product Stage12 on the complete *Opticks* corpus.

**Evidence.** `translation_stage.py`; `test_translation_stage_batching.py`; Product Core run `34225159869`; full-*Opticks* run `34224998708`.

## Source-owned structure preservation is permitted only for exhaustively identified non-linguistic classes

**Decision.** Pre-MT passthrough is permitted only when the bytes are demonstrably document structure rather than linguistic content, detection is narrow and source-derived, source spans stay immutable, and inline linguistic uses remain outside the rule. Current examples are ASCII table geometry/numeric cells and block section identifiers. Structural labels are different: their semantic heading text is translated by real OPUS rather than passed through.

**Why.** This boundary prevents structural preservation from becoming a disguised target-repair/identity-translation mechanism.

**Evidence.** Stage12 table/structural-label/block-section contracts and full-corpus evidence.

## Structural handling does not license generic n-best or numeric islands

**Decision.** Narrow structural-label n-best is an exception for a source-defined class with exhaustive corpus inventory and strict semantic selection. It must not be generalized to ordinary translation units. Historical `numeric-islands-v1` remains negative unless genuinely new evidence justifies reopening it.

**Why.** Generic high-beam experiments produced semantically wrong hypotheses, while numeric-island experiments created backend/empty failures and risk synthetic repair semantics.

**Evidence.** Full-*Opticks* generic n-best artifacts; historical Stage8/R1 research.

## Project memory uses progressive disclosure and mandatory pre-response synchronization

**Decision.** Recovery is L1 `PROJECT_STATE.md` → HEAD diff → L2 `docs/memory/INDEX.md`/relevant durable docs → unrestricted L3 as evidence requires. Before every user-facing development result after an iteration, `PROJECT_STATE.md`, `docs/memory/TRANSLATION_QUALITY.md` and `docs/memory/DECISIONS.md` must be checked and synchronized to actual HEAD/CI/evidence.

**Why.** Progressive disclosure saves repeated reconstruction cost only if its caches are current. Stale memory can redirect work toward already-closed blockers or obsolete contracts.

**Evidence.** `AGENTS.md`.
