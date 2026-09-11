# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`
- Engineering branch: `chatgpt/product-core-forward`
- Engineering/L3 checkpoint incorporated by this refresh: `5ed391d795d212bfd085b7e435c20b31b43b4ace` (`Run short angular DMS TC-big feasibility`).
- Maintained Product Core + Workbench are the forward implementation. Authoritative Product contract: `rocketdict/PRODUCT_TARGET.md`.
- Final approved heavy translation evidence still requires **0 unresolved hard numeric/symbol, punctuation and length failures** on the complete 90k+ corpus; current work is intermediate research, not release completion.
- Current accepted persisted full-*Opticks* research residual basis is Stage12 run `14`: **22 numeric/symbol / 18 punctuation / 0 length, 39 unique failures** over `3344` rows.
- TC-big delimiter, footnote-reference, figure-reference, semicolon→question and target-only-equals rescue layers have persisted full-corpus evidence but remain default OFF/not public-wired.
- A sixth default-OFF/not-public-wired wrapper for the narrow single-prime angular-minute case has a green persisted audit over run `14`; it produces research run `15` with **21/18/0, 38 unique** and changes exactly one row, but `promotion_allowed=false` and Product defaults remain unchanged.
- A seventh default-OFF wrapper for short standalone DMS angle statements (`D deg. M'. S''`) is implemented and unit-tested. A dedicated read-only full-*Opticks* feasibility workflow is currently the active gate; no persisted DMS correction or default promotion is authorized yet.

## Recovery protocol

Follow `AGENTS.md`: compare current HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; source/tests/CI/artifacts are L3 authority. If HEAD differs only by mandatory memory synchronization, no engineering drift is implied.

## Maintained identities

- OPUS baseline: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`.
- Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1` rescue veto.
- Pinned TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, license `CC-BY-4.0`.
- TC-big offline asset `rocketdict-tc-big-en-ru-asset/1`; accepted manifest SHA `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload-tree SHA `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`, 11 files / 968529922 bytes; inference is offline and Torch-free.
- Default-OFF/not-public-wired TC-big wrappers now include:
  - `rocketdict-stage12-tc-big-target-delimiter-context-rescue/1`
  - `rocketdict-stage12-tc-big-footnote-reference-lead-rescue/1`
  - `rocketdict-stage12-tc-big-figure-reference-lead-rescue/1`
  - `rocketdict-stage12-tc-big-semicolon-question-substitution-rescue/1`
  - `rocketdict-stage12-tc-big-target-only-equals-addition-rescue/1`
  - `rocketdict-stage12-tc-big-angular-minute-prime-rescue/1`
  - `rocketdict-stage12-tc-big-short-angular-dms-rescue/1`

## Canonical full-Opticks evidence

Pinned source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` characters.

Persisted progression through the current basis:
- run `4`: **30/34/5**, 64 unique;
- run `7`: **29/34/0**, 59 unique;
- run `8`: **25/33/0**, 55 unique;
- run `9`: **24/30/0**, 52 unique;
- run `10`: **24/25/0**, 47 unique;
- run `11`: **24/20/0**, 42 unique;
- run `12`: **23/19/0**, 41 unique;
- run `13`: **23/18/0**, 40 unique;
- run `14`: **22/18/0**, 39 unique.

### Run 14 — target-only equals addition

Heavy workflow `34643230375` is green; artifact `10280349240`.
- base run `13` → enabled run `14`;
- output SHA `12e1fe77ab8df3959b4bb9265292cdc5b9db279797d94e2f15df6482429e2c44`;
- persisted SQLite SHA `dfce68a8f7cae08b90380630ae29e31418b4d6e8987d3e7001fe72fa1d781304`;
- 1 attempt / 1 raw rank0 accept / 0 rejects at source start `107711`;
- selected source is the algebraic sentence beginning `And by squaring these Equals...`; the raw TC-big candidate preserves the algebraic variables/relations and removes the target-only `=` hallucination without target surgery;
- 3343 untouched rows exact, byte-exact source coverage and SQLite integrity are verified;
- evidence remains non-promoting/default-OFF.

### Angular-minute persisted audit — research run 15

Workflow `34643812392` is green; artifact `10281555120`.
- exact base is run `14` above;
- enabled output SHA `0e0ebb851e43079b3029a2a2638d0dc0ff5eb45bebd6c91895cb04483349fb45`;
- persisted SQLite SHA `bfb131c43c37276a906044cc23908251e1526b9943d2c54eac5bf409b6b64630`;
- hard counts **22/18/0,39 → 21/18/0,38 unique**;
- exactly one attempt/accept at source start `431358`, raw rank0 target `В то же время появляется гало на расстоянии около 22 градусов 35' от центра Луны.`;
- 3343 untouched rows exact, no source/target rewriting, placeholders, literal injection or corpus patching;
- this is persisted default-OFF research evidence only; automatic/default/public promotion is explicitly false.

### Boundary evidence relevant to the next residual family

Read-only workflow `34644023517` proved that the falsely split `whence is it | but from ... ?` pair has six strict + semantic TC-big hypotheses when translated as one exact contiguous source span. The experiment is non-promoting and does not by itself authorize a new wrapper.

The short standalone DMS residual at source start `110881` is exact source `Whence this Angle is 2 deg. 0'. 7''. ` with current run-14 target `Откуда угол 2 градуса. 0 футов 7 футов.`. The defect is a genuine prime-notation/measurement interpretation failure (`'`/`''` became feet), not an evaluator-only false positive. The implemented DMS trigger requires exact single-row Stage10 geometry, exactly one DMS expression, the source word `Angle`, <=12 alphabetic words, an existing hard failure and broken prime preservation. Its selector accepts only raw TC-big hypotheses with exact D/M/S prime preservation, Russian angle/degree semantics, strict mechanics, emphasis preservation and conservative source-relative length.

## Durable guardrails

- Generic OPUS/TC-big whole-context fallback remains rejected: mechanically clean candidates can lose or distort meaning.
- Exact Stage10 replacement requires complete current-row geometry; non-aligned contexts skip fail-closed.
- Mechanical integrity is necessary but not sufficient; semantic constraints/review remain mandatory.
- MetricX/QE is ranking evidence only.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches or evaluator weakening.
- Punctuation/numeric work proceeds by source-defined defect family; no universal fixer.
- A persisted corpus improvement does not by itself authorize a Product default.

## Active next actions

1. Finish the read-only short-DMS feasibility gate on exact run `14` and inspect all six raw TC-big hypotheses.
2. Only if at least one candidate passes strict + DMS-semantic selection, run a persisted composed audit over exact run `14` with both the already-proven angular-minute wrapper and the DMS wrapper enabled; require no new hard failures, exact untouched rows/source coverage and SQLite integrity.
3. Keep both wrappers default OFF/not public-wired unless broader evidence justifies promotion.
4. Rebuild the residual inventory from the latest verified persisted research basis and continue by the next source-defined defect family toward the Product requirement of zero unresolved hard failures.
