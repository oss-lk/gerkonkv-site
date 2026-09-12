# RocketDict maintained translation quality — L2

Durable translation-quality conclusions only. This is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). L3 source/tests/CI/artifacts outrank this file.

## Maintained contracts

- Production MT: pinned OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product/default Stage10 is V1; research V2 remains explicit only.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/6`; Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big remains a pinned independent comparator/narrow rescue, not a generic fallback. Research wrappers remain default OFF/not public-wired.
- Figure-reference rescue is `/2`; short-angular-DMS rescue/selector are `/2`; angular-minute rescue/selector are `/2`. These forward contracts authorize only the unique raw rank0 hypothesis. Higher beams may remain diagnostic evidence but cannot alter the persisted target.

## Canonical complete Opticks basis

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` chars.

Historical persisted run `23` is still the lowest-hard-failure full translation currently retained: **17 numeric/symbol / 14 punctuation / 0 length, 30 unique hard-failing sequences** over `3337` rows. Exact predecessor run22 is **18/14/0,31** over `3338` rows. Run23 remains valuable mechanical/research evidence, but it is **not rank0-clean lineage** under the current no-automatic-n-best rule and therefore must not be treated as the clean promotion baseline.

Run23 identities:

- workflow `34688874921`; artifact ID `10296696335`; ZIP SHA-256 `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`;
- SQLite SHA-256 `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`;
- translation output SHA-256 `976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493`;
- final text SHA-256 `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`;
- canonical evidence SHA-256 `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`.

The run23 evidence file correctly describes the final emphasized-modifier wrapper itself as non-cherry-picking, but that flag does not retroactively certify the complete predecessor lineage. Direct SQLite audit of all 23 stage runs proves historical automatic n-best selections earlier in the chain:

- run9 `illustration_label_rescue` accepted three source groups with selected ranks `[3,3,0]`; the two rank3 groups are spans `72401:72443` (`FIG. 21`) and `90105:90147` (`FIG. 24`). Their split output rows include sequences `424/425` and `515/516`; the linguistic `_Illustration._` remainders are seq `425` and `516`.
- inherited `tc_big_short_angular_dms_rescue/1` accepted seq `640`, source start `110881`, from rank2 (`Whence this Angle is 2 deg. 0'. 7''.`).
- other narrow rescue outputs visible in run23 that expose `*_selected_ranks` are rank0 for their accepted cases; that does not yet prove every active wrapper implementation is structurally rank0-only, so source audit remains required.

Consequently, a new rank0-clean replay must be built before the residual census is used as a promotion lineage. Historical run23 is not deleted or rewritten.

## Verified run23 residual census

Corrected read-only census workflow `34690365432` authenticated exact run23 without mutation. Artifact ID `10296887793`; ZIP SHA-256 `8cc7ea22a12f27ee0105767bfc7b13c39a9493e945e6d32508b847151c986393`; evidence SHA-256 `55848393832fd777d7ab23f03f36d8fb2eb1031748faa0d2a096a35ea781ed58`.

Residual sequences: `[325,641,642,644,646,650,743,750,751,752,1499,1579,1755,1788,2110,2290,2346,2357,2375,2591,2721,2741,2889,2997,3000,3007,3011,3083,3211,3305]`.

Numeric defect classes: `critical_symbol=1`, `duplicate_required=1`, `missing_literal=2`, `missing_literal+unlicensed_addition=4`, `prime_notation=4`, `prime_notation+missing_literal+unlicensed_addition=4`, `unlicensed_addition=1`. Source features include `numeric_prime_notation=10`, `round_parenthesis=10`, `fraction=5`, `big_integer=4`, `square_bracket=3`, `angle_word=3`, `apostrophe_decimal=2`, `ascii_x=1`, `formula_suffix=1`.

This census remains authoritative for understanding historical run23 residuals, but the counts must be recomputed after the rank0-clean replay because removing historical rank>0 rescues can change row geometry and hard-failure counts.

## Prime-notation findings

The historical `numeric_prime_notation=10` feature is heterogeneous. Eight rows are true angular prime/double-prime cases; two are Newton-style apostrophe decimals (`1'688`, `0'35`) that were feature-clustered lexically and are not equivalent angular-prime rescue targets.

Existing whole/multi-context raw rank0 OPUS/TC-big attempts already failed to produce an admissible candidate for the main prime families. Do not repeat them without materially new geometry.

### Sequence 2346 angle-list DOE

Workflow `34693396634` / artifact `10298311979` / artifact digest `sha256:1074aed027bdab4fd9ffb9bdd0375decbf18b7baace8f2e6330517e07904fcbd` tested exact historical run23 seq `2346` with four source-owned geometries (`whole_row`, `three_way`, `lead_clause_then_suffix`, `prefix_then_clause_suffix`) under raw rank0 OPUS and TC-big. Evidence SHA-256: `094140b1add91c3cdb6294319cfc691d38d488f97966c5cb41a9ae2386d055d6`.

- all 8 model/geometry candidates are mechanically inadmissible;
- OPUS continues to corrupt at least part of the double-prime structure and, in some splits, also corrupts a large integer;
- TC-big `three_way` and `lead_clause_then_suffix` preserve all four `M' S''` pairs exactly, but turn source `100000000` into target `10000000`; therefore the aggregate numeric gate correctly rejects them;
- database remained byte-identical; source coverage was byte-exact; selected ranks were rank0 only; no source rewriting, target literal injection, target surgery or separator injection occurred.

Conclusion: seq2346 is not rescuable by these four rank0 split geometries. Preserving the prime symbols while losing a digit from the radius is a strict regression, not a candidate for evaluator relaxation.

## Figure-reference sequence 325

Sequence `325` remains closed under the tested lead-split and preceding-boundary-pair geometries. Isolated figure-lead splitting can turn mechanical checks green while producing broken full-context syntax; restoring the syntactic boundary makes rank0 candidates inadmissible again. No target repair is permitted. Figure-reference implementation `/2` structurally enforces rank0-only selection; Product Core CI `34692166640` is green for that contract.

## Binding rescue/negative conclusions

- Generic OPUS/TC-big whole-context fallback, generic row-local TC-big punctuation fallback, broad Stage10-v2 geometry and generic bounded-parenthesis fallback remain rejected.
- Inline `[G]` remains unresolved under tested row-local and whole-context OPUS/TC-big formulations; tested hypotheses omit the marker.
- Large-integer source canonicalization/n-best feasibility rescued **0** baseline hard failures.
- Nonliteral numeric n-best can mechanically rescue isolated rows only through disallowed automatic beam selection.
- Never use target literal injection, corpus-specific target patches, placeholders, source rewriting, target surgery, automatic n-best cherry-picking or evaluator weakening.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Preserve immutable source/model/config/result identities and exact persisted predecessor lineage.
3. Current rescue research may persist only deterministic unmodified raw rank0 model output; higher beams are diagnostics unless a future explicit Product contract independently justifies a different policy.
4. Mechanical integrity is necessary but insufficient; semantic/boundary-aware review is mandatory.
5. Alternative geometry/model use requires a narrow existing-hard-failure/source-defined trigger.
6. A persisted evidence file may describe only its own wrapper unless it explicitly audits and certifies the complete predecessor lineage; do not infer lineage-wide safety from a local flag.
7. Final approved heavy evidence requires zero unresolved hard failures before downstream learner/export/release validation.

## Current quality frontier

Before further residual promotion work, construct a **rank0-clean full Opticks research baseline**. Harden every still-active n-best rescue selector that can automatically choose rank>0, starting with `illustration_label_rescue`; replay the maintained rescue chain from an exact pre-cherry-pick predecessor; then recompute hard-gate/residual census. Only that clean baseline should become the parent for subsequent prime/punctuation research.