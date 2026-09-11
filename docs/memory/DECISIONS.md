# RocketDict durable decisions — L2

Store only conclusions that are expensive or risky to rediscover. This is not a changelog; Git history and L3 evidence contain chronology and raw detail.

## Quality is a release invariant

**Decision.** Speed, storage and convenience may not reduce Product quality/evidence. Real EN→RU MT is mandatory; fake/identity/mock/dictionary substitution is never Product translation. Hard gates may not be weakened merely to pass CI, and corpus/source truncation may never be silent.

## Maintained Product Core is the forward implementation

**Decision.** New Product work targets `rocketdict-product-core` plus Workbench unified orchestration. Historical 0.30.x/checkpoint material remains provenance/compatibility evidence, not the forward path without an evidence-based reason.

## Product assets and downstream evidence are pinned and fail-closed

**Decision.** Use official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian and `float32` acceptance compute. Preserve immutable source/config/model/result identities and replayable evidence.

## Translation-quality promotion requires contiguous evidence and semantic review

**Decision.** A maintained quality change may be promoted only after classifying the defect, preserving immutable source ownership, and validating boundary-sensitive behavior on contiguous evidence. Mechanical gate success alone is insufficient.

Raw OPUS hypotheses are legitimate research candidates. Post-hoc insertion of missing literals/structure, corpus-specific target patches, arbitrary punctuation splitting, generic structural islands, source rewriting, broad fallback and evaluator weakening are not Product policies.

## Complete gate scope must not be inferred from stress subsets

**Decision.** Historical `product_numeric_failure_count` is a literal-bearing stress subset, not the complete gate. Complete maintained numeric/symbol evaluation is `rocketdict-maintained-numeric-integrity/5` over every selected Stage12 row.

## Source-owned structure is narrow and source-defined

**Decision.** Pre-MT structural treatment is allowed only when the class is exhaustively identifiable from immutable source structure, spans remain byte-exact, inline linguistic uses remain outside the rule, and any translated structural lexical content still comes from real raw MT candidates rather than identity/patch output.

This principle covers established block structural labels and the current standalone illustration-label research/product wrapper. It does **not** authorize arbitrary bracket or punctuation preservation.

## Bare Roman fragments are not headings

**Decision.** Standalone `II.`, `IV.` etc. produced by sentence segmentation are not automatically source-owned structure. Known failures are inline `Sect. IV.` / `Sect. II.` citation boundaries.

## Roman-after-Sect citation rescue is pair-level and opt-in

**Decision.** Use `rocketdict-stage12-citation-boundary-pair-rescue/1`, not a broad context merge and not a heading rule. Trigger: contiguous ordinary previous row ending `Sect.` + uppercase Roman fragment already failing length. Candidate: exact raw rank-0 OPUS pair output. Acceptance: Product hard clean, repaired length, no new strict-debt category. Default OFF.

## Length-failure whole-context rescue remains opt-in

**Decision.** `rocketdict-stage12-length-failure-whole-context-rescue/1` remains default OFF. Mechanical full-corpus gain alone is insufficient Product-default evidence.

## Generic whole-context strictness is not semantic proof

**Decision.** Do not promote generic whole-context fallback merely because the strict mechanical selector accepts it.

**Why.** Context `2725` removes an invented `=` yet silently drops source phrase `_per deliquium_`. Existing strict cleanliness therefore cannot substitute for semantic-preservation evidence.

## Ordinary Gutenberg underscore emphasis is a separate preservation signal

**Decision.** Keep `rocketdict-maintained-emphasis-markup-preservation/1` as a separate research diagnostic/veto rather than retroactively changing historical strict contracts.

## Numeric-hard split-context whole-context rescue remains narrow/default-OFF

**Decision.** `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1` remains a separate opt-in wrapper, not yet public-wired. Trigger and acceptance remain source/context defined; emphasis preservation is mandatory for its raw candidate.

**Evidence.** Full-*Opticks* run `34601313026` creates Stage12 run `8`: **29/34/0 → 25/33/0**, unique **59→55**, accepting contexts `550,669,1024,2238` and vetoing context `2725` for emphasis loss.

## Punctuation residuals must be split by defect family

**Decision.** Do not introduce a universal punctuation repair/selector. Residuals mix source-owned markers, illustration payloads, footnote-reference fragments, parentheticals, question punctuation and other delimiter/context failures.

## Illustration rescue may use a source-specific deterministic raw n-best selector

**Decision.** `rocketdict-stage12-illustration-label-rescue/1` is accepted as a **default-OFF, not-public-wired Product wrapper** for the closed hard-failing standalone illustration-label family.

Trigger requirements:
- row begins with standalone `[Illustration: ...]` plus blank-line separator;
- row already has a maintained hard failure;
- source structure is preserved byte-exactly;
- ordinary suffix uses exact source and rank0 OPUS;
- exact immutable `_Illustration._` may use canonical model input `Illustration.` with deterministic beam6/n6 and the first raw candidate satisfying hard/strict + structural target-form checks.

No target rewrite, placeholder, literal injection or arbitrary bracket generalization is allowed.

**Evidence.** Research v3 workflow `34609890716`, artifact `10267328730`, accepts exact source starts `72401,90105,203786` at raw ranks `3,3,0` and reaches **24/30/0, 52 unique**. Product Core CI `34610493157` is green. Persisted audit workflow `34610787826`, artifact `10268850347`, creates run `9`, output SHA `c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be`, DB SHA `9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad`, with byte-exact source coverage and exact raw applied targets.

**Default decision.** Evidence supports the wrapper as opt-in only. It does not yet support automatic/default Product promotion.

## Run 9 is the current residual basis

**Decision.** After persisted illustration composition, residual research must use Stage12 run `9` identities/source spans, not run-8 sequence positions. Current gates are **24 numeric / 30 punctuation / 0 length, 52 unique**.

## Block-start footnote marker-only split is rejected as Product policy

**Decision.** Do not productize marker-only `[G]/[H]/[J]/[K]/[M]` body retranslation despite the mechanical counterfactual **24/30/0,52 unique → 24/25/0,47 unique**.

**Why.** The first-row bodies are sentence fragments of larger bibliographic footnote paragraphs. L3 semantic inspection catches `_How to do this, is shewn in our_` → `Как это сделать, сшито в нашем...` and `_See our_` → `Посмотри на нас.`. Mechanical punctuation repair therefore masks translation-quality defects.

**Evidence.** Workflow `34611175668`, artifact `10268975960`, evidence SHA `14ecc93fe080a218dd9c62de35c7e6dff534867849e6c42cd677b905ef8d76fa`.

## Whole-footnote-context research must separate semantic and storage boundaries

**Decision.** The next admissible footnote experiment is complete linguistic footnote-body translation with the marker and separators kept as source-owned bytes, deterministic raw n-best, strict Product checks and emphasis preservation.

Do not equate the first `\n\n` paragraph boundary with the end of the current Stage12 row group. In run `9`, `[H]` and `[M]` have current final rows that extend three bytes beyond the semantic paragraph end because they own additional blank-line bytes. A replacement harness must therefore model separately:
1. marker bytes;
2. linguistic body bytes;
3. paragraph separator/trailing whitespace bytes;
4. the enclosing set of current rows replaced for exact source coverage.

**Evidence.** Initial workflow `34611517906` failed before MT evaluation on a fail-closed fixture assertion (`H` semantic end `151652` vs expected row-coverage end `151655`). This is a harness defect, not negative model evidence.

## Prime and formula negative evidence remains binding

**Decision.** Do not promote prime-fragment structural decomposition (`53 deg.`→`53 балла`, `hundred Feet`→`сто ног`), thousands grouping / narrow `x→×` preprocessing, or compact-formula spacing based on prior experiments; those branches either regressed semantics/successful cases or failed to rescue the target family.

## MetricX is research-only

**Decision.** MetricX-24 QE may rank immutable raw candidates, but neither its score nor preference is sufficient for Product selection without mechanical gates and semantic review.

## Acceptance order remains smoke → full corpus → distributable Product

**Decision.** User-facing real source→Stage25/replay must be green before full-corpus acceptance; full public-domain quality evidence must be stable before Windows distribution becomes the release frontier. `PRODUCT_TARGET.md` still requires unresolved hard translation failures to reach zero before approved final heavy evidence.

## Project memory uses progressive disclosure and mandatory synchronization

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Before a user-facing development result, synchronize `PROJECT_STATE.md`, `TRANSLATION_QUALITY.md`, and `DECISIONS.md` to actual HEAD/CI/artifacts. Interrupted synchronization becomes explicit debt that the next iteration clears before new work.
