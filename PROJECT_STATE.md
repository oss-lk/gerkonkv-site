# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`
- Engineering branch: `chatgpt/product-core-forward`
- L3 checkpoint incorporated by this refresh: `76e2d11af35f6f26cd3fcdaf2f8ea1ca5f877c87`
- Maintained Product Core + Workbench remain the forward implementation.
- Current frontier is full-corpus translation-quality hardening on complete pinned Project Gutenberg *Opticks*.
- Default Product behavior has **not** been broadened by the latest research. Length-failure and citation-boundary rescues remain public opt-in/default-OFF. The newer numeric-hard whole-context rescue is implemented and validated as a separate opt-in wrapper but is **not yet wired into public `product.stage12.run`**.

## Recovery protocol

Follow `AGENTS.md`: compare current HEAD with the checkpoint above, route through `docs/memory/INDEX.md`, and use source/tests/CI/artifacts as L3 authority. Any known stale L1/L2 state must be repaired before new engineering work.

## Maintained translation contracts

- Real EN→RU: pinned OPUS `opus-2020-02-11` → CTranslate2 Marian `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`.
- Block section IDs: `rocketdict-stage12-block-section-identifier/1`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`.
- Length rescue: `rocketdict-stage12-length-failure-whole-context-rescue/1`, default OFF.
- Citation-pair rescue: `rocketdict-stage12-citation-boundary-pair-rescue/1`, default OFF.
- Numeric-hard split-context rescue: `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1`, selector `rocketdict-stage12-numeric-hard-failure-whole-context-selector/1`, default OFF and not yet public-wired.
- Gutenberg emphasis-preservation diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`; used as a veto by the numeric-hard rescue after a semantic-loss counterexample.

## Canonical full-Opticks baseline

Pinned source SHA-256: `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`.
Normalized text SHA-256: `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`.
Source length: `586543` characters.

Structural-label `/2` Product baseline:
- CI run `34575909618`, artifact `10190059238`;
- baseline JSON SHA-256 `48385b0b9e2539c9b82feb1f98fa68b660307aa1f76ce58e6e56ed6a93f32133`;
- baseline SQLite SHA-256 `eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c`;
- Stage12 run id `4`, output SHA-256 `b5c42141767a9760495c84023349402bf637b6591f3fa60d723d42c7d5760e22`;
- `3353` segments;
- complete hard gates: **30 numeric/symbol / 34 punctuation / 5 length**;
- **64 unique failing segments**.

Historical `product_numeric_failure_count=27` is only the literal-bearing stress subset; the complete gate also catches three non-literal-source failures.

## Validated opt-in rescue composition

### Length + citation

Combined run `34597648856`, artifact `10263095872`:
- Stage12 run id `7`, output SHA-256 `b9e61f1f381ac9cd32e450e66c36a1f16d380eb2ef8b20c18ed7fc5bfc2c38e8`;
- `3348` segments;
- hard gates **29 numeric / 34 punctuation / 0 length**;
- **59 unique failures**;
- source coverage byte-exact, untouched rows base-exact, applied targets exact raw rank-0, no source/target rewriting/placeholders/literal injection;
- SQLite SHA-256 `afc9eba1177e1ada86ae208d3f175cc34f84cd287145b236f4dad79fd73f7f67`.

### Numeric-hard split-context rescue

Residual lineage audit proved that the current composed run still contains exact source/target lineage for the old whole-context shadow. Eight historical mechanically accepted contexts remained lineage-exact, but semantic review found the decisive counterexample `2725`: its raw whole-context candidate removes invented `=` while silently dropping source phrase `_per deliquium_`. Therefore old strict mechanical selection is not sufficient.

A new conservative emphasis-markup diagnostic/veto was added. On the current numeric-hard split cohort, the safe opt-in selector accepts only contexts `550`, `669`, `1024`, `2238`; `2725` is rejected by the emphasis veto. Other attempted contexts are `1460`, `2132`, `2176`, `2190`, `2634`.

Persisted full-*Opticks* audit:
- workflow run `34601313026` — success;
- artifact `10264132732`, artifact digest SHA-256 `3020f5bb9e6c59b312bb8e09a26d1fea4e29deac29ace3bbeca0cfd695b4bd76`;
- evidence JSON SHA-256 `8af5a3e15997e55a790f0cf408274873a2281c5a7ddda29072039367043ca22d` (internal evidence field `c8908cbf8248b140c4efecd01ec0d1e83a84c51385760212659662a598c1c61e`);
- Stage12 run id `8`, output SHA-256 `d3b97f349a7983dc34ed9d8cbd8e64a98c8e237eefa508f4d2d88b62ec547346`;
- resulting SQLite SHA-256 `a84b2118f00bc386953fe11db48bdc29fcfe8db62735f9acf86178e1dbacf9a2`;
- segment count `3343`;
- hard gates **25 numeric / 33 punctuation / 0 length**;
- **55 unique hard-failing segments**;
- accepted contexts: `550`, `669`, `1024`, `2238`;
- rejected: `1460`, `2132`, `2176`, `2190`, `2634`, `2725`;
- base Stage12 run `7` reused from cache;
- source coverage byte-exact, untouched rows base-exact, applied targets exact raw rank-0, safety flags all false.

Product Core CI `34601005247` for the numeric-hard wrapper/tests completed successfully. The persisted audit keeps `promotion_allowed=false`, `automatic_product_default_allowed=false`, and `semantic_review_required=true`.

## Current unresolved frontier

The strongest validated opt-in research output now leaves:
- **25 numeric/symbol failures**;
- **33 punctuation failures**;
- **0 length failures**;
- **55 unique failures**.

There are therefore three numeric/punctuation-overlap segments (`25 + 33 - 55 = 3`).

Next research must use run `8`/immutable source spans as the current basis. Do not blindly reuse older sequence IDs after context merges.

## Important guardrails

- Do **not** reclassify bare Roman `IV.`/`II.` fragments as structural headings; they are inline `Sect.` citation boundaries.
- Do not promote generic whole-context fallback from mechanical cleanliness alone. Context `2725` proves the old selector can hide semantic content loss.
- Emphasis preservation is currently a conservative research veto, not a new Product hard gate.
- Punctuation residuals remain heterogeneous; no universal punctuation repair.
- Prime/unit ambiguity, compact formula/fraction corruption and very-large-integer corruption remain separate unresolved families.
- Generic alpha gain, target literal injection, corpus-specific target patches, placeholders, source rewriting and evaluator weakening remain forbidden.

## Next useful actions

1. Inventory the exact run-8 residual `25 numeric / 33 punctuation` set by immutable source span and Stage10 context.
2. Split the remaining numeric failures into notation/model/planner families and identify which are still split-context vs single-unit.
3. Re-run punctuation-family classification on run 8 because one punctuation failure was removed incidentally by the numeric-hard rescue.
4. Use existing shadow/n-best evidence only after exact lineage verification; add source-defined diagnostics where current selectors miss semantic loss.
5. Decide whether the numeric-hard wrapper has enough independent evidence to be exposed through public Stage12 while remaining default OFF; do not auto-promote it to default.

## Hot paths

- `rocketdict-product-core/src/rocketdict/translation_stage.py`
- `rocketdict-product-core/src/rocketdict/translation_length_rescue_stage.py`
- `rocketdict-product-core/src/rocketdict/translation_citation_rescue_stage.py`
- `rocketdict-product-core/src/rocketdict/translation_numeric_hard_rescue_stage.py`
- `rocketdict-product-core/src/rocketdict/emphasis_markup.py`
- `rocketdict-product-core/src/rocketdict/translation_rescue.py`
- `rocketdict-product-core/src/rocketdict/api/operations.py`
- `rocketdict-workbench/tests/real_translation_full_opticks_*`
- `rocketdict-workbench/tests/audit_full_opticks_*`
- `.github/workflows/`
