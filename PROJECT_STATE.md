# RocketDict project state — L1

- Repo: `oss-lk/gerkonkv-site`; branch: `chatgpt/product-core-forward`. Current engineering checkpoint before this memory catch-up: `2dc03d17824b620560260ac40d44632a4d984281`; subsequent commits `11e8749…` and `bee171e…` are memory-only catch-up.
- Product contract: `rocketdict/PRODUCT_TARGET.md`; release requires zero numeric/symbol, punctuation and length hard failures on the complete 90k+ corpus, then complete learner/export coverage and Windows clean-install validation.
- **Authenticated run58 is the sole forward parent.** Promotion workflow `34748268143`, artifact `10315026413` (`sha256:265ae3de4991544990aedf752451feb84733a3237ca3ae2bac2dfd49e97befc9`). Run58: 3335 rows; **16 numeric / 10 punctuation / 0 length, 25 unique**; translation output SHA `60349256eac118e9af7aa1366761342cd2041bb6ade4db04b45c78b46a8c6e5d`; target SHA `8297e8b6cf20233284042549132bfc2eb4be312046964eab22cd7aa785eee3fd`; SQLite SHA `a24f35d6f8bb4747a4fc301511f383b8b866846a3c448655fce1b9359cc0ac94`; parameters SHA `1cf60c7b582640c3923ea685ed329eb685a7b80e502e11507d99c752e6342315`.
- Promotion evidence SHA `0d5e893f5338e3b40c82a0e6eeb91d6f6b56dfc15fbae5974f0f6e9f042bb8c2`; independent residual-census SHA `f4db643126c611e5f41e07af9d2ffa63dc43e9e9e48ea7884b0da7563ef9a803`. SQLite `integrity_check=ok`, FK violations 0.
- New optional pinned M2M100 portability layer exists: exact snapshot hashes -> Product CTranslate2 float32 asset -> CPU torch-free inference. Model identity: `facebook/m2m100_418M`, revision `55c2e61bbf05dfb8d7abccdc3fae6fc8512fd636`, weight SHA `d907ea45e4e4b9db163382a6674f6218b3c59566fe06d77f4055c208b4e87ed1`. It is not a Product default replacement for OPUS.
- Real M2M100 CT2 parity workflow `34748655508`, artifact `10315206479` (`sha256:3f90caf7dcf13a807da14a5d3ebb65100ee7ed9c6478d43b8853ff64d4912a1e`) proved raw CT2 rank0 at source start `483234` is byte-identical to historical PyTorch rank0, preserves verified `700000 × 700000 = 490000000000`, passes current strict mechanical/emphasis checks, and has evidence SHA `bc739df0594e5f73331c2a2d5301bdb6d6eb27d9ab3921703dc99a16237dac57`.
- Generic source-verified arithmetic rules/tests were added at `2dc03d1`. Product CI `34748766251` currently fails exactly one new synthetic selector test (`1 failed, 408 passed`); real-runtime was skipped. This is the active engineering blocker and must be diagnosed without weakening gates.
- Process cleanup debt: `.github/workflows/rocketdict-full-opticks-run20-m2m100-product-restatement-doe.yml` is still temporarily repurposed for CT2 parity and `rocketdict-workbench/tests/real_translation_m2m100_ct2_restatement_parity.py` is one-shot research infrastructure. Restore the historical workflow and remove the one-shot harness after the parity result is retained in L2/Git evidence.
- Progression source start `268952` remains a durable TC-big fail-closed negative. Historical M2M100 compound-million output `десятьсот тысяч` remains semantically rejected despite a green numeric gate.

## Next actions

1. Diagnose/fix the single arithmetic selector test failure at `2dc03d1` using actual evaluator output; do not weaken current gates.
2. Restore the historical M2M100 restatement workflow and remove the parity one-shot harness.
3. Implement a default-OFF Stage12 M2M100 arithmetic wrapper only after rules/tests are green; exact immutable source -> pinned CT2 unique raw rank0, no rewriting/injection/n-best selection.
4. Run a full run58-based Opticks promotion with independent census; only then consider run59 as a new parent.
5. Continue quality-first to zero hard failures, then learner/export and Windows release validation.
