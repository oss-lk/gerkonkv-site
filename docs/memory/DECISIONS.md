# RocketDict durable decisions — L2

Store only conclusions that are expensive or risky to rediscover. This is not a changelog; Git history and L3 evidence contain chronology and raw detail.

## Quality is a release invariant

**Decision.** Speed, storage and convenience may not reduce Product quality/evidence. Real EN→RU MT is mandatory; fake/identity/mock/dictionary substitution is never Product translation. Hard gates may not be weakened merely to pass CI, and corpus/source truncation may never be silent.

## Maintained Product Core is the forward implementation

**Decision.** New Product work targets `rocketdict-product-core` plus Workbench unified orchestration. Historical 0.30.x/checkpoint material remains provenance/compatibility evidence, not the forward path without an evidence-based reason.

## Product assets and downstream evidence are pinned and fail-closed

**Decision.** Production baseline uses official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian and `float32` acceptance compute. Preserve immutable source/config/model/result identities and replayable evidence.

A second real MT may be researched, but it does not become Product merely because it passes hard gates on residual failures. Any Product role requires pinned identity/license, deterministic selection, semantic review, full-corpus regression and an offline installation/runtime plan.

## Translation-quality promotion requires contiguous evidence and semantic review

**Decision.** A maintained quality change may be promoted only after classifying the defect, preserving immutable source ownership and validating boundary-sensitive behavior on contiguous evidence. Mechanical gate success alone is insufficient.

Raw MT hypotheses are legitimate research candidates. Post-hoc insertion of missing literals/structure, corpus-specific target patches, arbitrary punctuation deletion, generic structural islands, source rewriting, broad fallback and evaluator weakening are not Product policies.

## Complete gate scope must not be inferred from stress subsets

**Decision.** Complete maintained numeric/symbol evaluation is `rocketdict-maintained-numeric-integrity/5` over every selected Stage12 row. Historical narrower stress counters do not define release quality.

## Source-owned structure is narrow and source-defined

**Decision.** Pre-MT structural treatment is allowed only when the class is exhaustively identifiable from immutable source structure, spans remain byte-exact, inline linguistic uses remain outside the rule, and translated lexical content still comes from real raw MT candidates rather than identity/patch output.

## Bare Roman fragments are not headings

**Decision.** Standalone `II.`, `IV.` etc. produced by sentence segmentation are not automatically source-owned structure. Known failures are inline citation boundaries.

## Existing opt-in rescue decisions remain

- `rocketdict-stage12-length-failure-whole-context-rescue/1` remains default OFF.
- `rocketdict-stage12-citation-boundary-pair-rescue/1` remains default OFF.
- `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1` remains default OFF/not public-wired. Context `2725` remains the semantic-loss counterexample proving generic mechanical cleanliness is insufficient.
- `rocketdict-stage12-illustration-label-rescue/1` is accepted only as a narrow default-OFF/not-public-wired wrapper. Persisted run `9` is **24 numeric / 30 punctuation / 0 length, 52 unique**.
- `rocketdict-maintained-emphasis-markup-preservation/1` remains a separate research veto rather than a retroactive Product hard gate.

## Punctuation residuals must remain defect-family-specific

**Decision.** Do not introduce a universal punctuation fixer. Current run-9 failures mix block footnotes, square-bracket payload loss, target-only delimiter hallucination, long-context question migration and other families with different root causes.

## Marker-only footnote split is rejected

**Decision.** Do not Productize marker-only `[G]/[H]/[J]/[K]/[M]` retranslation despite the attractive **24/25/0, 47 unique** counterfactual.

**Why.** Semantic inspection exposes fragment mistranslations (`shewn`→`сшито`, `_See our_`→`Посмотри на нас.`). Mechanical punctuation repair hides worse translation.

## Exact-source OPUS whole-footnote n-best is exhausted for the current formulation

**Decision.** Do not continue increasing beam/n-best on the same exact linguistic footnote bodies without a materially new representation/model hypothesis.

**Evidence.** Corrected whole-context workflow `34615540238` gives **0/30** strict+emphasis-safe candidates. Depth DOE `34615819431` evaluates beam/n-best `6/6`, `12/12`, `24/24`: **210 raw hypotheses, 0 mechanically admissible**.

The failure is dominated by Gutenberg underscore/emphasis corruption and, in H, persistent archaic-word semantic error. This is model/representation evidence, not a reason to weaken emphasis preservation.

## Context 2730 must not be rescued by the current whole/pair formulations

**Decision.** Do not raise the maintained whole-context cap merely to absorb context `2730`, and do not Productize the tested 138/132-token pair windows.

**Why.** The whole Stage10 context is 339 NLP tokens; workflow `34616386780` produces 0 admissible candidates and clear long-context degradation. The <=160 pair experiment `34616665018` gives a mechanically clean opening window but semantic repetition/distortion, while the closing window loses context and has no admissible candidate. This is another direct case where gate cleanliness is not semantic proof.

## Current square-bracket-loss OPUS n-best branch is negative

**Decision.** Do not treat raw OPUS n-best as a solution for the current `[in Fig.]`, inline `[G]`, and `[Greek:a]` loss family.

**Evidence.** Workflow `34617363701` evaluates 24 raw hypotheses across the four current rows and finds zero admissible candidates. A future attempt needs a different source representation or model, not a deeper identical beam.

## Target-only delimiter hallucinations expose a baseline-model basin

**Decision.** For the seven current source-no-delimiter / target-invented-delimiter rows, ordinary OPUS n-best is not a general rescue mechanism.

**Evidence.** Workflow `34616844554`: only metadata seq `3` has strict-clean OPUS alternatives; six substantive rows remain without a strict-clean candidate. Some baseline outputs contain obvious unrelated domain/religious hallucinations that persist across the beam.

Do not implement target punctuation deletion. The correct research direction is model differential on the same immutable source bytes.

## Pinned TC-big is the active independent model differential, not yet a Product fallback

**Decision.** Use pinned `Helsinki-NLP/opus-mt-tc-big-en-zle` revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, as the current independent real-MT research comparator.

**Evidence.** Delimiter differential workflow `34617224048` finds strict-clean raw alternatives for **6/7** current cases (`3,1864,1878,2219,2382,2862`). Rank0 candidates in the severe hallucination rows restore source-domain meaning rather than just altering punctuation. Seq `3220` remains unresolved mechanically.

**Interpretation.** A material portion of the remaining frontier is likely OPUS-baseline-model-specific rather than purely planner/evaluator failure.

**Non-promotion rule.** TC-big is research-only until an all-current-failures screen, semantic family review, deterministic source/failure trigger, persisted full-corpus regression, clean-row guardrail, license attribution, asset/runtime size/performance assessment and offline release strategy are complete.

## Run 9 is the current persisted residual basis

**Decision.** Residual research uses run `9` source spans/current identities. Current persisted gates are **24 numeric / 30 punctuation / 0 length, 52 unique**. Research counterfactuals do not replace that basis until a new persisted Product audit is created.

## Prime/formula negative evidence remains binding

**Decision.** Do not promote prime-fragment structural decomposition, thousands grouping / narrow `x→×` preprocessing, compact-formula spacing, or broad citation/group coalescing based on prior experiments; those branches regressed semantics/successful cases or failed to rescue the class.

## MetricX is research-only

**Decision.** MetricX/QE may rank immutable raw candidates, but neither its score nor preference is sufficient for Product selection without mechanical gates and semantic review.

## Acceptance order remains smoke → full corpus → distributable Product

**Decision.** User-facing real source→Stage25/replay must be green before full-corpus acceptance; final full public-domain quality evidence must reach zero unresolved hard failures before Windows distribution becomes the release frontier.

## Project memory uses progressive disclosure and mandatory synchronization

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Before a user-facing development result, synchronize `PROJECT_STATE.md`, `TRANSLATION_QUALITY.md`, and `DECISIONS.md` to actual HEAD/CI/artifacts. Interrupted synchronization becomes explicit debt that the next iteration clears before new work.
