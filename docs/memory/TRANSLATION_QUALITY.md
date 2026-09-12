# RocketDict maintained translation quality — L2

Durable translation-quality conclusions only. This is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). L3 source/tests/CI/artifacts outrank this file.

## Maintained contracts

- Production MT: pinned OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product/default Stage10 is V1; research V2 remains explicit only.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/6`; Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big remains a pinned independent comparator/narrow rescue, not a generic fallback. Research wrappers remain default OFF/not public-wired.
- Figure-reference research wrapper is now `rocketdict-stage12-tc-big-figure-reference-lead-rescue/2` with selector `/2`: only raw TC-big rank0 can be selected; rank1+ hypotheses are diagnostic evidence only.

## Canonical complete Opticks basis

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` chars.

The maintained research line composes narrow, source-defined, fail-closed geometry/model rescues over immutable persisted predecessors. Mechanical improvement is evidence only; it never authorizes Product-default promotion.

Current best persisted research translation remains **run 23**: **17 numeric/symbol / 14 punctuation / 0 length, 30 unique hard-failing sequences** over `3337` rows. It improves exact run22 (**18/14/0,31**) by one accepted emphasized-modifier context group while leaving rejected/untouched content unchanged.

Run23 identities:

- workflow run `34688874921`; artifact ID `10296696335`; ZIP SHA-256 `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`;
- SQLite SHA-256 `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`;
- translation output SHA-256 `976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493`;
- final text SHA-256 `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`;
- canonical evidence SHA-256 `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`;
- accepted context group `[2496,2497]`; rejected `[2633,2634]`; `3336` untouched rows exact; source byte-exact; SQLite `ok`; FK violations `0`;
- `promotion_allowed=false`; `automatic_product_default_allowed=false`; unsafe rewrite/injection/cherry-pick/evaluator-weakening flags false.

## Verified run23 residual census

Corrected read-only census workflow `34690365432` authenticated canonical run23 evidence and verified the exact persisted database without mutation.

- census artifact ID `10296887793`; ZIP SHA-256 `8cc7ea22a12f27ee0105767bfc7b13c39a9493e945e6d32508b847151c986393`; evidence SHA-256 `55848393832fd777d7ab23f03f36d8fb2eb1031748faa0d2a096a35ea781ed58`;
- residual sequences: `[325,641,642,644,646,650,743,750,751,752,1499,1579,1755,1788,2110,2290,2346,2357,2375,2591,2721,2741,2889,2997,3000,3007,3011,3083,3211,3305]`;
- numeric defect classes: `critical_symbol=1`, `duplicate_required=1`, `missing_literal=2`, `missing_literal+unlicensed_addition=4`, `prime_notation=4`, `prime_notation+missing_literal+unlicensed_addition=4`, `unlicensed_addition=1`;
- source features: `numeric_prime_notation=10`, `round_parenthesis=10`, `fraction=5`, `big_integer=4`, `square_bracket=3`, `angle_word=3`, `apostrophe_decimal=2`, `ascii_x=1`, `formula_suffix=1`.

The earlier census attempt `34689198589` failed solely because a derived SQLite digest had been copied independently and incorrectly; this was provenance/orchestration debt, not a translation regression.

## Figure-reference sequence 325: exhausted tested geometries

Sequence `325` contains the bracketed leading source reference `[in _Fig._ 16.]`. Existing L3 evidence already covers both an isolated figure-lead split and a restored syntactic boundary pair; therefore a new rescue must not simply repeat either geometry.

- Figure-lead split DOE `34683173809` splits immutable source into `figure lead | source whitespace | body`. Raw rank0 OPUS and TC-big become mechanically admissible in isolation, but the reconstructed full-context translation has a broken boundary/syntax around the preceding clause and figure lead. The representative composition is of the `...Призма DH[в рис. 16.] быть...` form. This is a semantic/boundary failure despite green mechanical gates.
- Figure-boundary-pair DOE `34683394207` restores the preceding incomplete source phrase. Both rank0 models become inadmissible again: OPUS keeps the figure concept but damages the Gutenberg emphasis/reference form, while TC-big drops the `Fig. 16` reference. Accepting either would require prohibited target repair.
- Historical persisted figure-reference replay accepted only rank0 for the case that actually survived all gates. Current implementation now makes that safety property structural: selector `/2` authorizes only rank0, fails closed if rank0 is rejected, and records later beam hypotheses as diagnostics only.
- Product Core CI run `34692166640` succeeded on commit `58654b801ed93562001b08479e194256af601fbc`. Dedicated regressions prove that a mechanically acceptable rank1 cannot rescue a rejected rank0 and that missing/duplicate rank0 cardinality fails closed.

Conclusion: sequence `325` is not currently rescuable by the tested lead-split or preceding-boundary-pair formulations without violating semantic quality or no-repair constraints. Mechanical green from isolated segmentation is not sufficient evidence.

## Binding rescue/negative conclusions

- Generic OPUS/TC-big whole-context fallback, generic row-local TC-big punctuation fallback, broad Stage10-v2 geometry and generic bounded-parenthesis fallback remain rejected.
- Inline `[G]` remains unresolved under tested row-local and whole-context OPUS/TC-big formulations; tested hypotheses omit the marker, so no wrapper is authorized.
- Long or mechanically unsafe punctuation groups remain fail-closed; run23 rejected `[2633,2634]` rather than trading content/semantic quality for a lower hard-gate count.
- Large-integer source canonicalization/n-best feasibility rescued **0** baseline hard failures; do not repeat it without materially new evidence.
- Nonliteral numeric n-best can mechanically rescue isolated rows only through disallowed automatic beam selection.
- Never use target literal injection, corpus-specific target patches, placeholders, source rewriting, target surgery, automatic n-best cherry-picking or evaluator weakening.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Preserve immutable source/model/config/result identities and exact persisted predecessor lineage.
3. Only deterministic unmodified raw rank0 model candidates may be persisted by current rescue research unless an independently justified Product contract explicitly changes that rule; beam alternatives are diagnostic, not automatic selectors.
4. Mechanical integrity is necessary but insufficient; semantic/boundary-aware review is mandatory.
5. Alternative geometry/model use requires a narrow existing-hard-failure/source-defined trigger; clean rows remain untouched unless separately justified.
6. Final approved heavy evidence requires zero unresolved hard failures before downstream learner/export/release validation.

## Current quality frontier

With figure-reference sequence `325` closed under its tested geometries, the next highest-value family is the run23 `numeric_prime_notation` cluster (`10` source-feature hits). Before adding code, recover exact affected rows, overlap with defect subclasses, and all prior prime-notation DOE/rescue history. Any new attempt must use materially new source-defined geometry and raw rank0 outputs, preserve exact source coverage, strictly improve hard gates without new failures, and pass semantic review.
