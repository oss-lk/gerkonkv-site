# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- Engineering/L3 checkpoint incorporated here: `6b90cc759275346471027a1d69a89f3e0641a9d5` (`Fix pinned TC-big provisioning for inline footnote DOE`).
- Maintained Product Core + Workbench remain the forward implementation. Authoritative contract: `rocketdict/PRODUCT_TARGET.md`.
- Final approved 90k+ evidence still requires **0 unresolved numeric/symbol, punctuation and length hard failures**, semantic acceptance and the complete learner/export path.
- Current best persisted research translation basis is run `20`: **20 numeric/symbol / 14 punctuation / 0 length, 33 unique failures** over `3341` rows.
- Product/default Stage10 remains V1. Broad Stage10-v2 remains explicit research evidence only and is rejected for wholesale translation geometry because semantic regressions were observed.
- All rescue layers added in this research line remain default OFF/not public-wired and non-promoting.

## Recovery protocol

Follow `AGENTS.md`: compare HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; L3 source/tests/CI/artifacts outrank L1/L2.

## Maintained identities

- OPUS: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product Stage10/default: `structural-entity-term-discourse-pronoun-v1`, schema `rocketdict-product-stage10/1`. Research V2 remains explicit only.
- Stage12 planner: `rocketdict-stage12-protected-split/8`; numeric gate: `rocketdict-maintained-numeric-integrity/5`; emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, `model.safetensors` SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0; offline asset manifest `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload tree `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`.

## Canonical full-Opticks evidence

Complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

Persisted progression: run `16` **20/18/0,37** → `17` **20/17/0,36** → `18` **20/16/0,35** → `19` **20/15/0,34** → `20` **20/14/0,33**.

Run-20 persisted identities: workflow `34678965465`; artifact `10292783763`; artifact ZIP SHA-256 `0e30b3d10cf263ef6256c422cf2c2003f0c81343ad59f13e1b3531e709b3f7cf`; output SHA `e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85`; final text SHA `16ab4a3c3ef192662604e90e428933ab23423b7872bae2bd6de3478b3a46f8c8`; SQLite SHA `879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d`; evidence SHA `2f21b87327033aab76e5d3485c22cfbd6ea672cae9c4c5055a3d129b3f5054c1`.

Run20 composes directly over exact run19 with default-OFF `rocketdict-stage12-parenthetical-whole-context-rescue/1`. Its generic source-owned trigger isolates one bounded split context (`1393`, 108 NLP tokens): exactly one short balanced source parenthetical pair, both parentheses lost from the aggregate split target, unrelated hard/research families clean, context <=160 tokens. Raw OPUS rank0 is selected; two base rows become one context row. **3340** other run19 rows remain source/target exact. Complete source reconstruction is byte-exact; SQLite integrity `ok`; FK violations `0`.

## Current verification and negative evidence

- Product CI `34678795359` is green for the parenthetical wrapper, including dependency-light and real-runtime Stage8→25/unified source→25.
- Full run20 replay `34678965465` is green and persisted the identities above.
- Run19 bounded-parenthesis DOE `34676468786` remains binding negative evidence against generic parenthesis fallback; only the narrower source predicate used by run20 is authorized for research.
- Inline `[G]` at Stage10 context `598` (`112541..113069`, 115 NLP tokens) was retested as a whole context on exact run20 with both OPUS and TC-big beam-6. Workflow `34679178153`, artifact `10293031844`, ZIP SHA `b4e8e09c848ce4015a6d4db5a80a2007420f93384563663df5e260a09d4a1d00`, evidence SHA `5530b8235e8d39e44be77032320cf898516b7dc07831e9b4929cd9283a300a61`. **All 12 hypotheses omit `[G]`**, so whole-context resegmentation does not solve this defect. No wrapper is authorized.
- Initial `[G]` workflow `34679083884` failed before inference because its orchestration checked nonexistent `pytorch_model.bin` instead of the pinned `model.safetensors`. Commit `6b90cc75` repaired provisioning using the already proven TC-big snapshot pattern; no quality criterion/model selector changed.

## Durable guardrails

- Generic OPUS/TC-big whole-context or punctuation fallback remains rejected.
- Mechanical integrity is necessary but insufficient; semantic review remains mandatory.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches, automatic n-best cherry-picking or evaluator weakening.
- Punctuation/numeric work remains defect-family-specific; a persisted improvement never authorizes a Product default by itself.
- New selectors must be source-defined and fail closed; raw-model output remains immutable selection evidence.

## Active next actions

1. Build the exact **20 numeric residual** census from persisted run20 and map every row to existing historical numeric feasibility evidence before adding new model/selectors.
2. Choose the next numeric family only if it has a materially new source-defined formulation; do not repeat rejected thousands-grouping, generic prime, narrow `x→×`, compact-formula spacing, or known bad `54796`/`112001` formulations.
3. Keep unresolved punctuation vetoes intact (`2726` emphasis failure, `2730` >160 tokens, inline `[G]` whole-context failure) unless materially new evidence appears.
4. Continue toward zero unresolved hard failures before downstream heavy learner/export and Windows release validation.
