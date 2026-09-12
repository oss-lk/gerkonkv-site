# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- Latest substantive engineering/research checkpoint incorporated here: `7438007a9800771c910689edc64d40b9f8846b0d` (`Run run23 prime angle-list split DOE`). Mandatory L2 memory was then synchronized through `8bc53e3c750c03911ab39c2680cba0fc0287f245`; this L1 replacement is the process-debt repair commit after that evidence.
- Maintained Product Core + Workbench remain the forward implementation. Authoritative contract: `rocketdict/PRODUCT_TARGET.md`.
- Final approved 90k+ evidence still requires **0 unresolved numeric/symbol, punctuation and length hard failures**, semantic acceptance and the complete learner/export path.
- Historical persisted run `23` remains the lowest-hard-failure full Opticks translation retained (**17 numeric / 14 punctuation / 0 length, 30 unique failing sequences, 3337 rows**) but is now classified as **historical research evidence, not rank0-clean promotion lineage**.
- Immediate critical path changed: harden every active rescue wrapper against automatic rank>0 selection, then build a rank0-clean full-Opticks replay from the exact predecessor before the first historical cherry-pick (currently run8 before illustration-label run9), recompute gates/census, and only then resume residual promotion.

## Recovery protocol

Follow `AGENTS.md`: compare current HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`. For current translation work load `docs/memory/TRANSLATION_QUALITY.md` and `docs/memory/DECISIONS.md`. L3 source/tests/CI/artifacts/SQLite outrank memory.

## Maintained identities

- OPUS: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product Stage10/default: `structural-entity-term-discourse-pronoun-v1`, schema `rocketdict-product-stage10/1`. Research V2 remains explicit only.
- Stage12 planner: `rocketdict-stage12-protected-split/8`; numeric gate: `rocketdict-maintained-numeric-integrity/6`; emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0; offline manifest `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload tree `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`.
- Current rank0-only TC-big contracts already hardened: figure-reference rescue/selector `/2`; short-angular-DMS rescue/selector `/2`; angular-minute rescue/selector `/2`.

## Canonical full-Opticks evidence

Complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

Historical run23 identities:

- workflow `34688874921`; artifact `10296696335`; ZIP SHA-256 `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`;
- SQLite SHA-256 `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`;
- translation output SHA-256 `976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493`;
- final text SHA-256 `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`;
- canonical evidence SHA-256 `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`.

## Rank0 lineage audit — active blocker

Direct audit of the exact run23 SQLite proves historical automatic n-best selection earlier in its Stage12 chain:

- run9 `illustration_label_rescue/1`: accepted-group ranks `[3,3,0]`; rank3 groups are source spans `72401:72443` (`FIG. 21`) and `90105:90147` (`FIG. 24`), represented by split rows `424/425` and `515/516` after the rescue;
- inherited `tc_big_short_angular_dms_rescue/1`: seq `640`, source start `110881`, selected rank2 for `Whence this Angle is 2 deg. 0'. 7''.`;
- other accepted narrow rescue layers exposed by run23 output metadata selected rank0, but several current wrapper implementations still require source audit to make rank0-only structural rather than accidental.

Therefore run23 must not be used as the parent for new promotion runs until a clean replay exists. Preserve it unchanged as historical evidence.

## Forward rank0 hardening already completed

- `short-angular-DMS` is now rescue/selector `/2`, phase v2: unique rank0 only; rank1+ diagnostics cannot rescue a failed rank0 (`41b7319`, regression `bda00c9`).
- `angular-minute` is now rescue/selector `/2`, phase v2 with the same invariant (`7d0f02f`, regression `f8512e5`).
- Product Core CI run `34693256404` succeeded for the angular hardening.
- Figure-reference `/2` was already rank0-only; Product Core CI `34692166640` remains its proof point.

## Historical run23 residual census

Read-only census workflow `34690365432`, artifact `10296887793`, ZIP SHA-256 `8cc7ea22a12f27ee0105767bfc7b13c39a9493e945e6d32508b847151c986393`, evidence SHA `55848393832fd777d7ab23f03f36d8fb2eb1031748faa0d2a096a35ea781ed58` remains authoritative for describing historical run23.

Residual sequences: `[325,641,642,644,646,650,743,750,751,752,1499,1579,1755,1788,2110,2290,2346,2357,2375,2591,2721,2741,2889,2997,3000,3007,3011,3083,3211,3305]`.

The `numeric_prime_notation=10` feature is heterogeneous: eight true angular prime/double-prime cases and two Newton apostrophe-decimals. Recompute all residual counts after the clean replay before treating them as the forward frontier.

## Sequence 2346 DOE result

Workflow `34693396634`, artifact `10298311979`, artifact digest `sha256:1074aed027bdab4fd9ffb9bdd0375decbf18b7baace8f2e6330517e07904fcbd`, evidence SHA `094140b1add91c3cdb6294319cfc691d38d488f97966c5cb41a9ae2386d055d6`.

- Tested four source-owned geometries × raw rank0 OPUS/TC-big; all 8 aggregate candidates failed maintained mechanical gates.
- TC-big `three_way` and `lead_clause_then_suffix` preserve all four source prime/double-prime pairs but corrupt `100000000` to `10000000`; this is a real numeric regression and cannot be repaired or evaluator-waived.
- DOE is read-only, byte-exact, no source/target rewriting or literal/separator injection, no n-best selection.
- Treat these four geometries as exhausted for seq2346 unless materially new evidence/model geometry is introduced.

## Durable guardrails

- Mechanical integrity is necessary but insufficient; semantic/boundary review remains mandatory.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches, automatic n-best cherry-picking or evaluator weakening.
- A local evidence flag about the current wrapper does not certify predecessor lineage unless lineage was explicitly audited.
- New selectors must be source-defined and fail closed; raw model output remains immutable evidence.
- Generic fallback, tested large-integer canonicalization, nonliteral beam-picking, figure seq325 tested geometries and seq2346 tested angle-list geometries remain rejected/exhausted under current evidence.

## Active next actions

1. Audit every maintained Stage12 rescue implementation for first-passing-beam / rank>0 automatic selection. Harden all active offenders; `illustration_label_rescue` is first because exact persisted history proves rank3 selection.
2. Build a reproducible rank0-clean full-Opticks replay beginning from exact run8, then reapply the maintained rescue chain under current contracts. Do not rewrite historical run23.
3. Verify source byte coverage, SQLite/FK integrity, model/source identities, no new disallowed transformation flags, and semantic diffs for every changed group.
4. Recompute full hard-gate counts and residual census from the clean replay. Only this new baseline may parent subsequent numeric/punctuation rescue research.
5. Continue until hard failures are zero, then finish downstream learner/export coverage and Windows clean-install/release validation.