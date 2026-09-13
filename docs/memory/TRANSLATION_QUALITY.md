# RocketDict maintained translation quality — L2

Durable quality conclusions only. `rocketdict/PRODUCT_TARGET.md` is authoritative; L3 source/tests/CI/artifacts outrank memory.

## Maintained invariants

- Pinned production OPUS EN→RU: `opus-2020-02-11`, archive SHA `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product Stage10 default is V1; Stage12 planner is `rocketdict-stage12-protected-split/8`; numeric gate is `rocketdict-maintained-numeric-integrity/6`.
- Persisted rescue output is unique unmodified raw rank0 only. Missing/duplicate/malformed rank0 fails closed. No source rewriting, target surgery/literal injection, placeholders, corpus-specific target patches, automatic n-best selection or evaluator weakening.

## Forward parent

Authenticated run41 from workflow `34695164876`, artifact `10297359600`, remains the only forward parent: `3335` rows, **18 numeric/symbol / 16 punctuation / 0 length, 33 unique**. Output SHA `d8948e43158a126703a90e6ce1cd25725da8774e1db64410ca67e3ec7bb1a10f`; SQLite SHA `e48df8a90a3aa5e07bbc7e86c150d7b65ce450e7b6a0ec0d2e34a0caf9846e2e`; replay evidence `e7504ef18ead81e9c437ab8236b787a7d59082c272ef102fcc9bae6e281deac1`; independent census `b384ae0936f2ec792dd8ec6fbfcdf5da0dea1ba097df951c6049f2f2cbbb5319`.

Historical run23 is diagnostic only because automatic rank>0 selections occurred.

## Illustration source-plan evidence

Workflow `34698906048`, artifact `10299487345`, evidence SHA `0af3deb591aee8da0dd11ba7a59aeab64c65d2d2327e923ebbeb64b9b077e3ee` proved the generic source-defined geometry:

- exact `[Illustration: FIG. N.]` → OPUS raw rank0;
- exact source blank-line separator → source-owned passthrough;
- exact `_Illustration._` → TC-big raw rank0;
- exact trailing whitespace → source-owned passthrough.

The plan is created before MT, model inputs equal immutable lexical source spans, source-owned spans are copied from source, and aggregate outputs pass maintained mechanical/emphasis checks. Accepted table rendering provides the architectural precedent for preplanned structural passthrough.

Forward implementation is contract `/4` in commit `cdf58def6e557c800e325aea31cd6b8a6237037d`. It preserves the prior ordinary-suffix OPUS path, uses exact-source OPUS+TC-big rank0 for the structural class, and is default OFF. Maintained workflow `34742479388` passed dependency-light plus real-runtime verification.

## Failed promotion and new rendering constraint

Full Opticks promotion workflow `34742555215` authenticated exact run41 and pinned OPUS/TC-big assets. The wrapper fixed the two intended punctuation failures, but promotion was rejected at **18 numeric / 14 punctuation / 4 length, 35 unique**. Failure artifact `10313456776` contains the persisted SQLite through final run `56`.

Direct L3 audit isolated all four new failures to structural-only translation rows: two `\n\n` separators and two trailing single spaces. `evaluate_rescue_pair._length_passed` deliberately requires `target.strip()` even when source alphabetic count is zero, so standalone whitespace translation segments are hard failures by contract.

Durable conclusion: **logical source-plan pieces need not equal persisted hard-gate rows**. Source-owned separators/whitespace may remain explicit subspan provenance but must be rendered inside a semantic carrier row whose source/target pair is evaluated as the intended aggregate. This is a representation fix, not an evaluator exception and not post-hoc target repair.

## Closed directions

- Do not weaken length or other hard gates to admit structural-only rows.
- Seq `638` tested short-DMS whole/split exact-source rank0 geometries are exhausted.
- Seq `325` tested figure-reference boundary geometries are closed.
- Historical angle-list seq `2346` has no admissible tested raw-rank0 OPUS/TC-big candidate; prime-preserving TC-big variants corrupted a large integer.
- Inline `[G]`, large-integer canonicalization, broad generic fallback, source rewriting, target repair and automatic n-best selection remain rejected.

## Current frontier

Refactor `/4` rendering to a semantic carrier row while retaining the four-piece pre-MT source plan in provenance; test; rerun maintained CI; then rerun exact run41 promotion and independent census. Only a clean **18 / 14 / 0, 31 unique** result can replace run41 as forward parent.
