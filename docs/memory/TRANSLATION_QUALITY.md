# RocketDict maintained translation quality — L2

Durable translation-quality conclusions only. This is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). L3 source/tests/CI/artifacts outrank this file.

## Maintained contracts

- Production MT: pinned OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product Stage10 translation geometry remains V1 unless an explicit research implementation is requested. Research V2 is `structural-entity-term-discourse-pronoun-v2`, schema `rocketdict-product-stage10/2`, policy `rocketdict-stage10-lowercase-continuation-coalescer/1`; raw Stage8 spaCy assignments remain immutable evidence.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`; Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- Independent TC-big comparator/rescue: `Helsinki-NLP/opus-mt-tc-big-en-zle` revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0, offline/Torch-free CTranslate2 asset.
- Narrow TC-big wrappers remain default OFF/not public-wired.

## Canonical complete Opticks basis

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` chars.

Persisted progression: run `4` **30/34/5,64** → `7` **29/34/0,59** → `8` **25/33/0,55** → `9` **24/30/0,52** → `10` **24/25/0,47** → `11` **24/20/0,42** → `12` **23/19/0,41** → `13` **23/18/0,40** → `14` **22/18/0,39** → `15` **21/18/0,38** → run `16` **20/18/0,37**.

Run `16` remains the best accepted research translation basis: workflow `34645769684`, artifact `10282227627`, output SHA `767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783`, SQLite SHA `573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11`, evidence SHA `86c865cef5a0081fd77aa8ad78c525ebb38a01e6f279cc560aea56bb84d4e37d`.

## Stage10 source-boundary research

Exact immutable run-16 Stage8 census establishes **38** V2 predicate matches. Seven offsets are already absorbed by Stage12 protected-span behavior; **31** remove actual run16 Stage12 boundaries.

Planner-impact workflow `34651300446` proves V1 `3353` → V2 `3325` planned units and removes all 31 affected plan boundaries without invoking MT.

Full exact real-MT replay workflow `34652579262` is green and persisted. Artifact `10284303389` has ZIP SHA-256 `7a477da19dbfea4e36c4f8c928e9c6e0b58213293aca0ec482e29c2d4f939db5`; evidence SHA `fdd823883fd5c9c89d13509915fca04dc9923a82247d321744f4dbe4edfe2f21`; replay SQLite SHA `ac4d438b63c8f008dd8331cc052e3daf9cd8343efe2fd78098dc8900d8a0dc00`; replay output SHA `fb893afbd0e6336e405874c29dd97236209f00d77d6c069248b9ef6c66504d48`.

Mechanical result is **20/18/0,37 → 20/16/0,36**, with `3264` unchanged source geometries and zero target drift. The aggregate numeric count hides a moved failure: `54796` is repaired but a new numeric failure appears at `204041`.

Semantic review rejects broad V2 translation promotion. Representative regressions on previously clean geometry include loss of `HEFK`, loss of `_in vacuo_`, and duplicated/garbled technical content. Therefore source-boundary correctness alone does not license wholesale MT resegmentation.

## Hard-pair real-MT feasibility

Workflow `34654758870`, artifact `10285163599`, ZIP SHA-256 `6b422e41e9978547b8a1d5dbf3ab49ac169d1ec10941ae1a8561e8474cfa9f99`, evidence SHA `4296e96dbf280678645927bc073d2cf1e139e387ef061447f6efcb43d1f4525a`.

The source-defined cohort is exactly three already-hard-failing adjacent run16 pairs whose boundary is independently proven by Stage10-v2: offsets `54796`, `112001`, `522572`.

- `54796`: OPUS can satisfy mechanical gates but fails technical/semantic diagnostics; TC-big has no safe selected candidate. Do not replace.
- `112001`: no mechanically admissible OPUS or TC-big candidate. Do not replace.
- `522572`: TC-big ranks `0..5` are mechanically admissible and satisfy the diagnostic anchors; this is the only current candidate family suitable for a deterministic default-OFF wrapper experiment.
- The feasibility artifact explicitly forbids automatic candidate selection/Product promotion.

## Earlier rescue evidence still binding

- run `10`: target-delimiter, **24/30/0,52 → 24/25/0,47**;
- run `11`: footnote-reference leads, **24/25/0,47 → 24/20/0,42**;
- run `12`: leading figure reference, **24/20/0,42 → 23/19/0,41**;
- run `13`: semicolon→question migration, **23/19/0,41 → 23/18/0,40**;
- run `14`: target-only equals addition, **23/18/0,40 → 22/18/0,39**;
- run `15`: angular-minute prime, **22/18/0,39 → 21/18/0,38**;
- run `16`: short DMS over run15, **21/18/0,38 → 20/18/0,37**.

Persisted success is research evidence, not automatic Product-default authorization.

## Rejected/exhausted directions

- Broad Stage10-v2 translation geometry: rejected for Product/default use because full semantic review found regressions despite improved hard-gate counts.
- Generic OPUS/TC-big whole-context fallback: rejected; mechanically clean alternatives can lose semantics.
- Broad context `2725`/`2730`: unsafe.
- Broad square-bracket-loss OPUS formulation: no admissible safe cohort.
- Generic prime normalization/decomposition: rejected; only source-defined narrow classes may proceed.
- Thousands grouping, narrow `x→×`, compact-formula spacing and broad citation/group coalescing remain rejected/ineffective absent materially new evidence.
- Never use target literal injection, corpus-specific target patches, placeholders, source rewriting, target surgery or evaluator weakening.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Preserve immutable source/model/config/result identities.
3. Select only unmodified raw model candidates; no target surgery.
4. Mechanical integrity is necessary but insufficient; semantic/boundary-aware review is mandatory.
5. A second MT may be invoked only by a narrow existing-hard-failure/source-defined trigger; clean Product rows remain untouched unless separately justified.
6. Exact replacement geometry must be representable by complete current rows; otherwise skip fail-closed.
7. MetricX/QE is ranking evidence only.
8. Alternative-MT completeness checks are source-relative; corrupt baseline verbosity is not a universal floor.
9. TC-big Product use requires deterministic selection, persisted full-corpus regression, exact untouched/source checks, offline identities, license attribution and release-size/performance assessment.
10. Final approved heavy evidence requires zero unresolved hard failures.
