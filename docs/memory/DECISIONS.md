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

This principle currently covers the established block structural labels and motivates research on standalone Gutenberg illustration labels and block-start footnote markers. It does **not** authorize arbitrary bracket or punctuation preservation.

## Bare Roman fragments are not headings

**Decision.** Standalone `II.`, `IV.` etc. produced by sentence segmentation are not automatically source-owned structure. Known failures are inline `Sect. IV.` / `Sect. II.` citation boundaries.

## Roman-after-Sect citation rescue is pair-level and opt-in

**Decision.** Use `rocketdict-stage12-citation-boundary-pair-rescue/1`, not a broad context merge and not a heading rule. Trigger: contiguous ordinary previous row ending `Sect.` + uppercase Roman fragment already failing length. Candidate: exact raw rank-0 OPUS pair output. Acceptance: Product hard clean, repaired length, no new strict-debt category. Default OFF.

**Why.** Broad citation/group coalescing lost unrelated numeric content and a footnote marker.

## Length-failure whole-context rescue remains opt-in

**Decision.** `rocketdict-stage12-length-failure-whole-context-rescue/1` remains default OFF. It improves the canonical corpus but mechanical gain alone is insufficient Product-default evidence.

## Combined length + citation closes current length class but is not auto-promoted

**Decision.** Public Stage12 may compose the two opt-in mechanisms, both OFF by default. Full-*Opticks* run `34597648856` reaches **29 numeric / 34 punctuation / 0 length**, 59 unique failures with byte-exact source coverage and raw applied targets.

## Generic whole-context strictness is not semantic proof

**Decision.** Do not promote generic whole-context fallback merely because the strict mechanical selector accepts it.

**Why.** Context `2725` removes an invented `=` yet silently drops source phrase `_per deliquium_`. This direct counterexample invalidates old strict cleanliness as sufficient semantic evidence.

## Ordinary Gutenberg underscore emphasis is a separate preservation signal

**Decision.** Preserve historical `critical_technical_tokens/3` semantics and use `rocketdict-maintained-emphasis-markup-preservation/1` as a separate research diagnostic/veto rather than retroactively widening the old contract.

## Numeric-hard split-context whole-context rescue is narrow and default-OFF

**Decision.** `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1` remains a separate opt-in wrapper above citation+length composition and is **not yet wired into public `product.stage12.run`**.

Trigger: current split Stage10 context; at least one selected row already fails numeric-integrity `/5`; exact unchanged whole Stage10 source fits the existing 160-NLP-token cap; pinned OPUS beam=6/rank0. Acceptance requires existing strict whole-context selector plus emphasis-preservation pass. No source/target rewrite, placeholders or literal injection.

**Evidence.** Run `34601313026`, artifact `10264132732`, accepts contexts `550,669,1024,2238`; rejects `1460,2132,2176,2190,2634,2725`; **29/34/0 → 25/33/0**, unique **59→55**. Product Core CI `34601005247` is green. Public exposure remains a separate decision from default promotion.

## Punctuation residuals must be split by defect family

**Decision.** Do not introduce a universal punctuation repair/selector. Residuals mix source-owned markers, illustration payloads, parentheticals, question punctuation and other delimiter/context failures.

## Illustration labels: v1 mechanical success is rejected

**Decision.** Do not promote the first standalone `[Illustration: ...]` structural split merely because it gave a mechanical counterfactual **24 numeric / 30 punctuation / 0 length, 52 unique**.

**Why.** Exact suffix `_Illustration._` produced malformed raw OPUS `*Иллюстрация._`, a semantic/markup defect not caught by the current hard gates. This is durable evidence that the label family needs an explicit semantic structural-word selector.

## Illustration labels: rank-0 canonical `Illustration.` is fail-closed

**Decision.** Research v2 may canonicalize model input for exact immutable `_Illustration._` to `Illustration.` while preserving source bytes, but must reject rank-0 `Пример.` because it is the wrong structural sense.

**Evidence.** Workflow `34603765083`, artifact `10265862004`, contract `rocketdict-full-opticks-illustration-label-feasibility/2`: source starts `72401` and `90105` are rejected; only ordinary suffix case `203786` is accepted. Counterfactual **24/32/0**, 54 unique. Database remains read-only and source coverage byte-exact.

## Illustration structural-word research may use deterministic raw n-best, not target repair

**Decision.** The next admissible research step is a v3 structural-word selector over canonical model input `Illustration.` using deterministic raw OPUS n-best, while immutable `_Illustration._` source bytes remain unchanged.

The selector may accept only an unmodified raw hypothesis that independently passes maintained hard/strict checks and an explicit structural target-shape contract (`Иллюстрация.`/approved equivalent, no markup artifacts). It may not rewrite `Пример.` into a desired term and may not inject markup/literals.

**Evidence.** DOE workflow `34603700499`, artifact `10265013225`, evaluated 144 raw hypotheses and found 25 admissible structural-word candidates. The selected deterministic candidate is beam `6`, `num_hypotheses=6`, rank `3`, exact raw target `Иллюстрация.`. This authorizes **research v3 only**; full three-case/full-corpus counterfactual evidence is required before any Product wrapper.

## Block-start footnote markers are a separate source-owned research class

**Decision.** `[A] ` … `[M] ` at definition-block start may be researched as source-owned marker bytes with only the linguistic body sent to MT. Inline markers such as `understand,[G] that` are out of scope. Existing baseline feasibility must be revalidated against current run `8` before Productization.

## Prime and formula negative evidence remains binding

**Decision.** Do not promote prime-fragment structural decomposition (`53 deg.`→`53 балла`, `hundred Feet`→`сто ног`), thousands grouping / narrow `x→×` preprocessing, or compact-formula spacing based on prior experiments; those branches either regressed semantics/successful cases or failed to rescue the target family.

## MetricX is research-only

**Decision.** MetricX-24 QE may rank immutable raw candidates, but neither its score nor preference is sufficient for Product selection without mechanical gates and semantic review.

## Acceptance order remains smoke → full corpus → distributable Product

**Decision.** User-facing real source→Stage25/replay must be green before full-corpus acceptance; full public-domain quality evidence must be stable before Windows distribution becomes the release frontier. The authoritative `PRODUCT_TARGET.md` requires unresolved hard translation failures to reach zero before approved final heavy evidence.

## Project memory uses progressive disclosure and mandatory synchronization

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Before a user-facing development result, synchronize `PROJECT_STATE.md`, `TRANSLATION_QUALITY.md`, and `DECISIONS.md` to actual HEAD/CI/artifacts. Interrupted synchronization becomes explicit debt that the next iteration clears before new work.
