# RocketDict maintained translation quality — L2

Durable translation-quality conclusions only. This is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). L3 source/tests/CI/artifacts outrank this file.

## Maintained contracts

- Production MT: pinned OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product/default Stage10 is V1; research V2 remains explicit only.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/6`; Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big remains a pinned independent comparator/narrow rescue, not a generic fallback. Research wrappers remain default OFF/not public-wired.
- Persisted rescue output must be the unique unmodified raw rank0 hypothesis. Higher beams may remain diagnostic only; missing/duplicate/malformed rank0 fails closed.

Current structurally rank0-only wrappers include figure-reference `/2`, short-angular-DMS `/2`, angular-minute `/2`, illustration-label `/2`, TC-big target-delimiter `/2`, footnote-reference `/2`, semicolon-question `/2`, and equals-addition `/2`. Shared `translation_rank0.py` enforces the unique-rank0 policy. Product Core CI workflow `34694302843` passed dependency-light and real-runtime jobs after this hardening.

## Canonical complete Opticks basis

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` chars.

## Authenticated rank0-clean full-corpus baseline

The corrected rank0-clean replay is now canonical for forward translation-quality work.

- Workflow `34695164876`: **success** from engineering HEAD `041b0293eecccc375c6264a39704e6b25d2b6665`.
- Artifact `10297359600`; digest `sha256:e2d7549965d893c0b877cfe21057b8490134392a966e42fd72483ebb19836b4d`.
- Replay schema `rocketdict-full-opticks-rank0-clean-lineage-replay/2`.
- Historical run23 SQLite was used as the immutable evidence/cache container only; replay root is run4.
- Recomputed runs `24`, `25`, `26` are source/target/geometry-identical to historical clean runs `6`, `7`, `8`; the harness authenticates these identities before accepting the post-boundary lineage.
- First post-boundary run `27`; final clean run `41`; 18 new runs total from run4.
- All persisted selected rescue hypotheses in the clean final lineage are rank0. No automatic n-best cherry-picking, source rewriting, target rewriting, literal injection, placeholders, corpus-specific target patches or evaluator weakening occurred.
- Source coverage is byte-exact; SQLite integrity is `ok`; foreign-key violations = `0`.
- Final clean run: **18 numeric/symbol / 16 punctuation / 0 length, 33 unique hard-failing sequences, 3335 rows**.
- Translation-output SHA-256 `d8948e43158a126703a90e6ce1cd25725da8774e1db64410ca67e3ec7bb1a10f`.
- Final-text SHA-256 `23170683ddbe183b4da6b4097d72cedc86b9c98044e9f3e1dee015015e16e15e`.
- SQLite SHA-256 `e48df8a90a3aa5e07bbc7e86c150d7b65ce450e7b6a0ec0d2e34a0caf9846e2e`.
- Replay evidence SHA-256 `e7504ef18ead81e9c437ab8236b787a7d59082c272ef102fcc9bae6e281deac1`.

Independent read-only census over run41 authenticated the same database/output/counts, retained byte-exact source coverage and left the database unchanged. Census evidence SHA-256 `b384ae0936f2ec792dd8ec6fbfcdf5da0dea1ba097df951c6049f2f2cbbb5319`.

Residual sequences:
`[325,424,514,638,639,640,642,644,648,741,748,749,750,1497,1577,1753,1786,2108,2288,2344,2355,2373,2589,2719,2739,2887,2995,2998,3005,3009,3081,3209,3303]`.

Numeric defect classes in the clean census:

- `critical_symbol`: 1
- `duplicate_required`: 1
- `missing_literal`: 2
- `missing_literal+unlicensed_addition`: 4
- `prime_notation`: 5
- `prime_notation+missing_literal+unlicensed_addition`: 4
- `unlicensed_addition`: 1

This run41 baseline is the only valid parent for subsequent promotion/rescue work.

## What rank0-clean lineage changed

Historical run23 remains immutable research evidence at **17 numeric/symbol / 14 punctuation / 0 length, 30 unique, 3337 rows**, but it is not rank0-clean and may not parent promotion.

Direct historical audit proved:

- run9 `illustration_label_rescue/1` accepted ranks `[3,3,0]`; rank3 spans were `72401:72443` (`FIG. 21`) and `90105:90147` (`FIG. 24`);
- inherited `tc_big_short_angular_dms_rescue/1` selected rank2 at source start `110881` for `Whence this Angle is 2 deg. 0'. 7''.`.

When those illegal higher-beam choices are removed, three clean-frontier failures reappear:

- seq `424`: `[Illustration: FIG. 21.]\n\n_Illustration._` → rank0 target contains two bracketed illustration clauses and fails punctuation preservation;
- seq `514`: the analogous `FIG. 24` pair → same failure family;
- seq `638`: `Whence this Angle is 2 deg. 0'. 7''.` → rank0 renders prime notation as feet and fails numeric-prime preservation.

The worse clean count is therefore expected and preferable to a lower count obtained through forbidden beam cherry-picking.

## Historical run23 retained evidence

Run23 workflow `34688874921`; artifact `10296696335`; ZIP SHA-256 `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`; SQLite SHA-256 `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`; translation output SHA-256 `976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493`; final text SHA-256 `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`; canonical evidence SHA-256 `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`.

Historical run23 residual census workflow `34690365432`, artifact `10296887793`, ZIP SHA `8cc7ea22a12f27ee0105767bfc7b13c39a9493e945e6d32508b847151c986393`, evidence SHA `55848393832fd777d7ab23f03f36d8fb2eb1031748faa0d2a096a35ea781ed58` is descriptive historical evidence only.

## Prime-notation findings

Prime-marked source contexts are heterogeneous: true angular prime/double-prime notation and Newton-style apostrophe decimals must not be treated as one rescue family.

Existing whole/multi-context raw rank0 OPUS/TC-big attempts failed to produce admissible candidates for the main prime families. Do not repeat them without materially new geometry.

### Sequence 2346 angle-list DOE

Workflow `34693396634` / artifact `10298311979` / artifact digest `sha256:1074aed027bdab4fd9ffb9bdd0375decbf18b7baace8f2e6330517e07904fcbd` tested four source-owned geometries under raw rank0 OPUS and TC-big. Evidence SHA-256 `094140b1add91c3cdb6294319cfc691d38d488f97966c5cb41a9ae2386d055d6`.

All eight aggregate candidates are mechanically inadmissible. TC-big `three_way` and `lead_clause_then_suffix` preserve all four angular pairs but change `100000000` to `10000000`; that is a strict regression and not grounds for evaluator or target repair.

## Figure-reference sequence 325

Sequence `325` remains closed under tested lead-split and preceding-boundary-pair geometries. Isolated figure-lead splitting can turn mechanical checks green while producing broken full-context syntax; restoring the syntactic boundary makes rank0 candidates inadmissible again. No target repair is permitted.

## Binding rescue/negative conclusions

- Generic OPUS/TC-big whole-context fallback, generic row-local TC-big punctuation fallback, broad Stage10-v2 geometry and generic bounded-parenthesis fallback remain rejected.
- Inline `[G]` remains unresolved under tested row-local and whole-context OPUS/TC-big formulations; tested hypotheses omit the marker.
- Large-integer source canonicalization/n-best feasibility rescued zero baseline hard failures.
- Nonliteral numeric n-best can mechanically rescue isolated rows only through disallowed automatic beam selection.
- Never use target literal injection, corpus-specific target patches, placeholders, source rewriting, target surgery, automatic n-best cherry-picking or evaluator weakening.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Preserve immutable source/model/config/result identities and exact persisted predecessor lineage.
3. Rescue research may persist only deterministic unmodified raw rank0 model output; higher beams are diagnostics only.
4. Mechanical integrity is necessary but insufficient; semantic/boundary-aware review is mandatory.
5. Alternative geometry/model use requires a narrow existing-hard-failure/source-defined trigger.
6. A persisted evidence file may describe only its own wrapper unless it explicitly audits and certifies the complete predecessor lineage.
7. Final approved heavy evidence requires zero unresolved hard failures before downstream learner/export/release validation.

## Current quality frontier

Start from authenticated run41 only. Inventory prior DOE for clean-returned seq `424`, `514`, `638`; test only materially new source-defined raw-rank0 OPUS/TC-big geometries. Promote a default-OFF wrapper only if a generic source predicate, maintained mechanical gates and semantic/boundary review all pass. Otherwise mark the family exhausted and move to the next clean residual cluster.
