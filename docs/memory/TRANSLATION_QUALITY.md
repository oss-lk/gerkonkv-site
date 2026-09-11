# RocketDict maintained translation quality — L2

This file stores durable conclusions from maintained Product translation-quality work. It is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Source/tests/CI/artifacts are L3 authority and outrank this summary if they disagree.

## Maintained contracts

- Production MT: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian, acceptance `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural-label contract: `rocketdict-stage12-block-structural-label-opus/2`; source-proven block headings only. Bare Roman sentence fragments are not headings.
- Block section identifier contract: `rocketdict-stage12-block-section-identifier/1`.
- Numeric/symbol hard gate: `rocketdict-maintained-numeric-integrity/5`, over every selected translation row.
- Length rescue: `rocketdict-stage12-length-failure-whole-context-rescue/1`, default OFF.
- Citation pair rescue: `rocketdict-stage12-citation-boundary-pair-rescue/1`, default OFF.
- Numeric-hard whole-context rescue: `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1`, selector `/1`, default OFF and not yet public-wired.
- Illustration-label rescue: `rocketdict-stage12-illustration-label-rescue/1`, selector `/1`, target-form `/1`, default OFF and not yet public-wired.
- Gutenberg underscore-emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`; research veto, not Product hard gate.

## Canonical full contiguous Opticks evidence

Pinned complete Project Gutenberg *Opticks*:
- source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`;
- normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`;
- `586543` source characters.

Structural-label `/2` baseline: workflow `34575909618`, artifact `10190059238`, Stage12 run `4`, output SHA `b5c42141767a9760495c84023349402bf637b6591f3fa60d723d42c7d5760e22`, SQLite SHA `eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c`. Complete gates: **30 numeric/symbol / 34 punctuation / 5 length**, **64 unique failures**.

Length+pair-citation composition: workflow `34597648856`, artifact `10263095872`, Stage12 run `7`, output SHA `b9e61f1f381ac9cd32e450e66c36a1f16d380eb2ef8b20c18ed7fc5bfc2c38e8`, `3348` segments, **29/34/0**, **59 unique**.

Numeric-hard whole-context opt-in: workflow `34601313026`, artifact `10264132732`, Stage12 run `8`, output SHA `d3b97f349a7983dc34ed9d8cbd8e64a98c8e237eefa508f4d2d88b62ec547346`, SQLite SHA `a84b2118f00bc386953fe11db48bdc29fcfe8db62735f9acf86178e1dbacf9a2`, `3343` segments, **25/33/0**, **55 unique**. Accepted Stage10 contexts `550,669,1024,2238`; context `2725` remains the durable semantic-loss counterexample blocked by emphasis preservation.

## Validated illustration-label rescue and current residual basis

Research v3 workflow `34609890716` succeeded on exact run `8`; artifact `10267328730`, digest `2c5a8b0d11c5924e370076cf4dc5d00b26ad8c4e580f8ca14e2faf642bf7b6e2`. The source-defined hard-failing standalone illustration starts are `72401,90105,203786`. Deterministic raw candidates selected ranks `3,3,0` with exact targets `Иллюстрация.`, `Иллюстрация.`, `С центром O`. Counterfactual becomes **24 numeric / 30 punctuation / 0 length, 52 unique** with byte-exact source coverage and no target rewrite/placeholders/literal injection.

The opt-in Product wrapper `rocketdict-stage12-illustration-label-rescue/1` reproduces that mechanism and remains default OFF. Product Core CI `34610493157` is green including real Stage8→25 smoke.

Persisted audit workflow `34610787826` succeeded; artifact `10268850347`, digest `1818c3cb67746d9ff1c8a49968e11584018264954f6204f014292344e37dbaee`. It creates Stage12 run `9`, output SHA `c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be`, SQLite SHA `9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad`, `3346` segments and **24/30/0**, **52 unique**. Untouched rows are base-exact; applied targets are exact raw hypotheses; source coverage and SQLite integrity are clean; all rewrite/placeholder safety flags remain false.

**Run `9` is now the current residual basis.** Future residual work must key on immutable source spans/current context identity, not shifted sequence numbers.

## Illustration-label negative evidence remains binding

Do not regress to v1/v2 shortcuts:
- exact `_Illustration._` raw rank0 can be malformed (`*Иллюстрация._`);
- canonical rank0 `Illustration.` can choose wrong sense `Пример.`;
- only the deterministic raw n-best structural target selector has contiguous three-case evidence.

This does not authorize default promotion. It only supports the current default-OFF wrapper.

## Block footnote markers: marker-only split is mechanically good but semantically insufficient

Run `9` contains a closed current hard-failing block-start marker cohort at source starts `151466,151557,253849,253919,254102`, corresponding to `[G]`, `[H]`, `[J]`, `[K]`, `[M]`. Inline markers are out of scope.

Marker-only feasibility workflow `34611175668`, artifact `10268975960`, evidence SHA `14ecc93fe080a218dd9c62de35c7e6dff534867849e6c42cd677b905ef8d76fa`, mechanically accepts all five and would move **24/30/0, 52 unique → 24/25/0, 47 unique**. This branch is **rejected for Productization** because semantic inspection catches at least:
- `[H]` `_How to do this, is shewn in our_` → `Как это сделать, сшито в нашем...`;
- `[J]` `_See our_` → `Посмотри на нас.`.

Therefore a locally clean marker/body split is not enough; these first rows are fragments of larger footnote-reference paragraphs.

## Whole-footnote-context research and boundary lesson

The promising next formulation is source-owned marker + source-owned paragraph/trailing separators + translation of the complete linguistic footnote body using deterministic raw n-best, strict hard checks and the emphasis-preservation veto.

Initial workflow `34611517906` failed **before MT evaluation** due a harness-boundary assertion, not due a model candidate. The script used the first `\n\n` as both semantic paragraph end and existing Stage12 replacement-row boundary. L3 immutable source/run-9 rows prove these are different for two cases:
- G: semantic paragraph end = row coverage end `151557`;
- H: semantic paragraph end `151652`, enclosing current Stage12 row ends `151655` because it owns three additional newline bytes;
- J: both `253919`;
- K: both `254026`;
- M: semantic paragraph end `254202`, enclosing current Stage12 row ends `254205` because it owns three additional newline bytes.

The correct harness must keep semantic body boundaries and row-replacement/source-coverage boundaries separate. Do not merely change fixture constants: preserve marker, translated paragraph body, paragraph separator and any extra trailing whitespace explicitly and byte-exactly.

## Residual families / durable negative evidence

Residuals remain heterogeneous. Prime notation, compact formula/fraction corruption, large integers, source-owned footnote markers, parentheticals/question punctuation and other delimiter failures require separate mechanisms.

Do not repeat unchanged without new evidence:
- prime-fragment structural decomposition is semantically unacceptable (`53 deg.`→`53 балла`, `hundred Feet`→`сто ног`);
- thousands grouping / narrow `x→×` preprocessing rescued `0/4` and regressed successful cases;
- compact-formula spacing did not rescue the investigated formula unit;
- broad citation/group coalescing lost unrelated content;
- generic whole-context strictness is not semantic proof;
- marker-only footnote repair is not semantically sufficient despite a five-failure mechanical gain;
- broad n-best fallback, target repair, literal injection, placeholders, source rewriting and evaluator weakening remain rejected.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Classify planner/evaluator/source/document/model/resource defects first.
3. Prefer source/planner fixes for pre-MT defects; select only unmodified raw model candidates when evidence supports them.
4. Source-owned bypass applies only to exhaustively identified non-linguistic structure; inline linguistic content remains ordinary.
5. Preserve source identity, deterministic/replayable contracts and contiguous-corpus evidence.
6. Mechanical integrity is necessary but not sufficient; semantic review remains required.
7. Research gains do not authorize Product defaults automatically.
8. MetricX/QE may rank research candidates but is not by itself an acceptance threshold.
