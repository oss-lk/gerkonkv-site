# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`
- Engineering branch: `chatgpt/product-core-forward`
- L3/L2 checkpoint incorporated by this refresh: `02e3c8a945c7984a4dca62a68fd17d2ef226866a`
- Maintained Product Core + Workbench remain the forward implementation.
- Authoritative Product target: `rocketdict/PRODUCT_TARGET.md`; final approved heavy evidence requires zero unresolved hard translation failures.
- Current persisted full-*Opticks* Product residual basis is Stage12 run `9`: **24 numeric/symbol / 30 punctuation / 0 length**, **52 unique failures**.
- Default Product behavior has not been broadened. Length/citation rescues remain public opt-in/default-OFF; numeric-hard, illustration, and TC-big delimiter rescues are separate default-OFF wrappers and are not public-wired.
- Current research frontier is a narrow, failure-triggered, row-boundary-aware second-MT rescue for target-only delimiter hallucinations, followed by persisted full-corpus validation. No TC-big result is yet Product-promoted.

## Recovery protocol

Follow `AGENTS.md`: compare current HEAD with the checkpoint above, route through `docs/memory/INDEX.md`, and use source/tests/CI/artifacts as L3 authority. If only this L1 refresh follows the checkpoint, no engineering drift is implied.

## Maintained translation identities

- OPUS Product baseline: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`.
- Block section IDs: `rocketdict-stage12-block-section-identifier/1`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`.
- Gutenberg emphasis preservation: `rocketdict-maintained-emphasis-markup-preservation/1` research veto.
- Pinned alternative MT: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, license `CC-BY-4.0`.
- Optional TC-big offline asset: `rocketdict-tc-big-en-ru-asset/1`, configured by `ROCKETDICT_TC_BIG_ASSET_DIR`, CTranslate2 float32 + exact local MarianTokenizer snapshot; Torch is not required for inference.
- TC-big delimiter rescue: `rocketdict-stage12-tc-big-target-delimiter-context-rescue/1`, selector `/1`, trigger `/1`, default OFF/not public-wired.

## Canonical full-Opticks evidence

Pinned source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; source length `586543` characters.

Persisted progression:
- run `4`: **30/34/5**, **64 unique**;
- run `7`: **29/34/0**, **59 unique**;
- run `8`: **25/33/0**, **55 unique**;
- run `9`: **24/30/0**, **52 unique**.

Run `9` evidence: workflow `34610787826`, artifact `10268850347`, output SHA `c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be`, SQLite SHA `9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad`, `3346` segments, byte-exact source coverage, clean SQLite integrity and no unsafe target repair.

## Current TC-big evidence

### Row-local all-52 screen and QE

All-52 workflow `34621706640`: **32/52** hard rows have a mechanically admissible raw TC-big hypothesis, `172` admissible hypotheses; mechanical-only ceiling **13/8/0, 20 unique**. Row-local substitution remains unsafe because a Stage12 row can be only a fragment of a larger source context.

Row-level MetricX workflow `34622530818`: QE prefers some admissible TC-big candidate in `30/32` cases and the first admissible candidate in `29/32`; QE is ranking evidence only, never an acceptance threshold.

### Corrected CTranslate2 parity

Workflow `34626241784` green; artifact `10274549063`, digest `7098e0a14deaab87a4edee5d63d29015e89973da9c16f9446bd74fb8b9c3e742`.
Evidence file SHA `01437639b2377a8fb624e16abf6cb2763891e0242f3b91638488ee8e35bed903`; internal evidence SHA `360c5f9b537ef46b2a178d3f3062c1633f5e54a126c59aa51be27ff0eb5f48d8`.

Using exact `MarianTokenizer.encode → convert_ids_to_tokens → CTranslate2 → convert_tokens_to_ids → decode` semantics:
- input-token parity: **52/52**;
- exact rank0 parity: **49/52**;
- at least one exact n-best overlap: **52/52**;
- CT2 mechanically admissible cases: **32/52**, `169` hypotheses;
- CT2 mechanical ceiling matches Transformers: **13/8/0, 20 unique**.

Conclusion: the earlier 0/52 mismatch was a tokenizer-semantics defect. Torch-free CTranslate2 inference is viable; the three rank0 search-order differences remain characterized rather than hidden.

### Whole Stage10 context audit

Workflow `34626136705` green; artifact `10273968597`, digest `f99e9903f80b90997e804a444eaa80b40dbc31ad4258ca287015b3a559201eb6`.
Evidence file SHA `49d679789207440d5160f044944f4261cc957070462f0cce464e047c955878d3`; internal evidence SHA `9309a2b0d4ed4cf84b4f2efc9a6353cc191a98b2557c26aa19fbc1489c3a0a55`.

- `52` hard rows map to `50` original Stage10 contexts.
- `49/50` contexts are exactly replaceable by whole run-9 rows; context `2480` is explicitly `replacement_row_aligned=false` and skipped fail-closed.
- no candidate context exceeds the tested model context limit.
- only `18` contexts are mechanically admissible as whole-context TC-big replacements.
- mechanical-only ceiling becomes **20/16/0, 34 unique**.
- manual inspection found semantic false positives among those 18, so generic whole-context TC-big fallback is rejected.

Whole-context MetricX workflow `34627052164` is green; artifact `10274977715`, digest `899ab34f255b9670f9d9b4ee4f96d7eb459f08b7850708ef8830af6cb1e365f0`; evidence file SHA `911f3d6808bf3bd114fb1c97fda2aef2212ae71a33c52a359aeb468002f6a72f`, internal evidence SHA `37447b126f493a7b7f596d5a2661ee484ebeafcd9d9c2af623a12c9cd2acaf87`. It scores `18` mechanically admissible contexts / `89` candidates and prefers some TC-big candidate over aggregate OPUS in `16/18`; the two counterexamples reinforce that QE is not an automatic selector.

### Narrow target-only delimiter feasibility

Workflow `34627371508` green; artifact `10275510035`, digest `5c76d7db662c66d86f073c36ab3baf99d739da0c200d7c88e38027b01b2947f6`.
Evidence file SHA `46e901c87730d1f5ff7d8fa2ae893500b41ea37fd6cc4a691ab573c910b34f13`; internal evidence SHA `ef22c81ecfda624787c61fed7be66ddb39e9ae2c6a426e842a22dc03fb6d2cb9`.

General trigger: row-aligned Stage10 context containing a current hard failure whose aggregate target adds `()[]{}` delimiters not present in source. Candidate must be strict-clean, emphasis-preserving, remove target-only delimiter additions, and keep target alphabetic volume within `0.75..1.50` of source alpha volume. It deliberately does **not** require candidate alpha >= already-corrupt baseline target alpha.

- `7` contexts trigger;
- `5` pass the selector: Stage10 contexts `3`, `1726`, `1737`, `2066`, `2605`;
- two complex cases remain rejected fail-closed;
- read-only counterfactual: **24/30/0, 52 unique → 24/25/0, 47 unique**;
- no corpus-specific whitelist, target rewrite, literal injection or placeholders.

This is feasibility evidence only. A persisted Product run has not yet been created.

## Current code / verification state

- `alternative_mt_runtime.py` provides the pinned byte-verified optional TC-big CT2 runtime; `alternative_mt_assets.py` provisions it separately.
- `rocketdict-assets build-tc-big-en-ru` provisions the pinned optional asset; `alt-mt` / `alt-mt-build` remain separate optional dependency profiles and are not part of the baseline `production` extra.
- `translation_tc_big_delimiter_rescue_stage.py` implements the narrow default-OFF wrapper above the current illustration→numeric→length→citation composition.
- Public `product.stage12.run` is still wired to the prior wrapper; the TC-big layer is intentionally not public yet.
- Product Core workflow `34628239731` at commit `02e3c8a...` is fully green: dependency-light and real Stage8→25 runtime jobs both pass. This proves the new files do not regress the maintained default path; the TC-big wrapper itself still needs dedicated unit + persisted heavy validation.

## Durable negative evidence still binding

- Whole-context mechanical cleanliness can hide semantic loss (`2725`) and other semantic regressions; generic whole-context TC-big is also unsafe.
- Marker-only footnote repair is semantically unsafe; exact-source whole-footnote OPUS n-best through 24 hypotheses has 0 admissible candidates.
- Whole/pair formulations for context `2730` are unsafe.
- Current square-bracket-loss cases have 0 admissible OPUS n-best candidates.
- Prime decomposition, thousands grouping / narrow `x→×`, compact-formula spacing and broad citation/group coalescing remain rejected.
- No target literal injection, corpus-specific target patching, placeholders, source rewriting or evaluator weakening.
- MetricX/QE may rank candidates but cannot override source-boundary or semantic vetoes.

## Active next actions

1. Add dedicated unit tests for `translation_tc_big_delimiter_rescue_stage.py`: disabled delegation, trigger geometry, non-row-aligned fail-closed behavior, selector bounds, raw-candidate provenance and untouched-row invariance.
2. Add a real optional TC-big asset/runtime smoke that proves builder → byte-verified loader → CT2 MarianTokenizer inference without Torch at inference.
3. Run a persisted full-*Opticks* Stage12 audit above exact run `9`; expected feasibility cohort is the five delimiter contexts and expected gate counterfactual is **24/25/0, 47 unique**, but treat the actual persisted result as authoritative.
4. Verify byte-exact source coverage, untouched run-9 rows, raw selected hypotheses, SQLite integrity, no rewrite/injection flags and exact asset/model identities.
5. Keep the wrapper default OFF/not public-wired until those proofs pass. Even after persisted success, do not make it Product default without broader semantic evidence and release-cost/license validation.
