# RocketDict maintained translation quality — L2

This file stores durable conclusions from the **maintained Product** translation-quality work. It is not a changelog and it does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Raw experiment JSON/SQLite, CI logs, source, tests and Git history remain L3 and outrank this summary if they disagree.

## Current maintained contracts

- Production MT baseline: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian, acceptance compute type `float32`.
- Stage12 maintained Product planner: `rocketdict-stage12-protected-split/8`.
- Structural-label contract: `rocketdict-stage12-block-structural-label-opus/1`; 108 block `_Exper._/_Obs._/_Qu._` labels are byte-exact source units, while the single supported inline occurrence remains ordinary prose. Label model input expands only the documented abbreviation; target is selected from raw real-OPUS hypotheses with narrow semantic/numeric acceptance.
- Block section identifier contract: `rocketdict-stage12-block-section-identifier/1`; block IDs such as `1.B.` / `1.F.3.` are source-owned structure preserved byte-exact and excluded from MT; inline references remain ordinary prose.
- ASCII-table execution remains explicit source-side parsing/logical grouping; source-owned geometry and alpha-free numeric/symbolic cells are preserved while logical text groups use real OPUS.
- Stage12 real-MT backend execution: `rocketdict-stage12-bounded-request-batch/1`, default batch `48`, hard maximum `128`; batching is order-preserving and part of cache/config/output provenance without changing planner units/model inputs.
- Stage15 hard evaluator: `rocketdict-maintained-numeric-integrity/5`; numeric prime/unit notation is fail-closed.
- Research diagnostics remain measurement surfaces unless explicitly promoted. Broad raw n-best selection is not Product fallback policy.
- Planner/evaluator/execution semantics that affect output, hard-gate meaning or cache interpretation are versioned.

## Proven Product baseline

The maintained direct real Stage8→25 path and unified user-facing `rocketdict-product-run` source→Stage25 path, including replay of the immutable Stage25 export, remain green under planner `/8`. The latest independent verification after the current research-only additions is Product Core run `34250903497`, artifact `10065987500`, with both dependency-light and real-runtime jobs green.

The old orchestration blocker is retired. Current work is full-corpus translation-quality hardening.

## Full contiguous Opticks planner `/8` acceptance baseline

Primary acceptance source: complete pinned Project Gutenberg *Opticks*, SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`.

Run `34244876537`, artifact `10064356708`, digest `sha256:7c77092dc86516983a7917931e9b000e6c2774595562e8854623a9faff4979b4`, completed **actual maintained Product Stage12** plus block-section, prime and generic staged-n-best audits on all `586543` source characters.

Facts:

- Stage12 planner `/8` units: `3347`, byte-exact full-source coverage;
- numeric-bearing units: `688`;
- structural-label numeric-bearing units: `108`, structural-label numeric failures `0`;
- table numeric-bearing units: `6`, table rank0 numeric failures `0`;
- Product rank0 numeric hard failures: `27`;
- isolated numeric-only failures: `11`;
- generic beam6 strict rescues across the research inventory: `6`; isolated beam6 rescues: `2`;
- staged beam12/16 generic research leaves five isolated residuals at planner-local sequences `744, 2296, 2381, 2750, 2898`.

Sequence IDs are planner-version-local. Compare future runs by immutable source span/text and failure class.

## Block Gutenberg section identifiers are now a closed maintained class

The immutable corpus contains 26 narrow `digit.letter.[digit.]` identifier occurrences: 21 block-level and 5 inline references. Under planner `/7`, only 12/21 block IDs were preserved exactly; the rest could be omitted or Cyrillicized by MT.

Planner `/8` promotes `rocketdict-stage12-block-section-identifier/1`: only block IDs are source-owned byte-exact units excluded from MT; all inline references remain ordinary linguistic context.

The `/8` full-corpus audit reports:

- 21/21 block identifiers preserved exactly;
- 0 block identifier failures;
- 0 model requests for block identifiers;
- all 5 inline identifiers remain in ordinary MT units.

This class is therefore considered closed unless new corpus evidence contradicts the detector boundary.

## Prime notation remains a hard-gate invariant and an unresolved model/planning class

Planner `/8` prime audit still finds `17` prime-bearing units / `38` source prime events. Rank0 OPUS corrupts prime semantics in `11` units. Numeric `/5` catches all of them (`prime_only_failure_count = 0`; no Product numeric failure passes prime semantics).

The following full-corpus research branches are **negative evidence and must not be repeated unchanged**:

1. **Unicode prime canonicalization of whole model input** — `0/16` strict success, even with beam6 n-best. It substantially worsens the baseline.
2. **Unchanged whole-unit raw n-best beam6→12→16** — rescues only `4/11` baseline prime failures; seven remain unresolved. This does not justify broad n-best Product fallback.
3. **Structural prime-fragment preservation** — mechanically reaches `16/16` strict success, but manual target review shows unacceptable semantic degradation because splitting removes essential local context. Real examples include `53 deg.` rendered as `53 балла` and `hundred Feet` rendered as `сто ног`. Therefore this branch is rejected despite green mechanical gates.
4. **Whole-unit semantic hints** (`arcminutes`, `arcseconds`, historical `thirds of arc`) — rescues `0/11` baseline prime failures and leaves only one strict success out of 16 ordinary prime units.

Primary evidence: run `34249764521`, artifact `10065557329`; prior whole-unit staged n-best evidence also exists in run `34248620999`, artifact `10065076540`.

Any future prime mechanism must preserve whole-sentence semantics and cannot reuse the rejected fragment decomposition merely because it satisfies numeric `/5`.

## Large integers: grouping and multiplication-glyph preprocessing are rejected

A dedicated planner `/8` corpus inventory found 12 ordinary Stage12 units containing ≥7-digit integers; four are baseline hard failures. Research-only source-side formatting grouped long integers into thousands and, in the narrow multiplication context, changed ASCII `x` to `×` before real OPUS generation. Raw targets were evaluated against the unchanged source.

Result: **0/4 baseline hard failures were rescued**, and some previously successful units lost strict eligibility. Therefore thousands grouping / `x→×` is not Product preprocessing.

Evidence: run `34250592035`, artifact `10065848534`, `rocketdict-full-opticks-large-integer-feasibility/1`.

The unresolved large-number examples include immutable spans containing `310000000`, `490,000,000,000`, and the `10^12/10^18`-scale literals near source span `507544:507698`. Treat these as a distinct model/technical-notation class.

## Compact formula operator spacing is rejected

The complete planner `/8` corpus contains exactly one ordinary unit matching the investigated compact algebraic class: the span containing `3/8A`, `75/8A`, and `((61-1/2)/8)A` (`401232:401532`, planner-local sequence `2296`).

Research-only whole-unit model-input spacing around arithmetic operators and `A` preserved the full linguistic context and used raw OPUS output only. It did **not** rescue the unit, including staged raw n-best. Therefore operator spacing is not Product preprocessing.

Evidence: run `34250960739`, artifact `10065980547`, `rocketdict-full-opticks-formula-spacing-feasibility/1`.

## Long-unit content loss is the next planner/model investigation

Immutable span `133139:133431` contains source numeric sequence `25, 30, 40`. Product rank0 target drops the earlier clause and literal `25`, retaining only later `30/40` content; staged generic n-best does not rescue the unit. This is visibly broader semantic compression, not a numeric-token-only substitution error.

Because the source unit is relatively long and the missing number belongs to an omitted clause, the next useful research branch should test **source-derived clause/context planning alternatives** while preserving byte-exact source coverage. Any candidate must be evaluated for semantic completeness, not just numeric pass rate.

## Structural labels remain a closed narrow OPUS class

Earlier planner versions fragmented supported `_Exper._/_Obs._/_Qu._` labels. Exhaustive real-OPUS inventory proved acceptable raw candidates for 106/109 at beam6 and 109/109 after beam12, while planner `/7+` isolates the 108 true block labels and leaves the single inline occurrence ordinary.

This narrow source-defined staged-n-best exception does **not** license generic n-best fallback.

## Bounded execution remains quality-neutral infrastructure

`rocketdict-stage12-bounded-request-batch/1` was introduced after two hosted-runner `exit 143` failures from a monolithic ~3.3k-request CTranslate2 batch. It preserves planner units/model inputs/order while bounding backend requests. Full-*Opticks* actual Product Stage12 completes under the bounded contract and direct/unified real Product smoke remains green.

Do not conflate backend batch boundaries with source/planner boundaries.

## Current residual families

Do not collapse the remaining failures into one fallback:

- long-unit semantic/content loss;
- prime/unit ambiguity;
- fraction/formula corruption;
- very large integer corruption;
- non-isolated delimiter/illustration/length failures measured by other diagnostics.

Target-side literal insertion, placeholders, corpus-specific target patches, evaluator weakening, generic structural islands and broad n-best fallback remain rejected.

## Promotion rules for translation-quality changes

1. Never make a hard gate green by weakening an evaluator when evidence shows real source/target loss.
2. Separate evaluator, planner, source-selection, document-structure, execution-resource and model defects before changing Product behavior.
3. Prefer source/planner fixes when the defect is created before MT; use raw-model candidate selection only when evidence proves a semantically valid candidate already exists.
4. Source-owned structural bytes may be preserved pre-MT only when exhaustive evidence shows they are document structure rather than linguistic content; inline linguistic references must remain outside such rules.
5. No post-hoc literal injection, placeholders presented as final MT, fabricated closing structure or corpus-specific target patch lists.
6. A promoted mechanism must preserve source identity, be versioned/replayable and have contiguous-corpus evidence.
7. Mechanical integrity pass is necessary but not sufficient; inspect target semantics.
8. Product promotion must retain zero empty/backend failures and must not regress direct/unified real Stage8→25.
9. Narrow n-best escalation requires a source-defined class and explicit semantic selector; broad fallback remains rejected.
10. Record expensive negative experiments here so future iterations do not repeat them without genuinely new evidence.
