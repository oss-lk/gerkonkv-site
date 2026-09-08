# RocketDict project state — L1

> Volatile operational memory for the **RocketDict** work in this mixed-purpose repository. Keep this file small. Replace stale state instead of appending history. Git is the detailed history.

## Active line and verified checkpoint

- Repository: `oss-lk/gerkonkv-site`.
- Active engineering branch: `chatgpt/product-core-forward`; `main` is not the current RocketDict engineering source of truth.
- Current inspected engineering HEAD before this memory update: `10ee4ad45e5daf0318bba5103d850d1e8ca2d328` (`Run full Opticks formula-spacing feasibility DOE`). Changes after the planner `/8` Product commit are research-only; maintained Product contracts are unchanged.
- Latest independent maintained Product Core verification: run `34250903497`, artifact `10065987500`, fully green for dependency-light, direct real Stage8→25, unified `rocketdict-product-run` source→Stage25, and replay.
- Latest complete actual-Product full contiguous pinned *Opticks* acceptance/audit: run `34244876537`, artifact `10064356708`, digest `sha256:7c77092dc86516983a7917931e9b000e6c2774595562e8854623a9faff4979b4`, source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`. It is the maintained planner `/8` full-corpus baseline.

Per `AGENTS.md`, re-check HEAD and CI before relying on this checkpoint if the branch advances.

## Main goal

Deliver one complete, locally installable RocketDict Product that turns English text/subtitles into a high-quality context-aware EN→RU learner dictionary through one resumable workflow. The immediate frontier is full-corpus translation hardening until the complete 90k+ acceptance corpus has zero unresolved hard translation failures; after that, continue through complete downstream heavy validation and the distributable Windows Product.

The mandatory requirements remain [`rocketdict/PRODUCT_TARGET.md`](rocketdict/PRODUCT_TARGET.md).

## Confirmed working

- Official pinned OPUS EN→RU `opus-2020-02-11` runs offline through CTranslate2 Marian with `float32` acceptance compute type.
- Stage12 maintained Product planner: `rocketdict-stage12-protected-split/8`.
- Structural-label contract `rocketdict-stage12-block-structural-label-opus/1`: 108 block `_Exper._/_Obs._/_Qu._` labels are byte-exact units with narrow real-OPUS beam6→12 selection; the single inline occurrence remains ordinary prose.
- Block section identifier contract `rocketdict-stage12-block-section-identifier/1`: 21 full-*Opticks* block IDs are byte-exact source-owned structure, excluded from MT; all 5 inline identifiers remain ordinary MT context. `/8` audit reports 21/21 preserved and zero block-ID model requests.
- Stage12 real-MT backend requests use `rocketdict-stage12-bounded-request-batch/1`, default batch `48`, hard maximum `128`, with batch provenance in cache/config/output identity.
- Stage12 ASCII tables remain source-structure-aware; table geometry and alpha-free numeric/symbolic cells are source-owned, while logical text groups use real OPUS.
- Stage15 hard gate is `rocketdict-maintained-numeric-integrity/5`; numeric prime notation remains fail-closed.
- Direct and unified real Stage8→25 paths remain green and replay-safe.

## Current full-Opticks `/8` facts

Actual Product Stage12 run `34244876537` on all `586543` source characters produced:

- Stage12 units: `3347` with byte-exact source coverage;
- numeric-bearing units: `688`;
- structural-label numeric-bearing units: `108`, failures `0`;
- table numeric-bearing units: `6`, table rank0 numeric failures `0`;
- Product rank0 numeric hard failures: `27`;
- isolated numeric-only failures: `11`;
- generic beam6 strict rescues across all failures: `6`, isolated beam6 rescues: `2`;
- staged generic beam12/16 leaves five isolated residuals: planner-local sequences `744, 2296, 2381, 2750, 2898`.

Prime audit on the same artifact finds `17` prime-bearing units / `38` prime events and `11` rank0 prime failures. Numeric `/5` catches all of them; none is a false Product pass.

Sequence IDs are planner-version-local. Compare future runs by immutable source span/text and failure class.

## Recent expensive negative research — do not repeat unchanged

All of the following are research-only and **not** Product policy:

- Prime whole-unit Unicode canonicalization: `0/16` strict success. Whole-unit unchanged source beam6→12→16 rescues only `4/11` prime failures. A fragment structural split is mechanically `16/16` but semantically degrades prose in real examples (`53 deg.` → `53 балла`, `hundred Feet` → `сто ног`), so it is rejected. Prime semantic hints (`arcminutes/arcseconds/thirds of arc`) rescue `0/11` failures. Primary run `34249764521`, artifact `10065557329`.
- Large-integer source formatting (thousands grouping and narrow `x`→`×`): among 12 ordinary ≥7-digit units, four are baseline hard failures and **0/4** are rescued; some previously successful units regress. Run `34250592035`, artifact `10065848534`. Reject as Product preprocessing.
- Compact-formula operator spacing on the sole matching full-*Opticks* unit (`3/8A ... ((61-1/2)/8)A`) does not rescue the failure, including staged raw n-best. Run `34250960739`, artifact `10065980547`. Reject as Product preprocessing.

## Active frontier

The remaining failures are not one mechanism. Keep these branches separate:

1. **Long-unit content loss** — immutable span `133139:133431` loses source numeric literal `25` while retaining later `30`/`40`; broad n-best does not rescue it. This is the next high-value planner/model investigation because the source unit is long and the target is visibly compressed.
2. **Prime ambiguity** — 11 current rank0 failures; cheap normalization, semantic hints and generic high-beam are insufficient. Any future solution must preserve whole-sentence semantics and may not use the rejected fragment split.
3. **Fraction/formula corruption** — immutable span `401232:401532`; operator spacing failed.
4. **Very large integer corruption** — immutable spans around `417625:417917`, `483234:483458`, `507544:507698`; grouping/`×` preprocessing failed.
5. Other non-isolated delimiter/illustration/length failures remain separately measurable and must not be hidden by numeric-only work.

No target-side literal insertion, placeholders, corpus-specific target patches, broad n-best fallback, or evaluator weakening.

## Immediate continuation

1. Investigate the long-unit content-loss span with source-derived clause/context planning alternatives while preserving complete immutable source coverage; test on the complete class, not a target patch.
2. If a candidate improves the identified class, run focused regressions, direct/unified real Stage8→25 and complete full-*Opticks* before Product promotion.
3. Continue prime, formula and extreme-integer research as separate evidence branches; record rejected mechanisms in L2.
4. Continue until full heavy translation hard gates are zero, then extend the heavy run through downstream alignment/lexical/sense/card/export acceptance and Windows packaging/clean-install validation.
5. Before every user-facing development result, synchronize this file plus `docs/memory/TRANSLATION_QUALITY.md` and `docs/memory/DECISIONS.md` to actual HEAD/CI per `AGENTS.md`.

## Hot paths

- `rocketdict-product-core/src/rocketdict/translation_stage.py`
- `rocketdict-product-core/src/rocketdict/structural_labels.py`
- `rocketdict-product-core/src/rocketdict/block_section_identifiers.py`
- `rocketdict-product-core/src/rocketdict/table_stage12.py`
- `rocketdict-product-core/src/rocketdict/numeric_integrity.py`
- `rocketdict-product-core/src/rocketdict/api/registry.py`
- `rocketdict-product-core/tests/test_translation_stage_*`
- `rocketdict-workbench/tests/real_translation_full_opticks_*`
- `.github/workflows/rocketdict-product-core.yml`
- `.github/workflows/rocketdict-full-opticks-numeric-stress.yml`
- `.github/workflows/rocketdict-full-opticks-prime-feasibility.yml`

## L2 routing

Start with [`docs/memory/INDEX.md`](docs/memory/INDEX.md). Translation-quality evidence lives in [`docs/memory/TRANSLATION_QUALITY.md`](docs/memory/TRANSLATION_QUALITY.md); durable architectural rules are in [`docs/memory/DECISIONS.md`](docs/memory/DECISIONS.md).

If L1/L2 conflicts with source, tests, CI, artifacts or Git history, L3 wins and memory must be repaired before the next user-facing development report.
