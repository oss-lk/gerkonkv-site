# RocketDict maintained translation quality — L2

Durable translation-quality conclusions only. This is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). L3 source/tests/CI/artifacts outrank this file.

## Maintained contracts

- Production MT is pinned OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product/default Stage10 is V1; research V2 remains explicit only.
- Stage12 planner is `rocketdict-stage12-protected-split/8`; numeric hard gate is `rocketdict-maintained-numeric-integrity/6`; emphasis diagnostic is `rocketdict-maintained-emphasis-markup-preservation/1`.
- Persisted rescue output must be the unique unmodified raw rank0 hypothesis. Higher beams are diagnostic only; missing/duplicate/malformed rank0 fails closed. No source rewriting, target surgery/literal injection, placeholders, corpus-specific target patches, automatic n-best cherry-picking or evaluator weakening.

## Canonical complete Opticks baseline

Pinned Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

Authenticated rank0-clean replay workflow `34695164876`, artifact `10297359600`, is the only forward promotion parent. Final run `41` has `3335` rows and **18 numeric/symbol / 16 punctuation / 0 length, 33 unique** hard failures. Translation-output SHA `d8948e43158a126703a90e6ce1cd25725da8774e1db64410ca67e3ec7bb1a10f`; final-text SHA `23170683ddbe183b4da6b4097d72cedc86b9c98044e9f3e1dee015015e16e15e`; SQLite SHA `e48df8a90a3aa5e07bbc7e86c150d7b65ce450e7b6a0ec0d2e34a0caf9846e2e`; replay evidence SHA `e7504ef18ead81e9c437ab8236b787a7d59082c272ef102fcc9bae6e281deac1`; independent census evidence SHA `b384ae0936f2ec792dd8ec6fbfcdf5da0dea1ba097df951c6049f2f2cbbb5319`.

Historical run23 remains immutable evidence but is not legal promotion lineage because direct audit proved rank3 illustration selections and a rank2 short-DMS selection.

## Returned-family exact-source/rank0 DOE

Workflow `34697653680`, artifact `10298988451`, evidence SHA `b6166ec906e30afa622d9a7b4af1d84a485b3188b148cce3c3d404f2368d61e7` authenticated exact run41 and used raw rank0 only.

- Illustration seq `424/514`: exact label OPUS rank0 + exact `_Illustration._` TC-big rank0 can pass maintained gates, but the initial aggregate omitted source-owned `\n\n`; that candidate is rejected.
- Short-DMS seq `638`: no tested exact-source/raw-rank0 whole-row or current split geometry passes. Do not repeat the same lead/measurement or degrees/prime formulations without materially new evidence.
- Earlier illustration canonicalization/word experiments remain diagnostics only because they rewrote model input and/or selected non-rank0 beams.

## Illustration source-owned structural-separator DOE

Workflow `34698906048` is the current authoritative illustration geometry evidence. It succeeded at engineering HEAD `001ba055f47f059529aa4b876db8d5308ae957d7` on exact run41.

- artifact `10299487345`;
- artifact digest `sha256:87c38ebc60cea7b243e36e580f8908bd90f9f975186a96cc7342344528ce87de`;
- schema `rocketdict-full-opticks-illustration-structural-separator-doe/1`;
- canonical evidence SHA `0af3deb591aee8da0dd11ba7a59aeab64c65d2d2327e923ebbeb64b9b077e3ee`;
- 8 candidates; only `illustration:72401:planned-separator:opus+tc_big` and `illustration:90105:planned-separator:opus+tc_big` pass maintained mechanical gates;
- database remains unchanged, source coverage byte-exact, source plan created before MT, raw rank0 only;
- `source_owned_structural_passthrough=true`; `source_bytes_rewritten=false`, `target_rewriting=false`, `placeholders=false`, `post_translation_literal_injection=false`, `corpus_specific_target_patches=false`, `evaluator_weakened=false`, `n_best_cherry_picking=false`, `automatic_n_best_cherry_picking=false`.

Passing geometry is generic and source-defined:

- exact source label `[Illustration: FIG. N.]` is translated by OPUS rank0;
- exact source blank-line separator (matched before MT) is passed through structurally;
- exact source `_Illustration._` suffix is translated by TC-big rank0;
- exact trailing source whitespace is passed through structurally.

Representative result: `[Иллюстрация: FIG. 21.]\n\n_Иллюстрация._ `, preserving the square-bracket payload, figure number, source blank-line boundary, emphasis and trailing structural whitespace. The corresponding FIG.24 case is equivalent.

This evidence establishes a mechanically clean geometry but does **not** alone prove that source-owned structural passthrough is an authorized Product composition operation. Before promotion, inspect accepted L3 precedent, especially `rocketdict-stage12-ascii-table-logical-rank0/1` and the Stage12 composition implementation/tests. If those establish that source-owned structural bytes planned before MT are preserved as structure rather than injected into model output, the illustration route may advance to a default-OFF wrapper and full replay. Otherwise reject it.

## Other durable negatives

- Sequence `325` figure-reference lead-split and preceding-boundary-pair geometries are closed: isolated green mechanics broke full-context syntax; restored syntactic context failed hard gates.
- Historical seq `2346` angle-list DOE workflow `34693396634`, evidence SHA `094140b1add91c3cdb6294319cfc691d38d488f97966c5cb41a9ae2386d055d6`, found no admissible raw-rank0 OPUS/TC-big geometry; TC-big candidates that preserved primes corrupted `100000000` to `10000000`.
- Inline `[G]`, large-integer canonicalization, generic whole-context/model fallback and nonliteral automatic n-best approaches remain rejected under tested formulations.

## Promotion rules / current frontier

1. Never weaken maintained evaluators or repair model output post hoc.
2. Preserve immutable source/model/config/result identities and exact predecessor lineage.
3. Persist only deterministic unmodified raw rank0 model output; semantic/boundary review remains mandatory in addition to mechanical gates.
4. New geometry/model use requires a generic source-defined trigger and must fail closed.
5. Source-owned structural passthrough may be used only if it is demonstrably planned from immutable source before MT and is supported by existing Product composition contract/precedent; it must never become post-MT target repair.
6. Immediate next step: audit the accepted structural-passthrough precedent. If compatible, implement the generic illustration wrapper and run full compose+census from exact run41. If incompatible, close this route and move to the next residual family.
