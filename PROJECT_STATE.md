# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- Engineering/L3 checkpoint incorporated here: `1152705abfbce59b70dc84cd3968a019318d5dd7` (`Refresh translation-quality memory through run23`), which includes verified product/research HEAD `56a76bead0f6df0226f82496ef96c4a796d60d9b` plus the L2 refresh.
- Maintained Product Core + Workbench remain the forward implementation. Authoritative contract: `rocketdict/PRODUCT_TARGET.md`.
- Final approved 90k+ evidence still requires **0 unresolved numeric/symbol, punctuation and length hard failures**, semantic acceptance and the complete learner/export path.
- Current best persisted **research** translation basis is run `23`: **17 numeric/symbol / 14 punctuation / 0 length, 30 unique hard-failing sequences** over `3337` rows.
- Product/default Stage10 remains V1. Broad Stage10-v2 and all current rescue layers remain explicit research evidence only, default OFF/not public-wired/non-promoting.
- The immediate blocker is not translation inference: the run23 residual-census workflow failed before analysis because it carried an incorrect duplicated SQLite SHA. The full run23 replay itself is green and its persisted database/evidence identities are verified.

## Recovery protocol

Follow `AGENTS.md`: compare HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; L3 source/tests/CI/artifacts outrank L1/L2.

## Maintained identities

- OPUS: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product Stage10/default: `structural-entity-term-discourse-pronoun-v1`, schema `rocketdict-product-stage10/1`. Research V2 remains explicit only.
- Stage12 planner: `rocketdict-stage12-protected-split/8`; numeric gate: `rocketdict-maintained-numeric-integrity/6`; emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, `model.safetensors` SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0; offline asset manifest `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload tree `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`.

## Canonical full-Opticks evidence

Complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

Current persisted research basis, run `23`:

- workflow run `34688874921` (`RocketDict Full Opticks Emphasized Modifier Boundary Rescue`), success;
- artifact `rocketdict-full-opticks-emphasized-modifier-boundary-rescue`, artifact ID `10296696335`, ZIP SHA-256 `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`;
- SQLite SHA-256 `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`;
- final text SHA-256 `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`;
- evidence SHA-256 `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`;
- exact predecessor run22: **18/14/0,31**, `3338` rows; run23: **17/14/0,30**, `3337` rows;
- attempted emphasized-modifier groups `[[2496,2497],[2633,2634]]`; accepted `[[2496,2497]]`; rejected `[[2633,2634]]`;
- `3336` untouched rows remain source/target exact; source reconstruction is byte-exact; SQLite integrity `ok`; FK violations `0`;
- focused composed regressions: `21 passed`; replay runtime verified torch-free;
- `promotion_allowed=false`; `automatic_product_default_allowed=false`; unsafe rewrite/injection/cherry-pick/evaluator-weakening flags all false.

## Current verification and blocker

- Full run23 replay `34688874921` is green and persisted the identities above.
- Run23 residual-census workflow `34689198589` failed at the pre-census database verification step and therefore produced **no residual census**. It expected the incorrect duplicated digest `75ec63eadd2a48d9fd8d68dde4ef16debf396aa8188324397d2a3f0b299b8495`; the persisted run23 evidence and actual database identify `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`.
- Treat this as an orchestration/provenance defect. Repair the census to authenticate the pinned upstream run23 evidence contract and derive/check the database identity from that evidence rather than maintaining an independent hand-copied digest.
- Do not infer the makeup of the remaining 30 residual sequences from stale run20/run22 censuses; rerun the read-only census first.

## Durable guardrails

- Generic OPUS/TC-big whole-context or punctuation fallback remains rejected.
- Mechanical integrity is necessary but insufficient; semantic review remains mandatory.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches, automatic n-best cherry-picking or evaluator weakening.
- Punctuation/numeric work remains defect-family-specific; a persisted improvement never authorizes a Product default by itself.
- New selectors must be source-defined and fail closed; raw-model output remains immutable selection evidence.
- Rejected run23 group `[2633,2634]` remains unchanged unless materially new evidence/geometry is tested.

## Active next actions

1. Repair the run23 residual-census provenance gate without weakening evidence: pin/authenticate upstream run23 evidence, then derive and verify the SQLite identity from it.
2. Rerun the read-only census against exact run23 and require its database-unchanged/source-coverage/canonical-evidence invariants.
3. Use the resulting **30-sequence** residual census to select a materially new source-defined hard-failure family; do not repeat exhausted generic whole-context, TC-big, prime/thousands or n-best ideas.
4. Continue research replay + semantic/mechanical verification until all hard failures are eliminated, then resume downstream heavy learner/export and Windows release validation.
