# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`
- Engineering branch: `chatgpt/product-core-forward`
- Engineering/L3 checkpoint incorporated by this refresh: `44eb4dde317a217c045b18a347d8079e7d8bad2b` (`Run composed angular DMS full-corpus audit`).
- Maintained Product Core + Workbench are the forward implementation. Authoritative Product contract: `rocketdict/PRODUCT_TARGET.md`.
- Final approved heavy translation evidence still requires **0 unresolved hard numeric/symbol, punctuation and length failures** on the complete 90k+ corpus; current work is intermediate research, not release completion.
- Current best persisted full-*Opticks* research basis is Stage12 run `16`: **20 numeric/symbol / 18 punctuation / 0 length, 37 unique failures** over `3344` rows.
- TC-big delimiter, footnote-reference, figure-reference, semicolon→question, target-only-equals, angular-minute and short-DMS rescue layers have full-corpus or composed persisted evidence, but all remain default OFF/not public-wired and non-promoting.
- The next frontier is not another phrase-specific translation patch: one punctuation residual (`And whence is it | but from ... ?`) is already split upstream by Stage8 NLP/Stage10 despite no terminal source punctuation. A corpus-wide Stage10 inventory found only five simple `no terminal punctuation + lowercase continuation` boundaries, so the next research task is to determine whether a generic, fail-closed sentence-boundary repair belongs upstream.

## Recovery protocol

Follow `AGENTS.md`: compare current HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; source/tests/CI/artifacts are L3 authority. If HEAD differs only by mandatory memory synchronization, no engineering drift is implied.

## Maintained identities

- OPUS baseline: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`.
- Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1` rescue veto.
- Pinned TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, license `CC-BY-4.0`.
- TC-big offline asset `rocketdict-tc-big-en-ru-asset/1`; manifest SHA `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload-tree SHA `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`, 11 files / 968529922 bytes; inference is offline and Torch-free.
- Default-OFF/not-public-wired TC-big wrappers include:
  - `rocketdict-stage12-tc-big-target-delimiter-context-rescue/1`
  - `rocketdict-stage12-tc-big-footnote-reference-lead-rescue/1`
  - `rocketdict-stage12-tc-big-figure-reference-lead-rescue/1`
  - `rocketdict-stage12-tc-big-semicolon-question-substitution-rescue/1`
  - `rocketdict-stage12-tc-big-target-only-equals-addition-rescue/1`
  - `rocketdict-stage12-tc-big-angular-minute-prime-rescue/1`
  - `rocketdict-stage12-tc-big-short-angular-dms-rescue/1`

## Canonical full-Opticks evidence

Pinned source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` characters.

Persisted progression:
- run `4`: **30/34/5**, 64 unique;
- run `7`: **29/34/0**, 59 unique;
- run `8`: **25/33/0**, 55 unique;
- run `9`: **24/30/0**, 52 unique;
- run `10`: **24/25/0**, 47 unique;
- run `11`: **24/20/0**, 42 unique;
- run `12`: **23/19/0**, 41 unique;
- run `13`: **23/18/0**, 40 unique;
- run `14`: **22/18/0**, 39 unique;
- run `15`: **21/18/0**, 38 unique;
- run `16`: **20/18/0**, 37 unique.

### Run 14 — target-only equals addition

Workflow `34643230375`, artifact `10280349240`, output SHA `12e1fe77ab8df3959b4bb9265292cdc5b9db279797d94e2f15df6482429e2c44`, SQLite SHA `dfce68a8f7cae08b90380630ae29e31418b4d6e8987d3e7001fe72fa1d781304`. It changes exactly source start `107711`, preserves 3343 untouched rows, byte-exact source coverage and SQLite integrity, and remains non-promoting/default-OFF.

### Run 15 — angular-minute research layer

Workflow `34643812392`, artifact `10281555120`, output SHA `0e0ebb851e43079b3029a2a2638d0dc0ff5eb45bebd6c91895cb04483349fb45`, SQLite SHA `bfb131c43c37276a906044cc23908251e1526b9943d2c54eac5bf409b6b64630`. It changes exactly source start `431358` to raw rank0 `В то же время появляется гало на расстоянии около 22 градусов 35' от центра Луны.`, reducing **22/18/0,39 → 21/18/0,38**. Non-promoting/default-OFF.

### Short-DMS feasibility and composed run 16

Read-only feasibility workflow `34645335141` is green on exact run `14`. For `Whence this Angle is 2 deg. 0'. 7''. `, only raw TC-big rank `2` simultaneously satisfies strict mechanics and DMS semantics: `Откуда этот угол 2 град. 0'. 7''.`. Rank `3` preserves mechanics but leaves English `deg.`; rank `5` preserves angle/degree semantics but corrupts the minute prime. This proves the selector is discriminating between independent failure modes.

Composed persisted workflow `34645769684` is green; artifact `10282227627`.
- exact base run `14` → angular intermediate run `15` → final run `16`;
- run `16` output SHA `6580654826710367569682fdd44805163d8f23a1ec3ede1c0d74c62b16ec06e`;
- persisted SQLite SHA `2f7fb592777a9ca18c86ff393954f9032dbe48e4b10d626a322596d5ed56a862`;
- evidence SHA `34598d7a05df08d01c610c83e9db8e2433e7537e31c9196fdc80eacc5b3f839`;
- hard counts **22/18/0,39 → 21/18/0,38 → 20/18/0,37 unique**;
- DMS stage attempts/accepts exactly source start `110881`, selected raw rank `2`, target `Откуда этот угол 2 град. 0'. 7''.`;
- DMS leaves all other `3343` rows byte-exact relative to angular run `15`; source coverage is byte-exact; SQLite integrity is `ok`, foreign-key violations `0`;
- angular + DMS unit regressions **14/14 passed**;
- no source/target rewriting, placeholders, literal injection or corpus patching;
- `promotion_allowed=false`, `automatic_product_default_allowed=false`, `public_stage12_surface_allowed=false`.

## Boundary evidence relevant to the next residual family

Read-only workflow `34644023517` proved the exact contiguous pair `And whence is it | but from ... ?` has six strict + semantic TC-big hypotheses when translated together. L3 inspection then showed the deeper source of the residual: Stage8 token `it` is marked `is_sent_end=True`, following lowercase `but` is `is_sent_start=True`, and Stage10 preserves the same split although the immutable source has no terminal punctuation there.

A simple corpus-wide Stage10 inventory (`previous fragment has no terminal punctuation` + `next fragment starts lowercase`) yields only five candidate boundaries: prose fragments ending `in a Prism`, `Nor do I see but that there is`, `And whence is it`, `seeing whether`, plus one structurally suspicious math/roman case. This is research evidence only; no boundary merge rule is authorized yet.

## Durable guardrails

- Generic OPUS/TC-big whole-context fallback remains rejected: mechanically clean candidates can lose or distort meaning.
- Exact Stage10 replacement requires complete current-row geometry; non-aligned contexts skip fail-closed.
- Mechanical integrity is necessary but not sufficient; semantic constraints/review remain mandatory.
- MetricX/QE is ranking evidence only.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches or evaluator weakening.
- Punctuation/numeric work proceeds by source-defined defect family; no universal fixer.
- A persisted corpus improvement does not by itself authorize a Product default.

## Active next actions

1. Inspect the Stage8/Stage10 sentence-construction implementation and metadata for all five lowercase-continuation candidate boundaries.
2. Determine whether a generic upstream fail-closed repair can merge genuine parser false splits while excluding structural/math boundaries; add unit/diagnostic evidence before changing full-corpus translation.
3. If upstream repair is safe, rerun the affected maintained stages and compare full-corpus hard gates/semantic effects against run `16`; otherwise retain the non-promoting Whence pair evidence and pursue another source-defined strategy.
4. Continue the run-16 residual inventory toward the Product requirement of zero unresolved hard failures.
