# RocketDict maintained translation quality — L2

This file stores durable conclusions from maintained Product translation-quality work. It is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Source/tests/CI/artifacts are L3 authority and outrank this summary if they disagree.

## Maintained contracts

- Production baseline MT: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian, acceptance `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`; bare Roman sentence fragments are not headings.
- Block section identifier: `rocketdict-stage12-block-section-identifier/1`.
- Numeric/symbol hard gate: `rocketdict-maintained-numeric-integrity/5` over every selected translation row.
- Length rescue: `rocketdict-stage12-length-failure-whole-context-rescue/1`, default OFF.
- Citation-pair rescue: `rocketdict-stage12-citation-boundary-pair-rescue/1`, default OFF.
- Numeric-hard whole-context rescue: `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1`, default OFF/not public-wired.
- Illustration-label rescue: `rocketdict-stage12-illustration-label-rescue/1`, default OFF/not public-wired.
- Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`, research veto rather than Product hard gate.
- Independent research MT: pinned `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, `model.safetensors` SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0. It remains research-only.

## Canonical contiguous Opticks evidence

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` source characters.

Persisted progression:
- structural-label `/2` baseline run `4`: **30 numeric / 34 punctuation / 5 length**, **64 unique**;
- length+pair-citation run `7`: **29/34/0**, **59 unique**;
- numeric-hard run `8`: **25/33/0**, **55 unique**;
- illustration composition run `9`: **24/30/0**, **52 unique**.

Run `9` remains the current Product residual basis. Workflow `34610787826`, artifact `10268850347`; output SHA `c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be`, SQLite SHA `9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad`, `3346` segments. Source coverage is byte-exact, untouched rows base-exact, SQLite integrity is clean, and rewrite/placeholder/literal-injection flags are false.

Research counterfactuals below do not replace run `9` until a new persisted Product audit is created.

## Exhausted / rejected OPUS residual branches

Current residual families are not safely solved by a generic OPUS fallback:

- Block footnotes `[G]/[H]/[J]/[K]/[M]`: marker-only rescue looked mechanically attractive but contains semantic errors; corrected whole-footnote beam/n-best through `24/24` produced **210 raw hypotheses, 0 mechanically admissible** (`34615540238`, `34615819431`).
- Context `2730`: exact Stage10 context is 339 NLP tokens; whole-context and tested 138/132-token windows either have no admissible candidate or semantic repetition/distortion (`34616386780`, `34616665018`).
- Current square-bracket losses (`[in Fig.]`, inline `[G]`, `[Greek:a]` family): **0/24** admissible OPUS hypotheses (`34617363701`).
- Target-only delimiter additions: ordinary OPUS beam6/n6 gives a strict-clean alternative only for metadata seq `3`; six substantive cases remain trapped in the same bad model basin (`34616844554`).
- Earlier prime-fragment decomposition, thousands-grouping / narrow `x→×`, compact-formula spacing and broad citation/group coalescing remain rejected because they regressed semantics or failed to rescue the class.

Do not spend more effort on an unchanged OPUS formulation without a materially new source representation/model hypothesis.

## Independent TC-big: all-current-failures differential

The delimiter pilot first established that TC-big can escape obvious OPUS hallucination basins. The full run-9 screen then evaluated every one of the **52** current hard-failing rows with six raw TC-big hypotheses.

Workflow `34621706640`; artifact `10272283502`, digest `sha256:907f34473ed4a6482b505fca68006880f0a8819a1b399ca85a85f467511301fc`.
Evidence file SHA-256 `5c87500453f9443f5aff42d4bfea1bc055b48fa3a2ec747e13ec99581fe16f69`; internal evidence SHA-256 `1e3ce22828f72b2409e1a4093646ef0a74a4dcf9b224b3f59d286011acbebca7`.
Schema: `rocketdict-full-opticks-alternative-mt-current-hard-failures-run9/1`.

Results:
- `52` hard-failing run-9 rows examined read-only;
- `32/52` have at least one raw TC-big hypothesis that is mechanically admissible under maintained strict checks plus emphasis preservation;
- there are `172` mechanically admissible hypotheses across those 32 cases;
- the purely mechanical upper bound would move **24/30/0, 52 unique → 13/8/0, 20 unique**;
- immutable run-9 DB SHA is unchanged and source coverage remains byte-exact;
- no source/target rewrite, placeholders, literal injection or corpus-specific target patches are used.

This is strong evidence that much of the residual frontier is baseline-model-specific. It is **not** Product selection. Manual inspection found cases where a mechanically clean TC-big row completes or punctuates a fragment that continues in the neighboring Stage12 row, and other cases with terminology/semantic concerns. Row-local hard-gate cleanliness therefore remains insufficient.

## MetricX-24 reference-free QE audit

Pinned MetricX-24 was run only as an independent research ranking surface over the mechanically admissible TC-big hypotheses; it is not an acceptance gate.

Workflow `34622530818` completed green. Artifact `10273439286`, digest `sha256:9eabcf24353fc46e285eff432373048ca06d9b96d14029153fbe7f95ccead34d`.
Evidence file SHA-256 `8272526960ee7c1a40bd4c76e84a1b878e396393ab967db73186d171c690c336`; internal evidence SHA-256 `949ffd1fc034a8d1aa5701b93eff1ff3507b5a58fda83dd1bdc08c3782018ad2`.
Schema: `rocketdict-full-opticks-metricx-qe-current-hard-failures-run9/1`.

Pinned QE identity:
- `google/metricx-24-hybrid-large-v2p6-bfloat16`, revision `febb720e29a059df2e8af3ffd71dcdc9e0a24910`;
- weights SHA-256 `b1f2c03ab5ec5318a55b90b42eefa22431daa7b1a8e28a97a6aef23d18a24278`;
- tokenizer `google/mt5-large`, revision `50b7223e98fcd124b0cabb1ec81bc6324c7df107`.

Results:
- `32` cases / `172` admissible TC-big candidates scored;
- MetricX prefers at least one admissible TC-big candidate over OPUS in `30/32` cases;
- it prefers the first mechanically admissible TC-big candidate over OPUS in `29/32` cases;
- best-QE admissible candidate ranks are distributed across all six beam ranks, so rank0 alone is not a justified selector.

Interpretation: QE supports the hypothesis that TC-big often improves the residual rows, but it does not supply a safe automatic Product threshold or remove the need for boundary-aware semantic evidence.

## CTranslate2 feasibility is proven; parity is not

The pinned TC-big Marian snapshot was converted to CTranslate2 4.8.2 float32 and successfully executed in a separate runtime where the audit script did not import Torch. This proves a possible torch-free inference architecture, but the first parity formulation did **not** reproduce Transformers hypotheses.

Workflow `34622860381` completed green. Artifact `10273014315`, digest `sha256:2f3033ed90b3397e638d5183b271a59a63c9002369a4fa16c2128813bd0c75d0`.
Evidence file SHA-256 `fe84f70a104d3906a4d426b7c6dd79ed7d410faac093dd97c6f930ada0f1c43c`; internal evidence SHA-256 `73f6640e1acf78d774872b6b75149e8344640bda6f2dac817667d797e6bb1ce3`.
Schema: `rocketdict-full-opticks-tc-big-ct2-parity-run9/1`.

First-pass results:
- exact rank0 matches to Transformers: `0/52`;
- cases with any exact hypothesis overlap: `0/52`;
- mechanically admissible CT2 cases: `15/52`, `84` hypotheses;
- CT2-only mechanical upper bound: **19/20/0, 37 unique**.

Therefore conversion success must not be equated with generation parity. The current harness used raw SentencePiece-side multilingual-prefix handling rather than a demonstrated reproduction of MarianTokenizer + Transformers generation semantics. Root cause must be proven by a corrected tokenizer/generation parity experiment before any release/runtime conclusion is promoted.

## Stage10-context boundary finding

A safer second-model fallback cannot simply replace isolated Stage12 rows because some rows are fragments of a larger source sentence/context. A research harness therefore grouped the 52 hard rows into their **50** original Stage10 contexts.

Initial workflow `34623402220` failed fail-closed before translation on context `2480:2480` with `run9 member coverage drift`; this is an orchestration/boundary finding, not model-quality evidence.

L3 inspection shows:
- Stage10 context 2480 source span is `[480217,480300)` and ends with `_Qu._ 19. ` including one trailing space;
- run-9 row 2729 covers `_Qu._ 19.` as `[480290,480299)`;
- row 2730 starts at byte `480299` and owns the following leading space plus the next question body.

Thus the exact Stage10 boundary cuts through a current Stage12 row. A context candidate cannot safely replace that exact span by whole existing Stage12 rows without either slicing an existing translated row or expanding the source span. Both actions need an explicit source-defined policy and fresh evidence. Future context fallback must be row-boundary-aware and fail closed when a source context is not exactly representable by whole replacement rows.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Preserve immutable source/model/config/result identities.
3. Select only unmodified raw model candidates; no target surgery.
4. Mechanical integrity is necessary but not sufficient; semantic and boundary-aware review is mandatory.
5. A second MT may be invoked only by a narrow failure trigger; clean Product rows must remain untouched unless separate evidence justifies otherwise.
6. Row-local fallback is not automatically safe when source semantics continue across Stage12 boundaries.
7. MetricX/QE may rank research candidates but is not itself an acceptance threshold.
8. Any Product TC-big role still requires deterministic selection, persisted full-corpus regression, offline asset/runtime design, license/attribution handling and release-size/performance assessment.
9. CTranslate2 may be used only after tokenizer/generation parity or intentionally different behavior is explicitly characterized; backend conversion alone is not parity evidence.
10. Final approved heavy evidence still requires zero unresolved hard failures.
