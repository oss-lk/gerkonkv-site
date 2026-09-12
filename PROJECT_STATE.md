# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- L3/engineering state incorporated through `001ba055f47f059529aa4b876db8d5308ae957d7` (`Run illustration structural separator DOE`).
- Authoritative Product contract: `rocketdict/PRODUCT_TARGET.md`. Release still requires **0 unresolved numeric/symbol, punctuation and length hard failures** on the complete 90k+ corpus, then learner/export coverage and Windows clean-install validation.
- Historical run23 remains immutable research evidence only; it is not legal promotion lineage because historical rank3/rank2 automatic beam selections were proven.
- Authenticated rank0-clean run41 is the **only forward promotion parent**.

## Recovery protocol

Follow `AGENTS.md`: compare current HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`; for translation-quality work load `TRANSLATION_QUALITY.md` and `DECISIONS.md`. L3 source/tests/CI/artifacts/SQLite outrank memory.

## Canonical run41 baseline

Full Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

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

Workflow `34697653680`, artifact `10298988451`, evidence SHA `b6166ec906e30afa622d9a7b4af1d84a485b3188b148cce3c3d404f2368d61e7` established:

- illustration seq `424/514`: OPUS rank0 on exact `[Illustration: FIG. N.]` + TC-big rank0 on exact `_Illustration._` passes mechanical gates, but the first aggregation incorrectly dropped source-owned `\n\n`; that aggregate is rejected;
- short-DMS seq `638`: tested exact-source/raw-rank0 whole/split geometries are exhausted and inadmissible;
- historical illustration canonicalization/beam experiments are diagnostic only because they rewrote model input and/or selected rank>0.

## Illustration structural-separator DOE

Workflow `34698906048` succeeded on exact run41 at engineering HEAD `001ba055f47f059529aa4b876db8d5308ae957d7`.

- artifact `10299487345`;
- artifact digest `sha256:87c38ebc60cea7b243e36e580f8908bd90f9f975186a96cc7342344528ce87de`;
- schema `rocketdict-full-opticks-illustration-structural-separator-doe/1`;
- evidence SHA-256 `0af3deb591aee8da0dd11ba7a59aeab64c65d2d2327e923ebbeb64b9b077e3ee`;
- exact run41 DB authenticated and unchanged; source coverage byte-exact; source plan created before MT; raw rank0 only;
- `source_owned_structural_passthrough=true`; all unsafe flags remain false, including `post_translation_literal_injection=false` and both n-best flags false;
- 8 candidates tested; exactly two pass maintained mechanical gates:
  - `illustration:72401:planned-separator:opus+tc_big`
  - `illustration:90105:planned-separator:opus+tc_big`.

The passing geometry is source-defined before MT:

1. exact label `[Illustration: FIG. N.]` → OPUS raw rank0;
2. exact source-owned blank-line separator `\n\n` is structural passthrough;
3. exact suffix `_Illustration._` → TC-big raw rank0;
4. exact trailing source whitespace is structural passthrough.

Representative aggregate: `[Иллюстрация: FIG. 21.]\n\n_Иллюстрация._ `, with square delimiters, emphasis, punctuation, numeric identity and source structural boundary all preserved.

This DOE resolves the **mechanical geometry** question. It does not by itself authorize promotion: implementation still requires confirming that existing accepted Product composition precedent treats pre-MT-planned source-owned structural bytes as legitimate passthrough rather than target injection.

## Active next actions

1. Inspect the accepted `rocketdict-stage12-ascii-table-logical-rank0/1` (and relevant Stage12 composition code/tests) to establish the structural-passthrough precedent from L3, not from the DOE's self-description.
2. If that precedent confirms pre-MT source-owned structural passthrough is legal, implement a generic source-defined, default-OFF illustration structural-separator wrapper using only OPUS rank0 + TC-big rank0 and exact source-owned separator/trailing bytes; add fail-closed unit/regression tests.
3. Replay the wrapper from exact run41 and run an independent residual census. Expected arithmetic improvement if and only if the two illustration failures disappear without regressions is 18 numeric / 14 punctuation / 0 length, 31 unique; do not accept this expectation without full evidence.
4. If full compose/census succeeds, make the new run the only forward parent and update all mandatory memory with exact identities. If the precedent is incompatible or replay regresses, reject the route and move to the next run41 residual family.
5. Continue to zero hard failures, then complete learner/export and Windows release validation.
