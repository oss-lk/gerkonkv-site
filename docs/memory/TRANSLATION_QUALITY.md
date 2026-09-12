# RocketDict maintained translation quality — L2

Durable translation-quality conclusions only. This is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). L3 source/tests/CI/artifacts outrank this file.

## Maintained contracts

- Production MT: pinned OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product/default Stage10 is V1; research V2 remains explicit only.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/6`; Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big remains a pinned independent comparator/narrow rescue, not a generic fallback. Research wrappers remain default OFF/not public-wired.
- Persisted rescue output must be the unique unmodified raw rank0 hypothesis. Higher beams may remain diagnostic evidence but cannot alter the target; missing/duplicate/malformed rank0 fails closed.

Current structurally rank0-only wrappers include figure-reference `/2`, short-angular-DMS `/2`, angular-minute `/2`, illustration-label `/2`, TC-big target-delimiter `/2`, footnote-reference `/2`, semicolon-question `/2`, and equals-addition `/2`. Shared `translation_rank0.py` enforces the unique-rank0 policy. Product Core CI workflow `34694302843` passed dependency-light and real-runtime jobs after this hardening.

## Canonical complete Opticks basis

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` chars.

Historical persisted run `23` remains immutable research evidence: **17 numeric/symbol / 14 punctuation / 0 length, 30 unique hard-failing sequences** over `3337` rows. It is **not rank0-clean lineage** and must not parent promotion work.

Run23 identities:

- workflow `34688874921`; artifact ID `10296696335`; ZIP SHA-256 `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`;
- SQLite SHA-256 `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`;
- translation output SHA-256 `976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493`;
- final text SHA-256 `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`;
- canonical evidence SHA-256 `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`.

Direct SQLite lineage audit proved historical automatic n-best selection:

- run9 `illustration_label_rescue/1` accepted ranks `[3,3,0]`; rank3 spans were `72401:72443` (`FIG. 21`) and `90105:90147` (`FIG. 24`);
- inherited `tc_big_short_angular_dms_rescue/1` selected rank2 at source start `110881` for `Whence this Angle is 2 deg. 0'. 7''.`.

Historical run23 is preserved unchanged; lower hard-failure count does not justify retaining disallowed lineage.

## Rank0-clean replay status

Workflow `34694587892` / artifact `10298234071` is the first full replay under current rank0-only contracts. The exact historical run23 SQLite was used only as a container/cache source; pinned OPUS and TC-big assets authenticated successfully.

The replay performed all expensive model/rescue computation but the workflow ended red on an orchestration assertion: the harness expected 15 newly created Stage12 runs and observed 18. This is not a Product evaluator/model failure.

Persisted replay SQLite establishes why:

- current contracts recomputed safe `length → citation → numeric-hard` layers from historical run4, creating new runs `24→26`;
- these three runs are source/target/geometry byte-identical to historical runs `6→8` respectively (`24==6`, `25==7`, `26==8` by translation-row identity);
- the clean chain then proceeds through new runs up to `41`;
- historical illustration rank3 and short-DMS rank2 selections no longer survive; persisted rescue selections in the new chain are rank0 only.

Therefore the correct harness invariant is not “exactly 15 new runs from run8”, but “18 new runs from run4 with explicit proof that the first three reproduce historical clean boundary runs `6→8` byte-for-byte, then all post-boundary rescue selections are unique raw rank0”. The completed rerun must still authenticate final hard-gate counts, census, source coverage, semantic diffs, SQLite/FK integrity and evidence hashes before this becomes the canonical forward baseline.

## Verified historical run23 residual census

Workflow `34690365432`, artifact ID `10296887793`, ZIP SHA-256 `8cc7ea22a12f27ee0105767bfc7b13c39a9493e945e6d32508b847151c986393`, evidence SHA-256 `55848393832fd777d7ab23f03f36d8fb2eb1031748faa0d2a096a35ea781ed58` remains authoritative only for describing historical run23.

Historical residual sequences: `[325,641,642,644,646,650,743,750,751,752,1499,1579,1755,1788,2110,2290,2346,2357,2375,2591,2721,2741,2889,2997,3000,3007,3011,3083,3211,3305]`.

Its counts must not be used as the forward frontier after the rank0-clean replay; recompute the census on the final clean run because row geometry and failures can change when rank>0 rescues disappear.

## Prime-notation findings

The historical `numeric_prime_notation=10` feature is heterogeneous. Eight rows are true angular prime/double-prime cases; two are Newton-style apostrophe decimals (`1'688`, `0'35`) and are not equivalent angular-prime rescue targets.

Existing whole/multi-context raw rank0 OPUS/TC-big attempts failed to produce admissible candidates for the main prime families. Do not repeat them without materially new geometry.

### Sequence 2346 angle-list DOE

Workflow `34693396634` / artifact `10298311979` / artifact digest `sha256:1074aed027bdab4fd9ffb9bdd0375decbf18b7baace8f2e6330517e07904fcbd` tested four source-owned geometries under raw rank0 OPUS and TC-big. Evidence SHA-256: `094140b1add91c3cdb6294319cfc691d38d488f97966c5cb41a9ae2386d055d6`.

- all 8 aggregate candidates are mechanically inadmissible;
- TC-big `three_way` and `lead_clause_then_suffix` preserve all four `M' S''` pairs exactly but change `100000000` to `10000000`;
- database/source remained immutable; no target repair/separator injection/n-best selection occurred.

Conclusion: these four geometries are exhausted under current models. Preserving primes while losing a digit is a strict regression, not grounds for evaluator relaxation.

## Figure-reference sequence 325

Sequence `325` remains closed under tested lead-split and preceding-boundary-pair geometries. Isolated figure-lead splitting can turn mechanical checks green while producing broken full-context syntax; restoring the syntactic boundary makes rank0 candidates inadmissible again. No target repair is permitted.

## Binding rescue/negative conclusions

- Generic OPUS/TC-big whole-context fallback, generic row-local TC-big punctuation fallback, broad Stage10-v2 geometry and generic bounded-parenthesis fallback remain rejected.
- Inline `[G]` remains unresolved under tested row-local and whole-context OPUS/TC-big formulations; tested hypotheses omit the marker.
- Large-integer source canonicalization/n-best feasibility rescued **0** baseline hard failures.
- Nonliteral numeric n-best can mechanically rescue isolated rows only through disallowed automatic beam selection.
- Never use target literal injection, corpus-specific target patches, placeholders, source rewriting, target surgery, automatic n-best cherry-picking or evaluator weakening.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Preserve immutable source/model/config/result identities and exact persisted predecessor lineage.
3. Current rescue research may persist only deterministic unmodified raw rank0 model output; higher beams are diagnostics only.
4. Mechanical integrity is necessary but insufficient; semantic/boundary-aware review is mandatory.
5. Alternative geometry/model use requires a narrow existing-hard-failure/source-defined trigger.
6. A persisted evidence file may describe only its own wrapper unless it explicitly audits and certifies the complete predecessor lineage.
7. Final approved heavy evidence requires zero unresolved hard failures before downstream learner/export/release validation.

## Current quality frontier

Repair the clean-replay harness to accept the demonstrated 18-run recomputation only when it also proves `24→26` are byte-identical translations of historical `6→8`. Rerun the heavy workflow, authenticate the final clean run and residual census, then use that clean baseline as the only parent for further numeric/punctuation rescue research.
