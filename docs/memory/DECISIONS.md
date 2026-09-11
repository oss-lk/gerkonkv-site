# RocketDict durable decisions — L2

Store only conclusions that are expensive or risky to rediscover. This is not a changelog; Git history and L3 evidence contain chronology and raw detail.

## Quality is a release invariant

**Decision.** Speed, storage and convenience may not reduce Product quality/evidence. Real EN→RU MT is mandatory; fake/identity/mock/dictionary substitution is never Product translation. Hard gates may not be weakened merely to pass CI, and corpus/source truncation may never be silent.

The authoritative release contract remains `rocketdict/PRODUCT_TARGET.md`: final approved 90k+ heavy evidence must have zero unresolved numeric/symbol, punctuation and length hard failures and the complete downstream learner-dictionary/export path must succeed.

## Maintained Product Core is the forward implementation

**Decision.** New Product work targets `rocketdict-product-core` plus Workbench unified orchestration. Historical 0.30.x/checkpoint material remains provenance/compatibility evidence, not the forward path without an evidence-based reason.

## Product assets and downstream evidence are pinned and fail-closed

**Decision.** Production baseline uses official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian and `float32` acceptance compute. Preserve immutable source/config/model/result identities and replayable evidence.

Pinned TC-big comparator/rescue source is `Helsinki-NLP/opus-mt-tc-big-en-zle` revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0. Correct MarianTokenizer semantics and CTranslate2 float32 are mandatory; accepted inference is offline and Torch-free. TC-big remains a separate optional asset and must not silently enter the baseline `production` extra.

## Translation-quality promotion requires contiguous evidence and semantic review

**Decision.** A maintained quality change may be promoted only after classifying the defect, preserving immutable source ownership and validating boundary-sensitive behavior on contiguous evidence. Mechanical gate success alone is insufficient.

Raw MT hypotheses are legitimate research candidates. Post-hoc insertion of missing literals/structure, corpus-specific target patches, arbitrary punctuation deletion, source rewriting, target surgery, placeholders, broad fallback and evaluator weakening are not Product policies. MetricX/QE may rank immutable raw candidates but cannot establish acceptance by itself.

## Source-owned structure must be narrow and source-defined

**Decision.** Structural treatment is allowed only when the class is exhaustively identifiable from immutable source structure, spans remain byte-exact, inline linguistic uses remain outside the rule, and translated lexical content still comes from real raw MT candidates.

Exact Stage10 source spans may be replacement units only when representable by complete current Stage12 rows; otherwise skip fail-closed and never slice target strings.

## Existing opt-in rescue layers remain default OFF

The maintained wrappers include target-delimiter, footnote-reference lead, figure-reference lead, semicolon→question substitution, target-only equals addition, angular-minute prime and short angular DMS. They remain default OFF/not public-wired unless a stronger release decision explicitly changes that. `rocketdict-maintained-emphasis-markup-preservation/1` remains a rescue veto, not a retroactive Product hard gate.

No internal rescue becomes Product default merely because one corpus-specific heavy run improves hard-gate counts.

## Run 16 remains the current best persisted research residual basis

**Decision.** Until the Stage10-v2 full-corpus rerun is persisted and audited, Stage12 run `16` remains the current best basis: **20 numeric / 18 punctuation / 0 length, 37 unique**. Evidence identities are workflow `34645769684`, artifact `10282227627`, output SHA `767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783`, SQLite SHA `573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11`, evidence SHA `86c865cef5a0081fd77aa8ad78c525ebb38a01e6f279cc560aea56bb84d4e37d`.

## Repair false NLP sentence boundaries upstream, not with phrase-specific MT patches

**Decision.** False spaCy sentence splits proven by immutable source structure belong in Stage10, while raw Stage8 parser evidence remains immutable. Do not add a `Whence`-specific translation rescue for `And whence is it | but from ... ?`.

The implemented default is `structural-entity-term-discourse-pronoun-v2` / schema `rocketdict-product-stage10/2`, using `rocketdict-stage10-lowercase-continuation-coalescer/1`. It merges only consecutive raw parser sentences when the inter-token gap is whitespace-only, does not cross a paragraph break, source before the boundary has no terminal `.?!` after closing punctuation, and the first lexical character on the right is lowercase. It persists original spaCy indices and full merge decisions; V1 remains explicitly selectable for compatibility.

**Reason.** A complete run-16 census found exactly five candidate boundaries and source/token review confirmed all five are genuine false splits. Narrow source-defined coalescing fixes ownership at the earliest maintained layer without target surgery, model-specific guessing, or destruction of Stage8 provenance.

**Evidence state.** Integration commit `b97825c5cbf1b1fab7f35133feca3f76cdd4b456` passed **12/12** focused Stage10 regressions before commit. Terminal HEAD `4564f383cc2b964fbecd15d1f214619cc52ef5c5` subsequently passed ordinary Product Core workflow `34648989553` in dependency-light and real-runtime jobs; real-runtime exercised maintained Stage8→25 plus unified source→25 with pinned production NLP, real OPUS and CEFR-J. The remaining evidence gap is complete-*Opticks* Stage10-v1↔v2 replay and semantic/hard-gate comparison against run16. Fail closed on any broader regression; do not weaken the source rule or patch targets.

## Punctuation and numeric residuals remain defect-family-specific

**Decision.** Do not introduce universal punctuation/numeric fixers. Current residuals mix source-owned labels/references, symbol corruption, target-only additions, prime/DMS notation, false sentence boundaries and long-context punctuation migration.

A failed OPUS formulation does not forbid a materially different model/source-defined formulation. Conversely, success on one source-defined class does not authorize generic second-model fallback.

## Broad TC-big remains rejected

**Decision.** TC-big is an independent comparator and narrow rescue model, not a generic fallback. Row-local and whole-context research proves substantial baseline-model-specific debt but also semantic false positives. Context `2725` remains a key counterexample: mechanical cleanliness can hide content loss.

Source-relative completeness bounds may be used inside justified alternative-MT selectors; baseline target verbosity is not a universal floor when the baseline itself is corrupted.

## Audit failures must be classified before changing Product logic

**Decision.** A red heavy workflow does not imply the model/selector is wrong. Inspect persisted output and logs first. If the run has correct selected output and the failure is in evidence code, fix the audit harness without changing Product acceptance semantics. The footnote `0 rejected`/`or -1` defect remains the canonical example.

## Acceptance order remains smoke → full corpus → distributable Product

**Decision.** Real source→Stage25/replay must be green before full-corpus acceptance; final full public-domain quality evidence must reach zero unresolved hard failures before Windows distribution becomes the release frontier.

## Project memory uses progressive disclosure and mandatory synchronization

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. A stale L1 must be repaired from HEAD/L3 before new feature/research work. Before a user-facing development result, synchronize `PROJECT_STATE.md`, `TRANSLATION_QUALITY.md`, and `DECISIONS.md` to actual HEAD/CI/artifacts. Interrupted synchronization is explicit process debt cleared at the start of the next development request.
