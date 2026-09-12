# RocketDict maintained translation quality — L2

Durable translation-quality conclusions only. This is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). L3 source/tests/CI/artifacts outrank this file.

## Maintained contracts

- Production MT is pinned OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product/default Stage10 is V1; research V2 remains explicit only.
- Stage12 planner is `rocketdict-stage12-protected-split/8`; numeric hard gate is `rocketdict-maintained-numeric-integrity/6`; emphasis diagnostic is `rocketdict-maintained-emphasis-markup-preservation/1`.
- Persisted rescue output must be the unique unmodified raw rank0 hypothesis. Higher beams are diagnostic only; missing/duplicate/malformed rank0 fails closed. No source rewriting, target surgery/literal injection, placeholders, corpus-specific target patches, automatic n-best cherry-picking or evaluator weakening.

## Canonical complete Opticks baseline

Pinned Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

Authenticated rank0-clean replay workflow `34695164876`, artifact `10297359600`, artifact digest `sha256:e2d7549965d893c0b877cfe21057b8490134392a966e42fd72483ebb19836b4d` is the only forward promotion parent. Final run `41` has `3335` rows and **18 numeric/symbol / 16 punctuation / 0 length, 33 unique** hard failures. Translation-output SHA-256 `d8948e43158a126703a90e6ce1cd25725da8774e1db64410ca67e3ec7bb1a10f`; final-text SHA-256 `23170683ddbe183b4da6b4097d72cedc86b9c98044e9f3e1dee015015e16e15e`; SQLite SHA-256 `e48df8a90a3aa5e07bbc7e86c150d7b65ce450e7b6a0ec0d2e34a0caf9846e2e`; replay evidence SHA-256 `e7504ef18ead81e9c437ab8236b787a7d59082c272ef102fcc9bae6e281deac1`; independent census evidence SHA-256 `b384ae0936f2ec792dd8ec6fbfcdf5da0dea1ba097df951c6049f2f2cbbb5319`.

Historical run23 remains immutable evidence but is not legal promotion lineage because direct audit proved rank3 illustration selections and a rank2 short-DMS selection.

## Returned-family exact-source/rank0 DOE

Workflow `34697653680` succeeded on engineering HEAD `bb63b48894555ca252cb52587b3dbd722ef23c4c`. Artifact `10298988451`, digest `sha256:b3a499d41da72d1039a943d55005ca79b7237b620a56f7f9a257ddf521b5ff09`; schema `rocketdict-full-opticks-clean-returned-family-geometry-doe/1`; canonical evidence SHA-256 `b6166ec906e30afa622d9a7b4af1d84a485b3188b148cce3c3d404f2368d61e7`.

The DOE authenticated exact run41, remained read-only/source-byte-exact, generated raw rank0 only, and kept all prohibited-transform flags false. It tested 30 candidates across illustration starts `72401,90105` and short-DMS start `110881`.

### Illustration pair (`seq 424`, `seq 514`)

Only four candidates passed maintained mechanical gates: two equivalent geometries per row using OPUS rank0 on exact source `[Illustration: FIG. N.]` and TC-big rank0 on exact source `_Illustration._`. Their aggregate targets were:

- `[Иллюстрация: FIG. 21.]_Иллюстрация._`
- `[Иллюстрация: FIG. 24.]_Иллюстрация._`

These candidates are **not promotable as tested** because aggregation deletes the source-owned `\n\n` boundary between the figure label and emphasized illustration word. Mechanical gate success is insufficient when source structural boundaries regress. The next experiment may preserve that exact separator only if existing Product/source composition contracts establish that carrying a source-owned separator between independently translated chunks is legitimate structural composition rather than prohibited target literal injection.

Earlier illustration experiments do not satisfy current promotion invariants: feasibility `/2` rewrote `_Illustration._` before MT; feasibility `/3` and illustration-word DOE used automatic beam selection (the word DOE also changed model input to canonical alternatives such as `Illustration.`, `Figure.`, `Picture.`). Their positive outcomes remain diagnostics only.

### Short-DMS (`seq 638`)

No exact-source/raw-rank0 candidate passed under the tested whole-row and split geometries. Whole OPUS renders prime notation as feet; whole TC-big drops one double-prime. Tested mixed/model split variants around the lead/measurement and degrees/prime boundaries remain mechanically inadmissible. Do not repeat these formulations without materially new source-defined geometry or model evidence.

## Other durable negatives

- Sequence `325` figure-reference lead-split and preceding-boundary-pair geometries are closed: isolated green mechanics broke full-context syntax; restored syntactic context failed hard gates.
- Historical seq `2346` angle-list DOE workflow `34693396634`, evidence SHA `094140b1add91c3cdb6294319cfc691d38d488f97966c5cb41a9ae2386d055d6`, found no admissible raw-rank0 OPUS/TC-big geometry; TC-big candidates that preserved primes corrupted `100000000` to `10000000`.
- Inline `[G]`, large-integer canonicalization, generic whole-context/model fallback and nonliteral automatic n-best approaches remain rejected under tested formulations.

## Promotion rules / current frontier

1. Never weaken maintained evaluators or repair model output post hoc.
2. Preserve immutable source/model/config/result identities and exact predecessor lineage.
3. Persist only deterministic unmodified raw rank0 model output; semantic/boundary review remains mandatory in addition to mechanical gates.
4. New geometry/model use requires a generic source-defined trigger and must fail closed.
5. A mechanically green aggregate that destroys source-owned structural boundaries is not promotable.
6. Immediate next step: determine from Product code/contracts and accepted composition precedent whether exact source-owned separator passthrough is legitimate. If yes, run a separator-preserving illustration DOE before implementing any wrapper. If no, mark this illustration route exhausted and move to the next run41 residual family.
