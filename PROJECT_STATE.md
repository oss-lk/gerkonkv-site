# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`
- Engineering branch: `chatgpt/product-core-forward`
- L3 checkpoint incorporated by this refresh: `0d29d62b0caf4d3c8eac686a81ea000e558824d9`
- Maintained Product Core + Workbench remain the forward implementation.
- Authoritative Product target: `rocketdict/PRODUCT_TARGET.md`; final approved heavy evidence still requires zero unresolved hard translation failures.
- Current frontier is full-corpus translation-quality hardening on complete pinned Project Gutenberg *Opticks*.
- Latest proven persisted research basis is Stage12 run `9`: **24 numeric/symbol / 30 punctuation / 0 length**, **52 unique failures**.
- Default Product behavior has not been broadened by the latest research. Length/citation rescues remain public opt-in/default-OFF; numeric-hard and illustration rescues are separate opt-in wrappers and are not yet public-wired/defaulted.

## Recovery protocol

Follow `AGENTS.md`: compare current HEAD with the checkpoint above, route through `docs/memory/INDEX.md`, and use source/tests/CI/artifacts as L3 authority. If the only commit after this checkpoint is this L1 refresh itself, no engineering drift is implied.

## Maintained translation contracts

- Real EN→RU: pinned OPUS `opus-2020-02-11` → CTranslate2 Marian `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`.
- Block section IDs: `rocketdict-stage12-block-section-identifier/1`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`.
- Length rescue: `rocketdict-stage12-length-failure-whole-context-rescue/1`, default OFF.
- Citation-pair rescue: `rocketdict-stage12-citation-boundary-pair-rescue/1`, default OFF.
- Numeric-hard split-context rescue: `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1`, selector `/1`, default OFF and not public-wired.
- Illustration-label rescue: `rocketdict-stage12-illustration-label-rescue/1`, selector `/1`, target-form `/1`, default OFF and not public-wired.
- Gutenberg emphasis preservation: `rocketdict-maintained-emphasis-markup-preservation/1`, research veto rather than Product hard gate.

## Canonical full-Opticks evidence

Pinned source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; source length `586543` characters.

Structural-label `/2` baseline:
- workflow `34575909618`, artifact `10190059238`;
- Stage12 run `4`, output SHA `b5c42141767a9760495c84023349402bf637b6591f3fa60d723d42c7d5760e22`;
- SQLite SHA `eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c`;
- `3353` segments; **30 numeric / 34 punctuation / 5 length**, **64 unique**.

Length+pair-citation composition:
- workflow `34597648856`, artifact `10263095872`;
- Stage12 run `7`, output SHA `b9e61f1f381ac9cd32e450e66c36a1f16d380eb2ef8b20c18ed7fc5bfc2c38e8`;
- `3348` segments; **29/34/0**, **59 unique**.

Numeric-hard opt-in composition:
- workflow `34601313026`, artifact `10264132732`;
- Stage12 run `8`, output SHA `d3b97f349a7983dc34ed9d8cbd8e64a98c8e237eefa508f4d2d88b62ec547346`;
- SQLite SHA `a84b2118f00bc386953fe11db48bdc29fcfe8db62735f9acf86178e1dbacf9a2`;
- `3343` segments; **25/33/0**, **55 unique**;
- accepted Stage10 contexts `550,669,1024,2238`; emphasis veto blocks context `2725`.

## Validated illustration-label rescue and run 9

Research v3 over exact run `8` succeeded in workflow `34609890716`, artifact `10267328730`, digest `2c5a8b0d11c5924e370076cf4dc5d00b26ad8c4e580f8ca14e2faf642bf7b6e2`. It accepted all three hard-failing standalone illustration rows at source starts `72401,90105,203786` with selected raw ranks `3,3,0` and exact targets `Иллюстрация.`, `Иллюстрация.`, `С центром O`. Counterfactual: **24/30/0**, **52 unique**. Source coverage is byte-exact; no target rewrite/placeholders/literal injection.

Product wrapper `rocketdict-stage12-illustration-label-rescue/1` is implemented default-OFF with narrow trigger `standalone_illustration_label_existing_hard_failure`. Product Core CI `34610493157` is green including real Stage8→25 smoke.

Persisted full-*Opticks* Product audit workflow `34610787826` succeeded; artifact `10268850347`, digest `1818c3cb67746d9ff1c8a49968e11584018264954f6204f014292344e37dbaee`:
- Stage12 run `9`, output SHA `c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be`;
- SQLite SHA `9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad`;
- `3346` segments; **24 numeric / 30 punctuation / 0 length**, **52 unique**;
- all 3340 untouched rows base-exact, applied targets exact raw hypotheses, source coverage byte-exact, SQLite integrity/foreign keys clean, safety flags false.

Run `9` is now the residual basis. Key future work by immutable source spans/current contexts rather than shifted sequence IDs.

## Footnote-marker research

A closed block-start marker cohort `[G]`, `[H]`, `[J]`, `[K]`, `[M]` remains among run-9 punctuation failures at source starts `151466,151557,253849,253919,254102`.

Marker-only body retranslation workflow `34611175668`, artifact `10268975960`, evidence SHA `14ecc93fe080a218dd9c62de35c7e6dff534867849e6c42cd677b905ef8d76fa`, mechanically accepted all five and counterfactually reached **24/25/0**, **47 unique**. This branch is **not Product-ready**: semantic inspection catches at least `[H]` `_How to do this, is shewn in our_` → `Как это сделать, сшито в нашем...` and `[J]` `_See our_` → `Посмотри на нас.`. Mechanical gate improvement is therefore insufficient.

Whole-footnote-context research is the current active direction: preserve the block marker/source separators as source-owned bytes and translate the complete linguistic footnote context with raw n-best plus strict/emphasis vetoes. Initial workflow `34611517906` failed before model evaluation because its fixture confused paragraph boundary with current Stage12-row boundary. Immutable source proves:
- `[G]` paragraph end `151557`;
- `[H]` paragraph end `151652`, while its existing last Stage12 row extends to `151655` with extra blank-line bytes;
- `[J]` paragraph end `253919`;
- `[K]` paragraph end `254026`;
- `[M]` paragraph end `254202`, while its existing last Stage12 row extends to `254205`.

This is a harness-boundary defect, not evidence against whole-context translation. The next patch must model marker, linguistic paragraph body, paragraph separator/trailing whitespace, and replacement row coverage separately rather than changing expected facts to make the test green.

## Important guardrails

- Do not reclassify bare Roman `IV.`/`II.` fragments as headings; they are inline citation boundaries.
- Context `2725` proves generic whole-context mechanical cleanliness can hide semantic loss.
- Punctuation residuals remain heterogeneous; no universal punctuation fixer.
- Prime notation, formula/fraction corruption and very-large-integer corruption remain separate unresolved families.
- Generic alpha gain, target literal injection, corpus-specific target patches, placeholders, source rewriting and evaluator weakening remain forbidden.
- Source-owned treatment must be exhaustively source-defined and must not capture inline linguistic bracket content.

## Next useful actions

1. Fix the whole-footnote-context research harness to distinguish semantic paragraph end from enclosing Stage12 row end and preserve separator/trailing whitespace byte-exactly.
2. Rerun on exact run `9`; inspect all raw n-best candidates semantically, especially H/J, and require strict hard gates + emphasis preservation before any mechanical acceptance.
3. If a narrow subset is demonstrably safe, productize only that source-defined subset as default-OFF with persisted full-corpus audit; otherwise record negative evidence and move to the next residual family.
4. Recompute the residual inventory after any persisted change; keep illustration/numeric/footnote mechanisms independently attributable.
5. Public/default promotion remains separate from opt-in research success.

## Hot paths

- `rocketdict-product-core/src/rocketdict/translation_stage.py`
- `rocketdict-product-core/src/rocketdict/translation_numeric_hard_rescue_stage.py`
- `rocketdict-product-core/src/rocketdict/translation_illustration_rescue_stage.py`
- `rocketdict-product-core/src/rocketdict/emphasis_markup.py`
- `rocketdict-product-core/src/rocketdict/translation_rescue.py`
- `rocketdict-product-core/src/rocketdict/api/operations.py`
- `rocketdict-workbench/tests/real_translation_full_opticks_block_footnote_marker_feasibility_run9.py`
- `rocketdict-workbench/tests/real_translation_full_opticks_block_footnote_context_feasibility_run9.py`
- `.github/workflows/rocketdict-full-opticks-block-footnote-*-run9.yml`
