# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`
- Engineering branch: `chatgpt/product-core-forward`
- Checkpoint before this state refresh: `484868cdb7d252a0b8ec53608d02163f086a649a`
- Maintained Product Core + Workbench remain the forward implementation.
- Current frontier is full-corpus translation-quality hardening on complete pinned Project Gutenberg *Opticks*.
- Default Product behavior has **not** been broadened by the latest rescue research: length-failure and citation-boundary rescues remain opt-in and disabled by default.

## Recovery protocol

Follow `AGENTS.md`:
1. Start from this L1 and compare current HEAD with the checkpoint above.
2. If L1 is known stale because a prior iteration ended before synchronization, **repair L1 from current HEAD/L3 at the beginning of the next development request before new work**. A one-word `продолжай` does not waive this.
3. Use `docs/memory/INDEX.md` as the L2 router.
4. Use source/tests/CI/artifacts and other primary evidence as L3 authority.

## Maintained translation contracts

- Real EN→RU: pinned OPUS `opus-2020-02-11` → CTranslate2 Marian `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`.
  - 108 `_Exper._/_Obs._/_Qu._` block labels.
  - 54 complete legacy Roman block headings.
  - total current full-*Opticks* structural units: 162.
- Block section IDs: `rocketdict-stage12-block-section-identifier/1`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`.
- Length rescue: `rocketdict-stage12-length-failure-whole-context-rescue/1`, default OFF.
- Citation-pair rescue: `rocketdict-stage12-citation-boundary-pair-rescue/1`, default OFF.
- Public Stage12 composes the narrow citation-pair rescue over the length-rescue stage while preserving disabled defaults.

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

Historical `product_numeric_failure_count=27` is only the literal-bearing stress subset. The complete numeric/symbol gate includes three additional non-literal-source failures: baseline sequences `617`, `1798`, `3013`.

## Latest validated opt-in rescue evidence

### Length rescue

Full-*Opticks* persisted audit succeeded (`34596212688`); public-wrapper rerun also succeeded (`34597532192`).

Accepted Stage10 contexts: `577`, `629`, `919`.

Result:
- Stage12 run id `6`;
- output SHA-256 `2224d71b20df64e853db1480380f4a78f01184d9021ef8e35142a66dd99d8437`;
- `3350` segments;
- hard gates **29 numeric / 34 punctuation / 2 length**;
- **61 unique failures**.

### Citation-boundary pair rescue

Two residual length failures were proven to be inline `Sect. IV.` / `Sect. II.` sentence-boundary fragments, not structural headings. Do **not** broaden structural Roman-heading detection to bare `IV.` / `II.`.

Pair feasibility run `34597127952`, artifact `10261744281`, evidence SHA-256 `0f90314ad6831647234ae6576b25c407d5c5fdb66dd11fa6e9b71c06404fbc49`:
- both exact previous-row + Roman-fragment pairs are mechanically promising;
- `Sect. II.` pair is fully strict-clean;
- `Sect. IV.` pair inherits an existing footnote-marker debt but introduces no new debt category.

Product implementation is narrow: Roman fragment immediately after contiguous ordinary source ending in `Sect.`, current row must already fail length, source-owned structural/table rows are excluded, candidate is exact raw rank-0 OPUS pair output, and acceptance requires Product hard clean + repaired length + no new strict-debt category.

Product Core CI for the implementation/public wrapper is green (`34597453583`, `34597532302`).

### Combined length + citation audit

Heavy run `34597648856` succeeded; artifact `10263095872`, artifact digest SHA-256 `e2407b28bd7d9a6f76e614551117e8feb8d4729373911b6a33cf53aacacd2aa7`. Evidence JSON SHA-256 `5edfe5b917c2274332ff27ce1e3be5191c95a4a8879a9a643a29ecb2516316da`.

Combined result:
- Stage12 run id `7`;
- output SHA-256 `b9e61f1f381ac9cd32e450e66c36a1f16d380eb2ef8b20c18ed7fc5bfc2c38e8`;
- `3348` segments;
- hard gates **29 numeric / 34 punctuation / 0 length**;
- **59 unique hard-failing segments**;
- accepted length contexts: `577`, `629`, `919`;
- accepted citation-pair source starts: `24799`, `151438`;
- source coverage byte-exact;
- untouched rows base-exact;
- applied targets exact raw rank-0;
- all rewrite/placeholder flags false;
- result SQLite SHA-256 `afc9eba1177e1ada86ae208d3f175cc34f84cd287145b236f4dad79fd73f7f67`;
- SQLite integrity check `ok`, foreign-key check empty.

The audit explicitly keeps `promotion_allowed=false`, `automatic_product_default_allowed=false`, and semantic review required.

## Current unresolved frontier

The composed opt-in output leaves:
- **29 numeric/symbol failures**;
- **34 punctuation failures**;
- **0 length failures**;
- **59 unique failures**.

Four residual segments fail both numeric/symbol and punctuation (`29 + 34 - 59 = 4`).

The next safe technical step is to build a post-composition hard-gate inventory keyed by immutable source spans/context identity on run `7`, then classify the exact residual families and cross-reference them against existing whole-context shadow evidence. Do not assume canonical sequence numbers remain stable after row merges.

Existing canonical whole-context strict candidates (`550, 669, 919, 1024, 1393, 2238, 2462, 2725, 2726`) are historical evidence only until remapped by source/context identity; `919` is already consumed by length rescue.

## Important residual classifications / guardrails

- Punctuation residual `34` is heterogeneous: lost footnote markers, illustration/bracket mismatches, parenthetical omission/addition, question-mark drift and combined delimiter failures. No universal punctuation fixer.
- Prime/unit ambiguity, compact formula/fraction corruption and very-large-integer corruption remain separate unresolved model/notation classes.
- Broad citation/group coalescing is rejected for the Roman-inline-reference class because a larger candidate lost unrelated numeric content and a footnote marker.
- Generic alpha gain is not an acceptance rule.
- Broad whole-context fallback remains research-only; source-defined trigger + semantic evidence are required.

## Forbidden shortcuts

Never promote:
- target literal insertion or fabricated structure;
- corpus-specific target patches;
- identity/dictionary substitution as translation;
- evaluator weakening;
- generic structural-island rules for inline linguistic text;
- broad n-best or whole-context fallback without semantic evidence;
- source/target rewriting, placeholders or post-translation literal injection in rescue paths.

## Next useful actions

1. Build/recompute the complete hard-gate residual inventory on composed run `7` using immutable source-span/context identities.
2. Separate the remaining `29` numeric/symbol and `34` punctuation failures into defect families and identify which remain split-context defects.
3. Cross-reference the remapped split residuals with existing whole-context raw-candidate evidence; do not reuse old context numbers blindly.
4. Only after source-defined trigger and semantic evidence exist, evaluate another narrow Product experiment.
5. Keep both current rescue mechanisms disabled by default until explicit promotion evidence exists.

## Hot paths

- `rocketdict-product-core/src/rocketdict/translation_stage.py`
- `rocketdict-product-core/src/rocketdict/translation_length_rescue_stage.py`
- `rocketdict-product-core/src/rocketdict/translation_citation_rescue_stage.py`
- `rocketdict-product-core/src/rocketdict/translation_rescue_stage.py`
- `rocketdict-product-core/src/rocketdict/api/operations.py`
- `rocketdict-product-core/src/rocketdict/structural_labels.py`
- `rocketdict-product-core/src/rocketdict/legacy_block_headings.py`
- `rocketdict-product-core/tests/test_translation_citation_rescue_stage.py`
- `rocketdict-workbench/tests/real_translation_full_opticks_*`
- `rocketdict-workbench/tests/audit_full_opticks_*`
- `.github/workflows/`
