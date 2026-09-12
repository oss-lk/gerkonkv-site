# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- L3/engineering state incorporated through `bb63b48894555ca252cb52587b3dbd722ef23c4c` (`Run rank0 clean returned-family geometry DOE`); mandatory L2 synchronization is incorporated through memory commit `6f2247d2aca707ad278c37499299b6b55b2d6d66`.
- Authoritative Product contract: `rocketdict/PRODUCT_TARGET.md`. Release still requires **0 unresolved numeric/symbol, punctuation and length hard failures** on the complete 90k+ corpus, then learner/export coverage and Windows clean-install validation.
- Historical run23 remains immutable research evidence only; it is not legal promotion lineage because historical rank3/rank2 automatic beam selections were proven.
- Authenticated rank0-clean run41 is the **only forward promotion parent**.

## Recovery protocol

Follow `AGENTS.md`: compare current HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; for translation-quality work load `TRANSLATION_QUALITY.md` and `DECISIONS.md`. L3 source/tests/CI/artifacts/SQLite outrank memory.

## Canonical run41 baseline

Full Project Gutenberg *Opticks* source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

Rank0-clean replay workflow `34695164876`, artifact `10297359600`, final run `41`:

- `3335` rows;
- **18 numeric/symbol / 16 punctuation / 0 length, 33 unique**;
- output SHA `d8948e43158a126703a90e6ce1cd25725da8774e1db64410ca67e3ec7bb1a10f`;
- final-text SHA `23170683ddbe183b4da6b4097d72cedc86b9c98044e9f3e1dee015015e16e15e`;
- SQLite SHA `e48df8a90a3aa5e07bbc7e86c150d7b65ce450e7b6a0ec0d2e34a0caf9846e2e`;
- replay evidence SHA `e7504ef18ead81e9c437ab8236b787a7d59082c272ef102fcc9bae6e281deac1`;
- independent census evidence SHA `b384ae0936f2ec792dd8ec6fbfcdf5da0dea1ba097df951c6049f2f2cbbb5319`.

Persisted rescue selection is unique raw rank0 only; no source rewriting, target rewriting/surgery, literal injection, placeholders, corpus patches, automatic n-best cherry-picking or evaluator weakening.

## Returned-family DOE

Workflow `34697653680` succeeded on exact run41 at engineering HEAD `bb63b48894555ca252cb52587b3dbd722ef23c4c`. Artifact `10298988451`, digest `sha256:b3a499d41da72d1039a943d55005ca79b7237b620a56f7f9a257ddf521b5ff09`; evidence SHA `b6166ec906e30afa622d9a7b4af1d84a485b3188b148cce3c3d404f2368d61e7`. The DOE was read-only, source-byte-exact and raw-rank0-only.

Findings:

- illustration seq `424/514`: OPUS rank0 on exact `[Illustration: FIG. N.]` + TC-big rank0 on exact `_Illustration._` passes current mechanical gates, but the tested aggregation **drops the source-owned `\n\n` boundary**, yielding `[Иллюстрация: FIG. N.]_Иллюстрация._`. This is not promotable as tested.
- short-DMS seq `638`: no tested exact-source/raw-rank0 whole-row or current split geometry passes. Do not repeat the same lead/measurement or degrees/prime formulations without materially new evidence.
- historical illustration word/canonicalization experiments are diagnostics only because they rewrote model input and/or selected non-rank0 beams.

## Durable blockers / next actions

1. Before modifying illustration translation, inspect `PRODUCT_TARGET.md`, Stage12/source segmentation and accepted composition wrappers to determine whether preserving an exact **source-owned separator** between independently translated chunks is legitimate structural composition or prohibited post-translation literal injection.
2. If source-owned separator passthrough is already authorized by existing contracts/precedent, run a read-only separator-preserving illustration DOE from exact run41. Do **not** implement a wrapper first.
3. If that DOE passes hard gates plus semantic/boundary review, implement a generic source-defined default-OFF rank0-only wrapper and replay full compose+census from run41.
4. If separator passthrough is not authorized or the DOE fails, close this illustration route; short-DMS current geometries are already exhausted. Advance to the next run41 residual cluster.
5. Continue to zero hard failures, then complete learner/export and Windows release validation.
