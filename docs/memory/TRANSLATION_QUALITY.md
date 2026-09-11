# RocketDict maintained translation quality — L2

This file stores durable conclusions from maintained Product translation-quality work. It is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Source/tests/CI/artifacts are L3 authority and outrank this summary if they disagree.

## Maintained contracts

- Production baseline MT: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`; bare Roman sentence fragments are not headings.
- Block section identifier: `rocketdict-stage12-block-section-identifier/1`.
- Numeric/symbol hard gate: `rocketdict-maintained-numeric-integrity/5` over every selected Stage12 row.
- Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`, a rescue veto rather than a Product hard gate.
- Independent MT: pinned `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, `model.safetensors` SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0.
- Optional TC-big asset: `rocketdict-tc-big-en-ru-asset/1`; manifest SHA `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload-tree SHA `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`, 11 files / 968529922 bytes. Inference is offline and Torch-free.
- Narrow TC-big wrappers remain default OFF/not public-wired unless explicitly stated otherwise:
  - target-delimiter `rocketdict-stage12-tc-big-target-delimiter-context-rescue/1`;
  - footnote-reference lead `rocketdict-stage12-tc-big-footnote-reference-lead-rescue/1`;
  - figure-reference lead `rocketdict-stage12-tc-big-figure-reference-lead-rescue/1`;
  - semicolon→question substitution `rocketdict-stage12-tc-big-semicolon-question-substitution-rescue/1`;
  - target-only equals addition `rocketdict-stage12-tc-big-target-only-equals-addition-rescue/1`;
  - angular-minute prime `rocketdict-stage12-tc-big-angular-minute-prime-rescue/1`;
  - short angular DMS `rocketdict-stage12-tc-big-short-angular-dms-rescue/1`.

## Canonical contiguous Opticks evidence

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` source characters, `3344` Stage12 rows.

Persisted progression through the current accepted research basis:
- run `4`: **30 numeric / 34 punctuation / 5 length**, 64 unique;
- run `7`: **29/34/0**, 59 unique;
- run `8`: **25/33/0**, 55 unique;
- run `9`: **24/30/0**, 52 unique;
- run `10`: **24/25/0**, 47 unique;
- run `11`: **24/20/0**, 42 unique;
- run `12`: **23/19/0**, 41 unique;
- run `13`: **23/18/0**, 40 unique;
- run `14`: **22/18/0**, 39 unique.

### Current persisted residual basis: run 14

Heavy workflow `34643230375` is green; artifact `10280349240`.

- run `14` output SHA `12e1fe77ab8df3959b4bb9265292cdc5b9db279797d94e2f15df6482429e2c44`;
- persisted SQLite SHA `dfce68a8f7cae08b90380630ae29e31418b4d6e8987d3e7001fe72fa1d781304`;
- base gate **23/18/0,40 → 22/18/0,39 unique**;
- 1 attempt / 1 raw rank0 accept / 0 rejects at source start `107711`;
- 3343 untouched rows exact; source coverage byte-exact; SQLite integrity/foreign keys clean;
- evidence remains non-promoting/default-OFF.

The selected source is the algebraic sentence beginning `And by squaring these Equals...`. The OPUS target introduced a source-absent `=`. The selected raw TC-big candidate removes that hallucinated sign while preserving emphasized algebraic variables/ratios and the semantic relation `equal to`. The earlier concern about an unrelated `Square of the Sine` hypothesis does not describe the persisted row and is no longer a blocker for this exact run-14 audit. No target surgery or corpus patch is involved.

## Additional persisted research evidence above run 14

### Angular-minute prime rescue — research run 15

Workflow `34643812392` is green; artifact `10281555120`.

- exact base is run `14`;
- output SHA `0e0ebb851e43079b3029a2a2638d0dc0ff5eb45bebd6c91895cb04483349fb45`;
- persisted SQLite SHA `bfb131c43c37276a906044cc23908251e1526b9943d2c54eac5bf409b6b64630`;
- hard counts **22/18/0,39 → 21/18/0,38 unique**;
- exactly one attempt/accept at source start `431358`, rank0 target `В то же время появляется гало на расстоянии около 22 градусов 35' от центра Луны.`;
- 3343 untouched rows exact, byte-exact source coverage, SQLite clean and all no-rewrite/no-injection safety flags false.

This establishes a real corpus improvement for the source-defined single angular-minute prime case. It does **not** authorize automatic/default/public promotion: the evidence itself records `promotion_allowed=false`, `automatic_product_default_allowed=false`, `public_stage12_surface_allowed=false`.

## Current short-DMS frontier

Run `14` contains the genuine residual at source start `110881`:

- source: `Whence this Angle is 2 deg. 0'. 7''. `;
- target: `Откуда угол 2 градуса. 0 футов 7 футов.`.

The prime evaluator is correctly exposing a translation defect: minute/second notation is being interpreted as feet rather than angular minutes/seconds.

The implemented short-DMS wrapper is deliberately narrower than a generic prime fixer. Eligibility requires exact single-row Stage10 geometry, exactly one `D deg. M'. S''` source expression, the word `Angle`, <=12 alphabetic source words, an existing Product hard failure and failed prime preservation. A raw TC-big candidate must then pass maintained strict checks, exact prime signature, emphasis preservation, conservative source-relative alpha bounds, and Russian angle/degree semantic anchors. The longer neighboring optics sentence containing `Chord` is excluded by the source-length gate because a mechanically clean DMS candidate can still corrupt its technical semantics.

A dedicated read-only feasibility workflow over the exact run-14 database is the current evidence gate. Until its raw hypotheses are inspected and a persisted composed audit succeeds, this wrapper is experimental/default-OFF only.

## Boundary/context evidence

Read-only workflow `34644023517` tested the exact contiguous pair `whence is it | but from ... ?`. All six TC-big n-best hypotheses passed the strict mechanics and the experiment's semantic anchors when the pair was translated together. This proves feasibility of the combined span, but `promotion_allowed=false` and no wrapper/default follows automatically. Boundary changes still require exact source geometry, a source-defined trigger and a persisted regression audit.

## Durable conclusions from the persisted rescue layers

- Target-only delimiter hallucination (run `10`) reduced **24/30/0,52 → 24/25/0,47** without generic TC-big fallback.
- Footnote-reference leads (run `11`) reduced **24/25/0,47 → 24/20/0,42** with 5/5 raw rank0 accepts; an earlier red run was only an audit `0 -> -1` bug.
- Leading `[in _Fig._ N.]` (run `12`) reduced **24/20/0,42 → 23/19/0,41`; one case accepted and one failed closed under the same source-defined rule.
- Semicolon→question migration (run `13`) reduced **23/19/0,41 → 23/18/0,40** by restoring source punctuation structure with an unmodified TC-big candidate.
- Target-only equals addition (run `14`) reduced **23/18/0,40 → 22/18/0,39** on the exact algebraic row.
- Angular-minute research run `15` demonstrates another one-row numeric improvement but remains intentionally non-promoted.

## Exhausted / rejected branches still binding

- Generic OPUS/TC-big whole-context fallback: rejected; mechanically clean candidates can hide semantic loss.
- Broad context `2725`/`2730` formulations: unsafe.
- Broad square-bracket-loss OPUS formulation: no admissible safe cohort.
- Generic prime decomposition/normalization: rejected because notation can be semantically corrupted; only source-defined narrow prime/DMS experiments may proceed.
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
