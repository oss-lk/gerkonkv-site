# RocketDict maintained translation quality — L2

This file stores durable conclusions from maintained Product translation-quality work. It is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Source/tests/CI/artifacts are L3 authority and outrank this summary if they disagree.

## Maintained contracts

- Production baseline MT: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`; bare Roman sentence fragments are not headings.
- Numeric/symbol hard gate: `rocketdict-maintained-numeric-integrity/5` over every selected Stage12 row.
- Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`, a rescue veto rather than a Product hard gate.
- Independent MT: pinned `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0.
- Optional TC-big asset: `rocketdict-tc-big-en-ru-asset/1`; manifest SHA `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload-tree SHA `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`, 11 files / 968529922 bytes. Inference is offline and Torch-free.
- Narrow TC-big wrappers remain default OFF/not public-wired: target-delimiter, footnote-reference lead, figure-reference lead, semicolon→question substitution, target-only equals addition, angular-minute prime and short angular DMS.

## Canonical contiguous Opticks evidence

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` source characters, `3344` Stage12 rows.

Persisted research progression:
- run `4`: **30 numeric / 34 punctuation / 5 length**, 64 unique;
- run `7`: **29/34/0**, 59 unique;
- run `8`: **25/33/0**, 55 unique;
- run `9`: **24/30/0**, 52 unique;
- run `10`: **24/25/0**, 47 unique;
- run `11`: **24/20/0**, 42 unique;
- run `12`: **23/19/0**, 41 unique;
- run `13`: **23/18/0**, 40 unique;
- run `14`: **22/18/0**, 39 unique;
- run `15`: **21/18/0**, 38 unique;
- run `16`: **20/18/0**, 37 unique.

## Current best persisted research basis: run 16

Composed angular-minute + short-DMS workflow `34645769684` is green; artifact `10282227627`; artifact ZIP SHA-256 `92b2ad3fa98af1d12c27eeb4ee749071d5152464b34c4ac1f3bf40ed7cc02e14`.

- exact base is run `14` (`12e1fe77ab8df3959b4bb9265292cdc5b9db279797d94e2f15df6482429e2c44`, DB `dfce68a8f7cae08b90380630ae29e31418b4d6e8987d3e7001fe72fa1d781304`);
- angular intermediate run `15` output SHA `0e0ebb851e43079b3029a2a2638d0dc0ff5eb45bebd6c91895cb04483349fb45`;
- final run `16` output SHA `767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783`;
- persisted run-16 SQLite SHA `573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11`;
- audit evidence SHA `86c865cef5a0081fd77aa8ad78c525ebb38a01e6f279cc560aea56bb84d4e37d`;
- gates compose as **22/18/0,39 → 21/18/0,38 → 20/18/0,37 unique**;
- angular layer changes only source start `431358` to raw rank0 `В то же время появляется гало на расстоянии около 22 градусов 35' от центра Луны.`;
- DMS layer changes only source start `110881` to raw rank2 `Откуда этот угол 2 град. 0'. 7''.` and preserves all other 3343 rows exactly relative to run `15`;
- byte-exact source coverage, SQLite `integrity_check=ok`, 0 foreign-key violations;
- angular + DMS unit regressions **14/14 passed**;
- no source/target rewriting, placeholders, literal injection, corpus-specific target patching or evaluator weakening;
- evidence explicitly keeps promotion/default/public wiring false.

### Why the short-DMS selector is evidence-backed

The run-14 residual is `Whence this Angle is 2 deg. 0'. 7''. ` → `Откуда угол 2 градуса. 0 футов 7 футов.`: the MT system interprets angular prime notation as feet.

Read-only workflow `34645335141` generated six raw TC-big hypotheses on the immutable run-14 DB. Only rank `2` passes both maintained strict mechanics and the DMS semantic selector:
- rank0 collapses seconds `7''` to `7'`;
- rank1 also leaves English `deg.` and collapses seconds;
- rank2 is `Откуда этот угол 2 град. 0'. 7''.` and passes both classes;
- rank3 preserves prime mechanics but leaves English `deg.`;
- rank4 leaves `дег.` and collapses seconds;
- rank5 has angle/degree semantics but turns minute `0'` into `0''`.

This separation is important: a mechanical-only or semantic-only selector would have admitted known bad outputs. The trigger remains narrow: exact single Stage10 row, exactly one `D deg. M'. S''` expression, source word `Angle`, <=12 alphabetic words, existing hard failure and broken prime signature. Longer `Chord` context is deliberately excluded because symbol preservation alone cannot establish technical semantic correctness.

## Earlier persisted rescue evidence still binding

- run `10`: target-only delimiter hallucination, **24/30/0,52 → 24/25/0,47**;
- run `11`: footnote-reference leads, **24/25/0,47 → 24/20/0,42**;
- run `12`: leading figure reference, **24/20/0,42 → 23/19/0,41**;
- run `13`: semicolon→question migration, **23/19/0,41 → 23/18/0,40**;
- run `14`: target-only equals addition, **23/18/0,40 → 22/18/0,39**;
- run `15`: single angular-minute prime, **22/18/0,39 → 21/18/0,38**;
- run `16`: short DMS composed over run15, **21/18/0,38 → 20/18/0,37**.

Persisted success is research evidence, not automatic Product-default authorization.

## Boundary/context frontier

Read-only workflow `34644023517` showed that the exact pair `And whence is it | but from ... ?` yields six strict + semantic TC-big hypotheses when translated as one contiguous source span. L3 then located the deeper cause: the immutable source has no terminal punctuation at the split, but Stage8 assigns separate spaCy sentence indices and Stage10 preserves that false boundary. The run-16 punctuation residual is therefore partly an upstream sentence-segmentation problem, not merely a translation-model problem.

A complete Stage10 census of `previous fragment lacks terminal sentence punctuation` plus `next fragment starts lowercase` yields exactly five boundaries. Full immutable-source and token review confirms **all five are genuine false spaCy sentence splits**, including the superficially structural `_ B | any where...` boundary, which is actually one sentence: `Line C _prt_ B any where between the Ends...`.

`run_stage10` currently groups directly by spaCy `sentence_index`. Therefore the next evidence-backed engineering step is a generic fail-closed Stage10 coalescer, not a phrase-specific `Whence` rescue. The coalescer must merge only contiguous adjacent parser sentences when the left side has no actual sentence-terminal punctuation, the right side begins with lowercase lexical continuation, and the gap does not cross a paragraph boundary. Raw Stage8 spaCy evidence should remain unchanged; Stage10 must expose merge provenance. Because current caching keys include the implementation name, changed behavior also requires a Stage10 implementation/schema contract bump so old cached run2 cannot masquerade as repaired output.

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
