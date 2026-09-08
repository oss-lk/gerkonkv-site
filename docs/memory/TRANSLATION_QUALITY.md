# RocketDict maintained translation quality — L2

This file stores durable conclusions from the **maintained Product** translation-quality work. It is not a changelog and it does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Raw experiment JSON/SQLite, CI logs, source, tests and Git history remain L3 and outrank this summary if they disagree.

## Current maintained contracts

- Production MT baseline: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian, acceptance compute type `float32`.
- Stage12 current Product planner at HEAD: `rocketdict-stage12-protected-split/8` in `rocketdict-product-core/src/rocketdict/translation_stage.py`.
- Stage12 structural-label contract: `rocketdict-stage12-block-structural-label-opus/1`; 108 block `_Exper._/_Obs._/_Qu._` labels are byte-exact source units, while the single supported inline occurrence remains ordinary prose. Label model input expands only the documented abbreviation; target is selected from raw real-OPUS hypotheses with narrow semantic/numeric acceptance.
- Stage12 block section identifier contract: `rocketdict-stage12-block-section-identifier/1`; block IDs such as `1.B.` / `1.F.3.` are source-owned structure preserved byte-exact and excluded from MT; inline references remain ordinary prose.
- Stage12 ASCII-table execution remains explicit source-side parsing/logical grouping; source-owned geometry and alpha-free numeric/symbolic cells are preserved while logical text groups use real OPUS.
- Stage12 primary real-MT execution contract: `rocketdict-stage12-bounded-request-batch/1`, default `48`, hard maximum `128`. Batching is order-preserving and part of cache/config/output provenance; it does not alter planner units or model inputs.
- Stage15 numeric/symbol evaluator: `rocketdict-maintained-numeric-integrity/5`; numeric prime/unit notation is part of the Product hard gate.
- Research diagnostics remain measurement surfaces unless explicitly promoted. Broad raw n-best selection is not Product fallback policy.
- Planner/evaluator/execution semantics that affect output, hard-gate meaning or cache interpretation are versioned.

## Proven Product baseline

The maintained direct real Stage8→25 path and unified user-facing `rocketdict-product-run` source→Stage25 path, including replay of the same immutable Stage25 export, are green with bounded Stage12 execution. Product Core run `34225159869`, artifact `10055422087`, proves planner `/7`, structural-label `/1`, request-batch `/1` with size `48`, numeric `/5`, and the downstream real Product path.

The old orchestration blocker is retired. Current work is full-corpus translation-quality hardening, not recovery of the unified runner.

## Full contiguous Opticks: first successful actual Product Stage12 under `/7`

Primary acceptance-quality source: complete pinned Project Gutenberg *Opticks*, SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`.

Run `34224998708`, artifact `10056028661`, is the first successful **actual maintained Product Stage12** over the complete corpus after structural-label/table boundary fixes and bounded execution. It completed Product Stage12, prime audit and generic staged-n-best research.

Facts:

- source characters: `586543`;
- Stage8 tokens: `129825`;
- Stage10 context sentences: `3001`;
- Stage12 planner `/7` units: `3333`, byte-exact full-source coverage;
- structural-label units: `108`; label numeric failures: `0`;
- structural-label model requests: `111`; three label units needed staged escalation;
- ASCII-table blocks: `6`; logical table groups: `116`;
- numeric-bearing units: `684`;
- Product rank0 numeric hard failures: `35`;
- isolated numeric-only failures: `12` (`588, 744, 1575, 1585, 1767, 2296, 2363, 2381, 2443, 2750, 2898, 3280` under this plan);
- beam6 raw ordinary-unit research rescues three isolated cases (`1767, 2363, 3280`);
- staged beam12/16 research leaves five isolated residuals (`744, 2296, 2381, 2750, 2898`).

Sequence IDs are planner-version-local. Compare future runs by immutable source span/text and failure class, not by assuming the same sequence number survives planner changes.

## Bounded Stage12 execution is a quality-neutral reliability contract

Before bounded execution, the first full-corpus Product Stage12 attempts passed planning but two hosted runners terminated with `exit 143` while all ~3.3k primary OPUS requests were submitted as one CTranslate2 batch. This was an execution scalability defect, not a translation-quality defect.

`rocketdict-stage12-bounded-request-batch/1` splits only backend requests into ordered batches. It preserves source units, model inputs, generation settings, hypothesis order and target assembly. Migration regression evidence passed focused tests plus complete dependency-light Product/Workbench suites, and Product Core run `34225159869` remained fully green. Full *Opticks* run `34224998708` then completed the previously failing Stage12 step successfully.

Do not conflate batch boundaries with planner/source boundaries, and do not change batching in ways that silently alter translation semantics.

## Prime notation remains a Product hard-gate invariant

Full-corpus prime stress under planner `/7` still finds 17 prime-bearing units / 38 source prime events; rank0 OPUS corrupts prime semantics in 11 units. Numeric `/5` catches all of these: `prime_only_failure_count = 0` and no Product numeric failure incorrectly passes the prime diagnostic.

Therefore numeric `/5` remains required. Do not collapse apostrophe decimals and prime/unit notation or weaken matching to recover old pass counts.

## Structural Gutenberg labels are now a closed Product planner/model class

Earlier planner `/4` fragmented 48/109 supported labels. Research proved that isolated literal source-side canonicalization (`Experiment`, `Observation`, `Query`) gives semantically/numerically acceptable raw OPUS candidates for 106/109 labels at beam6 and 109/109 after beam12; only `Observation 1.` needed beam12.

Planner `/7` promoted the narrow mechanism:

- 108 true block labels become byte-exact standalone units;
- the single inline `_Exper._ 10.` occurrence stays ordinary prose;
- no target-side literal insertion or placeholder repair is allowed;
- staged n-best is permitted only for this source-defined label class;
- full-*Opticks* `/7` evidence reports 108 label units and zero label numeric failures.

This success does **not** license generic n-best fallback.

## Block Gutenberg license section identifiers are a separate source-structure class

The `/7` artifact exposed recurring loss/corruption of Gutenberg license identifiers such as `1.B.`, `1.E.3.`, `1.F.2.` when they appear as block headings inside ordinary prose units. Examples include complete omission and Latin-to-Cyrillic identifier corruption (`1.E.3.` → `1.Е.3.`). Inline references such as `paragraph 1.F.3` are linguistic prose and must remain on the ordinary MT path.

Corpus inventory found 26 narrow `digit.letter.[digit.]` identifier occurrences, 21 of them block-level. Under planner `/7`, only 12/21 block IDs were preserved exactly; 9 were lost/corrupted. That justified the narrow maintained contract `rocketdict-stage12-block-section-identifier/1` and planner `/8`: block IDs are byte-exact source-owned document structure and are not sent to OPUS; inline references remain ordinary prose.

Planner `/8` migration run `34236048593` passed focused block-section/Stage12 regressions and the complete dependency-light Product/Workbench suites before committing `1f45b9eb66fe30e38eb35b5d6adc659e15f05092`. Independent normal real-runtime and full-*Opticks* acceptance for `/8` are still required before declaring the class closed.

## Generic n-best remains non-Product

Even after structural classes are removed, broad high-beam selection is not a universal solution. Prior experiments found hypotheses that pass narrow numeric checks while degrading semantics or unit meaning. The `/7` generic research leaves five isolated residuals after beam6→12→16.

Raw n-best is allowed for research and for a narrowly source-defined class only when independent semantics and fail-closed selection exist. Ordinary translation units remain rank0 Product policy until a stronger evidence-backed mechanism is promoted.

## Current non-structure residual classes

After removing known document-structure classes, remaining hard failures include separate mechanisms:

- long-unit content loss including missing numeric literals;
- fraction/formula corruption, including scientific/mathematical notation;
- very large integer corruption.

These classes must remain separate research branches. Do not use target-side literal injection, placeholders, corpus-specific target patches, or evaluator weakening.

## Promotion rules for translation-quality changes

1. Never make a hard gate green by weakening an evaluator when evidence shows real source/target loss.
2. Separate evaluator, planner, source-selection, document-structure, execution-resource and model defects before changing Product behavior.
3. Prefer source/planner fixes when the defect is created before MT; use raw-model candidate selection only when evidence proves a semantically valid candidate already exists.
4. Source-owned structural bytes may be preserved pre-MT when exhaustive evidence shows they are document structure rather than linguistic content; inline linguistic references must not be captured by such rules.
5. No post-hoc literal injection, placeholders presented as final MT, fabricated closing structure or corpus-specific target patch lists.
6. A promoted mechanism must preserve source identity, be versioned/replayable and have contiguous-corpus evidence.
7. Mechanical integrity pass is necessary but not sufficient; inspect target semantics.
8. Product promotion must retain zero empty/backend failures and must not regress direct/unified real Stage8→25.
9. Narrow n-best escalation requires a source-defined class and explicit semantic selector; broad fallback remains rejected.
