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
- Optional TC-big asset: `rocketdict-tc-big-en-ru-asset/1`; exact MarianTokenizer snapshot + CTranslate2 float32; accepted manifest SHA `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload-tree SHA `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`, 11 files / 968529922 bytes. Inference is offline and Torch-free.
- Narrow TC-big wrappers, all default OFF/not public-wired:
  - target-delimiter: `rocketdict-stage12-tc-big-target-delimiter-context-rescue/1`;
  - footnote-reference lead: `rocketdict-stage12-tc-big-footnote-reference-lead-rescue/1`;
  - figure-reference lead: `rocketdict-stage12-tc-big-figure-reference-lead-rescue/1`;
  - semicolon→question substitution: `rocketdict-stage12-tc-big-semicolon-question-substitution-rescue/1`;
  - target-only equals addition: `rocketdict-stage12-tc-big-target-only-equals-addition-rescue/1`.

## Canonical contiguous Opticks evidence

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` source characters.

Persisted progression:
- run `4`: **30 numeric / 34 punctuation / 5 length**, **64 unique**;
- run `7`: **29/34/0**, **59 unique**;
- run `8`: **25/33/0**, **55 unique**;
- run `9`: **24/30/0**, **52 unique**;
- run `10`: **24/25/0**, **47 unique**;
- run `11`: **24/20/0**, **42 unique**;
- run `12`: **23/19/0**, **41 unique**;
- run `13`: **23/18/0**, **40 unique**.

### Current persisted residual basis: run 13

Heavy workflow `34639494681` completed green. Artifact `10279502482`, digest `sha256:88dcd100745530a67add70faeedf27d5a623f597eaea03044530cfc4f5b923ef`.

Run-13 identities:
- base run `12` output SHA `57a8d2d519bf236c04b91d75b775a22b12f2a4c429cfc278ce6dba05c74a4063`;
- Stage12 run `13` output SHA `2fda987f054681a6561272d4c802980f498d9a01019a43c2c9bd2c7bbfb7f4c7`;
- persisted SQLite SHA `97ffae9254ac49e004ab372a5edb1e87ec045b39d8480bc086a99456bd5418a3`;
- evidence JSON file SHA `4a9ce328a8c2f20179a3b6e00da01afe6a282bab2aae38b987d8c6d432eb352b`;
- internal evidence SHA `8c1d13fb8a762dc1ed1c17079ba9bd14a6d2835ed7048319ec5d133a73be52e6`;
- `3344` selected rows;
- 1 attempt / 1 accept / 0 rejects at source start `382298`, selected rank `0`.

The run composes over exact run `12`; source coverage is byte-exact, 3343 unaffected rows are source/target/span exact, selected target is the exact raw TC-big rank0 hypothesis, SQLite integrity/foreign keys are clean, and source/target rewrite, placeholders, post-translation literal injection and corpus-specific target patching are all false.

The accepted source is Newton's sentence beginning `What kind of action or disposition this is; ... I do not here enquire.` The OPUS target converted the semicolon structure into a false question. TC-big preserves the semicolon, removes the invented question mark and retains the alternatives `Ray / Medium / something else`. Manual semantic review found the raw candidate materially more faithful. Russian wording is not polished literary translation, so this remains research-quality persisted improvement rather than default-promotion evidence.

## Persisted TC-big rescue layers

### Target-only delimiter hallucination — run 10

Run `10` is the first persisted TC-big layer: **24/30/0,52 → 24/25/0,47**. Source trigger requires exact Stage10 geometry and target-only `()[]{}` additions; raw candidates must pass maintained strict gates, emphasis preservation, zero added delimiters and source-relative alpha `0.75..1.50`. Manual review found removal of severe OPUS hallucinated content, including spurious religious vocabulary. Generic TC-big fallback remains rejected.

### Gutenberg footnote-reference leads — run 11

Corrected heavy workflow `34638137163` is green; artifact `10279415117`, digest `sha256:a49983989472444fd6a6924035d57e66bb2b712916cf515448e29a49b04b3d6c`.

- run `11` output SHA `ef38b21e7e7e384a00310123fd9f16ec10045b0741605867ad15f559f15c08c3`;
- SQLite SHA `329ed0cebe7b3af42b88b50f602c3bba3227fd75704e1e48fea4b1651169ded8`;
- 5 attempts / 5 raw rank0 accepts / 0 rejects;
- starts `[151466,151557,253849,253919,254102]`;
- final gates **24/20/0,42 unique**;
- 3339 untouched rows exact and source coverage byte-exact.

The earlier red workflow was an audit bug only: `int(rejected_count or -1)` converted valid `0` to `-1`. Product selector semantics were not changed to fix it. Context review confirmed each short accepted lead continues into following source rows as a bibliography/reference sentence, so the apparent fragmentary target is structural, not model truncation.

### Leading `[in _Fig._ N.]` reference — run 12

Heavy workflow `34638917374` is green; artifact `10279171721`, digest `sha256:96579405a7c1d620631c904df90495e53b542e098ed22f34210b937837f40f83`.

- run `12` output SHA `57a8d2d519bf236c04b91d75b775a22b12f2a4c429cfc278ce6dba05c74a4063`;
- SQLite SHA `9d8f277651e1b6fef26de70479a088afbe9e0f8bd8c743ec3a4742914c0d217d`;
- 2 attempts, one raw rank0 accept at start `228046`, one fail-closed reject;
- final gates **23/19/0,41 unique**;
- 3343 untouched rows exact, source coverage byte-exact.

The rule does not know corpus-specific figure numbers. It recognizes a source-defined leading Gutenberg reference, requires exact reference number/emphasis preservation and maintained strict checks. `Fig.15` passed; `Fig.16` failed closed under the same selector.

### Semicolon→question substitution — run 13

The trigger is deliberately narrower than “question mark mismatch”: exact single Stage10/current Stage12 sentence, source terminal period, at least one source semicolon, zero source question marks, current hard failure with lost semicolon(s) and added `?`. Candidate must restore semicolon count, restore source question count, preserve terminal period, pass strict mechanics/emphasis and source-relative alpha `0.75..1.50`.

This geometry excludes the incomplete `And whence is it` residual by construction. Run `13` confirms one safe raw candidate and reduces punctuation by exactly one with no numeric/length regression.

## Active target-only equals hypothesis

`translation_tc_big_equals_addition_rescue_stage.py` implements a separate default-OFF wrapper above run-13 composition. Trigger requirements:
- exact single Stage10/current Stage12 row;
- row already fails a Product hard gate;
- immutable source has zero `=`;
- current target adds one or more `=`.

Candidate requirements:
- unmodified raw TC-big n-best hypothesis;
- maintained `strictly_eligible` mechanical pass;
- Gutenberg emphasis preservation;
- exact source equals count (zero for this trigger);
- source-relative alpha `0.75..1.50`.

Product Core workflow `34639617628` is fully green for the implementation/tests. This is **not yet persisted full-corpus evidence**.

The corpus scan found two target-only equals failures. Exact geometry excludes historical context `2725` / `_per deliquium_`, the known semantic-loss counterexample. The remaining row-aligned case has a mechanically clean TC-big hypothesis, but mathematical terminology is suspect: `Square of the Sine` may become `площадь Сина`. Therefore mechanical acceptance must not be converted into run `14` without explicit semantic evaluation; if the candidate is terminologically wrong, the current selector is insufficiently semantic and should remain unpersisted/rejected or gain a source-defined semantic constraint rather than a corpus patch.

## Independent TC-big research conclusions

All-52 row-local screen showed many mechanically admissible candidates, and corrected CTranslate2 parity reproduced HF behavior closely. This proved the second model is useful evidence but not a generic fallback. A Stage12 row may be only a fragment of its source context, and whole-context experiments produced mechanically clean semantic failures. Exact Stage10 replacement geometry is therefore mandatory.

MetricX/QE remains research ranking evidence only. It may rank immutable raw candidates but neither absolute score nor preference is an acceptance threshold and it cannot override source-boundary or semantic vetoes.

## Exhausted / rejected branches still binding

- Generic OPUS/TC-big whole-context fallback: rejected; context `2725` proves mechanical cleanliness can hide content loss.
- Context `2730` broad whole/pair formulations: unsafe.
- Broad square-bracket-loss OPUS formulation: no admissible safe cohort.
- Prime decomposition/normalization: semantic corruption (`degree`/prime notation); do not revive unchanged.
- Thousands grouping / narrow `x→×`, compact-formula spacing, broad citation/group coalescing: rejected/ineffective.
- Never use target literal injection, corpus-specific target patching, placeholders, source rewriting, target surgery or evaluator weakening.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Preserve immutable source/model/config/result identities.
3. Select only unmodified raw model candidates; no target surgery.
4. Mechanical integrity is necessary but not sufficient; semantic and boundary-aware review is mandatory.
5. A second MT may be invoked only by a narrow existing-hard-failure/source-defined trigger; clean Product rows remain untouched unless separately justified.
6. Exact replacement geometry must be representable by complete current rows; otherwise skip fail-closed.
7. MetricX/QE is ranking evidence only.
8. Alternative-MT completeness checks are source-relative; corrupt baseline verbosity is not a universal floor.
9. Any TC-big Product role requires deterministic selection, persisted full-corpus regression, exact untouched/source checks, offline asset identities, license attribution and release-size/performance assessment.
10. TC-big rescue wrappers remain default OFF/not public-wired. Persisted success does not itself authorize Product-default promotion.
11. Final approved heavy evidence still requires zero unresolved hard failures.
