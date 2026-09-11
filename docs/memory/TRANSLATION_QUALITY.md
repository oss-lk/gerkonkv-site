# RocketDict maintained translation quality — L2

Durable translation-quality conclusions only. This is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). L3 source/tests/CI/artifacts outrank this file.

## Maintained contracts

- Production MT: pinned OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Stage10 default: `structural-entity-term-discourse-pronoun-v2`, schema `rocketdict-product-stage10/2`, policy `rocketdict-stage10-lowercase-continuation-coalescer/1`; raw Stage8 spaCy assignments remain immutable evidence.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`; Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1` rescue veto.
- Independent TC-big comparator/rescue: `Helsinki-NLP/opus-mt-tc-big-en-zle` revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0, offline/Torch-free CTranslate2 asset.
- Narrow TC-big wrappers remain default OFF/not public-wired: target-delimiter, footnote-reference lead, figure-reference lead, semicolon→question substitution, target-only equals addition, angular-minute prime and short angular DMS.

## Canonical complete Opticks basis

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` chars.

Persisted progression: run `4` **30/34/5,64** → `7` **29/34/0,59** → `8` **25/33/0,55** → `9` **24/30/0,52** → `10` **24/25/0,47** → `11` **24/20/0,42** → `12` **23/19/0,41** → `13` **23/18/0,40** → `14` **22/18/0,39** → `15` **21/18/0,38** → run `16` **20/18/0,37**.

Until the active Stage10-v2 full replay is persisted and semantically reviewed, run `16` remains the best translation basis: workflow `34645769684`, artifact `10282227627`, output SHA `767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783`, SQLite SHA `573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11`, evidence SHA `86c865cef5a0081fd77aa8ad78c525ebb38a01e6f279cc560aea56bb84d4e37d`.

## Stage10 source-boundary correction

False spaCy sentence splits proven by immutable source structure belong upstream in Stage10, not in phrase-specific MT patches. V2 merges only consecutive parser sentences with whitespace-only contiguous source geometry, no paragraph break, no terminal `.?!` on the left after closers, and a lowercase first lexical character on the right. It records original spaCy indices and every removed boundary; V1 remains explicitly selectable.

The earlier durable-memory assertion that the full corpus contained exactly five candidates was incorrect. Exact run-16/Stage8 L3 census now establishes **38** raw matching boundaries. Manual source/context review found all 38 source-continuous; examples include markup splits (`_q_`, `[Greek:a]`, `_viz._`), `[in _Fig._ N.]` continuations, `and | these`, `Nor do I see but | that`, `_Vacuum_ | we`, and `And whence is it | but from ... ?`.

Seven offsets (`18355, 64046, 155895, 166588, 168067, 301082, 412197`) were already coalesced by Stage12 protected-span behavior and do not alter Stage12 translation geometry. The other **31** are V1/run-16 Stage12 boundaries eliminated by v2.

Planner-impact evidence is green: workflow `34651300446`, artifact `10284047829`, artifact SHA `1833509238ae7d7ab4b79946aef8ac814bddedd4ffefc0f1da00e11886cda12a`, evidence SHA `aca590ef5fbaff3113ed52a664a607126e2d7ba3c0989525c889e692378a80f9`. It proves `3353 → 3325` Stage12 planned units, `79` V1-only and `51` V2-only geometries, with all 31 run-16 translation boundaries absent under v2; this run deliberately did not invoke MT.

Corpus audit commit `d9b58f81de90d76add54798b41f12e5f29dea7ef` pins the exact 38 offsets and extends generic regressions for figure-reference markup, Gutenberg emphasis/Greek markup, lowercase conjunction continuation and an uppercase lexical negative case. Product Core workflow `34652530247` is green: **293** Product Core tests, **213 passed + 1 skipped** Workbench tests, and real maintained Stage8→25 plus unified source→25 runtime paths.

Exact full translation replay workflow `34652579262` starts from immutable run16 DB, regenerates Stage10 v2 and real OPUS Stage12, then composes the same default-OFF research rescue stack. It requires byte-exact source coverage, no target drift on identical source geometry, non-regressing hard gates, repaired `whence` punctuation, SQLite integrity and unsafe flags false. Final counts and semantic conclusions are not durable until the workflow artifact is complete and reviewed.

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
