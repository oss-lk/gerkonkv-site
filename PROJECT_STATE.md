# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- Engineering/L3 checkpoint incorporated here: `4e9eaa2f68ebb4ff379e42fa35bceebb55c0b99c` (`Pin observed beam-6 boundary-pair rank0 evidence`).
- Maintained Product Core + Workbench remain the forward implementation. Authoritative contract: `rocketdict/PRODUCT_TARGET.md`.
- Final approved 90k+ evidence still requires **0 unresolved numeric/symbol, punctuation and length hard failures**, semantic acceptance and the complete learner/export path.
- Current best persisted research translation basis is run `17`: **20 numeric/symbol / 17 punctuation / 0 length, 36 unique failures** over `3343` rows.
- Product/default Stage10 is V1. Broad Stage10-v2 remains explicit research evidence only and is rejected for wholesale translation geometry because semantic regressions were observed.
- All TC-big rescue layers, including the new boundary-pair punctuation wrapper, remain default OFF/not public-wired and non-promoting.

## Recovery protocol

Follow `AGENTS.md`: compare HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; L3 source/tests/CI/artifacts outrank L1/L2.

## Maintained identities

- OPUS: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product Stage10/default: `structural-entity-term-discourse-pronoun-v1`, schema `rocketdict-product-stage10/1`. Research V2: `structural-entity-term-discourse-pronoun-v2`, schema `rocketdict-product-stage10/2`, policy `rocketdict-stage10-lowercase-continuation-coalescer/1`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`; numeric gate: `rocketdict-maintained-numeric-integrity/5`; emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0; offline asset manifest `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload tree `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`.

## Canonical full-Opticks evidence

Complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

Persisted progression: run `4` **30/34/5,64** → `7` **29/34/0,59** → `8` **25/33/0,55** → `9` **24/30/0,52** → `10` **24/25/0,47** → `11` **24/20/0,42** → `12` **23/19/0,41** → `13` **23/18/0,40** → `14` **22/18/0,39** → `15` **21/18/0,38** → `16` **20/18/0,37** → `17` **20/17/0,36**.

Run-17 persisted identities: workflow `34656818930`; artifact `10285447200`; artifact ZIP SHA-256 `339b71584f35f6981e1bcfa2dfcd391f98807d12f864ffae3070d6737356387d`; output SHA `f7c04209d9e8d7ffab673a2987b0024c334f24fee59736466597ea99125f7ff1`; SQLite SHA `2cbf20b39168003e494b2fb73c9b9baea427283def04a076a673e5023d7346a4`; evidence SHA `a5d786f4d25ee35917014aae7e435ad1f311c1ffb80744a3a60cacd4c62d6843`.

Run17 composes directly over exact run16 and applies one default-OFF `rocketdict-stage12-tc-big-boundary-pair-punctuation-rescue/1` replacement at source boundary `522572`. Two adjacent base rows become one raw TC-big rank0 row; **3342** other run16 rows remain source/target exact. Full source reconstruction is byte-exact; SQLite integrity is `ok`; FK violations `0`. The accepted candidate passes maintained strict/research/emphasis checks and diagnostic semantic anchors for relation/attractive power/water/salt/heat. Product promotion remains explicitly forbidden by the persisted evidence.

## Stage10/default verification

Low-level Stage10 default was realigned from V2 to V1 in commit `d438da03cbbd0882b34c3caea58a651a92058253`; migration workflow `34655882413` passed. V2 remains explicitly selectable.

The exact broad V2 census is **38** predicate matches; 7 are already absorbed by Stage12 protected spans and 31 change Stage12 geometry. Full replay workflow `34652579262` mechanically reached **20/16/0,36** with zero drift on 3264 unchanged geometries, but semantic regressions on changed clean contexts reject broad promotion.

## Boundary-pair punctuation rescue verification

Implementation commit `53c06e4308edc0fafff0f34b7979ff31c36d2590`. Trigger is generic/source-defined: two complete adjacent V1 rows, exact Stage10 contexts, independent Stage8/V2 false-boundary proof, existing punctuation-only hard failure, conservative source complexity. Product code contains no `whence`, corpus offset or expected Russian target selector.

Only raw TC-big rank0 is eligible; strict maintained checks, emphasis and source-relative completeness must pass. Any failure leaves both base rows unchanged. Wrapper is default OFF/not public-wired.

Product CI workflow `34656258155` passed `301` Product Core tests plus `213` Workbench tests (`1` skipped) and real-runtime Stage8→25/unified Product path. Terminal-head Product CI workflow `34656444553` also passed dependency-light and real-runtime jobs.

Corrected full replay workflow `34656818930` is green. The first replay intentionally failed closed when an audit fixture expected a beam-8 feasibility target but the implemented beam-6 rank0 differed; the selector/gates were not weakened. The persisted corrected beam-6 candidate preserves the source future tense (`will not distil` → `не будет ...`) and all maintained checks.

## Durable guardrails

- Generic OPUS/TC-big whole-context fallback remains rejected.
- Mechanical integrity is necessary but not sufficient; semantic review remains mandatory.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches or evaluator weakening.
- Punctuation/numeric work remains defect-family-specific; a persisted improvement never authorizes a Product default by itself.

## Active next actions

1. Rebuild the run17 residual census and cluster the remaining **17 punctuation** / **20 numeric** failures by source-owned defect family.
2. Search existing historical feasibility/audit evidence before introducing any new selector; avoid repeating rejected broad square-bracket/parenthesis approaches.
3. For the next candidate family, require source-defined triggering, raw-model candidates, exact unaffected-row/source invariants and a complete persisted *Opticks* replay.
4. Continue toward zero unresolved hard failures before downstream heavy learner/export and Windows release validation.
