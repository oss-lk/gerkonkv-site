# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- Engineering/L3 checkpoint incorporated here: `7015418ad91849338b7b8418e472bf1992a41b23` (`Run run19 bounded parenthesis-context DOE`).
- Maintained Product Core + Workbench remain the forward implementation. Authoritative contract: `rocketdict/PRODUCT_TARGET.md`.
- Final approved 90k+ evidence still requires **0 unresolved numeric/symbol, punctuation and length hard failures**, semantic acceptance and the complete learner/export path.
- Current best persisted research translation basis is run `19`: **20 numeric/symbol / 15 punctuation / 0 length, 34 unique failures** over `3342` rows.
- Product/default Stage10 is V1. Broad Stage10-v2 remains explicit research evidence only and is rejected for wholesale translation geometry because semantic regressions were observed.
- Rescue layers added in this research line remain default OFF/not public-wired and non-promoting.

## Recovery protocol

Follow `AGENTS.md`: compare HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; L3 source/tests/CI/artifacts outrank L1/L2.

## Maintained identities

- OPUS: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product Stage10/default: `structural-entity-term-discourse-pronoun-v1`, schema `rocketdict-product-stage10/1`. Research V2: `structural-entity-term-discourse-pronoun-v2`, schema `rocketdict-product-stage10/2`, policy `rocketdict-stage10-lowercase-continuation-coalescer/1`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`; numeric gate: `rocketdict-maintained-numeric-integrity/5`; emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0; offline asset manifest `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload tree `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`.

## Canonical full-Opticks evidence

Complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

Persisted progression: run `4` **30/34/5,64** → `7` **29/34/0,59** → `8` **25/33/0,55** → `9` **24/30/0,52** → `10` **24/25/0,47** → `11` **24/20/0,42** → `12` **23/19/0,41** → `13` **23/18/0,40** → `14` **22/18/0,39** → `15` **21/18/0,38** → `16` **20/18/0,37** → `17` **20/17/0,36** → `18` **20/16/0,35** → `19` **20/15/0,34**.

Run-19 persisted identities: workflow `34676310994`; artifact `10292442391`; artifact ZIP SHA-256 `51e00030d19799157d83db8a9dbc9093851da9be897619e465699b2cde72ef91`; output SHA `48096e0c1085c0598bc8abf212a2b2ba9a1109bb232fa2487c0472f35c06a1d9`; SQLite SHA `8519ea592b0bd948b68980ed19b710f05f20f9e0a60f0cb6c3e1a7763d5a8f76`; evidence SHA `ba6b24c0b4f628d908b5310aaf05268de2323033d7bbb629d081d755ddb8bf5f`.

Run19 composes directly over exact run18 with the default-OFF `rocketdict-stage12-question-mark-whole-context-rescue/1`. The trigger found two source-defined bounded split question contexts: `2462` (71 NLP tokens) and `2726` (157). Raw OPUS rank0 for `2462` was accepted and merged two current rows into one whole-context row; `2726` was rejected because Gutenberg emphasis preservation failed even though other mechanical checks were clean. The other **3341** run18 rows remain target-exact. Full source reconstruction is byte-exact; SQLite integrity is `ok`; FK violations `0`.

## Current verification

- Product CI `34676191351` is green for the bounded question-context wrapper: dependency-light plus real-runtime Stage8→25 and unified source→25 both completed successfully.
- Full run19 replay `34676310994` is green and persisted the identities above.
- Run18 capped-question DOE `34675824666` established that `2462` is clean for raw rank0 and `2726` must remain fail-closed; the production-style wrapper uses OPUS rank0 only.
- Run19 bounded parenthesis-context DOE `34676468786` is green/read-only. Four split Stage10 contexts under the 160-token cap were tested with OPUS and TC-big. Generic whole-context parenthesis fallback is rejected: TC-big rank0 is mechanically clean on `668/1393/1977` but loses material content in `1393` and `1977`; OPUS rank0 is mechanically admissible only on `1393`. OPUS higher-beam recovery on `1977` is research evidence only; n-best cherry-picking is not authorized.

## Durable guardrails

- Generic OPUS/TC-big whole-context or punctuation fallback remains rejected.
- Mechanical integrity is necessary but not sufficient; semantic review remains mandatory.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches, n-best cherry-picking or evaluator weakening.
- Punctuation/numeric work remains defect-family-specific; a persisted improvement never authorizes a Product default by itself.
- New selectors must be source-defined and fail closed; raw-model output remains immutable selection evidence.

## Active next actions

1. Decide whether the single OPUS-rank0 parenthesis success (`context 1393`) can be described by a generic source-owned trigger that does not accidentally include unsafe `668/1977/2969`; otherwise keep it research-only.
2. Rebuild the exact run19 residual census (**15 punctuation / 20 numeric**) after any accepted next layer and keep question-context `2726` and oversized `2730` fail-closed unless materially new evidence appears.
3. Treat the remaining square-bracket cases separately: `54796` is unsplit + numeric debt, `301051` is already a grouped unit, and only `[G]` at `112541` is plausibly a bounded split-context geometry case.
4. Continue toward zero unresolved hard failures before downstream heavy learner/export and Windows release validation.
