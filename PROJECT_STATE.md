# RocketDict project state — L1

> Volatile operational memory for the **RocketDict** work in this mixed-purpose repository. Keep this file small. Replace stale state instead of appending history. Git is the detailed history.

## Active line and verified checkpoint

- Repository: `oss-lk/gerkonkv-site`.
- Active engineering branch: `chatgpt/product-core-forward`; `main` is not the current RocketDict engineering source of truth.
- Current inspected HEAD: `112311961fb258351525cdd385c9767abddd4892` (`Test maintained structural-label contract`).
- Maintained direct real Stage8→25 and unified user-facing `rocketdict-product-run` source→Stage25 + replay are green. Product Core run `34207018066` passed dependency-light and real-runtime jobs.
- Latest complete full contiguous pinned *Opticks* numeric/prime evidence: run `34205049701`, artifact `10047696652`, source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`.
- Latest structural-label research: run `34210312015`, artifact `10049542652`; staged escalation run `34209680326`, artifact `10049272284`.

Per `AGENTS.md`, re-check HEAD and CI before relying on this checkpoint if the branch advances.

## Main goal

Deliver one complete, locally installable RocketDict Product that turns English text/subtitles into a high-quality context-aware EN→RU learner dictionary through one resumable workflow. The immediate quality frontier is Stage12 structural-label planning/execution on the full public-domain acceptance corpus; after full-corpus acceptance quality is stable, continue to the distributable Windows Product.

The mandatory requirements remain [`rocketdict/PRODUCT_TARGET.md`](rocketdict/PRODUCT_TARGET.md).

## Confirmed working

- Official pinned OPUS EN→RU `opus-2020-02-11` runs offline through CTranslate2 Marian with `float32` acceptance compute type.
- Stage12 current Product planner contract is `rocketdict-stage12-protected-split/4`, including protected spans and source-side ASCII-table handling.
- Stage15 maintained numeric/symbol hard gate is `rocketdict-maintained-numeric-integrity/5`; numeric prime notation is fail-closed. Full *Opticks* evidence showed 17 prime-bearing units and 11 rank0 prime corruptions, seven of which old `/4` had falsely passed.
- Full *Opticks* `/5` baseline has 671 numeric-bearing units and 49 rank0 numeric failures. Table numeric failures remain zero. Staged generic n-best leaves 10 residuals; broad n-best is not Product policy.
- Maintained Stage20→25 downstream evidence/identities remain pinned, immutable and replayable; CEFR-J/CMUdict/sense-scoped downstream behavior is proven by real smoke.

## Current blocker / active research result

Structural Gutenberg labels `_Exper._ N.`, `_Obs._ N.`, `_Qu._ N.` are a distinct source/planner defect, not a generic n-best problem.

- Complete *Opticks* inventory: 109 supported labels.
- Raw real OPUS with source-side literal abbreviation expansion (`Experiment`, `Observation`, `Query`) has a numerically and semantically acceptable label candidate for **109/109** events using staged beam6→12; only `Observation 1.` needs beam12 (rank5).
- Current Stage12 `/4` planning is structurally wrong for this class: only 61/109 labels are wholly contained in one planned unit; **48/109 cross Stage12 unit boundaries** (44 span two units, 4 span three). Of contained labels, 41 are suffix labels after prose, 19 are already isolated, and one is intentionally inline.
- Exactly one supported label is inline (`(_Exper._ 10. _Part_ 2.)`); the other 108 are block structural labels. A Product fix must isolate only the 108 block labels and leave the inline occurrence on the ordinary path.
- Maintained source-only contract `rocketdict-stage12-block-structural-label-opus/1` and unit tests exist, but it is not yet wired into Product Stage12.

Do not solve this by target-side literal insertion, placeholders, broad n-best fallback, or corpus-specific target patches.

## Immediate continuation

1. Promote Stage12 planner to a versioned `/5` that makes supported block structural-label spans byte-exact atomic standalone units while preserving complete immutable-source coverage and the single inline case.
2. Wire `rocketdict-stage12-block-structural-label-opus/1` into real Stage12 execution: canonical source-side model input only; staged beam6→12 only for those label units; accept raw OPUS candidate only when strict semantic form and numeric `/5` pass; fail closed otherwise.
3. Add planner/execution/registry regressions; run dependency-light + direct/unified real Stage8→25.
4. Re-run full contiguous *Opticks* numeric/prime/n-best evidence under planner `/5` and audit the new residual frontier before further Product changes.
5. Remove one-shot migration harness files from this active branch once no longer needed; previous cleanup was not verified against this branch.
6. Before every user-facing development result, synchronize this file plus `docs/memory/TRANSLATION_QUALITY.md` and `docs/memory/DECISIONS.md` to actual HEAD/CI per `AGENTS.md`.

## Hot paths

- `rocketdict-product-core/src/rocketdict/translation_stage.py`
- `rocketdict-product-core/src/rocketdict/structural_labels.py`
- `rocketdict-product-core/src/rocketdict/numeric_integrity.py`
- `rocketdict-product-core/src/rocketdict/api/registry.py`
- `rocketdict-product-core/tests/test_translation_stage_planner.py`
- `rocketdict-product-core/tests/test_translation_stage_emphasis_regression.py`
- `rocketdict-product-core/tests/test_structural_labels.py`
- `rocketdict-workbench/tests/real_translation_full_opticks_*`
- `.github/workflows/rocketdict-product-core.yml`
- `.github/workflows/rocketdict-full-opticks-numeric-stress.yml`
- `.github/workflows/rocketdict-structural-label-canonicalization.yml`

## L2 routing

Start with [`docs/memory/INDEX.md`](docs/memory/INDEX.md). Translation-quality evidence lives in [`docs/memory/TRANSLATION_QUALITY.md`](docs/memory/TRANSLATION_QUALITY.md); durable architectural rules are in [`docs/memory/DECISIONS.md`](docs/memory/DECISIONS.md).

If L1/L2 conflicts with source, tests, CI, artifacts or Git history, L3 wins and memory must be repaired before the next user-facing development report.
