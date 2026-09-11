# RocketDict durable decisions — L2

Store only conclusions that are expensive or risky to rediscover. This is not a changelog; Git history and L3 evidence contain chronology and raw detail.

## Quality is a release invariant

**Decision.** Speed, storage and convenience may not reduce Product quality/evidence. Real EN→RU MT is mandatory; fake/identity/mock/dictionary substitution is never Product translation. Hard gates may not be weakened merely to pass CI, and corpus/source truncation may never be silent.

## Maintained Product Core is the forward implementation

**Decision.** New Product work targets `rocketdict-product-core` plus Workbench unified orchestration. Historical 0.30.x/checkpoint material remains provenance/compatibility evidence, not the forward path without an evidence-based reason.

## Product assets and downstream evidence are pinned and fail-closed

**Decision.** Production baseline uses official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian and `float32` acceptance compute. Preserve immutable source/config/model/result identities and replayable evidence.

A second real MT does not become Product merely because it passes hard gates on residual failures. Any Product role requires pinned identity/license, deterministic selection, semantic review, full-corpus regression and an offline installation/runtime plan.

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
- `rocketdict-stage12-tc-big-target-delimiter-context-rescue/1` is implemented as a separate default-OFF/not-public-wired wrapper. Its unit invariants are green; persisted heavy proof is still required before public exposure or persisted-quality claims.

## Punctuation residuals remain defect-family-specific

**Decision.** Do not introduce a universal punctuation fixer. Run-9 failures mix block footnotes, square-bracket payload loss, target-only delimiter hallucination, long-context question migration and other families with different root causes.

The current exact-source OPUS formulations are exhausted or rejected for whole-footnote, square-bracket, context-2730, prime/formula and broad citation/group branches. A future attempt needs a materially new source representation/model hypothesis rather than deeper identical beam search.

## Pinned TC-big is the active independent model differential, not a generic fallback

**Decision.** Use pinned `Helsinki-NLP/opus-mt-tc-big-en-zle` revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, license `CC-BY-4.0`, as the independent real-MT comparator and current narrow-rescue candidate.

**Evidence.** The all-52 screen finds at least one mechanically admissible raw hypothesis in **32/52** cases, but the generic whole-Stage10 screen admits only **18/50** contexts and manual review still finds semantic false positives.

**Interpretation.** A material portion of the residual frontier is baseline-model-specific, but broad second-model replacement is not safe.

## A second MT may only be failure-triggered and boundary-aware

**Decision.** Do not replace clean OPUS rows merely because another model exists. Any second-model Product path must start from an existing maintained hard failure or a separately justified source-defined trigger.

**Decision.** Do not implement isolated Stage12-row TC-big substitution as the general fallback mechanism. A Stage12 row may be only a fragment of a larger source sentence/context; a mechanically clean candidate can finish or punctuate a clause that source text continues in the neighboring row.

A future selector must reason on a source-defined contiguous group/context and verify semantic validity for that full source span.

## Exact Stage10 contexts are not guaranteed to align with current Stage12 row boundaries

**Decision.** A Stage10 context may be used as a replacement unit only when its exact source span is representable by complete current Stage12 rows. Otherwise skip fail-closed; do not slice an existing target string or silently expand source.

**Evidence.** Boundary-aware workflow `34626136705` maps 52 hard rows to 50 Stage10 contexts and proves `49/50` exact row alignment. Context `2480` remains the sole non-row-aligned case and is explicitly skipped. This converts the earlier crash into a durable geometry classification without changing source ownership.

## Generic whole-context TC-big selection is rejected

**Decision.** `strict-clean + emphasis + baseline-alpha` is not a sufficient semantic selector for whole-context second-MT replacement. The 18 mechanically admissible Stage10 contexts include semantically poor/partial cases on manual inspection.

**Decision.** Do not treat aggregate mechanical ceiling **20/16/0, 34 unique** as Product progress. It is a research upper bound only.

## Corrupt baseline verbosity is not a valid completeness floor

**Decision.** The legacy `candidate target alpha >= baseline target alpha` condition must not be generalized to alternative-MT selection when the baseline target is itself inflated by hallucination. This rule rejected several plainly useful TC-big candidates.

For the narrow TC-big delimiter experiment, completeness is constrained against immutable source alphabetic volume instead. This change is local to that selector and does not weaken existing OPUS rescue contracts.

## Narrow target-only delimiter hallucination is the first admissible TC-big defect class

**Decision.** The only currently implemented second-MT rescue class is a source-defined Stage10 context that:
- contains a current hard failure;
- is exactly row-aligned to complete current Stage12 rows; and
- whose aggregate current target adds `()[]{}` delimiter characters beyond source counts.

Candidate acceptance requires a raw TC-big hypothesis, maintained strict-clean verdict, Gutenberg emphasis preservation, zero target-only delimiter additions, and target/source alpha ratio `0.75..1.50`. No corpus-specific whitelist or target editing is allowed.

**Evidence.** Workflow `34627371508` triggers on seven run-9 contexts and accepts five (`3`, `1726`, `1737`, `2066`, `2605`), giving a read-only counterfactual **24/30/0,52 → 24/25/0,47**. The remaining two trigger cases fail closed.

**Implementation proof.** Commit `aa776b57...` adds dedicated wrapper tests; Product Core workflow `34629151558` is fully green. Tests explicitly prove disabled exact delegation without TC-big runtime probing, trigger/row-alignment requirements, source-relative completeness bounds, emphasis and delimiter-debt vetoes, fail-closed Stage10/Stage12 cut-through geometry, raw selected-hypothesis provenance, untouched-row copying and byte-exact source reconstruction.

**Non-promotion rule.** These results authorize only continued persisted full-corpus validation. They do not authorize public wiring or Product-default promotion. The counterfactual **24/25/0,47** remains non-persisted until the real wrapper creates and validates a Stage12 run above exact run `9`.

## MetricX is a research ranking signal only

**Decision.** MetricX/QE may rank immutable raw candidates but neither its absolute score nor its preference is sufficient for Product selection.

Row-local evidence prefers TC-big in 30/32 mechanically admissible cases. Whole-context evidence (`34627052164`) prefers some TC-big candidate in 16/18 contexts and scores two contexts worse than OPUS. This is useful semantic triage evidence and further proof that QE cannot override source-boundary or semantic vetoes.

## Correct MarianTokenizer semantics make CTranslate2 a viable TC-big inference backend

**Decision.** The initial `0/52` CTranslate2 parity result is a tokenizer-harness defect, not a basis for rejecting CT2. The release-relevant TC-big runtime must use exact MarianTokenizer semantics, including the `>>rus<<` language prefix and HF token/id conversion.

**Evidence.** Corrected workflow `34626241784` obtains input-token parity `52/52`, exact rank0 parity `49/52`, at least one exact n-best overlap `52/52`, and the same 32 mechanically admissible cases / **13/8/0,20** ceiling as Transformers.

**Decision.** TC-big inference may therefore use CTranslate2 float32 without Torch, while preserving the three observed rank0 search-order differences as explicit backend behavior rather than pretending exact search identity.

## TC-big is provisioned as a separate optional offline asset

**Decision.** Keep the second model isolated from the accepted OPUS production asset. `rocketdict-tc-big-en-ru-asset/1` pins repository, revision, weight SHA, CC-BY-4.0 license, target prefix, tokenizer files, CTranslate2 float32 payload and complete payload-tree identity. `ROCKETDICT_TC_BIG_ASSET_DIR` selects the installed asset.

`rocketdict-assets build-tc-big-en-ru` is an explicit provisioning step. Runtime processing is offline. The baseline `production` dependency profile does not silently acquire TC-big; separate `alt-mt` / `alt-mt-build` profiles keep release cost visible and optional until promotion is justified.

## Run 9 is still the persisted residual basis

**Decision.** Current persisted gates remain **24 numeric / 30 punctuation / 0 length, 52 unique**. The **24/25/0,47** delimiter result is a read-only counterfactual until a persisted Stage12 run verifies the actual wrapper output, source coverage, untouched rows, SQLite integrity and asset provenance.

## Acceptance order remains smoke → full corpus → distributable Product

**Decision.** User-facing real source→Stage25/replay must be green before full-corpus acceptance; final full public-domain quality evidence must reach zero unresolved hard failures before Windows distribution becomes the release frontier.

## Project memory uses progressive disclosure and mandatory synchronization

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Before a user-facing development result, synchronize `PROJECT_STATE.md`, `TRANSLATION_QUALITY.md`, and `DECISIONS.md` to actual HEAD/CI/artifacts. Interrupted synchronization becomes explicit debt that the next iteration clears before new work.
