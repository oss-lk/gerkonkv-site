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
- Independent MT: pinned `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, `model.safetensors` SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0.
- Optional TC-big offline asset: `rocketdict-tc-big-en-ru-asset/1`; loader recomputes the payload tree, pins repository/revision/weights/license/`>>rus<<`, and requires CTranslate2 float32 plus the exact MarianTokenizer snapshot. Torch is not required for inference.
- Narrow TC-big delimiter rescue: `rocketdict-stage12-tc-big-target-delimiter-context-rescue/1`, selector `rocketdict-stage12-tc-big-target-delimiter-context-selector/1`, trigger `rocketdict-stage12-tc-big-target-delimiter-context-trigger/1`, default OFF/not public-wired.

## Canonical contiguous Opticks evidence

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` source characters.

Persisted progression:
- structural-label `/2` baseline run `4`: **30 numeric / 34 punctuation / 5 length**, **64 unique**;
- length+pair-citation run `7`: **29/34/0**, **59 unique**;
- numeric-hard run `8`: **25/33/0**, **55 unique**;
- illustration composition run `9`: **24/30/0**, **52 unique**.

Run `9` remains the current persisted Product residual basis. Workflow `34610787826`, artifact `10268850347`; output SHA `c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be`, SQLite SHA `9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad`, `3346` segments. Source coverage is byte-exact, untouched rows base-exact, SQLite integrity is clean, and rewrite/placeholder/literal-injection flags are false.

Research counterfactuals below do not replace run `9` until a new persisted Product audit is created.

## Exhausted / rejected OPUS residual branches

Current residual families are not safely solved by a generic OPUS fallback:

- Block footnotes `[G]/[H]/[J]/[K]/[M]`: marker-only rescue looked mechanically attractive but contains semantic errors; corrected whole-footnote beam/n-best through `24/24` produced **210 raw hypotheses, 0 mechanically admissible** (`34615540238`, `34615819431`).
- Context `2730`: exact Stage10 context is 339 NLP tokens; whole-context and tested 138/132-token windows either have no admissible candidate or semantic repetition/distortion (`34616386780`, `34616665018`).
- Current square-bracket losses (`[in Fig.]`, inline `[G]`, `[Greek:a]` family): **0/24** admissible OPUS hypotheses (`34617363701`).
- Target-only delimiter additions: ordinary OPUS beam6/n6 gives a strict-clean alternative only for metadata seq `3`; six substantive cases remain trapped in the same bad model basin (`34616844554`).
- Earlier prime-fragment decomposition, thousands-grouping / narrow `x→×`, compact-formula spacing and broad citation/group coalescing remain rejected because they regressed semantics or failed to rescue the class.

Do not spend more effort on an unchanged OPUS formulation without a materially new source representation/model hypothesis.

## Independent TC-big: row-local differential

Workflow `34621706640`; artifact `10272283502`, digest `sha256:907f34473ed4a6482b505fca68006880f0a8819a1b399ca85a85f467511301fc`.
Evidence file SHA-256 `5c87500453f9443f5aff42d4bfea1bc055b48fa3a2ec747e13ec99581fe16f69`; internal evidence SHA-256 `1e3ce22828f72b2409e1a4093646ef0a74a4dcf9b224b3f59d286011acbebca7`.

Results:
- all `52` run-9 hard rows examined;
- `32/52` have at least one mechanically admissible raw TC-big hypothesis;
- `172` admissible hypotheses total;
- mechanical-only ceiling **24/30/0, 52 unique → 13/8/0, 20 unique**.

This proves substantial model-specific residual debt, but isolated Stage12-row replacement is not safe: a row may be only part of the source sentence/context.

## MetricX remains ranking evidence only

Row-level MetricX workflow `34622530818` scores all 172 mechanically admissible hypotheses. It prefers some TC-big alternative in `30/32` cases and the first admissible alternative in `29/32`. Best ranks span 0–5. No score threshold is a Product acceptance rule.

Whole-context MetricX workflow `34627052164` completed green. Artifact `10274977715`, digest `sha256:899ab34f255b9670f9d9b4ee4f96d7eb459f08b7850708ef8830af6cb1e365f0`; evidence file SHA `911f3d6808bf3bd114fb1c97fda2aef2212ae71a33c52a359aeb468002f6a72f`, internal evidence SHA `37447b126f493a7b7f596d5a2661ee484ebeafcd9d9c2af623a12c9cd2acaf87`.

It scores `18` whole Stage10 contexts / `89` admissible candidates and prefers some TC-big alternative in `16/18`; first admissible also wins in `16/18`. Two contexts score worse than aggregate OPUS. This reinforces, rather than removes, the rule that QE is not an automatic selector.

## CTranslate2 parity correction

The initial CT2 experiment used the wrong tokenizer-side formulation and produced 0/52 parity; that result is retained only as negative evidence about the harness, not about CTranslate2 itself.

Corrected workflow `34626241784` completed green. Artifact `10274549063`, digest `sha256:7098e0a14deaab87a4edee5d63d29015e89973da9c16f9446bd74fb8b9c3e742`; evidence file SHA `01437639b2377a8fb624e16abf6cb2763891e0242f3b91638488ee8e35bed903`, internal evidence SHA `360c5f9b537ef46b2a178d3f3062c1633f5e54a126c59aa51be27ff0eb5f48d8`.

The corrected runtime reproduces Hugging Face Marian semantics exactly on input:
`MarianTokenizer.encode → convert_ids_to_tokens → CTranslate2 translate_batch → convert_tokens_to_ids → decode`.

Results:
- input token parity **52/52**;
- exact rank0 match **49/52**;
- at least one exact hypothesis overlap **52/52**;
- CT2 mechanically admissible cases **32/52**, `169` hypotheses;
- CT2 mechanical ceiling **13/8/0, 20 unique**, identical to the Transformers all-52 ceiling.

Conclusion: a torch-free CTranslate2 inference architecture is viable. Three rank0 ordering differences remain explicit backend-search differences; they are not hidden or normalized away.

## Stage10-context boundary-aware differential

Workflow `34626136705` completed green. Artifact `10273968597`, digest `sha256:f99e9903f80b90997e804a444eaa80b40dbc31ad4258ca287015b3a559201eb6`; evidence file SHA `49d679789207440d5160f044944f4261cc957070462f0cce464e047c955878d3`, internal evidence SHA `9309a2b0d4ed4cf84b4f2efc9a6353cc191a98b2557c26aa19fbc1489c3a0a55`.
Schema `rocketdict-full-opticks-alternative-mt-hard-contexts-run9/2`.

The 52 hard rows map to 50 original Stage10 contexts:
- `49/50` are exactly representable by whole current Stage12 rows;
- context `2480` is the sole non-row-aligned case and is skipped fail-closed;
- no tested context exceeds the model context limit;
- `18` contexts have at least one mechanically admissible whole-context TC-big candidate;
- mechanical-only ceiling **20/16/0, 34 unique**;
- source coverage remains byte-exact and the database remains read-only.

Manual semantic inspection found false positives among those 18, including terminology drift and incomplete/poor translations. Therefore generic strict-clean whole-context TC-big fallback is rejected.

## Source-relative completeness replaces baseline-alpha monotonicity for the alternative-MT experiment

The old rescue heuristic `candidate target alpha >= baseline target alpha` is inappropriate when the baseline itself is inflated by hallucinated content. In run-9 TC-big evidence it rejects multiple obviously useful shorter candidates.

For the alternative-MT delimiter family, completeness is instead constrained against immutable **source** alpha volume. This does not relax the legacy OPUS selectors globally.

## Narrow target-only delimiter context rescue feasibility

Read-only workflow `34627371508` completed green. Artifact `10275510035`, digest `sha256:5c76d7db662c66d86f073c36ab3baf99d739da0c200d7c88e38027b01b2947f6`; evidence file SHA `46e901c87730d1f5ff7d8fa2ae893500b41ea37fd6cc4a691ab573c910b34f13`, internal evidence SHA `ef22c81ecfda624787c61fed7be66ddb39e9ae2c6a426e842a22dc03fb6d2cb9`.

General trigger:
- original Stage10 context contains a current Product-hard failure;
- its source span is exactly replaceable by whole current Stage12 rows;
- aggregate current target adds at least one `()[]{}` delimiter character beyond the immutable source counts.

General candidate requirements:
- raw TC-big hypothesis, no target editing;
- maintained strict mechanical checks all pass;
- Gutenberg emphasis shape preserved;
- target-only delimiter additions eliminated;
- target/source alphabetic ratio in `0.75..1.50`;
- no requirement that candidate alpha exceed the already-corrupt baseline target.

Results:
- `7` contexts trigger;
- `5` pass: Stage10 contexts `3`, `1726`, `1737`, `2066`, `2605`;
- the two harder trigger cases remain fail-closed;
- read-only counterfactual **24/30/0, 52 unique → 24/25/0, 47 unique**;
- no corpus-specific whitelist, source/target rewriting, placeholder or post-translation literal injection.

Manual review of the accepted substantive cases found the TC-big candidate removes OPUS hallucinated material rather than merely hiding a punctuation defect. This supports a default-OFF implementation, not default promotion.

## Implemented optional TC-big Product-Core infrastructure

`alternative_mt_runtime.py` implements a byte-verified offline TC-big CT2 runtime using local MarianTokenizer semantics; `alternative_mt_assets.py` provisions the pinned snapshot to CTranslate2 float32. `rocketdict-assets build-tc-big-en-ru` exposes provisioning. Dependency profiles `alt-mt` and `alt-mt-build` are separate from the baseline `production` extra.

`translation_tc_big_delimiter_rescue_stage.py` implements the feasibility rule as a separate wrapper above the current illustration→numeric→length→citation composition. It is `DEFAULT_ENABLED=False` and is not yet wired into public `product.stage12.run`.

Product Core CI `34628239731` at implementation commit `02e3c8a...` is fully green for dependency-light tests and the real maintained Stage8→25 smoke. Dedicated wrapper tests at commit `aa776b57...` are also fully green in workflow `34629151558`; they prove disabled exact delegation without TC-big runtime probing, the three-part trigger, source-relative ratio/emphasis/delimiter vetoes, non-row-aligned fail-closed geometry, raw-hypothesis provenance, untouched-row copying and byte-exact source reconstruction. Persisted full-*Opticks* validation over exact run `9` remains the next promotion prerequisite.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Preserve immutable source/model/config/result identities.
3. Select only unmodified raw model candidates; no target surgery.
4. Mechanical integrity is necessary but not sufficient; semantic and boundary-aware review is mandatory.
5. A second MT may be invoked only by a narrow failure trigger; clean Product rows must remain untouched unless separate evidence justifies otherwise.
6. Exact source replacement geometry must be representable by complete current rows; otherwise skip fail-closed. Do not slice target strings.
7. MetricX/QE may rank research candidates but is not itself an acceptance threshold.
8. Alternative-MT completeness rules must be source-relative; do not use corrupt baseline verbosity as a universal quality floor.
9. Any Product TC-big role requires deterministic selection, persisted full-corpus regression, byte-exact untouched-row/source checks, offline asset/runtime identities, license attribution and release-size/performance assessment.
10. The TC-big delimiter wrapper remains default OFF/not public-wired until persisted heavy evidence passes. Persisted success still does not by itself authorize Product-default promotion.
11. Final approved heavy evidence still requires zero unresolved hard failures.
