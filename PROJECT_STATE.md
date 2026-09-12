# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- Repository/L3 checkpoint incorporated here: `58654b801ed93562001b08479e194256af601fbc` (`Test rank0-only figure reference selection`).
- Maintained Product Core + Workbench remain the forward implementation. Authoritative contract: `rocketdict/PRODUCT_TARGET.md`.
- Final approved 90k+ evidence still requires **0 unresolved numeric/symbol, punctuation and length hard failures**, semantic acceptance and the complete learner/export path.
- Current best persisted **research** translation basis remains run `23`: **17 numeric/symbol / 14 punctuation / 0 length, 30 unique hard-failing sequences** over `3337` rows.
- Product/default Stage10 remains V1. Broad Stage10-v2 and current rescue layers remain explicit research evidence only, default OFF/not public-wired/non-promoting.
- The run23 residual census is a successful read-only persisted audit. The earlier failed census was an orchestration/provenance defect caused by independently duplicated derived hashes, not a translation regression.

## Recovery protocol

Follow `AGENTS.md`: compare HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; L3 source/tests/CI/artifacts outrank L1/L2.

## Maintained identities

- OPUS: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product Stage10/default: `structural-entity-term-discourse-pronoun-v1`, schema `rocketdict-product-stage10/1`. Research V2 remains explicit only.
- Stage12 planner: `rocketdict-stage12-protected-split/8`; numeric gate: `rocketdict-maintained-numeric-integrity/6`; emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, `model.safetensors` SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0; offline asset manifest `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload tree `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`.
- Current figure-reference research wrapper contract: `rocketdict-stage12-tc-big-figure-reference-lead-rescue/2`; selector `/2`. Only raw TC-big rank0 is selection-authorized; higher beam hypotheses are diagnostic evidence only.

## Canonical full-Opticks evidence

Complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

Current persisted research basis, run `23`:

- workflow run `34688874921`, artifact ID `10296696335`, ZIP SHA-256 `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`;
- SQLite SHA-256 `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`;
- translation output SHA-256 `976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493`;
- final text SHA-256 `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`;
- canonical evidence SHA-256 `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`;
- exact predecessor run22: **18/14/0,31**, `3338` rows; run23: **17/14/0,30**, `3337` rows;
- accepted emphasized-modifier group `[2496,2497]`; rejected `[2633,2634]`;
- `3336` untouched rows remain source/target exact; source reconstruction is byte-exact; SQLite integrity `ok`; FK violations `0`;
- `promotion_allowed=false`; `automatic_product_default_allowed=false`; unsafe rewrite/injection/cherry-pick/evaluator-weakening flags all false.

## Verified run23 residual census

- Workflow run `34690365432`; census artifact ID `10296887793`; ZIP SHA-256 `8cc7ea22a12f27ee0105767bfc7b13c39a9493e945e6d32508b847151c986393`; census evidence SHA-256 `55848393832fd777d7ab23f03f36d8fb2eb1031748faa0d2a096a35ea781ed58`.
- Database remained byte-identical and source coverage byte-exact.
- Residual sequences: `[325,641,642,644,646,650,743,750,751,752,1499,1579,1755,1788,2110,2290,2346,2357,2375,2591,2721,2741,2889,2997,3000,3007,3011,3083,3211,3305]`.
- Numeric defect classes: `critical_symbol=1`, `duplicate_required=1`, `missing_literal=2`, `missing_literal+unlicensed_addition=4`, `prime_notation=4`, `prime_notation+missing_literal+unlicensed_addition=4`, `unlicensed_addition=1`.
- Source features include `numeric_prime_notation=10`, `round_parenthesis=10`, `fraction=5`, `big_integer=4`, `square_bracket=3`, `angle_word=3`, `apostrophe_decimal=2`, `ascii_x=1`, `formula_suffix=1`.

## Figure-reference frontier closed under current evidence

- Sequence `325` (`[in _Fig._ 16.]`) has already been tested under materially different source geometries.
- Figure-lead split DOE run `34683173809`: isolated `figure lead | whitespace | body` makes rank0 OPUS and rank0 TC-big mechanically admissible, but the resulting full-context join is semantically/syntactically broken (`...Призма DH[в рис. 16.] быть...` class of boundary failure). Mechanical green is therefore insufficient.
- Figure-boundary-pair DOE run `34683394207`: restoring the preceding syntactic context makes both rank0 models inadmissible again; OPUS preserves the figure concept but damages Gutenberg emphasis/boundary form, while TC-big drops the `Fig. 16` reference. No target repair is permitted.
- Historical persisted figure-reference rescue selected rank0 for its accepted case; the current helper now enforces that rule structurally: contract/selector `/2` evaluates higher beam hypotheses only for diagnostics and refuses rescue if rank0 fails.
- Product Core CI run `34692166640` succeeded on commit `58654b8`, including explicit regressions that rank1 cannot rescue a rejected rank0 and rank0 cardinality drift fails closed.

## Durable guardrails

- Generic OPUS/TC-big whole-context or punctuation fallback remains rejected.
- Mechanical integrity is necessary but insufficient; semantic/boundary-aware review remains mandatory.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches, automatic n-best cherry-picking or evaluator weakening.
- Punctuation/numeric work remains defect-family-specific; a persisted improvement never authorizes a Product default by itself.
- New selectors must be source-defined and fail closed; raw-model output remains immutable evidence.
- Large-integer source canonicalization/n-best feasibility rescued **0** baseline hard failures; do not repeat it without materially new evidence.
- Nonliteral numeric n-best can mechanically rescue isolated rows only through disallowed automatic beam selection.
- Rejected run23 group `[2633,2634]` remains unchanged unless materially new evidence/geometry is tested.

## Active next actions

1. Treat sequence `325` as exhausted for the tested lead-split/boundary-pair geometries; do not create a rescue from mechanically green but semantically broken segmentation.
2. Move to the largest remaining source-defined numeric family, beginning with the run23 `numeric_prime_notation` residuals. Recover exact rows, defect subclasses and any prior prime-notation DOE/rescue history before inventing a new mechanism.
3. Test only materially new source/model geometry with immutable raw rank0 outputs, exact source coverage, strict hard-gate improvement, no new failures and semantic review.
4. Persist any accepted improvement as a new research run over exact run23; continue until hard failures reach zero, then resume downstream learner/export and Windows release validation.
