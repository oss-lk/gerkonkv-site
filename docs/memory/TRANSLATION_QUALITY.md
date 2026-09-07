# RocketDict maintained translation quality — L2

This file stores durable conclusions from the **maintained Product** translation-quality work. It is not a changelog and it does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Raw experiment JSON/SQLite, CI logs, source, tests and Git history remain L3 and outrank this summary if they disagree.

## Current maintained contracts

- Production MT baseline: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian, acceptance compute type `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/3` in `rocketdict-product-core/src/rocketdict/translation_stage.py`.
- Stage15 numeric/symbol evaluator: `rocketdict-maintained-numeric-integrity/3` in `rocketdict-product-core/src/rocketdict/numeric_integrity.py`.
- Research output-artifact diagnostic: `rocketdict-maintained-output-artifact/2`; target-only HTML entities/replacement characters and target-introduced quote characters are rejected by the research selector. These research diagnostics are not additional Product release gates by themselves.
- Planner/evaluator semantics that can change output or cache interpretation are versioned. Do not silently reuse results produced under an older contract as equivalent current evidence.

## Proven Product baseline

The maintained direct real Stage8→25 path and the unified user-facing `rocketdict-product-run` source→Stage25 path, including replay of the same immutable Stage25 export, are green. Product Core workflow run `34159939929` is a verified example after the Stage12 `/3` and current diagnostics work: dependency-light and real-runtime jobs both passed.

This retired the old L1 blocker that claimed unified Product orchestration was still red.

## Frozen maintained R1 challenge

The current deterministic R1 challenge is a **diagnostic stress set**, not a representative continuous corpus:

- 5,143 words;
- immutable selection SHA-256 `665f1ee5ad1778ac8ab1b1b2ae0da7e17a05a0321b8a25cb6d47d74294f4af32`;
- Stage12 planner `/3` produces 155 translation units;
- empty outputs = 0;
- backend errors = 0;
- current hard-gate failures = 7 events: numeric/symbol 5, punctuation 1, length-ratio 1.

The frozen selection intentionally joins distant excerpts. Consequently some apparent structure failures are **selection-boundary artifacts**. In particular, section labels such as `1.E.5.` / `1.F.4.` can be separated from the prose they introduce, and an excerpt can begin/end inside Gutenberg `_..._` emphasis. Do not promote a Product policy solely because it repairs such a synthetic join. Validate the class against contiguous source evidence first.

Primary L3 evidence: `.github/workflows/rocketdict-maintained-r1-challenge.yml`, `rocketdict-workbench/tests/real_translation_challenge.py`, and the `rocketdict-maintained-r1-challenge` workflow artifacts.

## Durable Stage12 findings

### Protected planner `/3` is a positive production change

Stage12 must not cut inside balanced source-owned `[]`, `()`, `{}` or valid Gutenberg emphasis. It also must not let malformed/excerpt-boundary `_` parity coalesce unrelated sentences or paragraphs. The `/3` parser classifies emphasis from local source context and drops an unmatched opener at a blank paragraph boundary rather than inventing a closer.

This fixed a real planner defect and passed Product Core unit/regression tests plus the real direct/unified Product smoke. On frozen R1 it reduced structural/punctuation noise without creating numeric regressions.

Evidence: `rocketdict-product-core/src/rocketdict/translation_stage.py`; `test_translation_stage_planner.py`; `test_translation_stage_emphasis_regression.py`; Product Core workflow.

### Arbitrary punctuation-preferred cuts are not promoted

A full-parent-context DOE tested moving the 64-token split to preceding comma/semicolon/colon boundaries. Natural-looking `54/60/13` groups still left the central long colour/range enumeration badly compressed by OPUS. Therefore merely choosing a nearby punctuation boundary is not a sufficient general Product policy.

### Fine-grained clause/list splitting is research-only

Smaller list clauses can make the difficult numeric colour enumeration mechanically pass current integrity checks, but manual target review found weak or misleading Russian phrasing and target-introduced quotation artifacts. After output-artifact contract `/2`, some earlier apparent successes were correctly rejected. Integrity-green is necessary but not sufficient evidence of translation quality.

Do not promote broad clause splitting or a list planner without stronger semantic evidence on contiguous source.

## Durable n-best findings

Raw n-best selection is allowed as a research candidate because it chooses an existing model hypothesis; it must never append/reconstruct missing literals after MT.

Broad n-best is **not** safe as a universal fallback. Some candidates satisfy one hard invariant by deleting or materially changing useful content. Frozen R1 demonstrated this for non-numeric failures.

A narrower numeric-only audit scopes retry only when rank-0 fails numeric/symbol preservation while punctuation, length, delimiter, critical-token and output-artifact checks otherwise pass. Under fixed beam6/n-best6 R1 evidence this scope reduced automatically to sequences `44` and `131`, both with a strictly eligible rank1 candidate. However locality differs materially: the `2'389 → 2'38` case is almost a one-token correction (target similarity ≈0.998), while the `_Exper._ 2.` case changes noticeably more text (≈0.786). Similarity is evidence only, not a semantic-quality guarantee.

Therefore **do not enable a production numeric retry from R1 alone**. Validate prevalence, rescue rate, rank stability and candidate quality on contiguous full-corpus units first.

Primary L3 evidence: `real_translation_nbest_feasibility.py`, `real_translation_numeric_nbest_policy_feasibility.py`, maintained R1 artifacts.

## Structural-island finding

Source-owned structural islands can mechanically preserve Gutenberg/technical tokens that MT drops, but wholesale islanding is not a proven Product policy. Inline symbolic fragments can damage grammar/context when detached from prose, and several frozen-R1 section-label successes are selection artifacts. Treat explicit document structure separately from ordinary prose only when the source structure and provenance are unambiguous and contiguous-source evidence supports the behavior.

Historical `numeric-islands-v1` remains a negative branch; do not confuse structural parsing with numeric placeholder repair.

## Current heavy evidence frontier

A separate full-contiguous-Opticks numeric stress exists at:

- `rocketdict-workbench/tests/real_translation_full_opticks_numeric_stress.py`
- `.github/workflows/rocketdict-full-opticks-numeric-stress.yml`

It runs real maintained Stage8/10 on the complete pinned Opticks source, materializes current Stage12 `/3` units byte-exactly, translates every numeric-bearing planned unit with rank0, and requests beam6/n-best6 only for actual rank0 numeric failures. It does not mutate the Stage8/10 research DB and does not perform synthetic target repair.

Workflow run `34160613314` was still executing when this memory entry was first written. Its artifact/result is L3 and must be inspected before deciding whether a production numeric-retry selector is justified. Update this paragraph rather than appending history once that conclusion is known.

## Promotion rules for translation-quality changes

1. Never make a hard gate green by weakening the evaluator when the source/target evidence shows a real loss.
2. Separate evaluator defects, planner defects, source-selection artifacts and model defects before changing Product behavior.
3. Prefer source/planner fixes when the defect is created before MT; prefer raw-model candidate selection only when evidence shows the model already produced a better hypothesis.
4. No post-hoc literal injection, numeric placeholders presented as final MT, or fabricated closing structure.
5. A research candidate must preserve source identity and be replayable/config-versioned before Product promotion.
6. Mechanical integrity pass is not sufficient for semantic promotion. Inspect target quality and validate on contiguous source beyond the frozen stress set.
7. Product promotion must retain zero empty/backend failures and must not create regressions in the direct or unified real Stage8→25 gates.
