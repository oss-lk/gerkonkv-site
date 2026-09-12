# RocketDict durable decisions — L2

Store only conclusions expensive or risky to rediscover. Git/L3 remains chronology and primary evidence.

## Quality/release invariants

**Decision.** Quality cannot be traded for speed/storage/convenience. No fake MT, silent truncation, evaluator weakening, target literal injection, source rewriting, target surgery, placeholders, corpus-specific target patches or automatic n-best cherry-picking. Final approved 90k+ evidence needs zero unresolved numeric/symbol, punctuation and length failures plus semantic/downstream acceptance.

## Current persisted research basis: run23

**Decision.** Run `23` remains the current best accepted persisted **research** translation basis: **17 numeric/symbol / 14 punctuation / 0 length, 30 unique hard-failing sequences** over `3337` rows. Exact predecessor run22 is **18/14/0,31** over `3338` rows.

Run23 identities: workflow `34688874921`; artifact ID `10296696335`; ZIP SHA `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`; SQLite SHA `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`; translation-output SHA `976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493`; final-text SHA `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`; canonical evidence SHA `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`.

The run23 emphasized-modifier rescue accepted `[2496,2497]`, rejected `[2633,2634]`, preserved `3336` untouched rows exactly, reconstructed source byte-exactly and passed SQLite/FK integrity. It is research-only: `promotion_allowed=false`, `automatic_product_default_allowed=false`.

## Run23 residual census and provenance

**Decision.** Corrected read-only census workflow `34690365432` is authoritative for choosing the next hard-failure family. Artifact ID `10296887793`, ZIP SHA `8cc7ea22a12f27ee0105767bfc7b13c39a9493e945e6d32508b847151c986393`, census evidence SHA `55848393832fd777d7ab23f03f36d8fb2eb1031748faa0d2a096a35ea781ed58`. It verified exact run23 without mutation and preserved byte-exact source coverage.

The earlier census `34689198589` failed because a derived SQLite digest was copied independently and incorrectly. Derived identities should be authenticated/derived from pinned canonical upstream evidence instead of maintained as duplicated hand-copied constants whenever possible.

Residual sequences: `[325,641,642,644,646,650,743,750,751,752,1499,1579,1755,1788,2110,2290,2346,2357,2375,2591,2721,2741,2889,2997,3000,3007,3011,3083,3211,3305]`.

## Rank0-only rescue selection is structural

**Decision.** Current research rescue selectors may not use automatic beam cherry-picking. The TC-big figure-reference wrapper is tightened to `rocketdict-stage12-tc-big-figure-reference-lead-rescue/2` / selector `/2`: all generated hypotheses may be retained as raw diagnostic evidence, but only the unique `rank==0` hypothesis is selection-authorized. If rank0 fails, the rescue fails closed even when rank1+ pass mechanical checks. Missing or duplicate rank0 cardinality is a StageExecutionError.

This change does not rewrite historical evidence; it hardens the forward implementation to match the safety property of the actually persisted successful figure-reference replay, whose accepted case selected rank0. Product Core CI `34692166640` is green on commit `58654b801ed93562001b08479e194256af601fbc`, including explicit regressions for rank1 rejection and rank0 cardinality failure.

## Figure-reference sequence 325 is closed under tested geometries

**Decision.** Do not turn sequence `325` into a rescue from the existing split/boundary experiments.

- Figure-lead split DOE `34683173809` isolates `[in _Fig._ 16.]` from the following body. Raw rank0 OPUS and TC-big become mechanically admissible, but reconstructed full-context syntax/boundary quality is broken; the translation joins the preceding clause into a `...Призма DH[в рис. 16.] быть...`-class result. This is not semantically acceptable evidence.
- Figure-boundary-pair DOE `34683394207` restores the preceding incomplete phrase. Rank0 OPUS preserves the figure concept but damages Gutenberg emphasis/reference form; rank0 TC-big drops the figure reference. Both are inadmissible under maintained checks and any repair would violate the no-target-surgery rule.

Therefore the tested `figure lead | whitespace | body` and preceding-boundary-pair formulations are exhausted. A future revisit requires materially new source-defined geometry/model evidence, not a repackaging of either DOE.

## Source-defined parenthetical rescue

**Decision.** `rocketdict-stage12-parenthetical-whole-context-rescue/1` remains an accepted default-OFF research layer only because a corpus-wide source predicate distinguished the safe rank0 case from unsafe siblings without offset/text whitelisting.

Eligibility requires one complete split Stage10 context, `<=160` NLP tokens, exactly one short balanced source parenthetical pair (`<=8` alpha words), both parentheses absent from aggregate current target, other hard punctuation exact and unrelated member diagnostics clean. Only raw OPUS rank0 is eligible, with strict hard/research/emphasis/punctuation/content-volume vetoes.

## Inline `[G]` is not a simple resegmentation defect

**Decision.** Do not create an inline-footnote wrapper for context `598` under current model/search evidence. Corrected whole-context DOE `34679178153` tested six OPUS and six TC-big hypotheses on the exact 115-token Stage10 source. All twelve omit `[G]`; no hypothesis is mechanically admissible.

The first DOE `34679083884` is orchestration-only: it checked the wrong snapshot filename (`pytorch_model.bin`). Commit `6b90cc75` corrected provisioning to the pinned `model.safetensors`/proven snapshot pattern without changing model or acceptance criteria.

## Generic fallbacks remain rejected

**Decision.** Product/default Stage10 stays V1. Broad V2 resegmentation, generic row-local TC-big punctuation fallback, generic OPUS/TC-big whole-context fallback, generic bounded-parenthesis fallback and broad square-bracket repair remain rejected because mechanically clean alternatives have demonstrated semantic loss.

## Numeric/symbol frontier remains family-specific

**Decision.** Start new work from exact run23 and its verified 30-sequence census. With sequence `325` closed under tested figure geometries, inspect the `numeric_prime_notation` cluster next because it is the largest identified residual source feature (`10` hits). First recover exact affected rows, defect-subclass overlaps and prior prime-notation experiments; do not assume one mechanism fits all ten.

Do not repeat tested large-integer source canonicalization/n-best feasibility (0 baseline rescues) or nonliteral numeric beam selection (mechanical rescues only through disallowed automatic n-best choice) without materially new source/model geometry or evidence.

## Audit/orchestration classification

**Decision.** A red workflow does not justify Product changes until failure is classified. Harness/provisioning/provenance defects are repaired without weakening Product criteria. The `[G]` snapshot-filename failure and first run23 census digest mismatch are concrete examples.

## Memory protocol

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Before any user-facing development result, synchronize L1 plus both mandatory L2 files to actual HEAD/CI/artifacts.
