# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- Current engineering HEAD before this synchronization: `5eb4efc6eea9f3f10e80a95dbf12043f15652554` (`Run full Opticks rank0-clean lineage replay`).
- Maintained Product Core + Workbench remain the forward implementation. Authoritative contract: `rocketdict/PRODUCT_TARGET.md`.
- Final approved 90k+ evidence still requires **0 unresolved numeric/symbol, punctuation and length hard failures**, semantic acceptance and the complete learner/export path.
- Historical persisted run `23` remains immutable research evidence (**17 numeric / 14 punctuation / 0 length, 30 unique failing sequences, 3337 rows**) but is **not rank0-clean promotion lineage** because direct SQLite audit proved historical automatic rank>0 choices.
- The active critical path is now to finish and authenticate the new rank0-clean full-Opticks replay/census, then use only that clean baseline for further residual-family work.

## Recovery protocol

Follow `AGENTS.md`: compare current HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`. For current translation work load `docs/memory/TRANSLATION_QUALITY.md` and `docs/memory/DECISIONS.md`. L3 source/tests/CI/artifacts/SQLite outrank memory.

## Maintained identities

- OPUS: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product Stage10/default: `structural-entity-term-discourse-pronoun-v1`, schema `rocketdict-product-stage10/1`. Research V2 remains explicit only.
- Stage12 planner: `rocketdict-stage12-protected-split/8`; numeric gate: `rocketdict-maintained-numeric-integrity/6`; emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0; offline manifest `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload tree `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`.

## Rank0-only policy — current implementation

Automatic lower-beam fallback is forbidden. Persisted rescue output must come from the unique raw rank0 hypothesis; missing/duplicate/malformed rank0 fails closed. Rank1+ may remain diagnostic only.

Current hardened wrappers include:

- figure-reference rescue/selector `/2`;
- short-angular-DMS rescue/selector `/2`;
- angular-minute rescue/selector `/2`;
- illustration-label rescue `/2`;
- TC-big target-delimiter rescue `/2`;
- TC-big footnote-reference rescue `/2`;
- TC-big semicolon-question rescue `/2`;
- TC-big equals-addition rescue `/2`.

Shared helper `translation_rank0.py` structurally enforces unique-rank0 selection. Product Core CI workflow `34694302843` passed both dependency-light and real-runtime jobs after this hardening.

## Canonical full-Opticks source identity

Complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

Historical run23 identities remain:

- workflow `34688874921`; artifact `10296696335`; ZIP SHA-256 `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`;
- SQLite SHA-256 `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`;
- translation output SHA-256 `976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493`;
- final text SHA-256 `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`;
- canonical evidence SHA-256 `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`.

## Historical lineage defect

Exact run23 SQLite audit proved:

- historical run9 `illustration_label_rescue/1` selected ranks `[3,3,0]`; rank3 spans were `72401:72443` (`FIG. 21`) and `90105:90147` (`FIG. 24`);
- inherited `tc_big_short_angular_dms_rescue/1` selected rank2 for source start `110881`, `Whence this Angle is 2 deg. 0'. 7''.`;
- therefore run23 cannot parent promotion work despite its lower historical hard-failure count.

## Rank0-clean replay — current evidence and blocker

Workflow `34694587892`, artifact `10298234071`, ran from HEAD `5eb4efc6eea9f3f10e80a95dbf12043f15652554` using the exact historical run23 SQLite plus pinned OPUS and TC-big assets. Asset/provenance staging succeeded.

The heavy replay itself completed all model/rescue computation but the workflow was marked failed by a **harness cardinality assertion**, not by a Product/evaluator/model failure: the script expected 15 newly created Stage12 runs after the clean boundary, while the current wrappers created **18**.

Primary evidence from the persisted partial artifact/SQLite establishes that the extra three are the safe pre-boundary `length → citation → numeric-hard` layers recomputed from run4. Their source/target/geometry outputs are byte-identical to historical runs `6→8` (`24==6`, `25==7`, `26==8` by translation-row identity). The current rank0-clean lineage then continues through new runs up to `41`.

The first replay also confirms the intended policy effect: historical illustration rank3 rescues and short-DMS rank2 rescue are no longer selected; new rescue metadata exposes only rank0 selections for persisted candidates. This remains preliminary until the corrected harness completes evidence generation and the residual census is authenticated.

## Historical run23 residual census

Read-only census workflow `34690365432`, artifact `10296887793`, ZIP SHA-256 `8cc7ea22a12f27ee0105767bfc7b13c39a9493e945e6d32508b847151c986393`, evidence SHA `55848393832fd777d7ab23f03f36d8fb2eb1031748faa0d2a096a35ea781ed58` remains authoritative only for describing historical run23. Recompute all residual counts from the corrected clean replay before using them as the forward frontier.

## Sequence 2346 DOE result

Workflow `34693396634`, artifact `10298311979`, artifact digest `sha256:1074aed027bdab4fd9ffb9bdd0375decbf18b7baace8f2e6330517e07904fcbd`, evidence SHA `094140b1add91c3cdb6294319cfc691d38d488f97966c5cb41a9ae2386d055d6`.

- Four source-owned geometries × raw rank0 OPUS/TC-big; all 8 aggregate candidates failed maintained mechanical gates.
- TC-big `three_way` and `lead_clause_then_suffix` preserve all four source prime/double-prime pairs but corrupt `100000000` to `10000000`; no evaluator waiver/target repair is allowed.
- Treat these geometries as exhausted unless materially new evidence/model geometry is introduced.

## Durable guardrails

- Mechanical integrity is necessary but insufficient; semantic/boundary review remains mandatory.
- No target repair, literal injection, source rewriting, placeholders, corpus-specific target patches, automatic n-best cherry-picking or evaluator weakening.
- A local evidence flag about the current wrapper does not certify predecessor lineage unless lineage was explicitly audited.
- New selectors must be source-defined and fail closed; raw model output remains immutable evidence.
- Generic fallback, tested large-integer canonicalization, nonliteral beam-picking, figure seq325 tested geometries and seq2346 tested angle-list geometries remain rejected/exhausted under current evidence.

## Active next actions

1. Correct the clean-replay harness to validate the actual 18-run recomputation and explicitly prove the byte-identical `24→26` equivalence to historical `6→8` rather than assuming only 15 new runs.
2. Rerun workflow `.github/workflows/rocketdict-full-opticks-rank0-clean-replay.yml` to completion; authenticate source coverage, model identities, source/target lineage, selected ranks, SQLite/FK integrity and canonical evidence hashes.
3. Run and authenticate the residual census on the final clean run; record exact hard-failure counts/sequences and semantic diffs caused by removal of historical rank>0 rescues.
4. Synchronize L1/L2 with that completed clean baseline and make it the only parent for subsequent residual-family promotion research.
5. Continue until hard failures are zero, then finish downstream learner/export coverage and Windows clean-install/release validation.
