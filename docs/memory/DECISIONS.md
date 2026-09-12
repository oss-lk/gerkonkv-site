# RocketDict durable decisions — L2

Store only conclusions expensive or risky to rediscover. Git/L3 remains chronology and primary evidence.

## Quality/release invariants

**Decision.** Quality cannot be traded for speed/storage/convenience. No fake MT, silent truncation, evaluator weakening, target literal injection, source rewriting, target surgery, placeholders, corpus-specific target patches or automatic n-best cherry-picking. Final approved 90k+ evidence needs zero unresolved numeric/symbol, punctuation and length failures plus semantic/downstream acceptance.

## Current persisted research basis: run23

**Decision.** Run `23` is the current best accepted persisted **research** translation basis: **17 numeric/symbol / 14 punctuation / 0 length, 30 unique hard-failing sequences** over `3337` rows. Its exact predecessor run22 is **18/14/0,31** over `3338` rows.

Run23 identities: workflow `34688874921`; artifact ID `10296696335`; ZIP SHA `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`; SQLite SHA `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`; translation-output SHA `976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493`; final-text SHA `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`; canonical evidence SHA `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`.

The run23 emphasized-modifier rescue accepted context group `[2496,2497]`, rejected `[2633,2634]`, preserved `3336` untouched rows exactly, reconstructed source byte-exactly and passed SQLite/FK integrity. It is research-only: `promotion_allowed=false`, `automatic_product_default_allowed=false`.

## Run23 residual census and provenance

**Decision.** The corrected read-only run23 census is authoritative for choosing the next hard-failure family. Workflow `34690365432`, artifact ID `10296887793`, ZIP SHA `8cc7ea22a12f27ee0105767bfc7b13c39a9493e945e6d32508b847151c986393`, census evidence SHA `55848393832fd777d7ab23f03f36d8fb2eb1031748faa0d2a096a35ea781ed58`. It verified the exact persisted run23 database without mutation and preserved byte-exact source coverage.

The earlier census attempt `34689198589` failed because a derived SQLite digest had been copied independently and incorrectly. Derived identities must therefore be authenticated/derived from the pinned canonical upstream evidence whenever possible instead of being maintained as duplicated hand-copied constants.

The authoritative residual sequence set is `[325,641,642,644,646,650,743,750,751,752,1499,1579,1755,1788,2110,2290,2346,2357,2375,2591,2721,2741,2889,2997,3000,3007,3011,3083,3211,3305]`.

## Source-defined parenthetical rescue

**Decision.** `rocketdict-stage12-parenthetical-whole-context-rescue/1` is an accepted default-OFF research layer only because a corpus-wide source predicate distinguished the safe rank0 case from unsafe siblings without offset/text whitelisting.

Eligibility requires one complete split Stage10 context, `<=160` NLP tokens, exactly one short balanced source parenthetical pair (`<=8` alpha words), both parentheses absent from aggregate current target, other hard punctuation exact and unrelated member diagnostics clean. Only raw OPUS rank0 is eligible, with strict hard/research/emphasis/punctuation/content-volume vetoes.

## Inline `[G]` is not a simple resegmentation defect

**Decision.** Do not create an inline-footnote wrapper for context `598` under the current model/search evidence. Corrected whole-context DOE `34679178153` tested six OPUS and six TC-big hypotheses on the exact 115-token Stage10 source. All twelve omit `[G]`; no hypothesis is mechanically admissible. This materially different formulation confirms that the earlier row-local TC-big failure was not merely caused by Stage12 splitting.

The first DOE attempt `34679083884` is classified as orchestration-only: it checked the wrong snapshot filename (`pytorch_model.bin`). Commit `6b90cc75` corrected provisioning to the pinned `model.safetensors`/proven snapshot pattern without changing model or acceptance criteria.

## Generic fallbacks remain rejected

**Decision.** Product/default Stage10 stays V1. Broad V2 resegmentation, generic row-local TC-big punctuation fallback, generic OPUS/TC-big whole-context fallback, generic bounded-parenthesis fallback and broad square-bracket repair remain rejected because mechanically clean alternatives have demonstrated semantic loss.

## Numeric/symbol frontier remains family-specific

**Decision.** Start new work from exact run23 and its verified 30-sequence census. Residual numeric/symbol work must remain source-defined and defect-family-specific. Do not repeat tested large-integer source canonicalization/n-best feasibility (0 baseline rescues) or nonliteral numeric beam selection (mechanical rescues only through disallowed automatic n-best choice) without materially new source/model geometry or evidence.

Sequence `325` is the first current investigation because `[in _Fig._ 16.]` overlaps an existing narrow TC-big figure-reference experiment. Inspect that implementation, tests, history and actual lineage before inventing another rescue. If whole-row geometry is genuinely exhausted, a split-geometry experiment is admissible only if selection stays source-defined/fail-closed and uses unmodified raw rank0 model outputs.

## Audit/orchestration classification

**Decision.** A red workflow does not justify Product changes until the failure is classified. Harness/provisioning/provenance defects are repaired without weakening Product criteria. The `[G]` snapshot-filename failure and the first run23 census digest mismatch are concrete examples.

## Memory protocol

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Before any user-facing development result, synchronize L1 plus both mandatory L2 files to actual HEAD/CI/artifacts.
