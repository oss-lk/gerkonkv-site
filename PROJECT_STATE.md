# RocketDict project state — L1

> Volatile operational memory for the **RocketDict** work in this mixed-purpose repository. Keep this file small. Replace stale state instead of appending history. Git is the detailed history.

## Active line and verified checkpoint

- Repository: `oss-lk/gerkonkv-site`.
- Active engineering branch: `chatgpt/product-core-forward`; `main` is not the current RocketDict engineering source of truth.
- Current inspected HEAD: `1f45b9eb66fe30e38eb35b5d6adc659e15f05092` (`Preserve block section identifiers in Product Stage12`).
- Maintained direct real Stage8→25 and unified user-facing `rocketdict-product-run` source→Stage25 + replay are green on bounded Stage12 execution: Product Core run `34225159869`, artifact `10055422087`.
- Latest complete actual-Product full contiguous pinned *Opticks* acceptance/audit: run `34224998708`, artifact `10056028661`, source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`. It completed full Product Stage12 plus prime and staged-n-best research successfully under planner `/7` and bounded request batching.
- Current planner `/8` block-section-ID migration was dependency-light verified by run `34236048593` and then committed by the migration runner. Because that final commit was created by `GITHUB_TOKEN`, independent normal Product Core/full-*Opticks* workflows have not yet verified `/8`.

Per `AGENTS.md`, re-check HEAD and CI before relying on this checkpoint if the branch advances.

## Main goal

Deliver one complete, locally installable RocketDict Product that turns English text/subtitles into a high-quality context-aware EN→RU learner dictionary through one resumable workflow. The immediate frontier is full-corpus translation hardening until the complete 90k+ acceptance corpus has zero unresolved hard translation failures; after that, continue through complete downstream heavy validation and the distributable Windows Product.

The mandatory requirements remain [`rocketdict/PRODUCT_TARGET.md`](rocketdict/PRODUCT_TARGET.md).

## Confirmed working

- Official pinned OPUS EN→RU `opus-2020-02-11` runs offline through CTranslate2 Marian with `float32` acceptance compute type.
- Stage12 current Product planner contract at HEAD is `rocketdict-stage12-protected-split/8`.
- Stage12 structural-label contract `rocketdict-stage12-block-structural-label-opus/1` is integrated: 108 block `_Exper._/_Obs._/_Qu._` labels are byte-exact source units, real OPUS staged beam6→12 is used only for this source-defined class, and the single inline label remains ordinary prose.
- Stage12 block section identifier contract is `rocketdict-stage12-block-section-identifier/1`: block IDs such as `1.B.` / `1.F.3.` are preserved byte-exact and never sent to MT; inline references remain ordinary prose.
- Stage12 primary real-MT execution is bounded by `rocketdict-stage12-bounded-request-batch/1`, default batch size `48`, hard maximum `128`; batching is part of cache/config/output identity and does not change planner spans/model inputs/output order.
- Stage12 ASCII-table execution remains source-structure-aware; table geometry and alpha-free numeric/symbolic cells are source-owned, while logical text groups use real OPUS.
- Stage15 maintained numeric/symbol hard gate is `rocketdict-maintained-numeric-integrity/5`; numeric prime notation is fail-closed.
- Maintained Stage20→25 downstream evidence/identities remain pinned, immutable and replayable; CEFR-J/CMUdict/sense-scoped downstream behavior is proven by real small-corpus smoke.

## Latest full-Opticks `/7` facts

Actual Product Stage12 run `34224998708` completed successfully on all `586543` source characters:

- Stage8 tokens: `129825`;
- Stage10 context sentences: `3001`;
- Stage12 planned/translated units: `3333`;
- structural-label units: `108`, structural-label numeric failures: `0`;
- ASCII-table blocks: `6`;
- numeric-bearing units: `684`;
- Product numeric hard failures at rank0: `35`;
- isolated numeric-only failures: `12`;
- beam6 rescues among isolated failures: `3`;
- staged beam12/16 leaves five isolated residual units: `744, 2296, 2381, 2750, 2898` under the `/7` plan.

Generic n-best remains research-only. Sequence IDs are plan-local; use immutable source spans/text when comparing across planner versions.

## Current active frontier

Planner `/7` full-corpus evidence exposed a separate document-structure class in Project Gutenberg license section identifiers. The immutable corpus contains block IDs such as `1.B.` and `1.F.3.`; when left inside prose, OPUS can drop or Cyrillicize them (for example `1.E.3.` → `1.Е.3.`). Current HEAD promotes a narrow block-only source-owned preservation contract and planner `/8`.

Immediate requirement: independently verify planner `/8` through ordinary Product Core real-runtime and a complete actual-Product full-*Opticks* rerun. Only after the fresh `/8` artifact may residual hard failures be reclassified and the next quality mechanism selected.

Known remaining non-structure classes from `/7` include long-unit numeric content loss, fraction/formula corruption and very large-number corruption. Do not solve them with target-side literal insertion, placeholders, broad n-best fallback, or evaluator weakening.

## Immediate continuation

1. Trigger and complete independent Product Core dependency-light + direct/unified real Stage8→25 on planner `/8`.
2. Re-run complete actual-Product pinned *Opticks* under planner `/8`; audit exact block-section-ID preservation and compute the new hard-failure/residual frontier from the artifact.
3. If `/8` works as intended, remove any one-shot block-section migration harness/workflow and keep only maintained source/tests/workflows.
4. Investigate the remaining immutable-span classes separately: long-unit content loss, fraction/formula corruption, and extreme integer corruption; promote only evidence-backed source/planner/model mechanisms.
5. Continue until full heavy translation hard gates are zero, then extend the heavy run through downstream alignment/lexical/sense/card/export acceptance and finally Windows packaging/clean-install validation.
6. Before every user-facing development result, synchronize this file plus `docs/memory/TRANSLATION_QUALITY.md` and `docs/memory/DECISIONS.md` to actual HEAD/CI per `AGENTS.md`.

## Hot paths

- `rocketdict-product-core/src/rocketdict/translation_stage.py`
- `rocketdict-product-core/src/rocketdict/structural_labels.py`
- `rocketdict-product-core/src/rocketdict/block_section_identifiers.py`
- `rocketdict-product-core/src/rocketdict/table_stage12.py`
- `rocketdict-product-core/src/rocketdict/numeric_integrity.py`
- `rocketdict-product-core/src/rocketdict/api/registry.py`
- `rocketdict-product-core/tests/test_translation_stage_*`
- `rocketdict-product-core/tests/test_block_section_identifiers.py`
- `rocketdict-workbench/tests/real_translation_full_opticks_*`
- `.github/workflows/rocketdict-product-core.yml`
- `.github/workflows/rocketdict-full-opticks-numeric-stress.yml`

## L2 routing

Start with [`docs/memory/INDEX.md`](docs/memory/INDEX.md). Translation-quality evidence lives in [`docs/memory/TRANSLATION_QUALITY.md`](docs/memory/TRANSLATION_QUALITY.md); durable architectural rules are in [`docs/memory/DECISIONS.md`](docs/memory/DECISIONS.md).

If L1/L2 conflicts with source, tests, CI, artifacts or Git history, L3 wins and memory must be repaired before the next user-facing development report.
