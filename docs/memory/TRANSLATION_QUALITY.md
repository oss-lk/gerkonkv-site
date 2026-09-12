# RocketDict maintained translation quality — L2

Durable translation-quality conclusions only. This is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). L3 source/tests/CI/artifacts outrank this file.

## Maintained contracts

- Production MT: pinned OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product/default Stage10 is V1; research V2 remains explicit only.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/6`; Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big remains a pinned independent comparator/narrow rescue, not a generic fallback. Research wrappers remain default OFF/not public-wired.

## Canonical complete Opticks basis

Pinned complete Project Gutenberg *Opticks*: normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` chars.

The maintained research line composes narrow, source-defined, fail-closed geometry/model rescues over immutable persisted predecessors. Mechanical improvement is evidence only; it never authorizes Product-default promotion.

Current best persisted research translation is **run 23**: **17 numeric/symbol / 14 punctuation / 0 length, 30 unique hard-failing sequences** over `3337` rows. It improves the exact run22 basis (**18/14/0,31**) by one accepted emphasized-modifier context group while leaving rejected/untouched content unchanged.

Run23 identities and provenance:

- full replay workflow run `34688874921`, artifact `rocketdict-full-opticks-emphasized-modifier-boundary-rescue` / artifact ID `10296696335`;
- artifact ZIP SHA-256 `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`;
- SQLite SHA-256 `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`;
- final text SHA-256 `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`;
- canonical evidence SHA-256 `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`;
- accepted context group `[2496,2497]`; rejected context group `[2633,2634]`;
- `3336` untouched rows preserve source/target exactly; source coverage remains byte-exact; SQLite integrity is `ok`; foreign-key violations are `0`;
- raw OPUS rank0 is selected; source rewriting, target rewriting, placeholders, post-translation literal injection, corpus-specific target patches, evaluator weakening and automatic n-best cherry-picking remain false;
- `promotion_allowed=false` and `automatic_product_default_allowed=false` remain binding.

Focused regression coverage for the composed run23 replay is green: `21 passed`. The replay runtime is explicitly torch-free and rebuilds the pinned OPUS asset from the verified archive.

## Residual census provenance blocker

The read-only run23 residual-census workflow run `34689198589` did **not** reach the census. It failed while staging the already-successful run23 artifact because the workflow duplicated the SQLite digest incorrectly as `75ec63eadd2a48d9fd8d68dde4ef16debf396aa8188324397d2a3f0b299b8495`; the persisted run23 evidence and actual database both identify `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`.

This is an orchestration/provenance defect, not evidence of translation regression. The next census must verify the upstream persisted run23 evidence contract and derive/check the database identity from that pinned evidence rather than trusting an independently hand-copied digest. No claims about the composition of the remaining 30 residual sequences are valid until that census completes.

## Binding rescue/negative conclusions

- Generic OPUS/TC-big whole-context fallback, generic row-local TC-big punctuation fallback, broad Stage10-v2 translation geometry and generic bounded-parenthesis fallback remain rejected.
- Inline `[G]` remains unresolved under tested row-local and whole-context OPUS/TC-big formulations: tested hypotheses omit the marker, so no wrapper is authorized.
- Long or mechanically unsafe punctuation groups remain fail-closed; run23 explicitly rejected `[2633,2634]` rather than trading content/semantic quality for a lower hard-gate count.
- Numeric rescue remains defect-family-specific. Historical generic prime/thousands/compact-formula/n-best approaches do not become valid merely because a narrower later family succeeds.
- Never use target literal injection, corpus-specific target patches, placeholders, source rewriting, target surgery, automatic n-best cherry-picking or evaluator weakening.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Preserve immutable source/model/config/result identities and exact persisted predecessor lineage.
3. Select only deterministic unmodified raw model candidates; no target surgery or automatic n-best cherry-picking.
4. Mechanical integrity is necessary but insufficient; semantic/boundary-aware review is mandatory.
5. Alternative geometry/model use requires a narrow existing-hard-failure/source-defined trigger; clean rows remain untouched unless separately justified.
6. Final approved heavy evidence requires zero unresolved hard failures before downstream learner/export/release validation.
