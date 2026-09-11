# RocketDict durable decisions — L2

Store only conclusions that are expensive or risky to rediscover. This is not a changelog. Git history and L3 evidence contain chronology and raw detail.

## Quality is a release invariant, not an optimization variable

**Decision.** Speed, storage and context-cost optimizations may not reduce Product quality or evidence. Real EN→RU MT is mandatory; fake/identity/mock/dictionary substitution is never Product translation. Hard gates must not be weakened merely to pass CI, and source/corpus truncation must never be silent.

**Why.** Full-corpus research repeatedly finds failures that can look superficially successful: semantic compression, numeric corruption, prime/unit corruption and document-structure loss.

**Evidence.** `rocketdict/PRODUCT_TARGET.md`; `docs/memory/TRANSLATION_QUALITY.md`; maintained full-*Opticks* workflows/artifacts.

## Maintained Product Core is the forward implementation

**Decision.** New Product work targets `rocketdict-product-core` plus Workbench unified orchestration. Historical 0.30.x/checkpoint recovery remains provenance/compatibility evidence but is not the critical path without a specific evidence-based reason.

**Why.** Direct and unified real source→Stage25 paths are replay-safe; current work is full-corpus quality hardening rather than rebuilding old orchestration.

## Product assets and downstream evidence are pinned and fail-closed

**Decision.** Use official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian and `float32` acceptance compute. Downstream maintained identities remain pinned/replayable.

**Why.** These constraints distinguish reproducible Product evidence from heuristics or silent degradation.

## Unified runs must be resumable and replay-safe

**Decision.** User-facing Product workflow resumes from durable identities/cache rather than reconstructing synthetic state. Re-entry after completion must preserve immutable Stage25 export identity/content for identical inputs/configuration.

**Why.** Full-corpus runs are expensive and reproducibility is part of Product quality.

## Translation-quality promotion requires contiguous evidence and semantic review

**Decision.** A maintained quality change may be promoted only after correctly classifying the defect (planner vs evaluator vs source-selection vs document structure vs execution resource vs model), preserving immutable source ownership, and validating on contiguous evidence when boundaries matter. Mechanical gate success alone is insufficient.

Raw OPUS hypotheses are legitimate research candidates; post-hoc insertion of missing literals/structure is not. Broad n-best fallback, arbitrary punctuation splitting, generic structural islands and evaluator weakening are not Product policies.

**Evidence.** `docs/memory/TRANSLATION_QUALITY.md`; maintained Stage12 and full-*Opticks* artifacts.

## Numeric prime notation is a Product hard-gate invariant

**Decision.** Stage15 numeric/symbol integrity uses `rocketdict-maintained-numeric-integrity/5`; prime/unit notation is fail-closed and must not be collapsed into apostrophe-decimal semantics.

**Why.** Full-corpus evidence still contains genuine rank0 prime corruptions and the maintained gate catches them.

## Prime-fragment structural decomposition is rejected despite mechanical success

**Decision.** Do not promote the research branch that preserves prime-expression fragments byte-exact while separately translating surrounding prose.

**Why.** It can make mechanical gates green while destroying local semantics (`53 deg.` → `53 балла`, `hundred Feet` → `сто ног`). Whole-unit normalization/hints and broad staged n-best also fail to solve the class sufficiently.

## Structural Gutenberg labels are a narrow source-defined OPUS class

**Decision.** Maintained structural-label contract is `rocketdict-stage12-block-structural-label-opus/2`.

It includes only source-proven block structure:
- 108 `_Exper._/_Obs._/_Qu._` numeric labels;
- 54 complete legacy Roman headings from the pinned corpus (`DEFIN.`, `AX.`, `PROP.`, `_PROP._ ... PROB./THEOR.`).

All are isolated byte-exact; only documented English abbreviations/headings may be expanded in model input; accepted targets must be unmodified real-OPUS hypotheses satisfying strict family/identifier forms. Inline linguistic references remain ordinary prose.

**Why.** `/2` removes the intended legacy-heading length-loss class: full-corpus length failures fall from 24 to 5 while numeric remains 27 and punctuation remains 34. The change is class-specific rather than a generic bypass.

**Evidence.** `structural_labels.py`; `legacy_block_headings.py`; `/2` full-*Opticks* run `34575909618`, artifact `10190059238`.

## Bare Roman fragments must not be reclassified as structural headings

**Decision.** Do not add a rule that treats standalone `II.`, `IV.` etc. as source-owned structure merely because Stage8/Stage10 sentence segmentation produced a tiny Stage12 row.

**Why.** Current residual examples are inline footnote references such as `Sect. IV.` / `Sect. II.`, not block headings. Treating them as structure would turn a context-boundary defect into false document classification.

**Next valid direction.** Investigate abbreviation/sentence-boundary context preservation or another source-derived context mechanism.

## Source-owned block section identifiers are a closed maintained class

**Decision.** Narrow block identifiers of form `digit.A.` or `digit.A.digit.` are source-owned Gutenberg structure only at block/paragraph start and are excluded from MT under `rocketdict-stage12-block-section-identifier/1`. Inline references remain ordinary linguistic prose.

**Why.** Full-corpus evidence preserves all 21 block identifiers exactly while keeping all five inline occurrences on the ordinary MT path.

## Stage12 backend batching is execution, not planning

**Decision.** Primary OPUS requests use `rocketdict-stage12-bounded-request-batch/1`, default batch size `48`, maximum `128`. Backend batches must preserve request order/cardinality and must not alter source/planner spans, model inputs, generation settings or assembly.

**Why.** This bounds resource usage without changing translation semantics.

## Whole-context rescue remains research-only; hard-failure triggering is the next evidence boundary

**Decision.** Do not promote generic whole-context translation from corpus-wide alpha gain or mechanical cleanliness. The existing Product-exposed whole-context path remains opt-in and narrowly numeric-triggered.

For further research, restrict attention to split contexts that already contain a maintained Product hard-gate failure. On the current `/2` full-*Opticks* evidence this yields 23 contexts; 22 are within the 160-NLP-token cap and the existing strict selector accepts eight (`550, 669, 919, 1024, 1393, 2238, 2462, 2726`).

**Why.** This trigger is causally tied to an already-proven Product defect and is much safer than selecting among 234 mechanically clean whole-context candidates or 213 positive-alpha candidates corpus-wide. Even so, eight accepted cases still require independent semantic/QE evidence before any Product policy change.

**Evidence.** `audit_full_opticks_hard_gates.py`; `audit_full_opticks_whole_context_hard_failures.py`; whole-context run `34575909649`, artifact `10190367866`.

## MetricX is an independent research ranker, not an acceptance threshold

**Decision.** MetricX-24 reference-free QE may compare immutable raw candidates, but neither a score nor “MetricX prefers candidate” is sufficient for Product selection. Scores must be version-pinned, preserved as evidence, and paired with mechanical gates plus semantic review.

**Why.** Previous TC-big evidence shows MetricX can rank useful strict hypotheses, but learned QE is not a proof of faithfulness. The new whole-context MetricX audit is intentionally limited to the eight already-hard-failing strict candidates.

## Punctuation residuals must be split by defect family

**Decision.** Do not introduce a universal punctuation repair or selector for the current 34 failures.

**Why.** The residual mixes lost footnote markers, illustration brackets, omitted parenthetical content, added parentheses/hallucinations and question-mark drift. Source-structure defects, context loss and model errors require different mechanisms.

## Large-integer grouping is rejected as Product preprocessing

**Decision.** Do not insert thousands separators or rewrite narrow multiplication `x` to `×` merely to improve OPUS preservation.

**Why.** Complete planner `/8` research rescued 0/4 affected hard failures and regressed some previously successful cases.

## Compact-formula operator spacing is rejected as Product preprocessing

**Decision.** Do not rely on adding whitespace around arithmetic operators / trailing algebraic `A` for the current compact formula class.

**Why.** The complete corpus has one investigated matching unit and spacing does not rescue it even with staged raw n-best.

## Source-owned structure preservation is allowed only for exhaustively identified non-linguistic classes

**Decision.** Pre-MT passthrough is allowed only when bytes are demonstrably document structure rather than linguistic content, detection is narrow/source-derived, spans stay immutable, and inline linguistic uses stay outside the rule. Structural headings are translated through strict real OPUS rather than identity-passed.

**Why.** This prevents structural handling from becoming disguised target repair.

## Acceptance order remains unified smoke → full corpus → distributable Product

**Decision.** User-facing real source→Stage25/replay must be green before full-corpus acceptance; full public-domain acceptance/quality evidence must be stable before Windows distribution becomes the release frontier.

**Why.** Packaging an unproven quality path would freeze known translation defects into the distributable Product.

## Project memory uses progressive disclosure and mandatory synchronization

**Decision.** Recovery is L1 `PROJECT_STATE.md` → HEAD diff → L2 `docs/memory/INDEX.md`/relevant durable docs → unrestricted L3 as evidence requires. Before a user-facing development result after a substantial iteration, synchronize L1/L2 with actual HEAD/CI/evidence.

**Evidence.** `AGENTS.md`.
