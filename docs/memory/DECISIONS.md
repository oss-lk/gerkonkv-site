# RocketDict durable decisions — L2

Store only conclusions that are expensive or risky to rediscover. This is not a changelog; Git history and L3 evidence contain chronology and raw detail.

## Quality is a release invariant

**Decision.** Speed, storage and convenience may not reduce Product quality/evidence. Real EN→RU MT is mandatory; fake/identity/mock/dictionary substitution is never Product translation. Hard gates may not be weakened merely to pass CI, and corpus/source truncation may never be silent.

## Maintained Product Core is the forward implementation

**Decision.** New Product work targets `rocketdict-product-core` plus Workbench unified orchestration. Historical 0.30.x/checkpoint material remains provenance/compatibility evidence, not the forward path without an evidence-based reason.

## Product assets and downstream evidence are pinned and fail-closed

**Decision.** Production baseline uses official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian and `float32` acceptance compute. Preserve immutable source/config/model/result identities and replayable evidence.

A second real MT does not become Product merely because it passes hard gates on residual failures. Any Product role requires pinned identity/license, deterministic selection, semantic review, full-corpus regression and an explicit offline installation/runtime plan.

## Translation-quality promotion requires contiguous evidence and semantic review

**Decision.** A maintained quality change may be promoted only after classifying the defect, preserving immutable source ownership and validating boundary-sensitive behavior on contiguous evidence. Mechanical gate success alone is insufficient.

Raw MT hypotheses are legitimate research candidates. Post-hoc insertion of missing literals/structure, corpus-specific target patches, arbitrary punctuation deletion, generic structural islands, source rewriting, target surgery, broad fallback and evaluator weakening are not Product policies.

## Complete gate scope is the maintained Product gate

**Decision.** Complete numeric/symbol evaluation is `rocketdict-maintained-numeric-integrity/5` over every selected Stage12 row. Historical stress counters do not define release quality.

## Source-owned structure must be narrow and source-defined

**Decision.** Structural treatment is allowed only when the class is exhaustively identifiable from immutable source structure, spans remain byte-exact, inline linguistic uses remain outside the rule, and translated lexical content still comes from real raw MT candidates rather than identity/patch output.

Bare `II.`, `IV.` and similar fragments created by sentence segmentation are not headings. Exact Stage10 source spans may be replacement units only when representable by complete current Stage12 rows; otherwise skip fail-closed and never slice target strings.

## Existing opt-in rescue layers remain default OFF

- `rocketdict-stage12-length-failure-whole-context-rescue/1` — public opt-in/default OFF.
- `rocketdict-stage12-citation-boundary-pair-rescue/1` — public opt-in/default OFF.
- `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1` — default OFF/not public-wired. Context `2725` remains the key semantic-loss counterexample proving mechanical cleanliness is insufficient.
- `rocketdict-stage12-illustration-label-rescue/1` — default OFF/not public-wired.
- `rocketdict-stage12-tc-big-target-delimiter-context-rescue/1` — default OFF/not public-wired; now backed by persisted run `10`.
- `rocketdict-stage12-tc-big-footnote-reference-lead-rescue/1` — default OFF/not public-wired; heavy verification is being repaired after an audit-harness zero-handling defect.
- `rocketdict-maintained-emphasis-markup-preservation/1` remains a rescue veto, not a retroactive Product hard gate.

No internal rescue becomes Product default merely because a corpus-specific heavy run improves hard-gate counts.

## Punctuation residuals are defect-family-specific

**Decision.** Do not introduce a universal punctuation fixer. Current failures mix source-owned labels/reference leads, square-bracket payload loss, target-only delimiter hallucination, long-context question migration and other families with different root causes.

A failed OPUS formulation does not forbid a materially different model/source-defined formulation. Conversely, success on one source-defined class does not authorize generic second-model fallback.

## Pinned TC-big is an independent comparator and narrow rescue model, not a generic fallback

**Decision.** Use pinned `Helsinki-NLP/opus-mt-tc-big-en-zle` revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, license `CC-BY-4.0`, as the independent real-MT comparator/current narrow-rescue source.

Broad TC-big replacement remains rejected. All-52 and whole-context research proves substantial baseline-model-specific debt but also semantic false positives. A second model may only be invoked by a narrow existing-hard-failure/source-defined trigger with exact source geometry and explicit semantic evidence.

## CTranslate2 is the accepted TC-big inference backend

**Decision.** Correct MarianTokenizer semantics are mandatory: `>>rus<<`, HF encode/token conversion, CTranslate2 translation, then HF token/id decode. The earlier 0/52 parity result was a harness defect. Corrected evidence obtains 52/52 input parity, 49/52 rank0 parity and at least one n-best overlap in all 52 residual cases.

TC-big inference may therefore use CTranslate2 float32 without Torch. Search-order differences remain explicit rather than hidden.

## TC-big is a separate optional offline asset

**Decision.** Keep TC-big isolated from the accepted OPUS production asset. `rocketdict-tc-big-en-ru-asset/1` pins repository, revision, source-weight SHA, CC-BY-4.0, target prefix, tokenizer snapshot and CTranslate2 float32 payload. Runtime must record and verify the actual manifest SHA and complete payload-tree SHA/file-count/bytes.

`rocketdict-assets build-tc-big-en-ru` is explicit provisioning. Builder dependencies and runtime dependencies remain separate; accepted inference is Torch-free. The baseline `production` extra must not silently acquire TC-big.

## Run 10 is the current persisted residual basis

**Decision.** Stage12 run `10` supersedes run `9` as the current persisted research residual basis: **24 numeric / 25 punctuation / 0 length, 47 unique**.

**Evidence.** CPU-provisioning workflow `34631662056`, artifact `10276009101`, output SHA `6dec2080a8fe21716587e4f4ffbe1f8ebf816911b542ab99ac598a8462ed01df`. It composes over exact run `9`, preserves byte-exact source coverage and exact untouched rows, selects five raw TC-big rank0 candidates, passes independent gate recount/SQLite integrity and records exact TC-big asset identities.

**Interpretation.** This is persisted quality progress, not Product-default promotion. The delimiter wrapper remains default OFF/not public-wired.

## Source-relative completeness replaces corrupt-baseline verbosity only for justified alternative-MT selectors

**Decision.** `candidate target alpha >= baseline target alpha` is not a universal alternative-MT rule when the baseline itself is inflated by hallucination. Narrow TC-big selectors may use conservative immutable-source-relative alpha bounds, but this does not weaken legacy OPUS selectors globally.

## Target-only delimiter hallucination is an admissible TC-big defect class

**Decision.** A delimiter rescue context must contain a current hard failure, be exactly row-aligned to complete current Stage12 rows, and add `()[]{}` delimiters beyond source counts. Candidate acceptance requires raw TC-big output, maintained strict cleanliness, emphasis preservation, zero added delimiters and source-relative alpha `0.75..1.50`.

Persisted run `10` confirms the earlier five-context counterfactual exactly: **24/30/0,52 → 24/25/0,47**. Manual review found removal of serious OPUS hallucinated content rather than punctuation-only masking.

## Gutenberg footnote-reference leads are a separate source-defined candidate class

**Decision.** The footnote-reference wrapper is intentionally narrower than “all square-bracket failures.” It triggers only when one exact Stage10/current Stage12 row is a complete source lead matching `[A-Z] _..._`, the current row is already Product-hard-failing, and its exact ASCII marker is lost.

Candidate acceptance requires an unmodified raw TC-big hypothesis, exact marker restoration, strict mechanical pass, Gutenberg emphasis preservation and source-relative alpha `0.70..2.00`. There is no G/H/J/K/M whitelist in the selector; those letters arise from the actual hard-failing corpus cohort.

**Evidence so far.** Product Core workflow `34632793371` is fully green. The first heavy run `34632917048` persisted run `11` with five attempts, five raw rank0 accepts and zero rejects, but the audit script then failed because `int(rejected_count or -1)` converts valid `0` to `-1`.

**Decision.** Treat that red run as an audit/orchestration defect, not a translation/model defect. Do not change the selector, trigger or acceptance thresholds to make the workflow green. Correct only the zero-handling assertion, rerun the independent gate/SQLite/source evidence, and promote run `11` to current residual basis only if the rerun is green.

## Audit failures must be classified before changing Product logic

**Decision.** A red heavy workflow does not imply the model/selector is wrong. Inspect persisted output and logs first. If the run has correct selected output and the failure is in evidence code, fix the audit harness without changing Product acceptance semantics. The footnote `0 rejected`/`or -1` defect is the canonical example.

## MetricX is ranking evidence only

**Decision.** MetricX/QE may rank immutable raw candidates but neither its absolute score nor its preference is sufficient for Product selection. It cannot override source-boundary or semantic vetoes.

## Acceptance order remains smoke → full corpus → distributable Product

**Decision.** Real source→Stage25/replay must be green before full-corpus acceptance; final full public-domain quality evidence must reach zero unresolved hard failures before Windows distribution becomes the release frontier.

## Project memory uses progressive disclosure and mandatory synchronization

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Before a user-facing development result, synchronize `PROJECT_STATE.md`, `TRANSLATION_QUALITY.md`, and `DECISIONS.md` to actual HEAD/CI/artifacts. Interrupted synchronization is explicit debt cleared at the start of the next development request.
