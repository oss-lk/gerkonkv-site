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

The original promotion workflow ended red only because its final verifier still asserted the old four-row segment count. Replay and independent census both succeeded. A separate persisted-artifact verifier, workflow `34743557365`, succeeded and proved the result independently: verification artifact `10312893755`, digest `sha256:5746ab7e5cdb1b70412787095a214baa0089aeaa96bb26547b3360596fb07e00`, verification SHA `dcd1e4e256edfb0b2e2729e25461dd474b251d13503692c1d6316466bf50b5b7`. SQLite integrity is `ok`, FK violations are zero, source coverage is byte-exact, unrelated run41 spans are target-exact, lexical model inputs equal immutable source subspans, raw rank0 only is preserved, and all unsafe flags are false.

Previous run41 (`18 / 16 / 0, 33 unique`) remains immutable lineage evidence but is no longer the active parent. Historical run23 remains diagnostic only because automatic rank>0 selections occurred.

## Illustration source-plan / semantic-carrier contract

The mechanically proven source geometry is four logical pieces planned before MT:

- exact `[Illustration: FIG. N.]` → OPUS rank0;
- exact source blank-line separator → source-owned passthrough;
- exact `_Illustration._` → TC-big rank0;
- exact trailing whitespace → source-owned passthrough.

The `/4` renderer exposed each logical piece as an independent translation row. Full-corpus evidence showed that this introduced four artificial length failures because row-local `_length_passed` correctly rejects standalone whitespace targets. The evaluator was not changed.

Forward illustration rescue `/5` (substantive commit `c99749b9214db572af72fb30baf8a7e98816b972`) preserves the four-piece plan and exact component provenance but renders it through one semantic carrier row over the original source span. Carrier target is exactly `label_rank0 + separator_source + suffix_rank0 + trailing_source`. This is preplanned source rendering, not target post-editing. Maintained Product Core workflow `34743281948` passed dependency-light and real-runtime Stage8→25 on this implementation, and run56 proves the full-corpus result.

## Durable closed directions

- Seq638 tested short-DMS exact-source/rank0 whole/split geometries are exhausted.
- Seq325 tested figure-reference lead/boundary-pair geometries are closed.
- Historical seq2346 angle-list DOE has no admissible tested raw-rank0 geometry; prime-preserving TC-big variants corrupted a large integer.
- Inline `[G]`, large-integer canonicalization, broad generic whole-context/model fallback, source rewriting, target repair and automatic n-best selection remain rejected under tested formulations.
- Historical prime multi-context DOE `34687752297` found only `english_miles_boundary` OPUS rank0 admissible; that family is already covered by the emphasized-modifier wrapper and is absent from run56 residuals. Do not repeat that DOE.

## Current frontier

Run56 leaves 31 unique hard failures: 18 numeric/symbol and 14 punctuation with one overlapping row, and zero length failures. Choose the next source-defined family from the persisted run56 census and current wrapper eligibility. New geometry/model use must remain generic, exact-source, rank0-only, fail-closed and should first be proven read-only before promotion.
