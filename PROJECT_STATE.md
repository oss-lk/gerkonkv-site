# RocketDict project state — L1

- Repo: `oss-lk/gerkonkv-site`; branch: `chatgpt/product-core-forward`.
- Product contract: `rocketdict/PRODUCT_TARGET.md`; release requires zero numeric/symbol, punctuation and length hard failures on the full 90k+ corpus, then learner/export and Windows clean-install validation.
- **Authenticated run57 is the sole forward parent.** Promotion workflow `34746052346`, artifact `10314371661` (`sha256:7e06036210f610194ee38a1545671197b081e3acf7aa7d437509b0e8d759e37f`). Run57: 3335 rows; **18 numeric / 10 punctuation / 0 length, 27 unique**; output SHA `c29e50beafd12f2a6670a3a34f4057beab9b23db9ab9f9a4b22850601b174195`; target SHA `6e5c8b0c1e7717fd8d82b94eb1a4d09fe0744ed3f6b87aadf7d0cf8d59789e3f`; SQLite SHA `f6eae41e02211a35f3519c8abcdeceb2699f4f0089dc2c2fa10800682fe06115`.
- Promotion evidence SHA `8565e338f6ed8993498427d67235fa03062728c02edc0e19a4cd3826a8122e54`; independent residual-census SHA `38192e8ea390637012cdb2ecb4aeea0eae76a72a3edc17bf3c2df6004d4109a7`.
- Exact run56 was cache-resolved as base; exactly rows `741,1497,2108,2589` changed, 3331 unrelated targets stayed byte-exact; source coverage, raw-rank0/exact-model-input provenance, SQLite integrity and FK checks passed.
- Correct ancestry: run57 parenthetical wrapper delegates through `translation_emphasized_modifier_boundary_rescue_stage`, because run56 is that outer wrapper over run55 illustration `/5`. The incorrect illustration-direct change `6793fd1` was reverted by `f97b7962201389f1967dcf6650035d7ff191931d`; authoritative replay commit is `e8960cdc5815c86c10243c0a395648244c4c75f8`.
- Maintained Product Core workflow `34746052211` passed dependency-light and real-runtime Stage8→25 on the correct ancestry.
- Whole-context parenthetical route stays rejected because context `1977` semantically truncates despite mechanical eligibility. Row-local focused DOE evidence remains `c82ce59e48eb380a4cf23b41e69574271cf8480659f0815617732fd4cc56ce5e`.
- One-shot parenthetical research/promotion infrastructure was removed in cleanup commit `19e1933610421ad57ba8e068e36cc5527a492ef6`; reproducible evidence remains in Git history and Actions artifacts.

## Next actions

1. Use run57 independent census as the only forward residual baseline: 27 unique = 18 numeric/symbol + 10 punctuation, 0 length.
2. Do not repeat closed seq638 short-DMS, seq325 figure-reference, historical angle-list/big-integer, inline `[G]`, broad fallback or automatic n-best directions without materially new evidence.
3. Audit the remaining numeric families against current wrappers, then run a read-only exact-row OPUS/TC-big rank0 screening as discovery evidence for genuinely new source-defined classes.
4. Continue quality-first to zero hard failures, then finish learner/export and Windows release validation.
