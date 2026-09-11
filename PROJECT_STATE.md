# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`
- Engineering branch: `chatgpt/product-core-forward`
- L3 checkpoint incorporated by this refresh: `2910072e63b3eed0dbd25cc837bbb94b949d368d`
- Maintained Product Core + Workbench remain the forward implementation.
- Authoritative Product target: `rocketdict/PRODUCT_TARGET.md`; unresolved hard translation failures must reach zero before approved final heavy evidence.
- Current frontier is full-corpus translation-quality hardening on complete pinned Project Gutenberg *Opticks*.
- Default Product behavior has **not** been broadened by the latest research. Length and citation rescues remain public opt-in/default-OFF. Numeric-hard whole-context rescue is implemented/validated as a separate opt-in wrapper but is not yet wired into public `product.stage12.run`.
- Previous interrupted v3 staging debt is cleared: the three `.v3_staging_note*` files and placeholder `real_translation_full_opticks_illustration_label_feasibility_v3.py` were removed. No Product code was changed by that cleanup.

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
- Gutenberg emphasis preservation: `rocketdict-maintained-emphasis-markup-preservation/1`, research veto rather than Product hard gate.

## Canonical full-Opticks evidence

Pinned source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; source length `586543` characters.

Structural-label `/2` Product baseline:
- workflow `34575909618`, artifact `10190059238`;
- Stage12 run `4`, output SHA `b5c42141767a9760495c84023349402bf637b6591f3fa60d723d42c7d5760e22`;
- SQLite SHA `eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c`;
- `3353` segments; hard gates **30 numeric/symbol / 34 punctuation / 5 length**; **64 unique failures**.

Validated length+pair-citation composition:
- workflow `34597648856`, artifact `10263095872`;
- Stage12 run `7`, output SHA `b9e61f1f381ac9cd32e450e66c36a1f16d380eb2ef8b20c18ed7fc5bfc2c38e8`;
- `3348` segments; **29/34/0**, **59 unique**.

Validated numeric-hard opt-in composition:
- workflow `34601313026`, artifact `10264132732`, artifact digest `3020f5bb9e6c59b312bb8e09a26d1fea4e29deac29ace3bbeca0cfd695b4bd76`;
- Stage12 run `8`, output SHA `d3b97f349a7983dc34ed9d8cbd8e64a98c8e237eefa508f4d2d88b62ec547346`;
- SQLite SHA `a84b2118f00bc386953fe11db48bdc29fcfe8db62735f9acf86178e1dbacf9a2`;
- `3343` segments; hard gates **25 numeric / 33 punctuation / 0 length**; **55 unique failures**;
- accepted Stage10 contexts `550,669,1024,2238`; rejected `1460,2132,2176,2190,2634,2725`;
- source coverage byte-exact, untouched rows base-exact, applied targets exact raw rank-0, safety flags false;
- Product Core CI `34601005247` green.

Run `8` is the current residual basis. It has three numeric/punctuation-overlap rows (`25 + 33 - 55 = 3`). Use immutable source spans/current Stage10 context IDs, not old shifted sequence numbers.

## Current illustration-label research

Run-8 classification identified three current hard-failing rows beginning with standalone Gutenberg `[Illustration: ...]` lines. The source contains 57 such standalone lines.

- v1 source-owned split looked mechanically excellent (**24 numeric / 30 punctuation / 0 length, 52 unique**) but is **rejected**: exact `_Illustration._` yielded malformed raw OPUS `*Иллюстрация._`, proving the hard gates alone miss this semantic/markup defect.
- v2 contract `rocketdict-full-opticks-illustration-label-feasibility/2` preserves the source label+separator byte-exactly; exact `_Illustration._` uses canonical model input `Illustration.` and an explicit semantic structural-word target check. Workflow `34603765083` succeeded; artifact `10265862004`, digest `85231d8a9eca686deb6cf72240fc395aecfd0fc3d85de116ba3b0d7132026a4e`. Starts `72401` and `90105` produce rank-0 `Пример.` and are correctly rejected; ordinary suffix start `203786` is accepted. Counterfactual: **24/32/0**, **54 unique**. Evidence file SHA `0043d0a912a0ff35001d55fcea0b792ca534fe43b434f015c8f7ceec7d866653`.
- Illustration-word DOE workflow `34603700499` succeeded; artifact `10265013225`, digest `3e92ac761908175f25d0a66c0942e1772809f402fedb9c637c2f8ad8f1bf50c0`. It evaluated 144 raw hypotheses and found 25 admissible structural-word candidates. Deterministic selected candidate: model input `Illustration.`, beam `6`, `num_hypotheses=6`, raw rank `3`, target `Иллюстрация.`. Evidence file SHA `54e23fd53c2a4015e030aee5699aa92bb6c051471ae6b4f367cc16957f683025`.

This authorizes a **research v3 only**: immutable `_Illustration._` source bytes + canonical model input + strict raw n-best structural-word selector. It does not authorize Product promotion/default behavior.

## Important guardrails

- Do not reclassify bare Roman `IV.`/`II.` fragments as headings; they are inline citation boundaries.
- Context `2725` proves generic whole-context mechanical cleanliness can hide semantic loss.
- Punctuation residuals remain heterogeneous; no universal punctuation fixer.
- Prime notation, formula/fraction corruption and very-large-integer corruption remain separate unresolved families.
- Generic alpha gain, target literal injection, corpus-specific target patches, placeholders, source rewriting and evaluator weakening remain forbidden.
- Source-owned treatment must be exhaustively source-defined and must not capture inline linguistic bracket content.

## Next useful actions

1. Implement research-only illustration feasibility v3 over run `8`: preserve `[Illustration: ...]` + separator bytes, use canonical `Illustration.` only for exact `_Illustration._`, generate deterministic beam6/n6, select an unmodified raw hypothesis only if hard+strict checks and structural target-shape pass.
2. Run v3 on the exact three current hard-failing source starts and recompute the full run-8 counterfactual. Require byte-exact source coverage, read-only DB, no rewrites/placeholders/injection, and explicit accepted ranks/targets.
3. Only if v3 proves all three cases cleanly, design a **default-OFF** Product wrapper restricted to already-hard-failing standalone illustration-label rows; do not disturb the other 54 currently successful illustration labels without independent evidence.
4. Revalidate the existing block-start footnote-marker feasibility against run `8`; it is the next promising punctuation family after illustration v3.
5. Keep public/default promotion separate from research success until full persisted heavy evidence and semantic review justify it.

## Hot paths

- `rocketdict-product-core/src/rocketdict/translation_stage.py`
- `rocketdict-product-core/src/rocketdict/translation_length_rescue_stage.py`
- `rocketdict-product-core/src/rocketdict/translation_citation_rescue_stage.py`
- `rocketdict-product-core/src/rocketdict/translation_numeric_hard_rescue_stage.py`
- `rocketdict-product-core/src/rocketdict/emphasis_markup.py`
- `rocketdict-product-core/src/rocketdict/translation_rescue.py`
- `rocketdict-product-core/src/rocketdict/api/operations.py`
- `rocketdict-workbench/tests/real_translation_full_opticks_illustration_label_feasibility.py`
- `rocketdict-workbench/tests/real_translation_full_opticks_illustration_word_doe.py`
- `rocketdict-workbench/tests/real_translation_full_opticks_block_footnote_marker_feasibility.py`
- `.github/workflows/rocketdict-full-opticks-*`
