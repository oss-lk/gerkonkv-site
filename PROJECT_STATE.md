# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`
- Engineering branch: `chatgpt/product-core-forward`
- L3/L2 checkpoint incorporated by this refresh: `39ef23a57f737e7a2574a99e0e8d4a7fd11429b9`
- Maintained Product Core + Workbench remain the forward implementation.
- Authoritative Product target: `rocketdict/PRODUCT_TARGET.md`; final approved heavy evidence requires zero unresolved hard translation failures.
- Current persisted full-*Opticks* residual basis is Stage12 run `10`: **24 numeric/symbol / 25 punctuation / 0 length**, **47 unique failures**.
- TC-big delimiter rescue is now persisted and verified, but remains default OFF/not public-wired. Product defaults have not broadened.
- A second default-OFF/not-public-wired TC-big footnote-reference lead wrapper is implemented and unit/real-runtime CI is green.
- Active blocker is an audit-harness bug, not a translation defect: heavy run `34632917048` persisted run `11` with 5 attempts / 5 accepts / 0 rejects, then falsely failed because `int(rejected_count or -1)` maps valid zero to `-1`. Fix only the audit assertion, rerun independent gates/SQLite/source checks, and do not change selector thresholds.

## Recovery protocol

Follow `AGENTS.md`: compare current HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; source/tests/CI/artifacts are L3 authority. If HEAD contains only the L1 refresh after this checkpoint, no engineering drift is implied.

## Maintained identities

- OPUS baseline: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`.
- Block section IDs: `rocketdict-stage12-block-section-identifier/1`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`.
- Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1` rescue veto.
- Pinned TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, license `CC-BY-4.0`.
- TC-big offline asset `rocketdict-tc-big-en-ru-asset/1`; accepted run-10 asset manifest SHA `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload-tree SHA `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`, 11 files / 968529922 bytes. Inference is offline and Torch-free.
- TC-big delimiter wrapper: `rocketdict-stage12-tc-big-target-delimiter-context-rescue/1`, selector/trigger `/1`, default OFF/not public-wired.
- TC-big footnote wrapper: `rocketdict-stage12-tc-big-footnote-reference-lead-rescue/1`, selector/trigger `/1`, default OFF/not public-wired.

## Canonical full-Opticks evidence

Pinned source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` characters.

Persisted progression:
- run `4`: **30/34/5**, 64 unique;
- run `7`: **29/34/0**, 59 unique;
- run `8`: **25/33/0**, 55 unique;
- run `9`: **24/30/0**, 52 unique;
- run `10`: **24/25/0**, 47 unique.

Run `10` authoritative persisted evidence:
- workflow `34631662056`, artifact `10276009101`, digest `21e374f3b9863ef35b04220118c3326b860d6506e16116a0242310a7236d24e1`;
- output SHA `6dec2080a8fe21716587e4f4ffbe1f8ebf816911b542ab99ac598a8462ed01df`;
- SQLite SHA `4a5bd2159c1aca0b5bcf5580d7aa0d767f0faedd2b1dcdaef92dab96a36d3087`;
- evidence file SHA `e5787def5adcd6780115ea13fa3fa90637494221246fd36afcc292071975e1a8`, internal evidence SHA `494379a1b4f0e98f9c0cc336864231418d5c7587b4a5a5983a55fe425e383b20`;
- `3344` rows; byte-exact source; 3339 untouched rows exact; five raw rank0 TC-big replacements; SQLite integrity clean; no rewrite/placeholders/literal injection/corpus patches.

Manual review of the five run-10 delimiter replacements found meaningful semantic improvement, including removal of severe OPUS hallucinated religious vocabulary. This remains research-quality persisted progress, not a default-promotion decision.

## Footnote-reference frontier

The new wrapper only triggers on an exact single-Stage10/current-Stage12 hard-failing source lead matching `[A-Z] _..._` whose exact ASCII marker is lost. Candidate must be raw TC-big, restore the exact marker, pass strict mechanical checks, preserve emphasis and keep target/source alpha in `0.70..2.00`. There is no corpus-specific letter whitelist.

Product Core workflow `34632793371` is fully green, including real Stage8→25 and unified Product smoke.

Heavy run `34632917048` verified exact run10, pinned TC-big snapshot, byte-verified asset and torch-free inference. It then persisted run `11` with:
- attempted/accepted source starts `[151466, 151557, 253849, 253919, 254102]`;
- 5 accepted, 0 rejected, all rank0;
- targets `[G] _Это продемонстрировано в нашем_`, `[H] _Как это сделать, показано в нашем_`, `[J] _Смотрите наш_`, `[K] _Как это делается в нашем_`, `[M] _Это продемонстрировано в нашем_`;
- output SHA `ef38b21e7e7e384a00310123fd9f16ec10045b0741605867ad15f559f15c08c3`.

The workflow is red only because the audit script treats zero rejected as missing via `or -1`. Run `11` is therefore not yet the residual basis; independent gate recount and SQLite/source evidence must complete green after the harness fix.

## Durable guardrails

- Generic OPUS/TC-big whole-context fallback remains rejected: mechanically clean candidates can lose or distort meaning.
- Exact Stage10 replacement requires complete current-row geometry; non-aligned contexts skip fail-closed.
- MetricX/QE is ranking evidence only.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches or evaluator weakening.
- Existing prime, broad citation/group, thousands-grouping, compact-formula and unsafe long-context branches remain negative evidence unless a materially new hypothesis is tested.

## Active next actions

1. Fix only the footnote heavy audit zero-handling assertion (`0` must remain `0`); do not alter Product selector/trigger thresholds.
2. Rerun persisted footnote heavy audit over exact run `10` and require independent hard-gate recount, byte-exact source coverage, untouched-row exactness, raw-hypothesis provenance, SQLite integrity and exact TC-big asset identities.
3. If green, inspect all five persisted footnote targets semantically and make run `11` the new residual basis only then.
4. Rebuild the residual inventory from that persisted basis and choose the next defect family from L3 evidence.
5. Keep all TC-big rescue layers default OFF/not public-wired until stronger cross-corpus semantic/release evidence exists; final acceptance still requires zero unresolved hard failures.
