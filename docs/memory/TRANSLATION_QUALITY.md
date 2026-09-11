# RocketDict maintained translation quality — L2

This file stores durable conclusions from maintained Product translation-quality work. It is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Source/tests/CI/artifacts are L3 authority and outrank this summary if they disagree.

## Maintained contracts

- Production baseline MT: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Stage10 context default: `structural-entity-term-discourse-pronoun-v2`, schema `rocketdict-product-stage10/2`, source-boundary policy `rocketdict-stage10-lowercase-continuation-coalescer/1`. Raw Stage8 spaCy assignments are retained as evidence.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`; bare Roman sentence fragments are not headings.
- Numeric/symbol hard gate: `rocketdict-maintained-numeric-integrity/5` over every selected Stage12 row.
- Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`, a rescue veto rather than a Product hard gate.
- Independent MT: pinned `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0.
- Optional TC-big asset: `rocketdict-tc-big-en-ru-asset/1`; manifest SHA `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload-tree SHA `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`, 11 files / 968529922 bytes. Inference is offline and Torch-free.
- Narrow TC-big wrappers remain default OFF/not public-wired: target-delimiter, footnote-reference lead, figure-reference lead, semicolon→question substitution, target-only equals addition, angular-minute prime and short angular DMS.

## Canonical contiguous Opticks evidence

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` source characters, `3344` Stage12 rows in the current run-16 basis.

Persisted research progression: run `4` **30/34/5,64** → `7` **29/34/0,59** → `8` **25/33/0,55** → `9` **24/30/0,52** → `10` **24/25/0,47** → `11` **24/20/0,42** → `12` **23/19/0,41** → `13` **23/18/0,40** → `14` **22/18/0,39** → `15` **21/18/0,38** → `16` **20/18/0,37**.

## Current best persisted research basis: run 16

Composed angular-minute + short-DMS workflow `34645769684` is green; artifact `10282227627`; artifact ZIP SHA-256 `92b2ad3fa98af1d12c27eeb4ee749071d5152464b34c4ac1f3bf40ed7cc02e14`.

- exact base run `14`; angular intermediate run `15`; final run `16` output SHA `767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783`;
- persisted run-16 SQLite SHA `573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11`; audit evidence SHA `86c865cef5a0081fd77aa8ad78c525ebb38a01e6f279cc560aea56bb84d4e37d`;
- gates compose as **22/18/0,39 → 21/18/0,38 → 20/18/0,37 unique**;
- angular layer changes only source start `431358`; DMS layer changes only source start `110881` to raw TC-big rank2 `Откуда этот угол 2 град. 0'. 7''.`;
- byte-exact source coverage, SQLite `integrity_check=ok`, 0 foreign-key violations, angular+DMS unit regressions **14/14**;
- no source/target rewriting, placeholders, literal injection, corpus-specific target patching or evaluator weakening; promotion/default/public wiring remains false.

## Stage10 boundary repair

The run-16 punctuation residual `And whence is it | but from ... ?` exposed an upstream false spaCy split: immutable source has no terminal punctuation at the boundary. A complete census found exactly five boundaries matching `left has no terminal sentence punctuation + right starts lowercase`; source/token review established all five as genuine false parser splits, including `_ B | any where...` inside one sentence.

This is now implemented generically at Stage10. Default implementation `structural-entity-term-discourse-pronoun-v2` coalesces only consecutive parser sentences when source geometry is contiguous through whitespace, the gap has no paragraph break, the source before the boundary has no terminal `.?!` after closers, and the next lexical character is lowercase. Every merge persists its source offset/reason and original spaCy sentence indices. V1 remains an explicit compatibility implementation; changed default/cache identity and schema prevent old V1 cached output from masquerading as repaired V2 output.

Integration commit `b97825c5cbf1b1fab7f35133feca3f76cdd4b456` passed a dedicated **12/12** Stage10 regression suite before commit. Terminal HEAD `4564f383cc2b964fbecd15d1f214619cc52ef5c5` then passed ordinary Product Core workflow `34648989553` in both dependency-light and real-runtime jobs; the real-runtime path exercised maintained Stage8→25 and unified source→25 with pinned production NLP, real OPUS and CEFR-J. This closes the downstream smoke-regression debt. No new full-corpus counts are claimed from that smoke run: the next evidence task is exact complete-*Opticks* Stage10-v1↔v2 replay from immutable run-16/Stage8 evidence, comparing the five boundary changes, unchanged source geometry/targets, hard gates and semantic evidence.

## Earlier persisted rescue evidence still binding

- run `10`: target-only delimiter hallucination, **24/30/0,52 → 24/25/0,47**;
- run `11`: footnote-reference leads, **24/25/0,47 → 24/20/0,42**;
- run `12`: leading figure reference, **24/20/0,42 → 23/19/0,41**;
- run `13`: semicolon→question migration, **23/19/0,41 → 23/18/0,40**;
- run `14`: target-only equals addition, **23/18/0,40 → 22/18/0,39**;
- run `15`: single angular-minute prime, **22/18/0,39 → 21/18/0,38**;
- run `16`: short DMS composed over run15, **21/18/0,38 → 20/18/0,37**.

Persisted success is research evidence, not automatic Product-default authorization.

## Exhausted / rejected branches still binding

- Generic OPUS/TC-big whole-context fallback: rejected; mechanically clean candidates can hide semantic loss.
- Broad context `2725`/`2730` formulations: unsafe.
- Broad square-bracket-loss OPUS formulation: no admissible safe cohort.
- Generic prime decomposition/normalization: rejected; only source-defined narrow prime/DMS classes may proceed.
- Thousands grouping, narrow `x→×`, compact-formula spacing and broad citation/group coalescing remain rejected/ineffective absent materially new evidence.
- Never use target literal injection, corpus-specific target patching, placeholders, source rewriting, target surgery or evaluator weakening.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Preserve immutable source/model/config/result identities.
3. Select only unmodified raw model candidates; no target surgery.
4. Mechanical integrity is necessary but not sufficient; semantic and boundary-aware review is mandatory.
5. A second MT may be invoked only by a narrow existing-hard-failure/source-defined trigger; clean Product rows remain untouched unless separately justified.
6. Exact replacement geometry must be representable by complete current rows; otherwise skip fail-closed.
7. MetricX/QE is ranking evidence only.
8. Alternative-MT completeness checks are source-relative; corrupt baseline verbosity is not a universal floor.
9. Any TC-big Product role requires deterministic selection, persisted full-corpus regression, exact untouched/source checks, offline asset identities, license attribution and release-size/performance assessment.
10. Persisted success does not itself authorize Product-default promotion; current TC-big wrappers remain default OFF/not public-wired.
11. Final approved heavy evidence still requires zero unresolved hard failures.
