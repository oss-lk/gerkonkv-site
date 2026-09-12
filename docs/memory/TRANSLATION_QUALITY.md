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

Persisted progression: run `4` **30/34/5,64** → `7` **29/34/0,59** → `8` **25/33/0,55** → `9` **24/30/0,52** → `10` **24/25/0,47** → `11` **24/20/0,42** → `12` **23/19/0,41** → `13` **23/18/0,40** → `14` **22/18/0,39** → `15` **21/18/0,38** → run `16` **20/18/0,37** → run `17` **20/17/0,36** → run `18` **20/16/0,35**.

Run `18` is the best accepted persisted **research** translation basis. Workflow `34675224977`; artifact `10292311024`; artifact ZIP SHA-256 `ae4a32221985aaff2842a87bf9548698d8e76b33815633ddb67100b8fc9dea1d`; output SHA `666e8a2cae0bb6ff6f25b95475c2335ee5e3c98f7f2d6ab7deb9be92295be290`; SQLite SHA `803a2cbccb287ad0fadf4b14d932e1e33ebafef2ec5406619b0caf0898525143`; evidence SHA `61ddb44ceed56d0acb552a5cddecac1543e679c35ad450c41270136c5e014733`.

Run18 directly composes over exact run17. One source-defined orphan-closing-parenthesis failure at source start `417917` is replaced by raw TC-big rank0; 3342 other run17 rows have zero source/target drift. Source reconstruction is byte-exact, SQLite integrity `ok`, FK violations zero. The accepted source has no `(` or `)`, while the baseline target has exactly one target-only closing `)` and no opening `(`. The selected raw rank0 preserves the five required numeric expressions/order, removes the orphan delimiter, passes strict hard/research/emphasis checks and focused diagnostic semantic anchors (bright rings, observation, thinner glass, diameters, same rings, third observation, thicker glass). This remains research evidence and requires manual semantic review before any Product promotion.

## Run17-wide punctuation n-best DOE

Workflow `34674771224`, artifact `10292300428`, artifact ZIP SHA-256 `75a107b25e50f31b404f41a8129054d42303aaa7b29cb71f6ee154de3be60860` is a read-only exact-run17 TC-big beam-6/n-best screening over all 17 punctuation residual rows.

The DOE proves that multiple residuals have mechanically eligible TC-big hypotheses, including several rank0 candidates, but mechanical cleanliness is not a safe generic selector. Manual semantic inspection found false positives: examples include a parenthetical case where `very little convex` loses the intended degree relation and a question-loss case that leaves source wording such as `fix'd` untranslated. Therefore **generic row-local TC-big punctuation fallback is rejected**, even when hard/structural/emphasis checks are green. The DOE is candidate-generation evidence only.

## Orphan closing-parenthesis rescue

Contract: `rocketdict-stage12-tc-big-orphan-closing-parenthesis-rescue/1`, with matching selector/trigger `/1`; default OFF and not public-wired.

The trigger is source-defined and intentionally narrower than target-delimiter rescue: a current split linguistic Stage12 fragment must already hard-fail only because immutable source has `0/0` round-parenthesis counts while target has exactly `0/1`; no numeric/symbol, question/exclamation, square/curly delimiter or maintained technical-token debt may coexist; source complexity is capped conservatively. Only raw TC-big rank0 is considered. The candidate must be non-empty, preserve exact source punctuation counts, numeric/symbol integrity, Gutenberg emphasis, strict research diagnostics and source-relative alphabetic volume. Rejection preserves the base row byte/target exact.

Product CI `34675206945` passed dependency-light and real-runtime maintained Stage8→25/unified Product execution. Full replay `34675224977` proves exactly one run17 row is attempted/accepted and improves **20/17/0,36 → 20/16/0,35** with all other 3342 rows unchanged.

## Stage10 source-boundary research

Exact immutable run-16 Stage8 census establishes **38** V2 predicate matches. Seven offsets are already absorbed by Stage12 protected-span behavior; **31** remove actual run16 Stage12 boundaries.

Planner-impact workflow `34651300446` proves V1 `3353` → V2 `3325` planned units and removes all 31 affected plan boundaries without invoking MT.

Full broad V2 real-MT replay workflow `34652579262` is mechanically green at **20/16/0,36**, with 3264 unchanged source geometries and zero target drift. But semantic review rejects broad V2 translation promotion: representative regressions on previously clean geometry include loss of `HEFK`, loss of `_in vacuo_`, and duplicated/garbled technical content. Therefore source-boundary correctness alone does not license wholesale MT resegmentation.

Low-level `run_stage10()` default is V1; V2 remains explicit research selection only.

## Boundary-pair punctuation rescue

Contract: `rocketdict-stage12-tc-big-boundary-pair-punctuation-rescue/1`; default OFF and not public-wired. Eligibility requires two adjacent exact unsplit V1 rows, independent Stage8/V2 false-boundary proof, punctuation-only current hard debt, conservative complexity, and raw TC-big rank0 only. Full replay `34656818930` established run17 **20/18/0,37 → 20/17/0,36** with 3342 untouched rows.

## Earlier rescue evidence still binding

- run `10`: target-delimiter, **24/30/0,52 → 24/25/0,47**;
- run `11`: footnote-reference leads, **24/25/0,47 → 24/20/0,42**;
- run `12`: leading figure reference, **24/20/0,42 → 23/19/0,41**;
- run `13`: semicolon→question migration, **23/19/0,41 → 23/18/0,40**;
- run `14`: target-only equals addition, **23/18/0,40 → 22/18/0,39**;
- run `15`: angular-minute prime, **22/18/0,39 → 21/18/0,38**;
- run `16`: short DMS over run15, **21/18/0,38 → 20/18/0,37**;
- run `17`: punctuation-only false-boundary pair, **20/18/0,37 → 20/17/0,36**;
- run `18`: orphan closing parenthesis, **20/17/0,36 → 20/16/0,35**.

Persisted success is research evidence, not automatic Product-default authorization.

## Rejected/exhausted directions

- Broad Stage10-v2 translation geometry: rejected for Product/default use because full semantic review found regressions despite improved hard-gate counts.
- Generic OPUS/TC-big whole-context fallback: rejected; mechanically clean alternatives can lose semantics.
- Generic row-local TC-big punctuation fallback: rejected by the exact run17 n-best DOE; mechanical eligibility produced semantic false positives.
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
