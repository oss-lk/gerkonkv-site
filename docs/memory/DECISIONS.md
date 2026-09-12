# RocketDict durable decisions — L2

Store only conclusions expensive or risky to rediscover. Git/L3 remains chronology and primary evidence.

## Quality/release invariants

**Decision.** Speed, storage and convenience may not reduce Product quality/evidence. Real EN→RU MT is mandatory; no fake/identity/mock/dictionary substitution, silent truncation, evaluator weakening, target literal injection, source rewriting, target surgery, placeholders, corpus-specific target patches or automatic n-best cherry-picking.

`rocketdict/PRODUCT_TARGET.md` remains authoritative: final approved 90k+ heavy evidence needs zero unresolved numeric/symbol, punctuation and length failures, semantic acceptance, and successful complete learner-dictionary/export processing.

## Maintained implementation and assets

**Decision.** Forward work targets `rocketdict-product-core` + Workbench. Production baseline is pinned OPUS EN→RU `opus-2020-02-11` float32; TC-big remains an independent pinned comparator/narrow-rescue model, not a generic fallback.

## Translation-quality promotion

**Decision.** Promote only after classifying the defect, preserving immutable source ownership and validating contiguous/boundary-sensitive evidence. Mechanical hard-gate success is insufficient; semantic review is mandatory. Exact source spans may replace current translation only when representable by complete current rows. Research wrappers remain default OFF/not public-wired unless separately promoted.

## Run-19 research basis

**Decision.** Run `19` supersedes run18 as the best accepted persisted **research** basis: **20 numeric / 15 punctuation / 0 length, 34 unique**. Identities: workflow `34676310994`, artifact `10292442391`, ZIP SHA `51e00030d19799157d83db8a9dbc9093851da9be897619e465699b2cde72ef91`, output SHA `48096e0c1085c0598bc8abf212a2b2ba9a1109bb232fa2487c0472f35c06a1d9`, SQLite SHA `8519ea592b0bd948b68980ed19b710f05f20f9e0a60f0cb6c3e1a7763d5a8f76`, evidence SHA `ba6b24c0b4f628d908b5310aaf05268de2323033d7bbb629d081d755ddb8bf5f`.

It composes over exact run18. A new source-defined bounded-question wrapper attempts contexts `2462` and `2726`; only raw OPUS rank0 for `2462` is accepted. `2726` remains unchanged because emphasis preservation vetoes the candidate. 3341 other base rows are target-exact; source reconstruction and SQLite/FK integrity pass.

## Source-defined bounded question rescue

**Decision.** `rocketdict-stage12-question-mark-whole-context-rescue/1` is an accepted default-OFF research layer because it addresses a geometry-caused question-mark defect without widening the generic planner.

The trigger requires one complete Stage10 context represented by 2+ current split rows, one immutable source terminal `?`, extra premature target question-mark debt, no unrelated hard/research debt, and `<=160` NLP tokens. Only raw OPUS rank0 is eligible. Strict hard/research checks, Gutenberg emphasis, source coverage and conservative content-volume checks remain vetoes. Run19 proves one acceptance and one fail-closed rejection.

## Generic bounded-parenthesis rescue is rejected

**Decision.** The run19 bounded-parenthesis DOE `34676468786` does **not** justify a generic whole-context parenthesis rescue, even though counterfactual hard counts look attractive.

Four split contexts inside the 160-token cap were tested. TC-big rank0 is mechanically admissible on `668`, `1393`, `1977` but semantic inspection finds material omissions in `1393` and `1977`. OPUS rank0 is admissible only on `1393`; OPUS `668` still loses one of the two parenthetical clauses; `2969` remains inadmissible. OPUS rank2 for `1977` is evidence that search can recover content, but automatic n-best cherry-picking is not allowed.

A future `1393`-class wrapper is permitted only if a generic source-owned predicate can distinguish that safe case from unsafe siblings without encoding corpus offset, source phrase or expected target text. Otherwise `1393` stays research-only.

## Stage10 V2 and generic fallbacks remain rejected

**Decision.** Product/default Stage10 stays V1. Broad V2 resegmentation, generic row-local TC-big punctuation fallback, generic OPUS/TC-big whole-context fallback and broad square-bracket repair all remain rejected because mechanically clean outputs have demonstrated semantic loss.

## Residual defects stay family-specific

**Decision.** No universal punctuation/numeric fixer. Current run19 punctuation residuals mix square-bracket losses, parenthesis losses/corruption and question migration. In particular, bounded question `2726` is blocked by emphasis; oversized question context `2730` is above the proven cap. Square-bracket residuals also have different geometries: `54796` is unsplit and carries numeric debt, `301051` is already a grouped unit, while only `[G]` at `112541` is a bounded split-context candidate.

## Audit failures are classified before Product changes

**Decision.** A red heavy workflow is not automatically a Product/model defect. Inspect persisted output/logs first. Repair harness-only defects without weakening Product acceptance semantics; never change evaluators merely to make a run green.

## Acceptance order

**Decision.** Real source→Stage25 smoke/replay must be green before full-corpus acceptance. Final complete public-domain translation evidence must reach zero hard failures and semantic acceptance before downstream heavy learner/export and Windows clean-install/distribution become the release frontier.

## Memory protocol

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Stale L1 is repaired from L3 before new work. Before user-facing development completion, synchronize L1/L2 to actual HEAD/CI/artifacts.
