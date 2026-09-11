# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- Engineering/L3 checkpoint incorporated here: `1947e5518b0a284c6504cf6d55848a842593073d` (`Run Stage10 v2 hard-pair real-MT feasibility`).
- Maintained Product Core + Workbench remain the forward implementation. Authoritative contract: `rocketdict/PRODUCT_TARGET.md`.
- Final approved 90k+ evidence still requires **0 unresolved numeric/symbol, punctuation and length hard failures**, semantic acceptance and the complete learner/export path.
- Current best persisted translation basis remains run `16`: **20 numeric/symbol / 18 punctuation / 0 length, 37 unique failures** over `3344` rows.
- The broad Stage10-v2 translation replay is completed but **rejected for promotion** despite better mechanical counts because semantic regressions were found.
- All narrow TC-big rescue layers remain default OFF/not public-wired and non-promoting.

## Recovery protocol

Follow `AGENTS.md`: compare HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; L3 source/tests/CI/artifacts outrank L1/L2.

## Maintained identities

- OPUS: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product Stage10 must remain V1 translation geometry unless explicitly selecting the research V2 implementation. Research V2: `structural-entity-term-discourse-pronoun-v2`, schema `rocketdict-product-stage10/2`, policy `rocketdict-stage10-lowercase-continuation-coalescer/1`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`; numeric gate: `rocketdict-maintained-numeric-integrity/5`; emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0; offline asset manifest `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload tree `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`.

## Canonical full-Opticks evidence

Complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

Persisted progression: run `4` **30/34/5,64** → `7` **29/34/0,59** → `8` **25/33/0,55** → `9` **24/30/0,52** → `10` **24/25/0,47** → `11` **24/20/0,42** → `12` **23/19/0,41** → `13` **23/18/0,40** → `14` **22/18/0,39** → `15` **21/18/0,38** → `16` **20/18/0,37**.

Run-16 identities: workflow `34645769684`; artifact `10282227627`; artifact SHA-256 `92b2ad3fa98af1d12c27eeb4ee749071d5152464b34c4ac1f3bf40ed7cc02e14`; output SHA `767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783`; SQLite SHA `573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11`; evidence SHA `86c865cef5a0081fd77aa8ad78c525ebb38a01e6f279cc560aea56bb84d4e37d`.

## Stage10-v2 full replay conclusion

Immutable run-16 Stage8 evidence proves **38** raw spaCy boundaries satisfy the V2 source predicate; 7 are already absorbed by Stage12 protected-span planning and 31 change Stage12 geometry.

The exact full replay workflow `34652579262` is green. Artifact `10284303389`, ZIP SHA-256 `7a477da19dbfea4e36c4f8c928e9c6e0b58213293aca0ec482e29c2d4f939db5`; evidence SHA `fdd823883fd5c9c89d13509915fca04dc9923a82247d321744f4dbe4edfe2f21`; replay SQLite SHA `ac4d438b63c8f008dd8331cc052e3daf9cd8343efe2fd78098dc8900d8a0dc00`; replay output SHA `fb893afbd0e6336e405874c29dd97236209f00d77d6c069248b9ef6c66504d48`.

Mechanical result: run16 **20/18/0,37 → 20/16/0,36**; `3264` unchanged source geometries have **0 target drift**; SQLite integrity is `ok` with `0` FK violations. `whence` punctuation and the `[Fig.16]` failure are mechanically repaired, but a numeric failure moves to source start `204041`.

Semantic review rejects broad V2 promotion: changed clean geometries include material regressions such as loss of `HEFK`, loss of `_in vacuo_`, and duplicated/garbled technical content. Therefore broad V2 is research evidence only, not Product/default translation geometry.

## Hard-pair feasibility conclusion

Read-only real-MT feasibility workflow `34654758870` is green on HEAD `1947e551...`; artifact `10285163599`, ZIP SHA-256 `6b422e41e9978547b8a1d5dbf3ab49ac169d1ec10941ae1a8561e8474cfa9f99`, evidence SHA `4296e96dbf280678645927bc073d2cf1e139e387ef061447f6efcb43d1f4525a`.

Cohort is source-defined: exact Stage10-v2 boundary + adjacent complete run16 Stage12 rows + existing Product hard failure. Three boundaries qualify: `54796`, `112001`, `522572`.

- `54796`: OPUS has mechanically admissible hypotheses but semantic/technical diagnostics reject them; TC-big does not yield a safe candidate. Leave unchanged.
- `112001`: neither OPUS nor TC-big yields a mechanically admissible candidate. Leave unchanged.
- `522572` (`And whence is it | but from ...`): TC-big ranks `0..5` pass maintained mechanical checks and diagnostic anchors; rank0 is the intended deterministic research candidate for the next wrapper.
- No automatic candidate selection or Product/default promotion is authorized by the feasibility artifact itself.

## Durable guardrails

- Generic OPUS/TC-big whole-context fallback remains rejected.
- Mechanical integrity is necessary but not sufficient; semantic review remains mandatory.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches or evaluator weakening.
- Punctuation/numeric work remains defect-family-specific; a persisted improvement never authorizes a Product default by itself.

## Active next actions

1. Make low-level Stage10 default consistent with Product Profile: V1 by default; V2 explicit research implementation only.
2. Add a default-OFF source-defined TC-big boundary-pair rescue using exact adjacent V1 Stage12 rows and the independent Stage10-v2 predicate; fail closed unless TC-big rank0 passes all maintained checks and conservative semantic-independent completeness constraints.
3. Add unit/regression tests proving clean rows and non-qualifying pairs remain byte/target exact.
4. Run Product Core + Workbench CI and real-runtime gates.
5. Run a full persisted *Opticks* replay over run16. Expected research direction is removal of the `whence` punctuation failure without changing other source geometry; do not claim **20/17/0,36** until the persisted replay proves it.
