# RocketDict maintained translation quality — L2

Durable translation-quality conclusions only. This is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). L3 source/tests/CI/artifacts outrank this file.

## Maintained contracts

- Production MT: pinned OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product/default Stage10 is V1; research V2 remains explicit only.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`; Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big remains a pinned independent comparator/narrow rescue, not a generic fallback. Research wrappers remain default OFF/not public-wired.

## Canonical complete Opticks basis

Pinned complete Project Gutenberg *Opticks*: normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` chars.

Persisted late progression: run `16` **20/18/0,37** → `17` **20/17/0,36** → `18` **20/16/0,35** → `19` **20/15/0,34** → `20` **20/14/0,33**.

Run `20` is the best accepted persisted **research** translation basis. Workflow `34678965465`; artifact `10292783763`; artifact ZIP SHA-256 `0e30b3d10cf263ef6256c422cf2c2003f0c81343ad59f13e1b3531e709b3f7cf`; output SHA `e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85`; final text SHA `16ab4a3c3ef192662604e90e428933ab23423b7872bae2bd6de3478b3a46f8c8`; SQLite SHA `879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d`; evidence SHA `2f21b87327033aab76e5d3485c22cfbd6ea672cae9c4c5055a3d129b3f5054c1`.

## Bounded parenthetical rescue

Contract: `rocketdict-stage12-parenthetical-whole-context-rescue/1`, matching selector/trigger `/1`, default OFF/not public-wired.

The trigger is generic/source-defined: one exact Stage10 context represented by 2+ current split rows, `<=160` NLP tokens, exactly one balanced source `(...)` pair, short parenthetical payload (`<=8` alphabetic words), aggregate current target lost both parentheses, other hard punctuation exact, and member numeric/length/numeric-order/technical/artifact diagnostics clean. Candidate is raw primary OPUS rank0 only. It must pass strict maintained mechanical/research gates, Gutenberg emphasis, exact hard punctuation, source-alpha ratio and non-decreasing aggregate alphabetic content.

Full replay `34678965465` proves the predicate isolates context `1393` on run19. Two base rows are merged into one raw rank0 context translation, improving **20/15/0,34 → 20/14/0,33**. 3340 other rows are source/target exact, full source is byte-exact and SQLite/FK integrity passes. This remains research evidence, not Product-default promotion.

## Inline `[G]` whole-context result

Run20 square-bracket residual at context `598`, source span `112541..113069`, is a split 115-token Stage10 context containing inline `[G]`. Historical row-local TC-big failed to preserve the marker. A materially different whole-context DOE tested both OPUS and TC-big, six raw hypotheses each.

Corrected workflow `34679178153` is green; artifact `10293031844`, ZIP SHA `b4e8e09c848ce4015a6d4db5a80a2007420f93384563663df5e260a09d4a1d00`, evidence SHA `5530b8235e8d39e44be77032320cf898516b7dc07831e9b4929cd9283a300a61`. All OPUS ranks 0..5 and TC-big ranks 0..5 omit `[G]`; no candidate is mechanically admissible. OPUS is also compressed relative to the base aggregate; TC-big loses larger content. Therefore this source geometry does **not** justify an inline-footnote rescue wrapper.

The first workflow attempt `34679083884` failed before inference because the orchestration expected `pytorch_model.bin`; the pinned snapshot uses `model.safetensors`. The fixed workflow reused the proven allowlisted snapshot + builder stack and did not change research criteria.

## Earlier binding results

- run17 boundary-pair rescue: **20/18/0,37 → 20/17/0,36**;
- run18 orphan-closing-parenthesis rescue: **20/17/0,36 → 20/16/0,35**;
- run19 bounded question whole-context OPUS rank0: **20/16/0,35 → 20/15/0,34**;
- run20 bounded parenthetical whole-context OPUS rank0: **20/15/0,34 → 20/14/0,33**.

Persisted success is research evidence, not automatic Product-default authorization.

## Rejected/exhausted directions

- Broad Stage10-v2 translation geometry; generic OPUS/TC-big whole-context fallback; generic row-local TC-big punctuation fallback; generic bounded-parenthesis fallback.
- Inline `[G]` row-local TC-big and bounded whole-context OPUS/TC-big: exhausted under current models/search; all whole-context beam-6 hypotheses lose the marker.
- `2726` bounded question remains fail-closed because OPUS rank0 violates emphasis preservation and TC-big truncates content; `2730` remains above the 160-token cap.
- Broad square-bracket-loss OPUS formulation remains rejected.
- Known numeric negative families remain binding unless a materially new formulation is tested: broad/generic prime normalization, thousands grouping, narrow `x→×`, compact formula spacing, and known bad whole-boundary formulations around `54796`/`112001`.
- Never use target literal injection, corpus-specific target patches, placeholders, source rewriting, target surgery, automatic n-best cherry-picking or evaluator weakening.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Preserve immutable source/model/config/result identities.
3. Select only deterministic unmodified raw model candidates; no target surgery or automatic n-best cherry-picking.
4. Mechanical integrity is necessary but insufficient; semantic/boundary-aware review is mandatory.
5. Alternative geometry/model use requires a narrow existing-hard-failure/source-defined trigger; clean rows remain untouched unless separately justified.
6. Final approved heavy evidence requires zero unresolved hard failures.
