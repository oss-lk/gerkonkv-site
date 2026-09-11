# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`
- Engineering branch: `chatgpt/product-core-forward`
- Engineering/L3 checkpoint incorporated by this refresh: `c196dd2b4985445fbcb015ac0f3a71af1b97ad9d` (`Test TC-big equals addition rescue`). Memory-only recovery commits may follow this checkpoint.
- Maintained Product Core + Workbench remain the forward implementation.
- Authoritative Product target: `rocketdict/PRODUCT_TARGET.md`; final approved heavy evidence still requires zero unresolved hard translation failures.
- Current persisted full-*Opticks* residual basis is Stage12 run `13`: **23 numeric/symbol / 18 punctuation / 0 length**, **40 unique failures**.
- TC-big delimiter, footnote-reference, figure-reference and semicolon→question rescue layers are persisted/verified research improvements, but remain default OFF and not public-wired. Product defaults have not broadened.
- A fifth default-OFF/not-public-wired TC-big target-only-equals rescue is implemented and Product Core CI is green; it has **not** yet earned persisted full-corpus promotion. The known mechanically admissible `Square of the Sine` candidate needs explicit semantic review before any persisted baseline change.

## Recovery protocol

Follow `AGENTS.md`: compare current HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; source/tests/CI/artifacts are L3 authority. If HEAD differs only by this mandatory memory recovery, no engineering drift is implied.

## Maintained identities

- OPUS baseline: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`.
- Block section IDs: `rocketdict-stage12-block-section-identifier/1`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`.
- Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1` rescue veto.
- Pinned TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, license `CC-BY-4.0`.
- TC-big offline asset `rocketdict-tc-big-en-ru-asset/1`; accepted manifest SHA `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload-tree SHA `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`, 11 files / 968529922 bytes; inference is offline and Torch-free.
- Default-OFF/not-public-wired TC-big wrappers:
  - `rocketdict-stage12-tc-big-target-delimiter-context-rescue/1`
  - `rocketdict-stage12-tc-big-footnote-reference-lead-rescue/1`
  - `rocketdict-stage12-tc-big-figure-reference-lead-rescue/1`
  - `rocketdict-stage12-tc-big-semicolon-question-substitution-rescue/1`
  - `rocketdict-stage12-tc-big-target-only-equals-addition-rescue/1`

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
- run `13`: **23/18/0**, 40 unique.

### Run 11 — footnote-reference lead

Workflow `34638137163` green; artifact `10279415117`, digest `a49983989472444fd6a6924035d57e66bb2b712916cf515448e29a49b04b3d6c`.
- output SHA `ef38b21e7e7e384a00310123fd9f16ec10045b0741605867ad15f559f15c08c3`;
- persisted SQLite SHA `329ed0cebe7b3af42b88b50f602c3bba3227fd75704e1e48fea4b1651169ded8`;
- 5 attempts / 5 raw rank0 accepts / 0 rejects;
- accepted starts `[151466,151557,253849,253919,254102]`;
- 3339 untouched rows exact, byte-exact source coverage, SQLite clean.
The earlier red workflow was only an audit `0 -> -1` bug; the corrected heavy rerun is authoritative.

### Run 12 — leading `[in _Fig._ N.]` reference

Workflow `34638917374` green; artifact `10279171721`, digest `96579405a7c1d620631c904df90495e53b542e098ed22f34210b937837f40f83`.
- output SHA `57a8d2d519bf236c04b91d75b775a22b12f2a4c429cfc278ce6dba05c74a4063`;
- persisted SQLite SHA `9d8f277651e1b6fef26de70479a088afbe9e0f8bd8c743ec3a4742914c0d217d`;
- 2 attempts / 1 accept / 1 fail-closed reject;
- accepted start `228046` (`Fig.15`); `Fig.16` remained rejected;
- 3343 untouched rows exact and source coverage byte-exact.

### Run 13 — semicolon→question substitution

Workflow `34639494681` green; artifact `10279502482`, digest `88dcd100745530a67add70faeedf27d5a623f597eaea03044530cfc4f5b923ef`.
- output SHA `2fda987f054681a6561272d4c802980f498d9a01019a43c2c9bd2c7bbfb7f4c7`;
- persisted SQLite SHA `97ffae9254ac49e004ab372a5edb1e87ec045b39d8480bc086a99456bd5418a3`;
- evidence-file SHA `4a9ce328a8c2f20179a3b6e00da01afe6a282bab2aae38b987d8c6d432eb352b`, internal evidence SHA `8c1d13fb8a762dc1ed1c17079ba9bd14a6d2835ed7048319ec5d133a73be52e6`;
- 1 attempt / 1 raw rank0 accept / 0 rejects at start `382298`;
- selected target preserves the source semicolon, removes the invented question mark and retains all three motion alternatives; manual semantic review found it materially more faithful than the OPUS baseline;
- 3343 untouched rows exact, byte-exact source coverage, SQLite clean, pinned TC-big asset identities exact.

## Active equals frontier

`translation_tc_big_equals_addition_rescue_stage.py` triggers only on an exact single-Stage10/current Stage12 hard-failing row with zero source `=` and target-only `=` additions. Candidates are unmodified raw TC-big hypotheses and must pass strict mechanical checks, Gutenberg emphasis preservation, exact equals-count restoration and source-relative alpha `0.75..1.50`. No formula rewriting or target surgery is allowed.

Product Core workflow `34639617628` is green for commit `c196dd2...`.

The corpus scan found two target-only `=` failures, but exact Stage10 geometry admits only the safe row-aligned case; historical context `2725` / `_per deliquium_` is excluded by geometry. The admissible candidate still needs semantic evaluation: a mechanically clean translation of `Square of the Sine` as `площадь Сина` would be terminologically wrong, so mechanical acceptance alone must not create run `14` evidence.

## Durable guardrails

- Generic OPUS/TC-big whole-context fallback remains rejected: mechanically clean candidates can lose or distort meaning.
- Exact Stage10 replacement requires complete current-row geometry; non-aligned contexts skip fail-closed.
- MetricX/QE is ranking evidence only.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches or evaluator weakening.
- Prime decomposition, broad citation/group merging, thousands grouping, compact-formula spacing and unsafe long-context branches remain negative evidence unless a materially new hypothesis is tested.
- Punctuation/numeric work proceeds by source-defined defect family; no universal fixer.

## Active next actions

1. Audit the equals candidate semantically before persisting anything; reject or strengthen the selector if the raw candidate corrupts mathematical terminology.
2. Only if semantic evidence is positive, add a persisted run-14 full-*Opticks* audit over exact run `13`; otherwise record the negative result and leave run `13` authoritative.
3. Rebuild the remaining 40-failure inventory from the authoritative basis and identify the next narrow source-defined defect class.
4. Keep every TC-big rescue default OFF/not public-wired until stronger cross-corpus/release evidence exists; final acceptance still requires zero unresolved hard failures.
