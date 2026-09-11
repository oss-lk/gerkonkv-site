# RocketDict maintained translation quality — L2

This file stores durable conclusions from maintained Product translation-quality work. It is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Source/tests/CI/artifacts are L3 authority and outrank this summary if they disagree.

## Maintained contracts

- Production baseline MT: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`; bare Roman sentence fragments are not headings.
- Block section identifier: `rocketdict-stage12-block-section-identifier/1`.
- Numeric/symbol hard gate: `rocketdict-maintained-numeric-integrity/5` over every selected Stage12 row.
- Length rescue: `rocketdict-stage12-length-failure-whole-context-rescue/1`, default OFF.
- Citation-pair rescue: `rocketdict-stage12-citation-boundary-pair-rescue/1`, default OFF.
- Numeric-hard whole-context rescue: `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1`, default OFF/not public-wired.
- Illustration-label rescue: `rocketdict-stage12-illustration-label-rescue/1`, default OFF/not public-wired.
- Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`, a rescue veto rather than a Product hard gate.
- Independent MT: pinned `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, `model.safetensors` SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0.
- Optional TC-big asset: `rocketdict-tc-big-en-ru-asset/1`; CTranslate2 float32 plus exact local MarianTokenizer snapshot. Runtime verifies repository/revision/source-weight/license plus manifest SHA and complete payload-tree SHA/count/bytes. Inference is offline and Torch-free.
- TC-big target-delimiter rescue: `rocketdict-stage12-tc-big-target-delimiter-context-rescue/1`, selector `/1`, trigger `/1`, default OFF/not public-wired.
- TC-big footnote-reference lead rescue: `rocketdict-stage12-tc-big-footnote-reference-lead-rescue/1`, selector `/1`, trigger `/1`, default OFF/not public-wired.

## Canonical contiguous Opticks evidence

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` source characters.

Persisted progression:
- run `4`: **30 numeric / 34 punctuation / 5 length**, **64 unique**;
- run `7`: **29/34/0**, **59 unique**;
- run `8`: **25/33/0**, **55 unique**;
- run `9`: **24/30/0**, **52 unique**;
- run `10`: **24/25/0**, **47 unique**.

### Current persisted residual basis: run 10

CPU-provisioning heavy workflow `34631662056` completed green. Artifact `10276009101`, digest `sha256:21e374f3b9863ef35b04220118c3326b860d6506e16116a0242310a7236d24e1`.

Run-10 identities:
- Stage12 output SHA `6dec2080a8fe21716587e4f4ffbe1f8ebf816911b542ab99ac598a8462ed01df`;
- persisted SQLite SHA `4a5bd2159c1aca0b5bcf5580d7aa0d767f0faedd2b1dcdaef92dab96a36d3087`;
- evidence file SHA `e5787def5adcd6780115ea13fa3fa90637494221246fd36afcc292071975e1a8`;
- internal evidence SHA `494379a1b4f0e98f9c0cc336864231418d5c7587b4a5a5983a55fe425e383b20`;
- `3344` selected rows;
- accepted source starts `[488, 325892, 329077, 388656, 501398]`, all selected at raw TC-big rank `0`.

The wrapper composes over exact run `9`; source coverage is byte-exact, 3339 unaffected run-9 rows are source/target/span exact, selected targets are exact raw hypotheses, SQLite integrity/foreign keys are clean, and source/target rewrite, placeholders, post-translation literal injection and corpus-specific target patching are all false.

The same persisted output was reproduced in the earlier heavy run `34631528054`. The two runs agree on run ID `10`, output SHA, selected ranks/targets and asset payload identity. SQLite file hashes may differ because persisted database metadata contains run-time timestamps; semantic/run output identity is the deterministic comparison surface.

Pinned TC-big asset used by run 10:
- manifest SHA `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`;
- payload-tree SHA `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`;
- `11` payload files, `968529922` bytes;
- builder uses pinned CPU Torch; inference runtime contains no Torch.

Manual review of the five persisted delimiter replacements found the intended semantic improvement: the substantive cases remove severe OPUS hallucinated material (including spurious religious vocabulary such as Allah/Quran/Muhammad) and restore physically relevant clauses. Some Russian phrasing remains stylistically rough, so this is persisted quality progress, not Product-default promotion.

## Independent TC-big research conclusions

All-52 row-local screen `34621706640`: `32/52` run-9 hard rows have at least one mechanically admissible raw TC-big hypothesis (`172` admissible hypotheses); the mechanical-only ceiling was **13/8/0, 20 unique**. Isolated row substitution remains rejected because a Stage12 row may be only a fragment of its source sentence/context.

Corrected CTranslate2 parity workflow `34626241784`: input-token parity `52/52`, exact rank0 `49/52`, at least one exact n-best overlap `52/52`, and the same 32 mechanically admissible cases / **13/8/0, 20 unique** ceiling. The initial 0/52 CT2 result was a tokenizer-harness defect, not model evidence. Correct runtime semantics are `MarianTokenizer.encode → ids-to-tokens → CTranslate2 → tokens-to-ids → decode` with `>>rus<<`.

Whole Stage10 context audit `34626136705`: 52 hard rows map to 50 Stage10 contexts; `49/50` are exactly replaceable by complete current rows, context `2480` is non-row-aligned and must be skipped fail-closed. Generic whole-context TC-big produced mechanically clean but semantically poor/partial candidates, so broad second-model fallback remains rejected.

MetricX/QE is research ranking evidence only. Row-level and whole-context QE often prefer TC-big, but neither absolute score nor preference is an acceptance threshold and QE cannot override source-boundary or semantic vetoes.

## Narrow target-only delimiter rescue

The source-defined trigger requires a row-aligned Stage10 context that contains a current hard failure and whose aggregate current target adds one or more `()[]{}` delimiters beyond immutable source counts. Candidate acceptance requires an unmodified raw TC-big hypothesis, all maintained strict mechanical checks, Gutenberg emphasis preservation, no target-only delimiter additions, and target/source alphabetic ratio `0.75..1.50`.

Read-only feasibility workflow `34627371508` triggered on 7 run-9 contexts and accepted 5 (`3`, `1726`, `1737`, `2066`, `2605`), predicting **24/25/0, 47 unique**. Persisted run `10` subsequently confirmed that prediction exactly. The wrapper remains default OFF and not public-wired.

## Narrow Gutenberg footnote-reference lead rescue

`translation_tc_big_footnote_reference_rescue_stage.py` implements a separate wrapper above the delimiter layer. Its source class is general rather than a letter whitelist: an exact single-Stage10/current-Stage12 row whose entire immutable source matches `[A-Z] _..._`, is currently Product-hard-failing, and no longer preserves the exact ASCII marker. A candidate must be a raw TC-big hypothesis, restore the exact marker, pass strict mechanical checks, preserve emphasis shape and stay within source-relative alpha ratio `0.70..2.00`.

Dedicated Product Core workflow `34632793371` is fully green, including dependency-light tests and real maintained Stage8→25 plus unified Product smoke. Tests cover disabled exact delegation without runtime probing, clean-reference non-triggering, exact marker restoration, emphasis/ratio vetoes, exact Stage10 geometry, raw-hypothesis provenance, untouched-row copying and source coverage.

The first persisted heavy attempt `34632917048` is **not** evidence of translation failure. The wrapper actually persisted run `11` with:
- 5 attempts, 5 accepts, 0 rejects;
- accepted source starts `[151466, 151557, 253849, 253919, 254102]`;
- all selected ranks `0`;
- raw targets `[G] _Это продемонстрировано в нашем_`, `[H] _Как это сделать, показано в нашем_`, `[J] _Смотрите наш_`, `[K] _Как это делается в нашем_`, `[M] _Это продемонстрировано в нашем_`;
- output SHA `ef38b21e7e7e384a00310123fd9f16ec10045b0741605867ad15f559f15c08c3`.

The workflow failed before independent gate verification because the audit harness used `int(rejected_count or -1)`, so the correct zero reject count became `-1`. This is an audit/orchestration defect. Do not alter the selector or acceptance rule to address it. Fix the zero-handling assertion and rerun the persisted audit; only a green independent recount may promote run `11` to the residual basis.

## Exhausted / rejected branches still binding

- OPUS whole-footnote/n-best formulations produced no safe candidate for the hard `[G]/[H]/[J]/[K]/[M]` class; the new footnote work is materially different because it uses an independently pinned model and exact source-owned reference-lead structure.
- Whole-context mechanical cleanliness can hide semantic loss (`2725`) and other regressions; generic OPUS or TC-big whole-context fallback remains unsafe.
- Context `2730` whole/pair formulations are unsafe.
- Current square-bracket-loss OPUS formulation had `0/24` admissible hypotheses.
- Prime decomposition, thousands grouping/narrow `x→×`, compact-formula spacing and broad citation/group coalescing remain rejected.
- Never use target literal injection, corpus-specific target patching, placeholders, source rewriting, target surgery or evaluator weakening.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Preserve immutable source/model/config/result identities.
3. Select only unmodified raw model candidates; no target surgery.
4. Mechanical integrity is necessary but not sufficient; semantic and boundary-aware review is mandatory.
5. A second MT may be invoked only by a narrow hard-failure/source-defined trigger; clean Product rows remain untouched unless separately justified.
6. Exact replacement geometry must be representable by complete current rows; otherwise skip fail-closed.
7. MetricX/QE is ranking evidence only.
8. Alternative-MT completeness checks are source-relative; corrupt baseline verbosity is not a universal floor.
9. Any TC-big Product role requires deterministic selection, persisted full-corpus regression, exact untouched/source checks, offline asset identities, license attribution and release-size/performance assessment.
10. TC-big rescue wrappers remain default OFF/not public-wired. Persisted success does not itself authorize Product-default promotion.
11. Final approved heavy evidence still requires zero unresolved hard failures.
