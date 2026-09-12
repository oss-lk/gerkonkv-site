# RocketDict maintained translation quality — L2

Durable translation-quality conclusions only. This is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). L3 source/tests/CI/artifacts outrank this file.

## Maintained contracts

- Production MT: pinned OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product/default Stage10 is `structural-entity-term-discourse-pronoun-v1`, schema `rocketdict-product-stage10/1`. Research V2 is `structural-entity-term-discourse-pronoun-v2`, schema `rocketdict-product-stage10/2`, policy `rocketdict-stage10-lowercase-continuation-coalescer/1`; raw Stage8 spaCy assignments remain immutable evidence.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`; Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- Independent TC-big comparator/rescue: `Helsinki-NLP/opus-mt-tc-big-en-zle` revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0, offline/Torch-free CTranslate2 asset.
- Narrow TC-big wrappers remain default OFF/not public-wired.

## Canonical complete Opticks basis

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` chars.

Persisted progression: run `4` **30/34/5,64** → `7` **29/34/0,59** → `8` **25/33/0,55** → `9` **24/30/0,52** → `10` **24/25/0,47** → `11` **24/20/0,42** → `12` **23/19/0,41** → `13` **23/18/0,40** → `14` **22/18/0,39** → `15` **21/18/0,38** → run `16` **20/18/0,37** → run `17` **20/17/0,36**.

Run `17` is the best accepted persisted **research** translation basis. Workflow `34656818930`; artifact `10285447200`; artifact ZIP SHA-256 `e71c105aaa514612999838bacf9ee9e4e9a560033d4ff2a57abbf2a8d10a6581`; output SHA `5a224f0ef58cca18f60ea495a5dcde54fdc516260076eea9f5368d00809961dd`; SQLite SHA `00307c3e31fe3c42e208aba4c60a0502f102df2772dd06cc8c5804f1bccd1a53`; evidence SHA `d52b13a3d79d01e10482ea7208b90086828de2747cb478048426a97bcffe0057`.

Run17 directly composes over exact run16. One source-defined punctuation-only false-boundary pair at `522572` is replaced by raw TC-big rank0; 3342 other base rows have zero source/target drift. Source reconstruction is byte-exact, SQLite integrity `ok`, FK violations zero. The accepted pair passes maintained strict/research/emphasis checks and diagnostic semantic anchors. This makes run17 a research basis only; it does not promote TC-big or the wrapper into Product defaults.

## Stage10 source-boundary research

Exact immutable run-16 Stage8 census establishes **38** V2 predicate matches. Seven offsets are already absorbed by Stage12 protected-span behavior; **31** remove actual run16 Stage12 boundaries.

Planner-impact workflow `34651300446` proves V1 `3353` → V2 `3325` planned units and removes all 31 affected plan boundaries without invoking MT.

Full broad V2 real-MT replay workflow `34652579262` is mechanically green at **20/16/0,36**, with 3264 unchanged source geometries and zero target drift. But semantic review rejects broad V2 translation promotion: representative regressions on previously clean geometry include loss of `HEFK`, loss of `_in vacuo_`, and duplicated/garbled technical content. Therefore source-boundary correctness alone does not license wholesale MT resegmentation.

Low-level `run_stage10()` default was realigned to V1 in commit `d438da03cbbd0882b34c3caea58a651a92058253`; V2 is now explicit research selection only.

## Boundary-pair punctuation rescue

Contract: `rocketdict-stage12-tc-big-boundary-pair-punctuation-rescue/1`, with matching selector/trigger `/1`; default OFF and not public-wired.

Eligibility is generic and source-owned: exactly two adjacent complete unsplit V1 Stage12 rows, consecutive exact V1 Stage10 contexts, immutable Stage8 sentence evidence satisfying the V2 false-boundary predicate, at least one current punctuation hard failure, zero current numeric/symbol and length failures, and a conservative source complexity cap. Product code does not encode the corpus offset, `whence`, or an expected target phrase.

Only unmodified TC-big rank0 is considered. Strict maintained checks, Gutenberg emphasis preservation and source-relative completeness must all pass. Rejection leaves both rows exact. The wrapper composes over the existing run16 rescue stack; no source rewriting, target surgery, literals, placeholders or evaluator changes occur.

Product CI workflow `34656258155` passed 301 Product Core tests, 213 Workbench tests (1 skipped) and real-runtime maintained Product execution. Terminal workflow `34656444553` also passed dependency-light and real-runtime jobs.

The full corrected replay `34656818930` proves the one accepted pair improves run16 **20/18/0,37 → 20/17/0,36**, with 3342 untouched rows and zero target drift. The initial replay failure was audit-only: a beam-8 feasibility string was pinned while implementation uses beam6; the observed raw beam6 rank0 was independently inspected and the selector/gates were not changed.

## Earlier rescue evidence still binding

- run `10`: target-delimiter, **24/30/0,52 → 24/25/0,47**;
- run `11`: footnote-reference leads, **24/25/0,47 → 24/20/0,42**;
- run `12`: leading figure reference, **24/20/0,42 → 23/19/0,41**;
- run `13`: semicolon→question migration, **23/19/0,41 → 23/18/0,40**;
- run `14`: target-only equals addition, **23/18/0,40 → 22/18/0,39**;
- run `15`: angular-minute prime, **22/18/0,39 → 21/18/0,38**;
- run `16`: short DMS over run15, **21/18/0,38 → 20/18/0,37**;
- run `17`: punctuation-only false-boundary pair, **20/18/0,37 → 20/17/0,36**.

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
