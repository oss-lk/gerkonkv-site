# RocketDict maintained translation quality — L2

- `rocketdict/PRODUCT_TARGET.md` and L3 evidence are authoritative.
- Run56 remains the sole legal forward parent: 3335 rows, **18 numeric / 14 punctuation / 0 length, 31 unique**, SQLite SHA `cb4568584e70be0fb4d011cd9de212ae01edd046dec8c5ec104ee3bb0e91dc56`.
- Corrected whole-context parenthetical DOE `34744305345` is not promotion-safe: TC-big mechanically passes context `1977` but semantic review shows truncation of the final substantive clause.
- Focused exact-row TC-big DOE `34744521997`, evidence SHA `c82ce59e48eb380a4cf23b41e69574271cf8480659f0815617732fd4cc56ce5e`, accepted `741,1497,2108,2589` and rejected `2719,3081`; exact immutable row source is the model input and selection is unique raw rank0.
- Default-OFF row-local wrapper + neutral tests landed in `122392b89055eb515fea0cb2911e61a7d1ebbf4a`; maintained Product Core workflow `34744782708` passed dependency-light and real-runtime jobs.
- Commit `6793fd19cc2c0e2a9779b72d15ad198624820cc0` fixes wrapper layering so its base is `translation_illustration_rescue_stage`, preserving run56 ancestry.
- Promotion boundary: exact run56 base; exactly four target replacements; all unrelated source/target spans exact; raw rank0/exact-source provenance; SQLite integrity/FKs clean; independent census **18 numeric / 10 punctuation / 0 length, 27 unique**.
