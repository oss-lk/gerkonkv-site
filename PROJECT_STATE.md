# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`
- Engineering branch: `chatgpt/product-core-forward`
- L3/L2 checkpoint incorporated by this refresh: `d03179bf6253b557586b7271ce99d43f8fe18f54`
- Maintained Product Core + Workbench remain the forward implementation.
- Authoritative Product target: `rocketdict/PRODUCT_TARGET.md`; final approved heavy evidence requires zero unresolved hard translation failures.
- Current persisted full-*Opticks* Product residual basis is Stage12 run `9`: **24 numeric/symbol / 30 punctuation / 0 length**, **52 unique failures**.
- Default Product behavior has not been broadened. Length/citation rescues remain public opt-in/default-OFF; numeric-hard and illustration rescues remain separate default-OFF wrappers and are not public-wired.
- Current research frontier is a failure-triggered, boundary-aware second-MT fallback. TC-big is promising on the run-9 residuals but remains research-only.

## Recovery protocol

Follow `AGENTS.md`: compare current HEAD with the checkpoint above, route through `docs/memory/INDEX.md`, and use source/tests/CI/artifacts as L3 authority. If only this L1 refresh follows the checkpoint, no engineering drift is implied.

## Maintained translation identities

- OPUS Product baseline: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`.
- Block section IDs: `rocketdict-stage12-block-section-identifier/1`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`.
- Gutenberg emphasis preservation: `rocketdict-maintained-emphasis-markup-preservation/1` research veto.
- Pinned alternative MT: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, research-only.

## Canonical full-Opticks evidence

Pinned source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; source length `586543` characters.

Persisted progression:
- run `4`: **30/34/5**, **64 unique**;
- run `7`: **29/34/0**, **59 unique**;
- run `8`: **25/33/0**, **55 unique**;
- run `9`: **24/30/0**, **52 unique**.

Run `9` evidence: workflow `34610787826`, artifact `10268850347`, output SHA `c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be`, SQLite SHA `9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad`, `3346` segments, byte-exact source coverage, clean SQLite integrity and no unsafe target repair.

## Current TC-big evidence

### All 52 run-9 hard rows

Workflow `34621706640`, artifact `10272283502`, digest `907f34473ed4a6482b505fca68006880f0a8819a1b399ca85a85f467511301fc`.
Evidence file SHA `5c87500453f9443f5aff42d4bfea1bc055b48fa3a2ec747e13ec99581fe16f69`; internal evidence SHA `1e3ce22828f72b2409e1a4093646ef0a74a4dcf9b224b3f59d286011acbebca7`.

- **32/52** hard rows have at least one mechanically admissible raw TC-big hypothesis.
- `172` admissible hypotheses total.
- Purely mechanical upper bound: **24/30/0, 52 unique → 13/8/0, 20 unique**.
- This is not Product selection; row-local candidates can still be semantically or boundary-wise unsafe.

### MetricX ranking

Workflow `34622530818` green; artifact `10273439286`, digest `9eabcf24353fc46e285eff432373048ca06d9b96d14029153fbe7f95ccead34d`.
Evidence file SHA `8272526960ee7c1a40bd4c76e84a1b878e396393ab967db73186d171c690c336`; internal evidence SHA `949ffd1fc034a8d1aa5701b93eff1ff3507b5a58fda83dd1bdc08c3782018ad2`.

MetricX-24 prefers at least one admissible TC-big hypothesis over OPUS in **30/32** cases and the first admissible TC-big hypothesis in **29/32**. Best-QE ranks span 0–5. QE remains research-only and is not an acceptance threshold.

### CTranslate2 runtime feasibility / parity gap

Workflow `34622860381` green; artifact `10273014315`, digest `2f3033ed90b3397e638d5183b271a59a63c9002369a4fa16c2128813bd0c75d0`.
Evidence file SHA `fe84f70a104d3906a4d426b7c6dd79ed7d410faac093dd97c6f930ada0f1c43c`; internal evidence SHA `73f6640e1acf78d774872b6b75149e8344640bda6f2dac817667d797e6bb1ce3`.

Pinned TC-big converts to CTranslate2 4.8.2 float32 and executes in a torch-free audit runtime, but the first parity harness has `0/52` rank0 matches and `0/52` any-hypothesis overlap versus Transformers, with only `15/52` mechanically admissible cases. Conversion feasibility is proven; generation parity is not. Correct MarianTokenizer/multilingual-prefix/generation semantics must be reproduced before release-backend conclusions.

## Boundary finding blocking naïve fallback

A safer experiment grouped the 52 hard rows into 50 original Stage10 contexts. Initial workflow `34623402220` failed fail-closed before model inference on context `2480:2480` because the exact Stage10 span is not representable by whole run-9 rows.

Exact L3 geometry:
- Stage10 context 2480: `[480217,480300)` and ends with `_Qu._ 19. `;
- run-9 row 2729: `[480290,480299)` containing `_Qu._ 19.`;
- run-9 row 2730 begins at `480299` and owns the following space plus the next question body.

Therefore Stage10 boundaries can cut through Stage12 rows. Do not slice existing target text or silently expand source. Future second-MT rescue must be source-defined, contiguous, row-boundary-aware and fail closed when replacement geometry is not exact.

## Durable negative evidence still binding

- Whole-context mechanical cleanliness can hide semantic loss (`2725`).
- Marker-only footnote repair is semantically unsafe; exact-source whole-footnote OPUS n-best through 24 hypotheses has 0 admissible candidates.
- Whole/pair formulations for context `2730` are unsafe.
- Current square-bracket-loss cases have 0 admissible OPUS n-best candidates.
- Six substantive target-only delimiter hallucinations remain trapped in the OPUS beam basin.
- Prime decomposition, thousands grouping / narrow `x→×`, compact-formula spacing and broad citation/group coalescing remain rejected.
- No target literal injection, corpus-specific target patching, placeholders, source rewriting or evaluator weakening.

## Active next actions

1. Fix the Stage10-context research harness so non-row-aligned contexts are explicitly classified/skipped fail-closed instead of crashing; run TC-big on all exact row-aligned hard contexts and measure context-level mechanical/semantic potential.
2. Correct the CTranslate2 TC-big parity harness to reproduce MarianTokenizer multilingual-prefix/tokenization and generation semantics; distinguish tokenizer error from backend search differences.
3. Use completed MetricX evidence only as a ranking aid during semantic review, never as automatic Product acceptance.
4. If a narrow boundary-safe second-MT selector emerges, implement it default-OFF first, then run persisted full-*Opticks* regression. Do not promote Product default until clean-row invariance, semantic evidence, offline runtime/assets, license attribution and release cost are proven.
