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
- Gutenberg underscore-emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`; research veto, not Product hard gate.

## Canonical full contiguous Opticks evidence

Pinned complete Project Gutenberg *Opticks*:
- source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`;
- normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`;
- `586543` source characters.

Structural-label `/2` baseline: workflow `34575909618`, artifact `10190059238`, Stage12 run `4`, output SHA `b5c42141767a9760495c84023349402bf637b6591f3fa60d723d42c7d5760e22`, SQLite SHA `eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c`. Complete gates: **30 numeric/symbol / 34 punctuation / 5 length**, **64 unique failures**.

Length+pair-citation composition: workflow `34597648856`, artifact `10263095872`, Stage12 run `7`, output SHA `b9e61f1f381ac9cd32e450e66c36a1f16d380eb2ef8b20c18ed7fc5bfc2c38e8`, `3348` segments, **29/34/0**, **59 unique**. Source coverage byte-exact; untouched rows base-exact; accepted outputs exact raw rank-0; no rewriting/placeholders/literal injection.

Numeric-hard whole-context opt-in: workflow `34601313026`, artifact `10264132732`, artifact digest `3020f5bb9e6c59b312bb8e09a26d1fea4e29deac29ace3bbeca0cfd695b4bd76`, Stage12 run `8`, output SHA `d3b97f349a7983dc34ed9d8cbd8e64a98c8e237eefa508f4d2d88b62ec547346`, SQLite SHA `a84b2118f00bc386953fe11db48bdc29fcfe8db62735f9acf86178e1dbacf9a2`, `3343` segments, **25 numeric / 33 punctuation / 0 length**, **55 unique**. Accepted Stage10 contexts: `550, 669, 1024, 2238`; rejected: `1460, 2132, 2176, 2190, 2634, 2725`. Context `2725` is a durable counterexample: old strict mechanics accepted a candidate that silently dropped `_per deliquium_`; the emphasis-preservation veto correctly blocks it. Product Core CI `34601005247` is green.

## Current residual basis

Run `8` is the strongest persisted research basis: **25 numeric/symbol / 33 punctuation / 0 length**, **55 unique failures**; three rows overlap numeric and punctuation. Future work must key on immutable source spans/current Stage10 context identity rather than shifted sequence IDs.

Residuals are heterogeneous. Prime notation, compact formula/fraction corruption, large integers, footnote markers, illustration payloads, parentheticals/question punctuation and other delimiter failures are separate families. A universal punctuation or generic whole-context repair remains unsafe.

## Illustration-label research — source structure, not target patching

Run-8 classification found three current hard-failing rows beginning with a standalone Gutenberg line `[Illustration: ...]` followed by a blank line. The complete corpus contains 57 standalone illustration-label lines. This is a source-defined document-structure family; it must not be generalized to arbitrary bracketed linguistic text.

### Negative v1 evidence

A first read-only split preserved `[Illustration: ...]` + separator byte-exactly and translated only the linguistic remainder. Mechanical gates suggested a counterfactual **24 numeric / 30 punctuation / 0 length, 52 unique**, but semantic review caught malformed raw OPUS output for exact source suffix `_Illustration._`: `*Иллюстрация._`. Therefore mechanical hard-gate improvement was insufficient and v1 promotion was rejected.

### Fail-closed v2 evidence

The maintained v2 research contract is `rocketdict-full-opticks-illustration-label-feasibility/2`. For exact `_Illustration._`, model input is source-derived canonical `Illustration.` while immutable source bytes remain unchanged; ordinary linguistic suffixes use exact source text. The semantic target-form check accepts only the intended structural lexical class and no markup artifacts.

Workflow run `34603765083` succeeded; artifact `10265862004`, digest `85231d8a9eca686deb6cf72240fc395aecfd0fc3d85de116ba3b0d7132026a4e`. Evidence file SHA-256 `0043d0a912a0ff35001d55fcea0b792ca534fe43b434f015c8f7ceec7d866653`, internal evidence field `9a785068bb2c1fb9c580e3bf0419d4c350b9a9bad7b0471b43ef018d1c570ad6`.

The three attempted immutable source starts are `72401, 90105, 203786`. Rank-0 canonical `Illustration.` produced `Пример.` at starts `72401` and `90105`, so both are correctly rejected by the semantic target-form check. Only the ordinary suffix case at `203786` (`With the Center O ` → raw rank-0 `С центром O`) is accepted. Counterfactual result: **24 numeric / 32 punctuation / 0 length, 54 unique**. Source coverage remains byte-exact and the run-8 database is unchanged.

### Illustration-word OPUS DOE

Because v2 proved rank-0 ambiguity rather than absence of a good raw model candidate, a separate source-side DOE searched canonical model inputs and n-best cells without target rewriting. Workflow run `34603700499` succeeded; artifact `10265013225`, digest `3e92ac761908175f25d0a66c0942e1772809f402fedb9c637c2f8ad8f1bf50c0`. Evidence file SHA-256 `54e23fd53c2a4015e030aee5699aa92bb6c051471ae6b4f367cc16957f683025`, internal evidence field `3c7d3a6e651a33654783cff551d477fdd0973fc75a1a63048c0e0afc44414e08`.

DOE evaluated 8 canonical model inputs × two n-best generation cells, 144 raw hypotheses total, and found 25 mechanically + semantically admissible structural-word candidates. The selected deterministic candidate is:
- canonical model input `Illustration.`;
- beam `6`, `num_hypotheses=6`;
- raw rank `3`;
- exact raw target `Иллюстрация.`;
- no target rewrite/placeholders/literal injection.

This supports a **research v3**, not Product promotion: preserve immutable `_Illustration._` source bytes, generate n-best from canonical `Illustration.`, and select only an unmodified raw hypothesis satisfying hard/strict gates plus exact structural target shape. Full three-case/full-corpus counterfactual evidence is still required before any Product wrapper.

## Block footnote markers

The source also contains a closed block-start marker family `[A] ` … `[M] `. Existing research `real_translation_full_opticks_block_footnote_marker_feasibility.py` treats the marker+following horizontal whitespace as source-owned structure and translates only the linguistic body. Inline markers such as `understand,[G] that` and `[Illustration: ...]` are explicitly out of scope. This is a promising punctuation family but must be revalidated against run `8` before Productization.

## Durable negative evidence / promotion rules

Do not repeat unchanged without new evidence:
- prime-fragment structural decomposition is semantically unacceptable (`53 deg.`→`53 балла`, `hundred Feet`→`сто ног`); whole-unit prime normalization/hints and broad staged n-best do not solve the class;
- thousands grouping / narrow `x→×` preprocessing rescued `0/4` and regressed successful cases;
- compact-formula spacing did not rescue the investigated formula unit;
- broad citation/group coalescing lost unrelated content;
- generic whole-context strictness is not semantic proof;
- broad n-best fallback, target repair, literal injection, placeholders, source rewriting and evaluator weakening remain rejected.

Promotion principles:
1. Never weaken maintained evaluators to make a real loss green.
2. Classify planner/evaluator/source/document/model/resource defects first.
3. Prefer source/planner fixes for pre-MT defects; select only unmodified raw model candidates when evidence supports them.
4. Source-owned bypass applies only to exhaustively identified non-linguistic structure; inline linguistic content remains ordinary.
5. Preserve source identity, deterministic/replayable contracts and contiguous-corpus evidence.
6. Mechanical integrity is necessary but not sufficient; semantic review remains required.
7. Research gains do not authorize Product defaults automatically.
8. MetricX/QE may rank research candidates but is not by itself an acceptance threshold.
