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
- `rocketdict-stage12-illustration-label-rescue/1` remains a narrow default-OFF/not-public-wired wrapper. Persisted run `9` is **24 numeric / 30 punctuation / 0 length, 52 unique**.
- `rocketdict-maintained-emphasis-markup-preservation/1` remains a separate research veto rather than a retroactive Product hard gate.

## Punctuation residuals remain defect-family-specific

**Decision.** Do not introduce a universal punctuation fixer. Run-9 failures mix block footnotes, square-bracket payload loss, target-only delimiter hallucination, long-context question migration and other families with different root causes.

The current exact-source OPUS formulations are exhausted or rejected for whole-footnote, square-bracket, context-2730, prime/formula and broad citation/group branches. A future attempt needs a materially new source representation/model hypothesis rather than deeper identical beam search.

## Pinned TC-big is the active independent model differential, not a Product fallback

**Decision.** Use pinned `Helsinki-NLP/opus-mt-tc-big-en-zle` revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, as the current independent real-MT research comparator.

**Evidence.** The all-current-failures workflow `34621706640` evaluates all 52 run-9 hard rows and finds at least one mechanically admissible raw TC-big hypothesis for **32/52** cases, with 172 admissible hypotheses total. The purely mechanical upper bound is **24/30/0, 52 unique → 13/8/0, 20 unique**.

**Interpretation.** A material portion of the remaining frontier is baseline-model-specific rather than purely planner/evaluator failure.

**Non-promotion rule.** The 32 mechanically clean cases are not 32 safe Product replacements. Manual review found boundary-fragment completions and semantic/terminology concerns. TC-big remains research-only until a boundary-aware selector, persisted regression and release plan are proven.

## A second MT may only be failure-triggered and boundary-aware

**Decision.** Do not replace clean OPUS rows merely because another model exists. Any second-model Product path must start from an existing maintained hard failure or a separately justified source-defined trigger, so already-clean Product output remains untouched by default.

**Decision.** Do not implement isolated Stage12-row TC-big substitution as the general fallback mechanism. A Stage12 row may be only a fragment of a larger sentence/context; a mechanically clean candidate can finish or punctuate a clause that source text continues in the neighboring row.

A future selector must reason on a source-defined contiguous group/context and verify that the candidate is semantically valid for that full source span.

## Exact Stage10 contexts are not guaranteed to align with current Stage12 row boundaries

**Decision.** A Stage10 context may be used as a research translation unit only when its exact source span can be represented by whole replacement rows, or when the larger covering group is freshly translated and validated as its own source-defined unit. Do not slice an existing target string to force alignment.

**Evidence.** Stage10 context `2480` spans `[480217,480300)` and includes the trailing space after `_Qu._ 19.`. Current run-9 row 2729 ends at `480299`; row 2730 begins at `480299` and owns the following space plus the next question body. Initial context workflow `34623402220` therefore failed correctly with `run9 member coverage drift for context 2480:2480`.

This is orchestration/boundary evidence, not a TC-big quality failure.

## MetricX is a research ranking signal only

**Decision.** MetricX/QE may rank immutable raw candidates but neither its absolute score nor its preference is sufficient for Product selection.

**Evidence.** Run `34622530818` scores all 172 mechanically admissible TC-big hypotheses. MetricX prefers some admissible TC-big candidate over OPUS in **30/32** cases and the first admissible candidate in **29/32**, while the best-QE rank is spread across ranks 0–5.

**Interpretation.** This strengthens the hypothesis that TC-big often improves the hard residuals, but it does not define an acceptance threshold and cannot override boundary or semantic vetoes.

## CTranslate2 conversion feasibility does not imply generation parity

**Decision.** The pinned TC-big Marian model may be converted to CTranslate2 for research, and a torch-free inference runtime is technically feasible. Do not claim that the converted backend reproduces Transformers output until tokenizer and generation semantics are proven equivalent.

**Evidence.** Initial parity workflow `34622860381` runs successfully in CTranslate2 4.8.2 float32 without Torch import by the audit script, but has `0/52` exact rank0 matches, `0/52` any-hypothesis overlap and only `15/52` mechanically admissible cases, compared with `32/52` under Transformers.

The first harness used raw SentencePiece-side multilingual-prefix handling rather than demonstrated MarianTokenizer-equivalent behavior. A corrected parity experiment is required before choosing CT2 as the release backend for TC-big.

## Run 9 is the current persisted residual basis

**Decision.** Residual research uses run `9` source spans/current identities. Current persisted gates are **24 numeric / 30 punctuation / 0 length, 52 unique**. Research counterfactuals do not replace that basis until a new persisted Product audit is created.

## Acceptance order remains smoke → full corpus → distributable Product

**Decision.** User-facing real source→Stage25/replay must be green before full-corpus acceptance; final full public-domain quality evidence must reach zero unresolved hard failures before Windows distribution becomes the release frontier.

## Project memory uses progressive disclosure and mandatory synchronization

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Before a user-facing development result, synchronize `PROJECT_STATE.md`, `TRANSLATION_QUALITY.md`, and `DECISIONS.md` to actual HEAD/CI/artifacts. Interrupted synchronization becomes explicit debt that the next iteration clears before new work.
