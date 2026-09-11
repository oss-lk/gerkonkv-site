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

## Run 16 is the current best persisted research residual basis

**Decision.** Stage12 run `16` is the current best persisted research basis: **20 numeric / 18 punctuation / 0 length, 37 unique**.

**Evidence.** Composed workflow `34645769684`, artifact `10282227627` (ZIP SHA-256 `92b2ad3fa98af1d12c27eeb4ee749071d5152464b34c4ac1f3bf40ed7cc02e14`), exact base run `14`, angular intermediate run `15`, final run `16`, final output SHA `767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783`, persisted SQLite SHA `573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11`, evidence SHA `86c865cef5a0081fd77aa8ad78c525ebb38a01e6f279cc560aea56bb84d4e37d`. It composes **22/18/0,39 → 21/18/0,38 → 20/18/0,37**, preserves byte-exact source coverage and SQLite integrity, and passes 14/14 narrow wrapper unit regressions.

The DMS layer changes exactly source start `110881` to raw TC-big rank2 `Откуда этот угол 2 град. 0'. 7''.` and preserves all other 3343 rows exactly relative to the angular intermediate. All no-rewrite/no-injection safety invariants are true and promotion/default/public flags remain false.

## Short standalone DMS is validated research, not a default

**Decision.** Do not revive generic prime decomposition/normalization. The supported research class remains only the exact short standalone angular pattern `D deg. M'. S''` under strict source geometry and semantics.

The run-14 failure `Whence this Angle is 2 deg. 0'. 7''. ` → `Откуда угол 2 градуса. 0 футов 7 футов.` is a real model error. Read-only workflow `34645335141` proves selector necessity: among six raw TC-big hypotheses, only rank2 simultaneously passes strict mechanics and DMS semantics. Rank3 is mechanically clean but leaves English `deg.`; rank5 has angle/degree semantics but corrupts the minute prime. Therefore neither mechanical-only nor semantic-only acceptance is sufficient.

**Decision.** The persisted composed run16 proves technical non-regression for this narrow wrapper but still does not authorize Product-default promotion. The longer neighboring `Chord` sentence remains excluded because symbol preservation cannot prove its technical semantics.

## Repair false NLP sentence boundaries upstream, not with a Whence-specific MT patch

**Decision.** The `And whence is it | but from ... ?` residual is rooted upstream: Stage8 records a spaCy sentence split although immutable source has no terminal punctuation; current Stage10 groups directly by that `sentence_index`, so Stage12 receives two translation units.

Read-only workflow `34644023517` proves the exact contiguous pair is translatable, but a phrase-specific `Whence` rescue is not the preferred solution.

A complete run-16 Stage10 census of `left side has no terminal sentence punctuation + right side begins lowercase` finds exactly five boundaries. Full source/token inspection confirms **all five are real false spaCy sentence splits**, including `_ B | any where...`, which belongs to one sentence `Line C _prt_ B any where between the Ends...`.

**Decision.** Implement the correction in Stage10 as a generic fail-closed context coalescer while preserving raw Stage8 spaCy evidence. Merge only adjacent contiguous parser sentences when the immutable source gives no sentence-terminal punctuation at the boundary, the continuation begins with lowercase lexical text, and the gap does not cross a paragraph break. Persist original spaCy sentence indices and merge provenance. Because Stage10 cache identity includes the implementation name, changed behavior requires an implementation/schema contract bump; otherwise an old cached run may silently retain the bad boundary behavior.

After unit/diagnostic validation, rerun complete *Opticks* Stage10→translation evidence and compare against run16. If broader regressions appear, fail closed rather than weakening the rule or patching targets.

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
