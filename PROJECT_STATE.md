# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- Engineering/L3 checkpoint incorporated here: `b97825c5cbf1b1fab7f35133feca3f76cdd4b456` (`Integrate fail-closed Stage10 boundary coalescing`). HEAD may be ahead only by mandatory memory-sync or evidence commits.
- Maintained Product Core + Workbench are the forward implementation. Authoritative Product contract: `rocketdict/PRODUCT_TARGET.md`.
- Final heavy 90k+ evidence still requires **0 unresolved numeric/symbol, punctuation and length hard failures**. Current work is research, not release completion.
- Current best persisted full-*Opticks* research basis remains Stage12 run `16`: **20 numeric/symbol / 18 punctuation / 0 length, 37 unique failures** over `3344` rows.
- All narrow TC-big rescue layers remain default OFF/not public-wired and non-promoting.

## Recovery protocol

Follow `AGENTS.md`: compare HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; L3 source/tests/CI/artifacts outrank L1/L2.

## Maintained identities

- OPUS baseline: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`; numeric hard gate: `rocketdict-maintained-numeric-integrity/5`; Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1` rescue veto.
- Stage10 context default: `structural-entity-term-discourse-pronoun-v2`; schema `rocketdict-product-stage10/2`; boundary policy `rocketdict-stage10-lowercase-continuation-coalescer/1`.
- Pinned TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0.
- TC-big offline asset: manifest `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload tree `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`, 11 files / 968529922 bytes, Torch-free inference.

## Canonical full-Opticks evidence

Source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

Persisted progression: run `4` **30/34/5,64** → `7` **29/34/0,59** → `8` **25/33/0,55** → `9` **24/30/0,52** → `10` **24/25/0,47** → `11` **24/20/0,42** → `12` **23/19/0,41** → `13` **23/18/0,40** → `14` **22/18/0,39** → `15` **21/18/0,38** → `16` **20/18/0,37**.

### Run 16 — angular-minute + short-DMS composition

Workflow `34645769684` is green; artifact `10282227627`; artifact ZIP SHA-256 `92b2ad3fa98af1d12c27eeb4ee749071d5152464b34c4ac1f3bf40ed7cc02e14`.

- exact base run `14` → angular intermediate run `15` → final run `16`;
- run-16 output SHA `767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783`;
- persisted SQLite SHA `573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11`;
- evidence SHA `86c865cef5a0081fd77aa8ad78c525ebb38a01e6f279cc560aea56bb84d4e37d`;
- hard counts **22/18/0,39 → 21/18/0,38 → 20/18/0,37 unique**;
- byte-exact source coverage; SQLite `integrity_check=ok`, 0 FK violations; angular+DMS unit regressions **14/14**;
- no rewriting/injection/placeholders/corpus patches; promotion/default/public wiring flags remain false.

## Stage10 boundary repair state

The upstream cause behind `And whence is it | but from ... ?` is now repaired generically in Stage10 rather than by a phrase-specific MT patch. `context_sentence_boundaries.py` evaluates adjacent raw Stage8 parser sentences from immutable source geometry and merges only consecutive, whitespace-contiguous, non-paragraph boundaries with no source terminal punctuation when the next lexical character is lowercase. Stage8 evidence remains untouched and Stage10 v2 persists original spaCy indices plus every removed-boundary decision.

Integration commit `b97825c5...` was produced only after the dedicated Stage10 workflow passed **12/12** tests (`test_context_sentence_boundaries.py`, `test_stage10_context_coalescing.py`, `test_product_stages.py`). Because the workflow pushed the final commit with `GITHUB_TOKEN`, GitHub did not launch the ordinary Product workflow for that resulting HEAD; therefore terminal-head GT5/GT8/full-corpus evidence is still pending and must not be inferred from the focused test run.

## Durable guardrails

- Generic OPUS/TC-big whole-context fallback remains rejected.
- Mechanical integrity is necessary but not sufficient; semantic review remains mandatory.
- MetricX/QE is ranking evidence only.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches or evaluator weakening.
- Punctuation/numeric work is defect-family-specific; persisted improvement alone never authorizes a Product default.

## Active next actions

1. Run terminal-HEAD Product/GT5+GT8 regression gates with Stage10 v2 installed.
2. Rerun the exact complete *Opticks* Stage10→translation path and compare hard gates/semantic changes against run `16`, including the five coalesced boundaries and untouched-row invariants.
3. Classify the new residual inventory and continue only source-defined/general repairs toward zero hard failures.
