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

Raw MT hypotheses are legitimate research candidates. Post-hoc insertion of missing literals/structure, corpus-specific target patches, arbitrary punctuation deletion, source rewriting, target surgery, placeholders, broad fallback and evaluator weakening are not Product policies.

MetricX/QE may rank immutable raw candidates but cannot establish acceptance by itself.

## Source-owned structure must be narrow and source-defined

**Decision.** Structural treatment is allowed only when the class is exhaustively identifiable from immutable source structure, spans remain byte-exact, inline linguistic uses remain outside the rule, and translated lexical content still comes from real raw MT candidates.

Exact Stage10 source spans may be replacement units only when representable by complete current Stage12 rows; otherwise skip fail-closed and never slice target strings.

## Existing opt-in rescue layers remain default OFF

The following maintained wrappers are default OFF/not public-wired unless a stronger release decision explicitly changes that:

- `rocketdict-stage12-length-failure-whole-context-rescue/1`;
- `rocketdict-stage12-citation-boundary-pair-rescue/1`;
- `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1`;
- `rocketdict-stage12-illustration-label-rescue/1`;
- `rocketdict-stage12-tc-big-target-delimiter-context-rescue/1` — persisted run `10`;
- `rocketdict-stage12-tc-big-footnote-reference-lead-rescue/1` — persisted run `11`;
- `rocketdict-stage12-tc-big-figure-reference-lead-rescue/1` — persisted run `12`;
- `rocketdict-stage12-tc-big-semicolon-question-substitution-rescue/1` — persisted run `13`;
- `rocketdict-stage12-tc-big-target-only-equals-addition-rescue/1` — persisted run `14`;
- `rocketdict-stage12-tc-big-angular-minute-prime-rescue/1` — persisted research run `15`, explicitly non-promoting;
- `rocketdict-stage12-tc-big-short-angular-dms-rescue/1` — implementation/unit tests present, feasibility audit required before any persisted DMS result.

`rocketdict-maintained-emphasis-markup-preservation/1` remains a rescue veto, not a retroactive Product hard gate.

No internal rescue becomes Product default merely because one corpus-specific heavy run improves hard-gate counts.

## Run 14 is the current accepted persisted residual basis

**Decision.** Stage12 run `14` supersedes run `13` as the current persisted research residual basis: **22 numeric / 18 punctuation / 0 length, 39 unique**.

**Evidence.** Heavy workflow `34643230375`, artifact `10280349240`, output SHA `12e1fe77ab8df3959b4bb9265292cdc5b9db279797d94e2f15df6482429e2c44`, persisted SQLite SHA `dfce68a8f7cae08b90380630ae29e31418b4d6e8987d3e7001fe72fa1d781304`. It composes over exact run `13`, preserves byte-exact source coverage and 3343 exact untouched rows, selects one raw TC-big rank0 candidate and passes independent hard-gate/SQLite checks.

**Interpretation.** The accepted row is the algebraic sentence beginning `And by squaring these Equals...` at source start `107711`. OPUS added a source-absent `=`; the raw TC-big candidate removes that hallucinated sign while retaining emphasized algebraic terms/ratios and the `equal to` relation. The previously suspected `Square of the Sine` wording is not this persisted row and is not a valid reason to reject run `14`.

This is persisted research quality progress, not Product-default promotion.

## Angular-minute rescue is evidence-backed research, not a default

**Decision.** The narrow single-angular-minute-prime wrapper is technically validated on the complete corpus but remains default OFF/not public-wired.

**Evidence.** Workflow `34643812392`, artifact `10281555120`, exact base run `14`, enabled research run `15`, output SHA `0e0ebb851e43079b3029a2a2638d0dc0ff5eb45bebd6c91895cb04483349fb45`, SQLite SHA `bfb131c43c37276a906044cc23908251e1526b9943d2c54eac5bf409b6b64630`. It changes exactly source start `431358`, reduces **22/18/0,39 → 21/18/0,38 unique**, preserves 3343 untouched rows and all source/safety invariants. The evidence explicitly records `promotion_allowed=false`, `automatic_product_default_allowed=false`, `public_stage12_surface_allowed=false`.

Therefore a full-corpus improvement is necessary but not sufficient for default promotion.

## Short standalone DMS is a distinct prime-notation class

**Decision.** Do not revive generic prime decomposition/normalization. The current candidate class is only the exact short standalone angular pattern `D deg. M'. S''` under strict source geometry and semantics.

The concrete run-14 failure at source start `110881` is `Whence this Angle is 2 deg. 0'. 7''. ` → `Откуда угол 2 градуса. 0 футов 7 футов.`. This is a real model error: angular minute/second marks were interpreted as feet.

The implemented DMS trigger may act only when:
- the source/current row is an exact single Stage10 context;
- exactly one DMS expression is present;
- source contains `Angle`;
- source has at most 12 alphabetic words;
- the current row already hard-fails and its prime signature is broken.

A candidate must be an unmodified raw TC-big hypothesis with exact D/M/S prime preservation, strict mechanical pass, emphasis preservation, conservative source-relative alpha ratio and Russian angle/degree semantics. The neighboring longer `Chord` sentence is intentionally excluded because DMS mechanics alone cannot prove its technical meaning is preserved.

**Decision.** DMS implementation/unit success alone is not promotion evidence. First run read-only n-best feasibility on the immutable run-14 DB; only if a raw candidate is both mechanically and semantically admissible may a persisted composed corpus audit be attempted. Any persisted DMS evidence must compose with the already-validated angular-minute layer without new hard failures or source drift.

## Whence boundary-pair feasibility is positive but non-promoting

**Decision.** Read-only workflow `34644023517` shows that translating the exact falsely split pair `whence is it | but from ... ?` as one contiguous unit yields six strict candidates that also preserve the experiment's semantic anchors. This is useful evidence that source-boundary repair can unlock better real-MT behavior.

It does **not** authorize a general pair-merging rule or Product default. A future wrapper still needs a source-defined trigger, exact geometry and persisted corpus regression.

## Punctuation and numeric residuals are defect-family-specific

**Decision.** Do not introduce universal punctuation/numeric fixers. Current failures mix source-owned labels/references, symbol corruption, target-only additions, prime/DMS notation, long-context punctuation migration and other root causes.

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
