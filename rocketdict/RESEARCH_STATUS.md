# RocketDict Stage 8 — research status

This document freezes the current experimental state so work can continue without access to the original chat.

## Methodological objective

Do not optimize toward one lucky translation. Build a reproducible experimental base on a fixed corpus, preserve negative branches, and choose the production pipeline from evidence. The Research Vault is the durable materialization layer; the operational RocketDict DB remains the execution database.

Campaign structure:

1. deterministic ~5k challenge set;
2. integrity/structural DOE;
3. zero-critical-failure survivor selection;
4. ~10k stratified screening;
5. Pareto selection on quality/runtime/resource metrics;
6. full 104k+ confirmation only for survivors;
7. continue downstream dictionary pipeline and retain research comparisons.

## Real OPUS gate

GitHub Actions run `32991296384` succeeded with official OPUS EN→RU, Python 3.13, CTranslate2 4.8.1 and SentencePiece 0.2.2. This removed the old transport blocker permanently for research purposes.

The standalone gate showed that the model is real but not uniformly high quality. Example: `plane` can become `самолёт` in context where geometric `плоскость` is intended. Therefore later research must include terminology/context/glossary refinement; do not equate a successful MT runtime with sufficient final dictionary quality.

## Integrity DOE

### A — baseline

~5,051 words. Real OPUS, no preferred atomic split, no numeric islands.

Measured pre-rescore metrics:
- 208.91 s;
- 115 chunks;
- empty=0;
- backend errors=0;
- numeric failures=11 under the earlier evaluator;
- length-ratio failures=4;
- critical-symbol failures=0;
- Cyrillic rate ≈0.980;
- gate FAIL.

The old 11 numeric number must not be reused as a final scientific result because subsequent evaluator work proved some false positives.

### B — preferred split

Same ~5,051-word challenge set, atomic units split above preferred SentencePiece budget.

- 289.94 s;
- 152 chunks;
- length failures reduced 4 → 1;
- no empty/backend failures;
- gate still FAIL because numeric fidelity was not solved.

Conclusion: splitting is useful for long-unit completeness but is not sufficient for literal integrity.

### C — numeric islands

Experimental `numeric-islands-v1` placeholder protection.

- 708.59 s;
- 13 empty outputs;
- 13 backend-error units;
- 13 numeric failures;
- 13 length failures.

Conclusion: **negative result**. OPUS does not reliably preserve the tested placeholder grammars, particularly multiple markers. Keep this branch as evidence; do not revive it without new controlled evidence.

### D — split + islands

Combination branch. It does not change the conclusion that islands-v1 is unsuitable as a production mechanism in its current form. Preserve its Research Vault records; do not promote it.

### E — preferred split + `table-cells-v1`

The table-aware structural executor preserves table geometry and numeric-only cells and translates only textual cells.

Exact measured E result:
- 5,000 source words;
- 109 occurrences;
- 150 chunks;
- 109.9698 s;
- peak RSS 1,043,566,592 bytes;
- target words 3,852;
- empty=0;
- backend errors=0;
- numeric failures=5;
- critical-symbol failures=0;
- length failures=0;
- identity rate ≈0.06422;
- Cyrillic rate=0.99;
- Cyrillic alpha share≈0.98028;
- gate FAIL only because numeric failures >0.

This is a strong positive structural result: tables/long units ceased producing length failures and throughput improved substantially relative to A/B.

### F96 — current frontier

A later E-family run used a smaller preferred token budget (the label F96 refers to that refinement). Exact measured result:

- 5,000 source words;
- 109 occurrences;
- 168 chunks;
- 141.0552 s;
- peak RSS 906,489,856 bytes;
- target words 3,794;
- empty=0;
- backend errors=0;
- numeric failures=**3**;
- critical-symbol failures=0;
- length failures=0;
- identity rate=0.06422018348623854;
- Cyrillic rate=0.99;
- Cyrillic alpha share=0.9796639134149815;
- gate FAIL only because numeric mismatch count is 3.

F96 is the current measured frontier. Do **not** restart at A.

## Exact three remaining F96 numeric failures

All are evaluated with `rocketdict-numeric-integrity/3.2`.

### occurrence 15697 — structural figure reference

Source contains: `[in _Fig._ 2.]` plus spelled quantities `four`, `eight`, `three`.

Selected target preserved the spelled quantities as numeric `4`, `8`, `3` (licensed) but dropped the literal figure reference `2`.

Classification: **structural reference loss**, not ordinary measurement loss.

Important n-best result: in the saved n-best probe, all eight tested hypotheses for the relevant long first unit still missed source literal `2`. Therefore simple n-best selection cannot solve this particular unit at that segmentation/configuration.

### occurrence 16200 — short ordinary/structural numeric loss

Source: `15 Min. that of the exterior 3 Degr.`

Selected target: `15 Мин. внешней части.`

Missing literal: `3`.

Important n-best result: multiple alternate hypotheses *do* preserve both 15 and 3, e.g. rank 0 `15 Минус 3 дегр.` and rank 4 `15 Мин. внешней части 3.`. Therefore an **integrity-aware n-best selector** is a promising production/research branch for this class. It must choose among model hypotheses; it must not fabricate a number after translation.

### occurrence 17795 — extreme large-number sequence

Source includes:
`... 1000000, 1000000000000, or 1000000000000000000 times rarer ...`

Selected target transformed/lost the sequence, producing values such as `1 000 000 000` and `1 000 000 000 000`, missing 1,000,000 and 10^18 and adding an unlicensed 10^9.

Saved n-best probe: all eight tested hypotheses exhibited essentially the same failure pattern for the extreme literals. Thus ordinary n-best selection is not sufficient here.

Classification: **extreme literal/scientific-sequence fidelity failure**. Treat separately from tables and short references.

## Numeric evaluator history

Do not use old naive regex metrics.

Current contract: `rocketdict-numeric-integrity/3.2`.

It must support at least:
- fractions and mixed fractions (`22-1/2`);
- ordinal suffixes (`24th`, `1/89000th`);
- old ordinal notation (`42d` ↔ Russian ordinal form);
- grouped thousands with spaces/commas;
- decimal comma;
- spelled number licenses (`four → 4`, `sixteen → 16`, etc. where semantically licensed);
- Newton typography using apostrophe as decimal separator (`1'699`, `0'000625`, `4'27`).

Evaluator changes should normally rescore stored outputs rather than rerun expensive inference if the translation algorithm itself is unchanged. Store evaluation contract/version separately from generation contract.

## Table structural branch

A dedicated four-table probe with `table-cells-v1` achieved numeric integrity 100% on all four previously problematic tables. It preserved numeric-only cells and geometry and translated textual cells only. This is why table failures must no longer be mixed with prose literal failures.

Production code must keep structural table mode in the plan/config identity so old caches cannot be silently reused under a different structural algorithm.

## Read-only preflight contract

Stage 8 fixed diagnostic side effects:
- NLP registry has non-persisting `inspect_profile()`;
- translation registry has non-persisting `inspect_profile()`;
- execution `check_profile()` may persist evidence;
- availability/preflight paths use inspect, not check.

With real OPUS + managed runtime, repeated heavy preflight was verified byte-for-byte read-only: no new `nlp_model_checks`, no new tokenizer snapshots, no translation rows, unchanged SQLite SHA.

## Research Vault

The current Research Vault is an independent append-only SQLite. A compressed snapshot is part of this handoff payload/materialization. Key invariants:
- `PRAGMA quick_check` should be `ok`;
- FK violations = 0;
- operational DB is not mutated by export;
- all candidates retained;
- selected outputs identified separately;
- failed/pruned trials retained;
- repeated export is idempotent;
- shard merge is deterministic;
- common-unit pairwise comparisons can be generated.

## Recommended next DOE branches

### G — integrity-aware n-best selector

For each translated unit, ask CTranslate2 for multiple hypotheses and choose the highest-scoring hypothesis satisfying strict integrity constraints. Required experimental design:
- same deterministic source selection;
- same OPUS/runtime/float32;
- generation config stored exactly;
- compare beam/n-best values as explicit cells, not hidden fallback;
- quality constraints include numeric 3.2 and critical-symbol preservation;
- if no hypothesis passes, the unit remains a failure; do not synthesize target text.

Expected benefit: occurrence 16200 class.

### H — structural reference preservation

For figure/observation/section labels (`Fig. 2`, `Obs. 24`, etc.), test a structural parsing layer that treats the label as document structure rather than probabilistic prose. Preserve provenance and position. This is more principled than generic numeric placeholders.

Expected benefit: occurrence 15697 class.

### I — extreme literal sequence strategy

For occurrences like 17795, test an evidence-backed strategy separately. Possibilities to compare (not assume):
- more aggressive semantic chunking around enumerations;
- structural enumeration parsing with literal islands outside MT only if alignment/provenance can be proven;
- model-family alternative;
- constrained decoding if supported and empirically safe.

Acceptance remains zero missing/unlicensed numeric values. Do not append literals after the fact merely to satisfy the checker.

## Promotion rule

Do not move to the 10k screen until the identical 5k challenge set satisfies:
- numeric mismatches = 0;
- critical-symbol mismatches = 0;
- empty outputs = 0;
- backend errors = 0;
- length-ratio failures = 0;
- language/identity metrics not materially degraded.

After that, run 10k stratified screening on survivors, record Research Vault evidence, choose Pareto survivors, then perform the full 104k+ confirmation.
