# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`
- Engineering branch: `chatgpt/product-core-forward`
- L3 checkpoint incorporated by this refresh: `9c3b454eaa815b3033ea79a8de7bafff02edbe1c`
- Maintained Product Core + Workbench remain the forward implementation.
- Authoritative Product target: `rocketdict/PRODUCT_TARGET.md`; final approved heavy evidence requires zero unresolved hard translation failures.
- Current persisted full-*Opticks* residual basis is Stage12 run `9`: **24 numeric/symbol / 30 punctuation / 0 length**, **52 unique failures**.
- Default Product behavior has not been broadened. Length/citation rescues remain public opt-in/default-OFF; numeric-hard and illustration rescues remain separate default-OFF wrappers and are not public-wired.
- Current research frontier is no longer generic OPUS fallback. Recent evidence shows several remaining families are stable baseline-model defects, and the next active experiment is a pinned independent TC-big differential over all 52 current run-9 hard-failing rows.

## Recovery protocol

Follow `AGENTS.md`: compare current HEAD with the checkpoint above, route through `docs/memory/INDEX.md`, and use source/tests/CI/artifacts as L3 authority. If only this memory refresh follows the checkpoint, no engineering drift is implied.

## Maintained translation contracts

- Real EN→RU baseline: pinned OPUS `opus-2020-02-11` → CTranslate2 Marian `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`.
- Block section IDs: `rocketdict-stage12-block-section-identifier/1`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`.
- Length rescue: `rocketdict-stage12-length-failure-whole-context-rescue/1`, default OFF.
- Citation-pair rescue: `rocketdict-stage12-citation-boundary-pair-rescue/1`, default OFF.
- Numeric-hard whole-context rescue: `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1`, default OFF and not public-wired.
- Illustration-label rescue: `rocketdict-stage12-illustration-label-rescue/1`, default OFF and not public-wired.
- Gutenberg emphasis preservation: `rocketdict-maintained-emphasis-markup-preservation/1`, research veto rather than Product hard gate.
- Pinned research alternative MT: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, research-only until full-corpus evidence and semantic review justify any Product role.

## Canonical full-Opticks evidence

Pinned source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; source length `586543` characters.

Structural-label `/2` baseline: Stage12 run `4`, **30/34/5**, **64 unique**.
Length+pair-citation composition: run `7`, **29/34/0**, **59 unique**.
Numeric-hard composition: run `8`, **25/33/0**, **55 unique**.

Validated illustration-label composition:
- research v3 workflow `34609890716`, artifact `10267328730`;
- Product Core CI `34610493157` green;
- persisted workflow `34610787826`, artifact `10268850347`;
- Stage12 run `9`, output SHA `c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be`;
- SQLite SHA `9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad`;
- `3346` segments; **24/30/0**, **52 unique**; byte-exact source coverage, untouched rows base-exact, SQLite integrity clean, no target rewrite/placeholders/literal injection.

## Current negative OPUS evidence after run 9

### Block footnotes

Marker-only `[G]/[H]/[J]/[K]/[M]` retranslation mechanically reached **24/25/0, 47 unique** but is rejected semantically (`shewn`→`сшито`, `_See our_`→`Посмотри на нас`).

Corrected whole-footnote-context workflow `34615540238`, artifact `10269324277`, digest `8320b32015600e90ea06a1aba781e928cb0efc8e365bd6539cebddd249e0d264`, evidence file SHA `87474bdc7177b701c03bf9f0dc860d79db297daa1dc4b24a00935f10cb9d7c1a`, internal evidence SHA `6226b469de51b68dcbbb7a90473ee6aa618903104b9098b722d34fefeb5db652`: **0/30** beam6/n6 candidates survive strict+emphasis checks; gates stay **24/30/0, 52 unique**.

Depth DOE workflow `34615819431`, artifact `10269174895`, digest `d710734a482d9172020a183f86e979d35900793c6418f5e5511d59f523acfaf2`, evidence SHA `e6ea6ded3f9443f2e3d4cce2798095e2c5a910cf5f252b260e3ca141f9f9003e`: beam/n-best `6/6`, `12/12`, `24/24`, **210 raw hypotheses total, 0 mechanically admissible**. Do not spend further effort on the same exact-source OPUS n-best formulation without a new representation/model hypothesis.

### Question-mark migration context 2730

Whole exact Stage10 context is 339 NLP tokens, above the maintained 160-token whole-context cap. Workflow `34616386780`, artifact `10270386478`: **0/6** whole-context raw candidates admissible; long OPUS output degrades/truncates semantically.

Two disjoint <=160-token windows were tested in workflow `34616665018`, artifact `10270681641`, digest `f09217edc12af92cd53796eeba7c7433aa34dc494f7303fac8320801f0eb2a27`. Opening 138-token window has a mechanically admissible rank0 and counterfactually gives **24/29/0, 51 unique**, but semantic inspection shows repetition/distortion. Closing 132-token window has no admissible candidate and loses context toward `Lead?`. Do not Productize this pair formulation.

### Square-bracket losses and target-only delimiter hallucinations

Square-bracket-loss workflow `34617363701`, artifact `10270323366`, digest `73f939111f70e60ef677eee55f0898fee88d6646c81c49d4eaa9a1b5dab28780`, evidence SHA `76d578c3de6db93a0ebc3a3658077beff402e11c4b4530c532a4b1bc03f738a8`: four current rows (`[in Fig.]`, inline `[G]`, `[Greek:a]` family), **0/24** raw OPUS hypotheses admissible; gates unchanged.

Target-only delimiter-addition workflow `34616844554`, artifact `10271426528`, digest `5d9d1829d7d316b458378fa45acb5e8bda468c04a9078ed0bc641491b8d06fd8`, evidence SHA `465d2fca5e0787ad23210858dc1db3e37c004be141b7f56d010f3d5c5b1f0abd`: among seven rows, only metadata seq `3` has strict-clean OPUS n-best alternatives (first rank2); six substantive hallucination rows remain trapped in the same bad OPUS beam basin. Mechanical counterfactual from applying only seq3 is **24/29/0, 51 unique** and is too narrow to justify Product policy by itself.

## Alternative-MT evidence

Pinned TC-big delimiter differential workflow `34617224048`, artifact `10271482215`, digest `1c1e5cda7283171acd732431133b13acbe4a27e9406fb1da1b085325123db7a5`, evidence file SHA `77afbcd5e406f54fd71c66e493d6636ab3788f342ab075f924622d7e7176fe8c`, internal evidence SHA `e39bcd40219edc642f8e8179669ff0ece3f024b8260cd443abf2b8ef431db798`:
- strict-clean raw alternatives exist for 6/7 tested delimiter-addition rows (`3,1864,1878,2219,2382,2862`);
- seq `3220` remains without a strict-clean candidate;
- most importantly, TC-big rank0 removes the OPUS religious/domain hallucinations in seq `1864`, `2219`, `2862` rather than merely deleting punctuation.

This is strong evidence that part of the remaining frontier is baseline-model-specific rather than a planner/evaluator defect. It does **not** yet authorize automatic fallback or a second Product dependency.

## Active next action

`rocketdict-workbench/tests/real_translation_full_opticks_alternative_mt_current_hard_failures_run9.py` now defines a read-only TC-big screen over all 52 run-9 hard-failing rows. The next step is to add/run a pinned workflow for that script, retain all six raw hypotheses per row, compute the mechanical upper bound, then classify/semantically review survivor families before designing any second-model Product fallback.

## Guardrails

- Do not weaken hard/strict/emphasis gates to turn negative OPUS branches green.
- Do not reclassify bare Roman fragments as headings.
- Context `2725` remains proof that generic whole-context mechanical cleanliness can hide semantic loss.
- No target literal injection, corpus-specific target patching, placeholders, source rewriting or punctuation deletion repair.
- A second MT may only enter Product if a source-defined failure trigger, pinned model/runtime identity, deterministic raw candidate selection, semantic evidence, persisted full-corpus regression and release/runtime implications are all addressed.

## Hot paths

- `rocketdict-product-core/src/rocketdict/translation_stage.py`
- `rocketdict-product-core/src/rocketdict/translation_numeric_hard_rescue_stage.py`
- `rocketdict-product-core/src/rocketdict/translation_illustration_rescue_stage.py`
- `rocketdict-product-core/src/rocketdict/emphasis_markup.py`
- `rocketdict-product-core/src/rocketdict/translation_rescue.py`
- `rocketdict-product-core/src/rocketdict/api/operations.py`
- `rocketdict-workbench/tests/real_translation_full_opticks_alternative_mt_current_hard_failures_run9.py`
- `.github/workflows/rocketdict-full-opticks-*run9.yml`
