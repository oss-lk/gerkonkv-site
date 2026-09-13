# RocketDict project state — L1

- Repo: `oss-lk/gerkonkv-site`; branch: `chatgpt/product-core-forward`.
- Product contract: `rocketdict/PRODUCT_TARGET.md`; release requires zero numeric/symbol, punctuation and length hard failures on the full 90k+ corpus.
- Run56 remains the only legal forward parent until corrected parenthetical-row promotion passes independent verification. Run56: 3335 rows; **18 numeric / 14 punctuation / 0 length, 31 unique**; SQLite SHA `cb4568584e70be0fb4d011cd9de212ae01edd046dec8c5ec104ee3bb0e91dc56`.
- Corrected whole-context parenthetical DOE `34744305345` is not promotion-safe: TC-big mechanically passed context `1977` but semantic review found truncation.
- Focused exact-row TC-big DOE `34744521997`, evidence SHA `c82ce59e48eb380a4cf23b41e69574271cf8480659f0815617732fd4cc56ce5e`, accepted generic trigger rows `741,1497,2108,2589` and rejected `2719,3081`.
- Default-OFF row-local wrapper + neutral tests landed in `122392b89055eb515fea0cb2911e61a7d1ebbf4a`; Product Core workflow `34744782708` passed dependency-light and real-runtime jobs.
- Wrapper base-chain correction `6793fd19cc2c0e2a9779b72d15ad198624820cc0` delegates through `translation_illustration_rescue_stage`, preserving run56 ancestry.
- Mandatory L1/L2 recovery sync completed through commits `41a0ef1`, `97ad64d`, `96af399`.
- Corrected promotion replay trigger commit is prepared as `15da0a6a999f552c42a657965fb303f2e06907b0`; accept promotion only if base is exact run56, exactly four target rows change, unrelated spans remain exact, provenance is raw rank0/exact source, SQLite integrity passes, and independent census is **18 / 10 / 0, 27 unique**.
