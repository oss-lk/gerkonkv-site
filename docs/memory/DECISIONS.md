# RocketDict durable decisions — L2

Store only conclusions that are expensive or risky to rediscover. This is not a changelog; Git history and L3 evidence contain chronology and raw detail.

## Quality is a release invariant

**Decision.** Speed, storage and convenience may not reduce Product quality/evidence. Real EN→RU MT is mandatory; fake/identity/mock/dictionary substitution is never Product translation. Hard gates may not be weakened merely to pass CI, and corpus/source truncation may never be silent.

**Why.** Full-corpus work repeatedly exposes failures that look superficially successful: semantic compression, numeric corruption, prime/unit corruption and structure loss.

## Maintained Product Core is the forward implementation

**Decision.** New Product work targets `rocketdict-product-core` plus Workbench unified orchestration. Historical 0.30.x/checkpoint material remains provenance/compatibility evidence, not the forward path without an evidence-based reason.

## Product assets and downstream evidence are pinned and fail-closed

**Decision.** Use official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian and `float32` acceptance compute. Downstream identities remain pinned/replayable.

## Unified runs must be resumable and replay-safe

**Decision.** User-facing Product workflow resumes from durable identities/cache rather than reconstructing synthetic state. Re-entry after completion must preserve immutable Stage25 export identity/content for identical inputs/configuration.

## Translation-quality promotion requires contiguous evidence and semantic review

**Decision.** A maintained quality change may be promoted only after classifying the defect (planner/evaluator/source/document/model/resource), preserving immutable source ownership, and validating boundary-sensitive behavior on contiguous evidence. Mechanical gate success alone is insufficient.

Raw OPUS hypotheses are legitimate research candidates. Post-hoc insertion of missing literals/structure, corpus-specific target patching, arbitrary punctuation splitting, broad n-best fallback, generic structural islands and evaluator weakening are not Product policies.

## Complete Product gate scope must not be inferred from stress subsets

**Decision.** Historical `product_numeric_failure_count` is a literal-bearing stress subset, not the complete gate. The complete maintained numeric/symbol gate is `rocketdict-maintained-numeric-integrity/5` over every selected Stage12 row.

**Why.** The canonical structural-label `/2` artifact has 30 complete numeric/symbol failures, not 27; three failures have no source digit literal.

## Numeric prime notation is a hard-gate invariant

**Decision.** Prime/unit notation remains fail-closed and must not be collapsed into apostrophe-decimal semantics.

## Prime-fragment structural decomposition is rejected

**Decision.** Do not promote byte-preserving prime-expression fragment decomposition.

**Why.** It can make gates green while damaging semantics (`53 deg.`→`53 балла`, `hundred Feet`→`сто ног`). Whole-unit normalization/hints and broad staged n-best also do not solve the class sufficiently.

## Structural Gutenberg labels are a narrow source-defined OPUS class

**Decision.** `rocketdict-stage12-block-structural-label-opus/2` includes only source-proven block structure: 108 `_Exper._/_Obs._/_Qu._` labels and 54 complete legacy Roman headings. They are isolated byte-exactly and translated only through strict raw-OPUS heading candidates. Inline linguistic references remain ordinary prose.

## Bare Roman fragments must not be reclassified as headings

**Decision.** Standalone `II.`, `IV.` etc. produced by sentence segmentation are not automatically source-owned structure.

**Why.** Known residuals are inline `Sect. IV.` / `Sect. II.` references. Reclassifying them would turn a context-boundary defect into false document classification.

## Roman-after-Sect citation rescue is pair-level and opt-in

**Decision.** The valid experiment is `rocketdict-stage12-citation-boundary-pair-rescue/1`, not a broad context merge and not a heading rule. Trigger: contiguous ordinary previous row ending `Sect.` + uppercase Roman-fragment row already failing length. Candidate: exact raw rank-0 OPUS pair output. Acceptance: Product hard clean, repaired length, no new strict-debt category. No rewriting/placeholders/literal injection. Default OFF.

**Why.** Broad citation/group coalescing lost unrelated numeric content and a footnote marker; pair-level evidence is materially safer.

## Length-failure whole-context rescue remains opt-in

**Decision.** `rocketdict-stage12-length-failure-whole-context-rescue/1` remains default OFF despite full-*Opticks* gain.

**Why.** It removes three maintained length failures and one numeric failure, but mechanical improvement alone is not sufficient Product-default evidence.

## Combined length + citation rescue closes current length class but is not auto-promoted

**Decision.** Public Stage12 may compose the two opt-in mechanisms, but both remain OFF by default. Run `34597648856` reaches `29 numeric / 34 punctuation / 0 length`, `59` unique failures with byte-exact source coverage and exact raw rank-0 applied targets. This is evidence, not authorization for default promotion.

## Generic whole-context strictness is not semantically sufficient

**Decision.** Do not promote a generic whole-context fallback merely because the existing strict selector accepts it.

**Why.** Post-composition lineage auditing showed that context `2725` remains mechanically strict-clean as a whole-context candidate and removes an invented `=`, yet L3 inspection proves that the candidate silently drops source phrase `_per deliquium_`. This is a direct counterexample to treating old strict mechanical acceptance as semantic proof.

**Consequence.** Historical mechanically accepted contexts must be re-evaluated against current composed output and additional source-derived semantic-preservation diagnostics before use. Generic alpha gain remains non-authoritative.

## Ordinary Gutenberg underscore emphasis is a separate preservation signal

**Decision.** Preserve the historical `critical_technical_tokens/3` meaning and add `rocketdict-maintained-emphasis-markup-preservation/1` as a separate versioned research diagnostic rather than silently widening the old contract.

**Why.** `critical_technical_tokens/3` intentionally treated only symbolic underscore emphasis as technical. The `2725` counterexample loses ordinary emphasized prose (`_per deliquium_`), so widening the old contract retroactively would change the meaning of immutable historical evidence.

**Current use.** The emphasis diagnostic is a conservative veto in the numeric-hard whole-context rescue. It is not itself a Product hard gate.

## Numeric-hard split-context whole-context rescue is narrow, evidence-backed and default-OFF

**Decision.** `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1` is a separate opt-in wrapper above the current citation+length composition. It is **not yet wired into public `product.stage12.run`** and must remain default OFF pending explicit promotion/exposure evidence.

Trigger requirements:
- current Stage10 context remains split into multiple selected Stage12 rows;
- at least one current row already fails `rocketdict-maintained-numeric-integrity/5`;
- exact unchanged whole Stage10 source context fits the existing 160-NLP-token cap;
- pinned OPUS beam=6/rank0 generation is used.

Acceptance requires:
1. the existing strict whole-context selector accepts the single raw candidate;
2. `rocketdict-maintained-emphasis-markup-preservation/1` passes.

No source rewrite, target rewrite, placeholders or post-translation literal injection are permitted.

**Evidence.** Full-*Opticks* run `34601313026`, artifact `10264132732`, accepts only contexts `550, 669, 1024, 2238`; rejects `1460, 2132, 2176, 2190, 2634, 2725`, with `2725` specifically blocked by emphasis preservation. Result: **29/34/0 → 25/33/0**, unique failures **59→55**, source coverage byte-exact, untouched rows base-exact, applied targets exact raw rank-0. Product Core CI `34601005247` is green.

**Why not public/default yet.** The run explicitly keeps `promotion_allowed=false`, `automatic_product_default_allowed=false`, semantic review required. A public opt-in exposure decision should be separate from a default-promotion decision.

## Punctuation residuals must be split by defect family

**Decision.** Do not introduce a universal punctuation repair/selector.

**Why.** Residuals mix lost footnote markers, illustration brackets, omitted/added parentheticals, question-mark drift and other delimiter failures. Structure defects, context loss and model hallucinations require different mechanisms.

## Large-integer grouping is rejected as Product preprocessing

**Decision.** Do not insert thousands separators or rewrite narrow multiplication `x` to `×` merely to improve OPUS preservation.

**Why.** Full-corpus research rescued `0/4` affected hard failures and regressed successful cases.

## Compact-formula operator spacing is rejected

**Decision.** Do not rely on whitespace insertion around arithmetic operators/trailing algebraic `A` for the current compact formula class.

**Why.** The investigated matching unit was not rescued even with staged raw n-best.

## Source-owned structure preservation is allowed only for exhaustively identified non-linguistic classes

**Decision.** Pre-MT passthrough is allowed only when bytes are demonstrably document structure, detection is narrow/source-derived, spans stay immutable and inline linguistic uses stay outside the rule. Structural headings themselves still use strict real OPUS rather than identity output.

## Stage12 backend batching is execution, not planning

**Decision.** `rocketdict-stage12-bounded-request-batch/1`, default `48`, max `128`. Batches must preserve request order/cardinality and may not alter planner spans, model inputs, generation settings or assembly.

## MetricX is a research ranker, not an acceptance threshold

**Decision.** MetricX-24 QE may compare immutable raw candidates, but neither a score nor “MetricX prefers candidate” is sufficient for Product selection. Scores require mechanical gates and semantic review.

## Acceptance order remains unified smoke → full corpus → distributable Product

**Decision.** User-facing real source→Stage25/replay must be green before full-corpus acceptance; full public-domain quality evidence must be stable before Windows distribution becomes the release frontier.

## Project memory uses progressive disclosure and mandatory synchronization

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Before a user-facing development result after substantial work, synchronize `PROJECT_STATE.md`, `TRANSLATION_QUALITY.md`, and `DECISIONS.md` to actual HEAD/CI/artifacts. If interrupted, the next request must clear that process debt before new engineering work.

**Evidence.** `AGENTS.md`.
