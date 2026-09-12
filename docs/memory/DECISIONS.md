# RocketDict durable decisions — L2

Store only conclusions expensive or risky to rediscover. Git/L3 remains chronology and primary evidence.

## Quality/release invariants

**Decision.** Quality cannot be traded for speed/storage/convenience. No fake MT, silent truncation, evaluator weakening, target literal injection, source rewriting, target surgery, placeholders, corpus-specific target patches or automatic n-best cherry-picking. Final approved 90k+ evidence needs zero unresolved numeric/symbol, punctuation and length failures plus semantic/downstream acceptance.

## Historical run23 is not rank0-clean promotion lineage

**Decision.** Historical run `23` remains the lowest-hard-failure full Opticks translation currently persisted (**17 numeric/symbol / 14 punctuation / 0 length; 30 unique failing sequences; 3337 rows**) and remains valuable immutable research evidence. It is **not** the clean parent for future promotion because direct audit of its SQLite lineage found historical automatic n-best selections that violate the current rank0-only rescue policy.

Exact run23 identities remain: workflow `34688874921`; artifact ID `10296696335`; ZIP SHA `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`; SQLite SHA `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`; translation-output SHA `976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493`; final-text SHA `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`; canonical evidence SHA `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`.

Lineage audit facts:

- run9 `illustration_label_rescue/1` accepted three groups with selected ranks `[3,3,0]`; the rank3 groups are source spans `72401:72443` (`FIG. 21`) and `90105:90147` (`FIG. 24`), represented by split rows `424/425` and `515/516` in the resulting lineage;
- inherited `tc_big_short_angular_dms_rescue/1` accepted seq `640` / source start `110881` from rank2;
- run23 local evidence flags for the final emphasized-modifier layer do not certify every earlier predecessor wrapper. A local `automatic_n_best...=false` flag must never be interpreted as lineage-wide proof unless the evidence explicitly audits predecessors.

Do not mutate or rewrite run23 to hide this. Build a new replay with rank0-only forward contracts and preserve run23 as historical evidence.

## Rank0-only rescue selection is a forward structural invariant

**Decision.** Current rescue selectors may not automatically choose a lower-ranked beam when rank0 fails. Generated rank1+ candidates may be retained for diagnostics/research comparison only; a persisted rescue target must be the unique unmodified rank0 output. Missing or duplicate rank0 fails closed.

The following TC-big wrappers are already hardened to this rule:

- figure-reference rescue/selector `/2`;
- short-angular-DMS rescue/selector `/2` (commit `41b7319` + regression `bda00c9`);
- angular-minute rescue/selector `/2` (commit `7d0f02f` + regression `f8512e5`).

Product Core CI run `34693256404` is green on the angular hardening. Remaining active n-best wrappers must be audited and hardened before constructing the clean heavy baseline, with `illustration_label_rescue` first because historical persisted evidence proves rank3 selection occurred there.

## Run23 residual census is historical-family evidence, not the next clean parent

**Decision.** Corrected census workflow `34690365432` remains authoritative for describing exact historical run23 residuals and choosing hypotheses to study. Artifact ID `10296887793`; ZIP SHA `8cc7ea22a12f27ee0105767bfc7b13c39a9493e945e6d32508b847151c986393`; evidence SHA `55848393832fd777d7ab23f03f36d8fb2eb1031748faa0d2a096a35ea781ed58`.

Residual sequences are `[325,641,642,644,646,650,743,750,751,752,1499,1579,1755,1788,2110,2290,2346,2357,2375,2591,2721,2741,2889,2997,3000,3007,3011,3083,3211,3305]`.

Because a rank0-clean replay can reintroduce failures or alter segmentation where historical rank>0 rescues were applied, rerun the full hard-gate/residual census on the new clean baseline before using its counts as the forward promotion frontier.

## Sequence 2346 angle-list geometries are exhausted under current models

**Decision.** Do not promote or repeat the four tested source split geometries for historical run23 seq `2346` without materially new evidence.

DOE workflow `34693396634` (artifact `10298311979`, evidence SHA `094140b1add91c3cdb6294319cfc691d38d488f97966c5cb41a9ae2386d055d6`) tested `whole_row`, `three_way`, `lead_clause_then_suffix`, and `prefix_then_clause_suffix` with raw rank0 OPUS and TC-big. All eight aggregate candidates are inadmissible.

TC-big can preserve all four angular `M' S''` pairs in two geometries, but in both it changes `100000000` to `10000000`. This is a real numeric regression and the maintained gate must reject it. No evaluator relaxation or target digit repair is permitted.

## Figure-reference sequence 325 is closed under tested geometries

**Decision.** Do not turn sequence `325` into a rescue from the existing figure-lead split or preceding-boundary-pair experiments. Isolated splitting can make mechanical checks green while breaking full-context syntax; restoring the syntactic boundary makes rank0 candidates inadmissible. A future revisit requires materially new source-defined geometry/model evidence.

## Source-defined parenthetical rescue

**Decision.** `rocketdict-stage12-parenthetical-whole-context-rescue/1` remains accepted default-OFF research evidence because its corpus-wide source predicate distinguished a safe rank0 case from unsafe siblings without offset/text whitelisting. This acceptance does not exempt it from future complete-lineage replay validation.

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

**Decision.** The immediate critical path is now:

1. audit all maintained rescue wrappers for automatic rank>0 selection and harden every active offender;
2. start the full Opticks replay from an exact predecessor before the first historical rank>0 rescue (run8 is the current identified boundary before `illustration_label_rescue` run9);
3. reapply the maintained source-defined rescue chain using current rank0-only contracts and immutable model/source identities;
4. compute a new complete hard-gate/residual census and semantic diff;
5. only then resume residual-family promotion work from that clean baseline.

A lower hard-failure count from historical run23 is not sufficient reason to retain disallowed lineage.

## Memory protocol

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Before any user-facing development result, synchronize L1 plus both mandatory L2 files to actual HEAD/CI/artifacts.