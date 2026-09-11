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

## Full Product gate scope must not be inferred from a stress-subset metric

**Decision.** The historical `product_numeric_failure_count` in `rocketdict-full-opticks-numeric-stress/3` is a **literal-bearing stress subset**, because that harness filters to source rows where `extract_numeric_literals(source)` is non-empty. It must not be cited as the complete Product numeric/symbol gate.

The complete maintained gate is `rocketdict-maintained-numeric-integrity/5` applied to every selected Stage12 row. `rocketdict-full-opticks-hard-gate-inventory/3` therefore preserves and verifies the legacy literal-bearing subset while separately inventorying the complete gate.

**Why.** Direct recomputation on the immutable structural-label `/2` Product artifact yields 30 complete numeric/symbol failures, not 27. The additional rows are `617` (invented `=`), `1798` (unsafe generated `100 000` from `ten hundred thousand`) and `3013` (invented `=` before `_per deliquium_`). These are genuine hard-gate findings that the old cohort filter never inspected; they are not new model regressions.

**Evidence.** `real_translation_full_opticks_numeric_stress.py`; `numeric_integrity.py`; `audit_full_opticks_hard_gates.py`; immutable run `34575909618` database/artifact.

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

**Why.** `/2` removes the intended legacy-heading length-loss class: full-corpus length failures fall from 24 to 5. The literal-bearing numeric stress remains 27 and punctuation remains 34; the separate complete numeric/symbol inventory is 30 because it also sees three previously out-of-cohort failures. The structural change is therefore class-specific rather than a generic bypass.

**Evidence.** `structural_labels.py`; `legacy_block_headings.py`; `/2` full-*Opticks* run `34575909618`, artifact `10190059238`.

## Bare Roman fragments must not be reclassified as structural headings

**Decision.** Do not add a rule that treats standalone `II.`, `IV.` etc. as source-owned structure merely because Stage8/Stage10 sentence segmentation produced a tiny Stage12 row.

**Why.** The residual examples are inline references such as `Sect. IV.` / `Sect. II.`, not block headings. Treating them as structure would turn a context-boundary defect into false document classification.

**Evidence.** Immutable baseline rows around the two residual length failures; pair feasibility run `34597127952`, artifact `10261744281`.

## Roman-after-Sect citation rescue is narrow, pair-level and opt-in

**Decision.** The valid Product experiment for the `Sect. IV.` / `Sect. II.` boundary defect is `rocketdict-stage12-citation-boundary-pair-rescue/1`, not a broad context merge and not a heading rule.

The trigger requires an uppercase Roman-fragment row immediately after a contiguous ordinary row ending in `Sect.`, excludes source-owned structural/table classes, and requires the Roman row to already fail the maintained length gate. The candidate is raw rank-0 OPUS over the exact previous+current pair.

Acceptance requires Product hard-clean output, repaired length, and **no new strict-debt category** relative to the primary pair. Existing debt may be inherited but not worsened. No source rewrite, target rewrite, placeholders or literal injection are allowed. The mechanism is disabled by default.

**Why.** Pair feasibility gave mechanically promising results for both known cases while preserving an inherited footnote-marker debt in the `Sect. IV.` case. Earlier broad citation/group coalescing is rejected because a larger candidate lost unrelated numeric content and a footnote marker.

**Evidence.** `translation_citation_rescue_stage.py`; `test_translation_citation_rescue_stage.py`; feasibility run `34597127952`; Product Core CI `34597453583` / `34597532302`; combined audit `34597648856`.

## Length-failure whole-context rescue remains opt-in despite full-corpus gain

**Decision.** `rocketdict-stage12-length-failure-whole-context-rescue/1` remains disabled by default even though the full-*Opticks* audit accepts contexts `577`, `629`, `919` and reduces the maintained gates from `30/34/5` to `29/34/2`.

**Why.** The mechanism is narrow and mechanically sound, but Product default promotion still requires semantic confidence beyond aggregate gate improvement.

**Evidence.** Full audit run `34596212688`; public-wrapper rerun `34597532192`.

## Combined length + citation rescue closes current length failures but is not auto-promoted

**Decision.** The public Stage12 wrapper may compose the two opt-in mechanisms, but both remain OFF by default. The combined full-*Opticks* evidence is a research/Product audit, not a promotion authorization.

**Why.** Run `34597648856` reaches `29` numeric / `34` punctuation / `0` length with `59` unique failures, preserves byte-exact source coverage and raw rank-0 applied targets, and passes SQLite integrity checks. This is strong mechanical evidence, but the artifact itself keeps `promotion_allowed=false` and `automatic_product_default_allowed=false`.

**Evidence.** `real_translation_full_opticks_combined_length_citation_product_rescue.py`; workflow `.github/workflows/rocketdict-full-opticks-combined-length-citation-product-rescue.yml`; artifact `10263095872`.

## Source-owned block section identifiers are a closed maintained class

**Decision.** Narrow block identifiers of form `digit.A.` or `digit.A.digit.` are source-owned Gutenberg structure only at block/paragraph start and are excluded from MT under `rocketdict-stage12-block-section-identifier/1`. Inline references remain ordinary linguistic prose.

**Why.** Full-corpus evidence preserves all 21 block identifiers exactly while keeping all five inline occurrences on the ordinary MT path.

## Stage12 backend batching is execution, not planning

**Decision.** Primary OPUS requests use `rocketdict-stage12-bounded-request-batch/1`, default batch size `48`, maximum `128`. Backend batches must preserve request order/cardinality and must not alter source/planner spans, model inputs, generation settings or assembly.

**Why.** This bounds resource usage without changing translation semantics.

## Broad whole-context rescue remains research-only

**Decision.** Do not promote generic whole-context translation from corpus-wide alpha gain or mechanical cleanliness. The pre-existing Product-exposed whole-context path remains opt-in and narrowly triggered.

Canonical hard-failure research found nine mechanically strict whole-context candidates (`550, 669, 919, 1024, 1393, 2238, 2462, 2725, 2726`), but the newer length/citation composition changes some selected rows. Future work must therefore rebuild the residual cohort by **immutable source span/context identity on the composed output**, not blindly reuse old sequence/context numbers.

**Why.** A trigger must stay causally tied to an independently proven Product defect. Generic alpha gain is not an acceptance rule, and mechanical strictness is not semantic proof.

## MetricX is an independent research ranker, not an acceptance threshold

**Decision.** MetricX-24 reference-free QE may compare immutable raw candidates, but neither a score nor “MetricX prefers candidate” is sufficient for Product selection. Scores must be version-pinned, preserved as evidence, and paired with mechanical gates plus semantic review.

**Why.** Learned QE is useful ranking evidence, not proof of faithfulness.

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

## Project memory uses progressive disclosure, mandatory synchronization and next-request recovery

**Decision.** Recovery is L1 `PROJECT_STATE.md` → HEAD diff → L2 `docs/memory/INDEX.md`/relevant durable docs → unrestricted L3 as evidence requires. Before a user-facing development result after a substantial iteration, synchronize L1/L2 with actual HEAD/CI/evidence.

If that synchronization cannot be completed inside an iteration because the tool/context/request ends, the debt must be cleared at the **start of the very next development request before new engineering work**. Read current L1 and HEAD, reconstruct actual state from L3, update stale L1/affected mandatory L2, commit the repair, then continue. A one-word `продолжай` does not waive this requirement.

**Why.** L1 is useful only as a cheap current-state map. Allowing a known-stale L1 to survive another iteration defeats progressive disclosure and forces future agents to rediscover state from L3 unnecessarily.

**Evidence.** `AGENTS.md`.
