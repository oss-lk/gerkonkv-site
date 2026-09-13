# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- Current HEAD before this memory repair: `297eeef8688b9ac8a9cb57343b4c95cf0a9af2e7`. The four commits after the previous synchronized state are research-only harness/workflow additions; maintained Product translation code is unchanged.
- Current substantive engineering state is semantic-carrier illustration rescue `/5` from commit `c99749b9214db572af72fb30baf8a7e98816b972`; independent promotion verification is retained through `bf0c1b6be65bc9e303163328750d68556cbbf167`.
- Maintained Product Core workflow `34743880129` completed successfully after the current research harness additions. Earlier carrier workflow `34743281948` also passed dependency-light and real-runtime Stage8→25.
- Authoritative Product contract remains `rocketdict/PRODUCT_TARGET.md`: release still requires **0 unresolved numeric/symbol, punctuation and length hard failures** on the complete 90k+ corpus, then complete learner/export coverage and Windows clean-install validation.
- Historical run23 is research evidence only. Run41 is the immutable previous promotion parent. **Authenticated run56 is the only forward promotion parent.**

## Canonical full-Opticks source

Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

## Forward parent: run56

Full promotion was produced from exact run41 by workflow `34743281964`. Promotion artifact `10312992185`, digest `sha256:81be4996bce174e7aaa21c41da8ef531a9b6d0f59346c26b7fb6328861ab451a`, contains the persisted result.

Run `56`:

- `3335` translation segments;
- **18 numeric/symbol / 14 punctuation / 0 length, 31 unique**;
- translation output SHA-256 `2971fb099674aa81c14e0b75590c5fbcb943d1ea3477efb0ceedbd81bd69fbc5`;
- final text SHA-256 `705dac5de010af8d5c08a3da49b7ec5d568ddf144e435f4617b5cbe2e604f73d`;
- SQLite SHA-256 `cb4568584e70be0fb4d011cd9de212ae01edd046dec8c5ec104ee3bb0e91dc56`;
- promotion evidence SHA-256 `d6dfe0771e0a0c41506494b860c1733981adace656afb6a0130c291cfdfb57ff`;
- independent residual-census SHA-256 `8c79ba9f8bd17790b41bff9e10f8b89ee5706733780ddc6dcd8bebe93c77857e`.

Independent persisted-artifact verification workflow `34743557365` succeeded. SQLite integrity is `ok`, FK violations are zero, source coverage is byte-exact, unrelated run41 spans are target-exact, lexical model inputs equal immutable source subspans, raw rank0 only is preserved, and all unsafe flags are false.

## Illustration representation decision

For `[Illustration: FIG. N.]\n\n_Illustration._`, the immutable pre-MT plan remains four logical pieces: label → OPUS rank0; separator → source passthrough; suffix → TC-big rank0; trailing whitespace → source passthrough. Contract `/5` persists those pieces as provenance inside **one semantic carrier translation row** covering the original source span. The carrier target is exactly `label_rank0 + separator_source + suffix_rank0 + trailing_source`.

## Current residual research evidence

Read-only exact-row punctuation screening workflow `34743811304` succeeded against authenticated run56. Evidence SHA-256: `e001300774ddeb27d7f82f1c4e563f013d1677490384dfb913ceb0fb0de9a13a`.

- cohort: all `14` run56 punctuation failures;
- OPUS raw rank0 admissible cases: `0`;
- TC-big raw rank0 admissible cases: `5`;
- passing translation row sequences: `741`, `1497`, `2108`, `2589`, `3009`;
- four are parenthesis-loss/mismatch cases; seq `3009` is a question-mark case;
- database remained byte-identical and screening preserved exact-source / raw-rank0 / no-rewrite safety invariants.

This is diagnostic evidence only. It does **not** authorize a generic TC-big fallback or a production rescue without a source-defined trigger and independent context-level proof.

A follow-up parenthetical whole-context DOE, workflow `34743895800`, is **invalid as model evidence**. Its harness aborted before model comparison with `RuntimeError: parenthetical DOE member coverage drift at 53`. The failure is orchestration/selection logic, not a negative OPUS/TC-big result. Do not infer model quality from this run.

## Active next actions

1. Repair `real_translation_run56_parenthetical_context_rank0_doe.py` so candidate contexts are derived from the actual residual cohort and current translation-row/context membership rather than asserting coverage for unrelated context `53`.
2. Re-run the bounded parenthetical context DOE against exact authenticated run56, preserving unchanged DB identity and raw rank0-only selection.
3. If a generic source-defined context class is independently proven, implement it default-OFF with exact source/model-input provenance and fail-closed behavior; otherwise record the geometry as closed and choose the next residual family.
4. Do not promote from the five exact-row screening hits alone and do not introduce a broad model fallback.
5. Continue quality-first to zero hard failures, then complete learner/export and Windows clean-install/release validation.
