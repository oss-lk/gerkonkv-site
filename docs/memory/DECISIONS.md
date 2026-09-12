# RocketDict durable decisions — L2

Store only conclusions expensive or risky to rediscover. Git/L3 remains chronology and primary evidence.

## Quality/release invariants

**Decision.** Quality cannot be traded for speed/storage/convenience. No fake MT, silent truncation, evaluator weakening, target literal injection, source rewriting, target surgery, placeholders, corpus-specific target patches or automatic n-best cherry-picking. Final approved 90k+ evidence needs zero unresolved numeric/symbol, punctuation and length failures plus semantic/downstream acceptance.

## Historical run23 is not rank0-clean promotion lineage

**Decision.** Historical run `23` remains immutable research evidence (**17 numeric/symbol / 14 punctuation / 0 length; 30 unique failing sequences; 3337 rows**) but is **not** the parent for future promotion. Direct lineage audit found disallowed historical automatic n-best choices.

Exact run23 identities remain: workflow `34688874921`; artifact ID `10296696335`; ZIP SHA `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`; SQLite SHA `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`; translation-output SHA `976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493`; final-text SHA `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`; canonical evidence SHA `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`.

Lineage audit facts:

- historical run9 `illustration_label_rescue/1` accepted ranks `[3,3,0]`; rank3 spans were `72401:72443` (`FIG. 21`) and `90105:90147` (`FIG. 24`);
- inherited `tc_big_short_angular_dms_rescue/1` accepted source start `110881` from rank2;
- a wrapper-local `n_best_cherry_picking=false` flag never certifies predecessor lineage unless the evidence explicitly audits it.

Do not mutate run23 to hide this.

## Rank0-only rescue selection is a structural invariant

**Decision.** Automatic lower-beam fallback is forbidden. A persisted rescue target must be the unique unmodified raw rank0 output. Rank1+ may be retained for diagnostics only; missing/duplicate/malformed rank0 fails closed.

Current hardened wrappers include figure-reference `/2`, short-angular-DMS `/2`, angular-minute `/2`, illustration-label `/2`, TC-big target-delimiter `/2`, footnote-reference `/2`, semicolon-question `/2`, and equals-addition `/2`. Shared `translation_rank0.py` implements the unique-rank0 selector. Product Core CI `34694302843` is green for both dependency-light and real-runtime coverage after this hardening.

## Clean replay must certify effective boundary, not assume run numbering

**Decision.** The clean-replay boundary is defined by translation identity and safe lineage, not by an assumed count of newly created database run IDs.

First heavy rank0-clean workflow `34694587892` (artifact `10298234071`) successfully authenticated the historical SQLite and pinned OPUS/TC-big assets, then completed expensive replay computation. It failed only because the harness expected 15 newly created runs while current contracts created 18.

Persisted replay evidence proves the three extra runs are safe recomputation of the pre-boundary layers:

- new run `24` is source/target/geometry byte-identical to historical run `6`;
- new run `25` is byte-identical to historical run `7`;
- new run `26` is byte-identical to historical run `8`.

The clean chain then continues through new run `41`. Historical illustration rank3 and short-DMS rank2 selections disappear under current contracts; new persisted rescue selections are rank0 only.

Therefore do **not** change Product gates to make the workflow green. Repair the harness so it requires 18 new runs **and explicitly proves** `24→26 == 6→8` by translation-row identity before accepting the post-boundary lineage. Final clean counts/census remain untrusted until the corrected workflow completes and authenticates them.

## Historical run23 residual census is family evidence, not the next parent

**Decision.** Corrected census workflow `34690365432` remains authoritative for describing exact historical run23 residuals. Artifact ID `10296887793`; ZIP SHA `8cc7ea22a12f27ee0105767bfc7b13c39a9493e945e6d32508b847151c986393`; evidence SHA `55848393832fd777d7ab23f03f36d8fb2eb1031748faa0d2a096a35ea781ed58`.

Because clean replay removes historical rank>0 rescues and can alter segmentation, rerun the census on the authenticated clean final run before selecting the next promotion family.

## Sequence 2346 angle-list geometries are exhausted under current models

**Decision.** Do not promote or repeat the four tested source split geometries for historical run23 seq `2346` without materially new evidence.

DOE workflow `34693396634` (artifact `10298311979`, evidence SHA `094140b1add91c3cdb6294319cfc691d38d488f97966c5cb41a9ae2386d055d6`) tested `whole_row`, `three_way`, `lead_clause_then_suffix`, and `prefix_then_clause_suffix` with raw rank0 OPUS and TC-big. All eight aggregate candidates are inadmissible. TC-big preserves all four angular pairs in two geometries but changes `100000000` to `10000000`; no evaluator relaxation/target digit repair is permitted.

## Figure-reference sequence 325 is closed under tested geometries

**Decision.** Do not turn sequence `325` into a rescue from the existing figure-lead split or preceding-boundary-pair experiments. Isolated splitting can make mechanical checks green while breaking full-context syntax; restoring the syntactic boundary makes rank0 candidates inadmissible. A future revisit requires materially new source-defined geometry/model evidence.

## Source-defined parenthetical rescue

**Decision.** `rocketdict-stage12-parenthetical-whole-context-rescue/1` remains accepted default-OFF research evidence because its corpus-wide source predicate distinguished a safe rank0 case from unsafe siblings without offset/text whitelisting. It still requires complete clean-lineage validation before any Product promotion.

## Inline `[G]` is not a simple resegmentation defect

**Decision.** Do not create an inline-footnote wrapper for context `598` under current model/search evidence. Corrected whole-context DOE `34679178153` tested six OPUS and six TC-big hypotheses on the exact source; all omit `[G]` and none is mechanically admissible.

## Generic fallbacks remain rejected

**Decision.** Product/default Stage10 stays V1. Broad V2 resegmentation, generic row-local TC-big punctuation fallback, generic OPUS/TC-big whole-context fallback, generic bounded-parenthesis fallback and broad square-bracket repair remain rejected because mechanically clean alternatives have demonstrated semantic loss.

## Numeric/symbol work remains family-specific

**Decision.** The historical run23 prime feature cluster is heterogeneous: eight true angular prime/double-prime cases and two apostrophe-decimal cases. Do not treat all ten as one rescue family.

Large-integer source canonicalization/n-best feasibility rescued zero baseline failures; nonliteral numeric beam selection requires disallowed automatic n-best choice. Do not repeat either without materially new geometry/model evidence.

## Audit/orchestration classification

**Decision.** A red workflow does not justify Product changes until failure is classified. Harness/provisioning/provenance defects are repaired without weakening Product criteria. Derived identities should be authenticated from canonical upstream evidence rather than duplicated manually when practical.

## Forward replay decision

**Decision.** Immediate path:

1. repair the clean-replay harness to validate the observed 18-run recomputation and explicit `24→26 == 6→8` translation identity;
2. rerun and authenticate the final clean run, source/model identities, rank0-only selections, byte-exact coverage, SQLite/FK integrity and evidence hashes;
3. recompute the full hard-gate/residual census and semantic diff on that final clean run;
4. make the authenticated clean result the only parent for subsequent residual-family promotion;
5. continue to zero hard failures, then finish learner/export and Windows release validation.

A lower failure count from historical run23 is not sufficient reason to retain disallowed lineage.

## Memory protocol

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Before any user-facing development result, synchronize L1 plus both mandatory L2 files to actual HEAD/CI/artifacts.
