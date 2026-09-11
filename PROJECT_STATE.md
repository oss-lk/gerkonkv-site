# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- Engineering/L3 checkpoint incorporated here: `f7c4787857cd470249c3abc8e21c80ed429859b3` (`Remove completed Stage10 census migration`).
- Maintained Product Core + Workbench are the forward implementation. Authoritative contract: `rocketdict/PRODUCT_TARGET.md`.
- Final approved 90k+ evidence still requires **0 unresolved numeric/symbol, punctuation and length hard failures**, semantic acceptance and the complete learner/export path.
- Current best persisted translation basis remains run `16`: **20 numeric/symbol / 18 punctuation / 0 length, 37 unique failures** over `3344` rows, pending the active Stage10-v2 exact replay.
- All narrow TC-big rescue layers remain default OFF/not public-wired and non-promoting.

## Recovery protocol

Follow `AGENTS.md`: compare HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; L3 source/tests/CI/artifacts outrank L1/L2.

## Maintained identities

- OPUS: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Stage10: `structural-entity-term-discourse-pronoun-v2`, schema `rocketdict-product-stage10/2`, policy `rocketdict-stage10-lowercase-continuation-coalescer/1`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`; numeric gate: `rocketdict-maintained-numeric-integrity/5`; emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0; offline asset manifest `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload tree `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`, 11 files / 968529922 bytes, Torch-free inference.

## Canonical full-Opticks evidence

Complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

Persisted progression: run `4` **30/34/5,64** → `7` **29/34/0,59** → `8` **25/33/0,55** → `9` **24/30/0,52** → `10` **24/25/0,47** → `11` **24/20/0,42** → `12` **23/19/0,41** → `13` **23/18/0,40** → `14` **22/18/0,39** → `15` **21/18/0,38** → `16` **20/18/0,37**.

Run-16 identities: workflow `34645769684`; artifact `10282227627`; artifact SHA-256 `92b2ad3fa98af1d12c27eeb4ee749071d5152464b34c4ac1f3bf40ed7cc02e14`; output SHA `767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783`; SQLite SHA `573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11`; evidence SHA `86c865cef5a0081fd77aa8ad78c525ebb38a01e6f279cc560aea56bb84d4e37d`.

## Stage10-v2 evidence

The previous memory claim that the complete corpus had exactly five matching boundaries was false. L3 replay of immutable run-16 Stage8 evidence proves **38** raw spaCy boundaries satisfy the implemented source-defined predicate. Source review found all 38 to be source-continuous false parser splits/markup continuations; no corpus-specific offset is present in Product logic.

- **7/38** were already absorbed by Stage12 protected-span planning and therefore do not change final Stage12 geometry: offsets `18355, 64046, 155895, 166588, 168067, 301082, 412197`.
- **31/38** are actual V1/run-16 Stage12 boundaries removed by v2. This includes `[in _Fig._ …]` continuations, `_Vacuum_ | we`, `Nor do I see but | that`, and `And whence is it | but from ... ?`.
- Exact planner-impact workflow `34651300446` is green; artifact `10284047829`, artifact SHA-256 `1833509238ae7d7ab4b79946aef8ac814bddedd4ffefc0f1da00e11886cda12a`, evidence SHA `aca590ef5fbaff3113ed52a664a607126e2d7ba3c0989525c889e692378a80f9`.
- Planner impact: V1 `3353` units → V2 `3325`; `79` V1-only geometries / `51` V2-only geometries; 31 run-16 translation boundaries removed; MT backend was not invoked in this classification run.
- Code/audit commit `d9b58f81de90d76add54798b41f12e5f29dea7ef` pins all 38 offsets in the corpus audit and adds generic markup/figure/conjunction/uppercase-negative regressions.
- Product Core workflow `34652530247` is green on that code: dependency-light **293 passed** Product Core + **213 passed, 1 skipped** Workbench; real-runtime Stage8→25 and unified source→25 both passed with pinned production assets.

Full exact run16 → Stage10-v2 → real OPUS + same default-OFF composed TC-big research stack replay is workflow `34652579262`. At this checkpoint its immutable run16 lineage, focused regressions, exact OPUS/TC-big assets and Torch-free runtime have passed; the full translation replay is still executing. Do not infer final counts until its persisted evidence exists.

## Durable guardrails

- Generic OPUS/TC-big whole-context fallback remains rejected.
- Mechanical integrity is necessary but not sufficient; semantic review remains mandatory.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches or evaluator weakening.
- Punctuation/numeric work remains defect-family-specific; a persisted improvement never authorizes a Product default by itself.

## Active next actions

1. Complete workflow `34652579262`; inspect persisted hard-gate counts, exact unchanged-geometry invariants, changed source/target rows, `whence` repair and SQLite identities.
2. Perform semantic review of every changed Stage12 geometry before treating v2 replay as a better research basis.
3. Classify the resulting residual inventory and continue only source-defined/general repairs toward zero hard failures.
4. After zero translation hard failures, run complete downstream learner-dictionary/export heavy acceptance, then Windows distribution validation.
