# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- Engineering/L3 checkpoint incorporated here: `0466af269af143204ab78f5bd97bcffdf1052588` (`Run full Opticks orphan-parenthesis rescue replay`).
- Maintained Product Core + Workbench remain the forward implementation. Authoritative contract: `rocketdict/PRODUCT_TARGET.md`.
- Final approved 90k+ evidence still requires **0 unresolved numeric/symbol, punctuation and length hard failures**, semantic acceptance and the complete learner/export path.
- Current best persisted research translation basis is run `18`: **20 numeric/symbol / 16 punctuation / 0 length, 35 unique failures** over `3343` rows.
- Product/default Stage10 is V1. Broad Stage10-v2 remains explicit research evidence only and is rejected for wholesale translation geometry because semantic regressions were observed.
- All TC-big rescue layers, including boundary-pair and orphan-closing-parenthesis wrappers, remain default OFF/not public-wired and non-promoting.

## Recovery protocol

Follow `AGENTS.md`: compare HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; L3 source/tests/CI/artifacts outrank L1/L2.

## Maintained identities

- OPUS: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product Stage10/default: `structural-entity-term-discourse-pronoun-v1`, schema `rocketdict-product-stage10/1`. Research V2: `structural-entity-term-discourse-pronoun-v2`, schema `rocketdict-product-stage10/2`, policy `rocketdict-stage10-lowercase-continuation-coalescer/1`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`; numeric gate: `rocketdict-maintained-numeric-integrity/5`; emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0; offline asset manifest `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload tree `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`.

## Canonical full-Opticks evidence

Complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

Persisted progression: run `4` **30/34/5,64** → `7` **29/34/0,59** → `8` **25/33/0,55** → `9` **24/30/0,52** → `10` **24/25/0,47** → `11` **24/20/0,42** → `12` **23/19/0,41** → `13` **23/18/0,40** → `14` **22/18/0,39** → `15` **21/18/0,38** → `16` **20/18/0,37** → `17` **20/17/0,36** → `18` **20/16/0,35**.

Run-18 persisted identities: workflow `34675224977`; artifact `10292311024`; artifact ZIP SHA-256 `ae4a32221985aaff2842a87bf9548698d8e76b33815633ddb67100b8fc9dea1d`; output SHA `666e8a2cae0bb6ff6f25b95475c2335ee5e3c98f7f2d6ab7deb9be92295be290`; SQLite SHA `803a2cbccb287ad0fadf4b14d932e1e33ebafef2ec5406619b0caf0898525143`; evidence SHA `61ddb44ceed56d0acb552a5cddecac1543e679c35ad450c41270136c5e014733`.

Run18 composes directly over exact run17 and applies one default-OFF `rocketdict-stage12-tc-big-orphan-closing-parenthesis-rescue/1` replacement at source start `417917`. The source has no round parentheses while the run17 target had exactly one orphan closing `)`; raw TC-big rank0 removes that target-only delimiter debt while preserving numeric/symbol integrity and strict research diagnostics. The other **3342** run17 rows remain source/target exact. Full source reconstruction is byte-exact; SQLite integrity is `ok`; FK violations `0`. Persisted evidence still requires manual semantic review before any Product promotion.

## Current verification

- Product CI workflow `34675206945` is green: dependency-light plus real-runtime Stage8→25 and unified source→25 both completed successfully after the orphan-parenthesis implementation/replay audit landed.
- Full run18 replay workflow `34675224977` is green and persisted the identities above.
- The preceding run17-wide TC-big punctuation n-best DOE `34674771224` was intentionally read-only. It found mechanically clean rank0 candidates for multiple residual rows, but semantic review exposed false positives (including meaning loss/garbling), so **generic TC-big punctuation fallback is rejected**. Only source-defined narrow defect families may proceed.

## Stage10/default verification

Product/default Stage10 remains V1. Research V2 has 38 source-predicate matches; 7 are already absorbed by protected Stage12 behavior and 31 change Stage12 geometry. Broad V2 full replay mechanically improved punctuation but semantic regressions reject wholesale promotion.

## Durable guardrails

- Generic OPUS/TC-big whole-context or punctuation fallback remains rejected.
- Mechanical integrity is necessary but not sufficient; semantic review remains mandatory.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches or evaluator weakening.
- Punctuation/numeric work remains defect-family-specific; a persisted improvement never authorizes a Product default by itself.
- New selectors must be source-defined and fail closed; raw-model output remains immutable selection evidence.

## Active next actions

1. Rebuild the exact run18 residual census (**16 punctuation / 20 numeric**) and cluster by source-owned defect family.
2. Reuse the run17 punctuation n-best DOE only as candidate evidence; do not promote its broad mechanically-clean cohort.
3. Search historical feasibility/audit evidence for the remaining question-migration, parenthesis-loss and square-bracket families before introducing another selector.
4. For any next candidate family, require source-defined triggering, raw-model candidates, exact unaffected-row/source invariants, semantic review and a complete persisted *Opticks* replay.
5. Continue toward zero unresolved hard failures before downstream heavy learner/export and Windows release validation.
