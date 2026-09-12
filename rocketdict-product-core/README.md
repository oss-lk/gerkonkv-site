# RocketDict Product Core

Status: maintained forward Product runtime (`1.0.0.dev1`).

This package is the current RocketDict implementation. It is maintained forward code, not a reconstruction of an unavailable historical 0.30.x package.

## Maintained Product path

The maintained core owns the Product execution/storage path through Stage25:

`source → Stage8 production spaCy NLP → Stage10 context → Stage12 real OPUS EN→RU → Stage14 refinement boundary → Stage15 hard gates → Stage16 approval → Stage17 alignment → Stage18 lexical extraction → Stage19 sense induction → Stage20 contextual lexical OPUS → Stage21 CEFR-J → Stage22 CMUdict → Stage23 sense examples → Stage24 immutable cards/set → Stage25 JSON export`

The Workbench `rocketdict-product-run` drives the same public maintained API from source through Stage25 and resumes from immutable identities.

### Stage10 source-boundary policy

Product/default Stage10 is `structural-entity-term-discourse-pronoun-v1`, schema `rocketdict-product-stage10/1`. Research V2 remains explicit only. Broad V2 resegmentation is not a Product/default replacement: full-corpus mechanical gains were accompanied by semantic regressions on newly merged clean contexts.

### Stage12 translation and research layers

Stage12 uses `rocketdict-stage12-protected-split/8`. The real OPUS primary translation is immutable and cache-reusable. Rescue mechanisms are separate default-OFF selection layers and never rewrite primary output in place.

Public Stage12 continues to expose only the maintained public research surfaces already documented by the API. Additional evidence-backed wrappers remain internal/default OFF/not public-wired, including TC-big delimiter/reference/numeric classes, Stage10 boundary-pair rescue, orphan-closing-parenthesis rescue, and the bounded question-mark whole-context rescue.

`rocketdict-stage12-question-mark-whole-context-rescue/1` addresses a source-defined split-question defect without changing the general planner. It requires a complete Stage10 context represented by multiple current split rows, one source terminal question mark, premature extra target question debt, no unrelated hard/research debt, and `<=160` NLP tokens. Only unmodified OPUS rank0 is considered. Strict mechanical/research checks, Gutenberg emphasis preservation and conservative content-volume checks are mandatory; otherwise all base rows are copied unchanged.

No rescue path may perform source rewriting, target surgery, placeholders, post-translation literal injection, corpus-specific target patches, automatic n-best cherry-picking or evaluator weakening.

## Current full-Opticks evidence

Large-corpus acceptance uses the complete pinned Project Gutenberg *Opticks* source: normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` source characters.

Persisted progression now reaches:

- run `16`: **20 numeric / 18 punctuation / 0 length**, 37 unique;
- run `17`: **20/17/0**, 36 unique;
- run `18`: **20/16/0**, 35 unique;
- run `19`: **20/15/0**, 34 unique.

Run `19` is the current best persisted **research** residual basis. It composes directly over run18 with one accepted bounded question-context OPUS rank0 replacement. Workflow `34676310994`, artifact `10292442391`, artifact ZIP SHA-256 `51e00030d19799157d83db8a9dbc9093851da9be897619e465699b2cde72ef91`, final output SHA-256 `48096e0c1085c0598bc8abf212a2b2ba9a1109bb232fa2487c0472f35c06a1d9`, final SQLite SHA-256 `8519ea592b0bd948b68980ed19b710f05f20f9e0a60f0cb6c3e1a7763d5a8f76`, audit evidence SHA-256 `ba6b24c0b4f628d908b5310aaf05268de2323033d7bbb629d081d755ddb8bf5f`.

The wrapper attempts question contexts `2462` (71 NLP tokens) and `2726` (157). `2462` is accepted as raw OPUS rank0; `2726` is rejected because emphasis preservation fails. The persisted run keeps 3341 other run18 rows target-exact, reconstructs the complete source byte-exactly, and passes SQLite/FK integrity.

### Bounded parenthesis research

Run19 read-only DOE `34676468786` tests contexts `668`, `1393`, `1977`, `2969` with OPUS and TC-big n-best. Artifact `10292347874`, ZIP SHA-256 `85014707fc29663cbc75075e3660c1f053921b0b1caa6a575584d8c8736e4274`, evidence SHA `77027658bc87890d7d861f944bd99a7ba3f926aa365973f432410e3986352c7f`.

Mechanical counterfactuals alone are misleading: TC-big rank0 would reduce punctuation to 12 but loses source-owned content in at least contexts `1393` and `1977`; OPUS rank0 is mechanically admissible only on `1393`; OPUS `668` still loses one of two parenthetical clauses; `2969` is inadmissible. No generic parenthesis whole-context rescue is authorized. Higher-beam recovery is research evidence only and is not eligible for automatic selection.

These persisted improvements do **not** change Product defaults. Final approved heavy evidence still requires zero unresolved hard failures and complete semantic acceptance.

## External production assets

Processing is offline once assets are provisioned. The accepted OPUS EN→RU archive is pinned to SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`. Production NLP uses the pinned accepted spaCy model; Stage21 uses CEFR-J evidence and Stage22 exact CMUdict entries.

TC-big remains optional and separately provisioned. It is an independent comparator/narrow rescue model, not a generic fallback.

## Verification and release boundary

The maintained Stage8→25 path and unified `rocketdict-product-run` are continuously checked with real pinned NLP/OPUS/CEFR-J runtime. Optional research wrappers must not alter the default path while disabled.

A narrow rescue is never promoted merely because one corpus improves. Required evidence includes source-defined triggering, exact boundary geometry, unmodified deterministic raw candidates, semantic review, persisted full-corpus regression, byte-exact untouched/source checks, SQLite integrity, exact model/asset identity and release-size/performance assessment.

After heavy translation gates reach zero unresolved failures, the next release frontier is complete downstream learner/export validation and Windows distribution/clean-install testing.
