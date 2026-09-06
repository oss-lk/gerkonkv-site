# RocketDict project state — L1

> Volatile operational memory for the **RocketDict** work in this mixed-purpose repository. Keep this file small. Replace stale state instead of appending history. Git is the detailed history.

## Active line and verified checkpoint

- Repository: `oss-lk/gerkonkv-site`.
- Active development branch at the last audit: `chatgpt/product-core-forward` (`main` is older and is not the current engineering source of truth).
- Last inspected engineering checkpoint: `4c9417158a0b81bffda217966b88e5111ad3e57e` — `Run unified product smoke unbuffered`.
- Latest audited Product Core workflow at that checkpoint: run `34035734816`; dependency-light job passed, real-runtime job `101493384085` failed only after the direct maintained-core real smoke had passed.
- Evidence artifact `9990130261` proves the direct maintained-core real source→Stage25 path at this checkpoint, including a real Stage25 export.

A memory/documentation-only commit may be newer than the engineering checkpoint above. Per `AGENTS.md`, inspect the diff from this checkpoint to current HEAD before assuming anything about code or tests.

## Main goal

Deliver one complete, locally installable RocketDict Product that turns English text/subtitles into a high-quality context-aware EN→RU learner dictionary through one resumable workflow. The immediate goal is to make the unified user-facing `rocketdict-product-run` real source→Stage25 gate green **without weakening** the Product contract. After that: full 90k+ public-domain acceptance/research run, then Windows distribution.

The mandatory Product requirements remain [`rocketdict/PRODUCT_TARGET.md`](rocketdict/PRODUCT_TARGET.md). This memory layer changes context loading, not requirements.

## Confirmed working at the checkpoint

- Maintained Product Core is `1.0.0.dev1`; the direct real runtime path reaches Stage25.
- Official OPUS EN→RU `opus-2020-02-11` is hash-pinned and runs as real offline MT with `float32` acceptance compute type.
- Pinned CEFR-J and CMUdict evidence are part of the maintained downstream path; generated pronunciation fallback is not accepted as Product evidence.
- Maintained Stage20→25 implementation exists in `rocketdict-product-core`, with immutable/replayable downstream identities.
- Workbench routes downstream Product execution through `maintained_product_pipeline.py`; unit/dependency-light tests passed in the audited workflow.
- The direct real smoke produced lexical senses, real Cyrillic translations, CEFR evidence, exact pronunciation evidence, sense-scoped examples, immutable cards/set, and JSON export.

## Current blocker

The unified **user-facing** real `rocketdict-product-run` smoke is still red in the latest audited workflow even though the direct maintained-core Stage8→25 smoke immediately before it passes. Before changing orchestration, inspect the latest failing job/log/evidence. Do **not** reuse an older root-cause hypothesis merely because it appeared in a previous run.

Do not make this gate green by bypassing preflight, accepting fake/identity MT, weakening quality gates, inventing CEFR/pronunciation evidence, truncating source, or breaking replayability.

## Hot areas

- `rocketdict-workbench/src/rocketdict_workbench/product_run_cli.py`
- `rocketdict-workbench/src/rocketdict_workbench/product_run_state.py`
- `rocketdict-workbench/src/rocketdict_workbench/maintained_product_pipeline.py`
- `rocketdict-workbench/src/rocketdict_workbench/product_preflight.py`
- `rocketdict-workbench/src/rocketdict_workbench/product_profile.py`
- `rocketdict-workbench/src/rocketdict_workbench/core_compatibility.py`
- `rocketdict-workbench/tests/real_product_run_smoke.py`
- `rocketdict-workbench/tests/test_product_run_cli.py`
- `.github/workflows/rocketdict-product-core.yml`

## Highest-value continuation

1. Read the current HEAD diff after the checkpoint and the newest unified-smoke failure evidence.
2. Reproduce/locate the orchestration defect with the narrowest relevant test; add a regression before or with the fix.
3. Re-run the full Product Core workflow until the unified real source→Stage25 path and replay are green.
4. Only then move to the full 90k+ public-domain acceptance/research matrix and quality audit.
5. After acceptance, build/test the installable Windows Product artifact.

## L2 routing

Start with [`docs/memory/INDEX.md`](docs/memory/INDEX.md). Durable decisions are in [`docs/memory/DECISIONS.md`](docs/memory/DECISIONS.md).

If L1/L2 conflicts with source, tests, CI, artifacts, or Git history, L3 wins and this file must be repaired before the end of the iteration.
