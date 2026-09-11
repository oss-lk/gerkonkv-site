# RocketDict maintained translation quality — L2

This file stores durable conclusions from maintained Product translation-quality work. It is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Source/tests/CI/artifacts are L3 authority and outrank this summary if they disagree.

## Maintained contracts

- Production MT: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian, acceptance `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural-label contract: `rocketdict-stage12-block-structural-label-opus/2`; source-proven block headings only. Bare Roman fragments produced by sentence segmentation are not headings.
- Block section identifier contract: `rocketdict-stage12-block-section-identifier/1`.
- Numeric/symbol hard gate: `rocketdict-maintained-numeric-integrity/5`, applied to every selected translation row.
- Backend batching: `rocketdict-stage12-bounded-request-batch/1`, default `48`, max `128`; batching may not alter planner units/model inputs/order.
- Length whole-context rescue: `rocketdict-stage12-length-failure-whole-context-rescue/1`, default OFF.
- Citation pair rescue: `rocketdict-stage12-citation-boundary-pair-rescue/1`, default OFF.
- Numeric-hard whole-context rescue: `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1`, selector `/1`, implemented as a separate wrapper above citation+length composition, default OFF and not yet public-wired.
- Gutenberg underscore-emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`. This is a research veto, not a Product hard gate.

## Canonical full contiguous Opticks baseline

Pinned complete Project Gutenberg *Opticks*:
- source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`;
- normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`;
- `586543` source characters.

Structural-label `/2` Product baseline: run `34575909618`, artifact `10190059238`, JSON SHA `48385b0b9e2539c9b82feb1f98fa68b660307aa1f76ce58e6e56ed6a93f32133`, SQLite SHA `eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c`, Stage12 run id `4`, output SHA `b5c42141767a9760495c84023349402bf637b6591f3fa60d723d42c7d5760e22`.

Complete baseline gates: `3353` segments, **30 numeric/symbol / 34 punctuation / 5 length**, **64 unique failures**. Historical `product_numeric_failure_count=27` is only the literal-bearing stress subset; the complete gate also catches three non-literal-source failures.

## Validated length and citation rescue composition

Length rescue on full *Opticks* accepts Stage10 contexts `577`, `629`, `919`, resulting in Stage12 run `6`, SHA `2224d71b20df64e853db1480380f4a78f01184d9021ef8e35142a66dd99d8437`, `3350` segments and **29/34/2**, `61` unique failures.

The two remaining length failures were bare `IV.`/`II.` fragments split from inline `Sect. IV.` / `Sect. II.` references. A broad citation-group merge was unsafe because it lost unrelated numeric content and a footnote marker. The narrow exact-pair mechanism was therefore implemented instead; it accepts raw rank-0 OPUS only when Product hard gates and length pass and strict debt categories do not worsen.

Combined run `34597648856`, artifact `10263095872`, evidence SHA `5edfe5b917c2274332ff27ce1e3be5191c95a4a8879a9a643a29ecb2516316da` gives Stage12 run `7`, SHA `b9e61f1f381ac9cd32e450e66c36a1f16d380eb2ef8b20c18ed7fc5bfc2c38e8`, `3348` segments and **29 numeric / 34 punctuation / 0 length**, **59 unique failures**. Source coverage is byte-exact, untouched rows are base-exact, applied targets are exact raw rank-0, and all rewrite/placeholder flags are false.

## Composed residual whole-context lineage

A post-composition audit mapped run-7 residuals by immutable source span/Stage10 context and cross-referenced the old whole-context shadow. The old mechanically accepted contexts still lineage-match exactly for `550, 669, 1024, 1393, 2238, 2462, 2725, 2726` (`919` is already consumed by length rescue).

Mechanical acceptance is **not semantic proof**. Manual/L3 inspection found the decisive counterexample in context `2725`: the raw whole-context candidate removes an invented `=` but also silently drops source phrase `_per deliquium_`. The existing strict selector did not detect this because `critical_technical_tokens/3` only treats symbolic underscore emphasis as critical, not ordinary emphasized prose.

Therefore generic strict whole-context selection remains non-promotable.

## Emphasis markup preservation veto

`rocketdict-maintained-emphasis-markup-preservation/1` was added as a separate versioned research diagnostic rather than silently changing historical `critical_technical_tokens/3`. It checks preservation of Gutenberg underscore-emphasis markup shape/content conservatively enough to reject the `2725` loss.

This diagnostic is currently a selector veto only for the new numeric-hard whole-context rescue. It is not a release hard gate and must not be retroactively treated as one.

## Numeric-hard split-context whole-context rescue

The new wrapper targets only current split Stage10 contexts where at least one selected Stage12 row already fails `rocketdict-maintained-numeric-integrity/5`. It uses the exact unchanged whole Stage10 source context, bounded by the existing 160 non-space NLP token cap, translated once using pinned OPUS beam=6/rank0.

Acceptance requires both:
1. existing strict whole-context selector acceptance (`evaluate_candidate_context`), including Product hard checks, research diagnostics and alpha non-decrease;
2. `rocketdict-maintained-emphasis-markup-preservation/1` pass.

No source rewrite, target rewrite, placeholders or post-translation literal injection are permitted. Rejected candidates leave the current base output untouched.

Full-*Opticks* persisted audit run `34601313026` succeeded. Artifact `10264132732`, digest `3020f5bb9e6c59b312bb8e09a26d1fea4e29deac29ace3bbeca0cfd695b4bd76`; evidence file SHA-256 `8af5a3e15997e55a790f0cf408274873a2281c5a7ddda29072039367043ca22d`, internal canonical evidence field `c8908cbf8248b140c4efecd01ec0d1e83a84c51385760212659662a598c1c61e`.

Persisted result:
- base Stage12 run `7` reused from cache;
- enabled Stage12 run `8`, output SHA `d3b97f349a7983dc34ed9d8cbd8e64a98c8e237eefa508f4d2d88b62ec547346`;
- resulting SQLite SHA `a84b2118f00bc386953fe11db48bdc29fcfe8db62735f9acf86178e1dbacf9a2`;
- attempted contexts: `550, 669, 1024, 1460, 2132, 2176, 2190, 2238, 2634, 2725`;
- accepted: `550, 669, 1024, 2238`;
- rejected: `1460, 2132, 2176, 2190, 2634, 2725`;
- emphasis veto rejects `2725`;
- segments `3348 → 3343`;
- gates **29/34/0 → 25/33/0**;
- unique hard failures **59 → 55**;
- source coverage byte-exact; untouched rows base-exact; applied targets exact raw rank-0; safety flags false.

Product Core CI run `34601005247` for the wrapper/tests completed successfully. The persisted audit explicitly keeps `promotion_allowed=false`, `automatic_product_default_allowed=false`, `semantic_review_required=true`.

## Current residual frontier

The strongest validated opt-in research output is run `8`: **25 numeric/symbol / 33 punctuation / 0 length**, **55 unique failures**. Three rows fail both numeric and punctuation (`25 + 33 - 55 = 3`).

All further residual work must key on immutable source spans/current Stage10 context identity from run 8; sequence numbers may shift after merged contexts.

## Punctuation residual remains heterogeneous

The punctuation class contains multiple defect families, including lost square-bracket footnote markers, illustration/bracket payload mismatches, omitted/added parentheticals, question-mark drift and mixed delimiter failures. A universal punctuation fixer is unsafe. The run-8 cohort must be reclassified because one punctuation failure disappeared incidentally in the numeric-hard rescue.

## Numeric residual families / negative evidence

Do not repeat unchanged without genuinely new evidence:
- prime-fragment structural decomposition is semantically unacceptable (`53 deg.`→`53 балла`, `hundred Feet`→`сто ног`); whole-unit prime normalization/hints and broad staged n-best do not solve the class;
- thousands grouping / narrow `x→×` preprocessing rescued `0/4` and regressed successful cases;
- compact formula operator spacing did not rescue the investigated `3/8A ... ((61-1/2)/8)A` unit even with staged raw n-best;
- broad n-best fallback, target repair, literal injection and generic whole-context fallback remain rejected;
- broad citation/group coalescing is unsafe.

Prime notation, formula/fraction corruption and very-large-integer corruption remain separate unresolved model/notation families.

## MetricX remains research-only

Pinned MetricX-24 QE may rank immutable raw candidates but cannot by itself authorize Product selection. Learned QE must remain evidence alongside mechanical checks and semantic review.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Classify planner/evaluator/source/document/model/resource defects before changing Product behavior.
3. Prefer source/planner fixes for pre-MT defects; select only unmodified raw model candidates when evidence supports them.
4. Source-owned bypass is allowed only for exhaustively identified non-linguistic structure; inline linguistic text remains ordinary.
5. No post-hoc literal insertion, target patch lists, fabricated structure or final placeholders.
6. Promoted mechanisms must preserve source identity, be versioned/replayable and have contiguous-corpus evidence.
7. Mechanical integrity is necessary but not sufficient; semantic review remains required.
8. Narrow rescue escalation requires a source-defined trigger and explicit evidence.
9. Stress-subset metrics may not be relabeled as complete release-wide gate counts.
10. Expensive negative evidence belongs here so it is not rediscovered blindly.
