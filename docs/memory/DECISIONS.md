# RocketDict durable decisions — L2

Store only conclusions expensive or risky to rediscover. Git/L3 remains chronology and primary evidence.

## Quality/release invariants

**Decision.** Quality cannot be traded for speed/storage/convenience. No fake MT, silent truncation, evaluator weakening, target literal injection, source rewriting, target surgery, placeholders, corpus-specific target patches or automatic n-best cherry-picking. Final approved 90k+ evidence needs zero unresolved numeric/symbol, punctuation and length failures plus semantic/downstream acceptance.

## Authenticated run41 is the only forward promotion parent

**Decision.** The corrected full-Opticks rank0-clean replay is canonical for all subsequent translation-quality promotion work.

Workflow `34695164876` succeeded from engineering HEAD `041b0293eecccc375c6264a39704e6b25d2b6665`. Artifact `10297359600`, digest `sha256:e2d7549965d893c0b877cfe21057b8490134392a966e42fd72483ebb19836b4d`.

Authenticated final clean run `41`:

- `3335` rows;
- **18 numeric/symbol / 16 punctuation / 0 length, 33 unique**;
- translation-output SHA-256 `d8948e43158a126703a90e6ce1cd25725da8774e1db64410ca67e3ec7bb1a10f`;
- final-text SHA-256 `23170683ddbe183b4da6b4097d72cedc86b9c98044e9f3e1dee015015e16e15e`;
- SQLite SHA-256 `e48df8a90a3aa5e07bbc7e86c150d7b65ce450e7b6a0ec0d2e34a0caf9846e2e`;
- replay evidence SHA-256 `e7504ef18ead81e9c437ab8236b787a7d59082c272ef102fcc9bae6e281deac1`;
- independent census evidence SHA-256 `b384ae0936f2ec792dd8ec6fbfcdf5da0dea1ba097df951c6049f2f2cbbb5319`.

The replay has byte-exact source coverage, SQLite integrity `ok`, zero FK violations, no source/target rewriting, no literal injection/placeholders/corpus patches/evaluator weakening, and only raw unique rank0 persisted rescue selections.

Do not parent new rescue promotion from historical run23 even when its raw hard-failure count is numerically lower.

## Effective clean boundary is defined by translation identity, not run numbering

**Decision.** Safe replay boundaries must be certified by content/geometry identity and lineage, not assumed database run cardinality.

The corrected replay starts from historical run4 and creates 18 new runs. New runs `24→26` are translation/source/geometry-identical to historical clean runs `6→8`, with identity SHAs:

- `24 == 6`: `093cbd882a44e1ca31ff30dcb95c71f33307da464ecb51338ba2d9e48734cba0`;
- `25 == 7`: `5586d6dc7716c258c492e2f7da803aa6ccdc5f48396e765b2fb4c6db78a6cb6d`;
- `26 == 8`: `43d05d6227aab8ba57c90f14db5b70bcfc153d32b39eafeb4ffc5d42750affdb`.

Run `27` is therefore the first post-boundary recomputation. The earlier red replay was an orchestration-cardinality defect, not grounds to modify Product gates.

## Historical run23 remains immutable evidence, not clean lineage

**Decision.** Historical run `23` remains immutable research evidence (**17 numeric/symbol / 14 punctuation / 0 length; 30 unique; 3337 rows**) but is not the parent for future promotion because direct lineage audit found forbidden automatic n-best choices.

Exact historical identities remain: workflow `34688874921`; artifact `10296696335`; ZIP SHA `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`; SQLite SHA `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`; translation-output SHA `976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493`; final-text SHA `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`; evidence SHA `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`.

Lineage audit facts:

- historical run9 `illustration_label_rescue/1` accepted ranks `[3,3,0]`; rank3 spans were `72401:72443` (`FIG. 21`) and `90105:90147` (`FIG. 24`);
- inherited `tc_big_short_angular_dms_rescue/1` accepted source start `110881` from rank2;
- a wrapper-local `n_best_cherry_picking=false` flag never certifies predecessor lineage unless the evidence explicitly audits it.

Do not mutate run23 to hide this.

## Removing illegal higher beams exposes three real clean-frontier failures

**Decision.** The reappearance of seq `424`, `514`, `638` in run41 is an expected consequence of the rank0-only policy, not a regression to “fix” by restoring old ranks.

- seq `424`, `[Illustration: FIG. 21.]\n\n_Illustration._`: rank0 emits two bracketed illustration clauses and fails punctuation preservation;
- seq `514`, analogous `FIG. 24` pair: same family;
- seq `638`, `Whence this Angle is 2 deg. 0'. 7''.`: rank0 renders prime notation as feet and fails numeric-prime preservation.

Future work on these rows must use materially new **source-defined** geometry/model evidence with raw rank0 only. Historical rank3/rank2 outputs remain diagnostics, never candidates for automatic persistence.

## Rank0-only rescue selection is a structural invariant

**Decision.** Automatic lower-beam fallback is forbidden. A persisted rescue target must be the unique unmodified raw rank0 output. Rank1+ may be retained for diagnostics only; missing/duplicate/malformed rank0 fails closed.

Current hardened wrappers include figure-reference `/2`, short-angular-DMS `/2`, angular-minute `/2`, illustration-label `/2`, TC-big target-delimiter `/2`, footnote-reference `/2`, semicolon-question `/2`, and equals-addition `/2`. Shared `translation_rank0.py` implements the unique-rank0 selector. Product Core CI `34694302843` is green for dependency-light and real-runtime coverage after hardening.

## Historical run23 census is descriptive only

**Decision.** Historical census workflow `34690365432`, artifact `10296887793`, ZIP SHA `8cc7ea22a12f27ee0105767bfc7b13c39a9493e945e6d32508b847151c986393`, evidence SHA `55848393832fd777d7ab23f03f36d8fb2eb1031748faa0d2a096a35ea781ed58` remains authoritative only for historical run23.

The forward residual set is the authenticated run41 census, not the historical run23 list.

## Sequence 2346 angle-list geometries are exhausted under current models

**Decision.** Do not promote or repeat the four tested source split geometries for historical run23 seq `2346` without materially new evidence.

DOE workflow `34693396634` (artifact `10298311979`, evidence SHA `094140b1add91c3cdb6294319cfc691d38d488f97966c5cb41a9ae2386d055d6`) tested `whole_row`, `three_way`, `lead_clause_then_suffix`, and `prefix_then_clause_suffix` with raw rank0 OPUS and TC-big. All eight aggregate candidates are inadmissible. TC-big preserves all four angular pairs in two geometries but changes `100000000` to `10000000`; no evaluator relaxation/target digit repair is permitted.

## Figure-reference sequence 325 is closed under tested geometries

**Decision.** Do not turn sequence `325` into a rescue from the existing figure-lead split or preceding-boundary-pair experiments. Isolated splitting can make mechanical checks green while breaking full-context syntax; restoring the syntactic boundary makes rank0 candidates inadmissible. A future revisit requires materially new source-defined geometry/model evidence.

## Source-defined parenthetical rescue

**Decision.** `rocketdict-stage12-parenthetical-whole-context-rescue/1` remains accepted default-OFF research evidence because its corpus-wide source predicate distinguished a safe rank0 case from unsafe siblings without offset/text whitelisting. Any Product promotion still requires complete clean-lineage validation from run41.

## Inline `[G]` is not a simple resegmentation defect

**Decision.** Do not create an inline-footnote wrapper for context `598` under current model/search evidence. Corrected whole-context DOE `34679178153` tested six OPUS and six TC-big hypotheses on the exact source; all omit `[G]` and none is mechanically admissible.

## Generic fallbacks remain rejected

**Decision.** Product/default Stage10 stays V1. Broad V2 resegmentation, generic row-local TC-big punctuation fallback, generic OPUS/TC-big whole-context fallback, generic bounded-parenthesis fallback and broad square-bracket repair remain rejected because mechanically clean alternatives have demonstrated semantic loss.

## Numeric/symbol work remains family-specific

**Decision.** Prime-marked source contexts are heterogeneous. True angular prime/double-prime notation and Newton-style apostrophe decimals must not share one rescue predicate merely because they contain apostrophes.

Large-integer source canonicalization/n-best feasibility rescued zero baseline failures; nonliteral numeric beam selection requires disallowed automatic n-best choice. Do not repeat either without materially new geometry/model evidence.

## Audit/orchestration classification

**Decision.** A red workflow does not justify Product changes until failure is classified. Harness/provisioning/provenance defects are repaired without weakening Product criteria. Derived identities should be authenticated from canonical upstream evidence rather than duplicated manually when practical.

## Forward decision

**Decision.** Immediate path from run41:

1. inventory already-tested source-defined geometries for clean-returned seq `424`, `514`, `638`;
2. run only materially new raw-rank0 OPUS/TC-big DOE for the illustration-pair and short-DMS families;
3. promote only a generic source-predicate, raw-rank0, mechanically clean and semantically acceptable default-OFF wrapper;
4. otherwise record that family as exhausted and move to the next run41 residual cluster;
5. after every promoted change, compose from run41 lineage and rerun the complete residual census;
6. continue to zero hard failures, then finish learner/export and Windows release validation.

A lower historical failure count is not sufficient reason to retain forbidden lineage.

## Memory protocol

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Before any user-facing development result, synchronize L1 plus both mandatory L2 files to actual HEAD/CI/artifacts.
