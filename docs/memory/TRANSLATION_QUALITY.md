# RocketDict maintained translation quality — L2

Durable translation-quality conclusions only. `rocketdict/PRODUCT_TARGET.md` is authoritative; source/tests/CI/artifacts/SQLite (L3) outrank memory.

## Maintained invariants

- Pinned production OPUS EN→RU: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product Stage10 default is V1; Stage12 planner is `rocketdict-stage12-protected-split/8`; numeric hard gate is `rocketdict-maintained-numeric-integrity/6`.
- Persisted rescue model output is unique unmodified raw rank0 only. Missing/duplicate/malformed rank0 fails closed. No source rewriting, target surgery/literal injection, placeholders, corpus-specific target patches, automatic n-best selection or evaluator weakening.

## Current full-Opticks promotion parent

**Run56 is the only forward parent.** It was composed from authenticated run41 by workflow `34743281964` and persisted in artifact `10312992185` (`sha256:81be4996bce174e7aaa21c41da8ef531a9b6d0f59346c26b7fb6328861ab451a`).

- `3335` translation segments;
- **18 numeric/symbol / 14 punctuation / 0 length, 31 unique**;
- output SHA `2971fb099674aa81c14e0b75590c5fbcb943d1ea3477efb0ceedbd81bd69fbc5`;
- final-text SHA `705dac5de010af8d5c08a3da49b7ec5d568ddf144e435f4617b5cbe2e604f73d`;
- SQLite SHA `cb4568584e70be0fb4d011cd9de212ae01edd046dec8c5ec104ee3bb0e91dc56`;
- promotion evidence SHA `d6dfe0771e0a0c41506494b860c1733981adace656afb6a0130c291cfdfb57ff`;
- independent census SHA `8c79ba9f8bd17790b41bff9e10f8b89ee5706733780ddc6dcd8bebe93c77857e`.

Independent persisted-artifact workflow `34743557365` verified the saved artifact, SQLite integrity/FKs, evidence hashes, source coverage, unchanged unrelated spans, exact model-input/rank0 provenance and safety flags. Maintained Product Core workflow `34743880129` also completed successfully after the current research harness additions.

## Illustration source-plan / semantic-carrier contract

The mechanically proven source geometry is four logical pieces planned before MT:

- exact `[Illustration: FIG. N.]` → OPUS rank0;
- exact source blank-line separator → source-owned passthrough;
- exact `_Illustration._` → TC-big rank0;
- exact trailing whitespace → source-owned passthrough.

Forward illustration rescue `/5` (substantive commit `c99749b9214db572af72fb30baf8a7e98816b972`) preserves the four-piece plan and exact component provenance but renders it through one semantic carrier row over the original source span. Carrier target is exactly `label_rank0 + separator_source + suffix_rank0 + trailing_source`. The maintained hard gates remain unchanged.

## Run56 punctuation screening

Read-only exact-row screening workflow `34743811304` evaluated every one of the 14 run56 punctuation failures with exact row source text and unique raw rank0 from pinned OPUS and pinned TC-big. Evidence SHA: `e001300774ddeb27d7f82f1c4e563f013d1677490384dfb913ceb0fb0de9a13a`.

- OPUS raw rank0 passed the maintained mechanical/emphasis/punctuation screening for `0` rows.
- TC-big raw rank0 passed for `5` rows: sequences `741`, `1497`, `2108`, `2589`, `3009`.
- Four passing rows are parenthesis-loss/mismatch defects; seq `3009` is a question-mark defect.
- The screening DB remained unchanged and prohibited-transform flags stayed false.

**Durable interpretation:** TC-big has real rank0 capability on a bounded subset of the residual punctuation cohort, but exact-row success is only a candidate-discovery signal. It does not justify broad model fallback. A production path still requires a generic source-defined trigger, exact immutable model input, independent context/row-geometry evidence, raw rank0-only selection and fail-closed integration.

A first whole-context parenthetical DOE (`34743895800`) is invalid evidence: the harness stopped before model comparison on `parenthetical DOE member coverage drift at 53`. Treat this strictly as an orchestration/selection bug. It neither proves nor disproves the parenthetical model geometry.

## Durable closed directions

- Seq638 tested short-DMS exact-source/rank0 whole/split geometries are exhausted.
- Seq325 tested figure-reference lead/boundary-pair geometries are closed.
- Historical seq2346 angle-list DOE has no admissible tested raw-rank0 geometry; prime-preserving TC-big variants corrupted a large integer.
- Inline `[G]`, large-integer canonicalization, broad generic whole-context/model fallback, source rewriting, target repair and automatic n-best selection remain rejected under tested formulations.
- Historical prime multi-context DOE `34687752297` found only `english_miles_boundary` OPUS rank0 admissible; that family is already covered by the emphasized-modifier wrapper and is absent from run56 residuals.

## Current frontier

Run56 leaves 31 unique hard failures: 18 numeric/symbol and 14 punctuation with one overlapping row, and zero length failures. Repair the parenthetical context DOE membership logic, rerun it against exact run56, and only then decide whether the four parenthetical exact-row TC-big hits form a safe generic rescue class. If not, record the negative result and move to the next source-defined residual family.
