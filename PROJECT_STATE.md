# RocketDict project state — L1

- Repository `oss-lk/gerkonkv-site`, branch `chatgpt/product-core-forward`. Engineering checkpoint: `fad465d52c2dfa3e90299dfba5110ab449784500`. The five commits after the previous checkpoint were reviewed; they added public combined-Greek replay/canonicalization orchestration and a binding regression, not a completed corpus promotion.
- `rocketdict/PRODUCT_TARGET.md` is authoritative. The requested result is a locally installable Windows text/subtitle-to-EN→RU learner dictionary with complete real NLP/MT, sense/card/export coverage and full 90k+ acceptance evidence. A translation experiment or green smoke test is not the final product.
- **Run59 remains the sole authorized forward parent.** Canonical workflow `34753122528`, artifact `10316657472`; 3335 translation rows; hard failures 15 numeric/symbol, 10 punctuation, 0 length, 24 unique. SQLite SHA `41bafa00619c83b87f55f7e452f8e9e27a1871d601bb5c846d3d561531dbb78d`; output SHA `5feeb168b77c3a763ab01fd5c9c0c25aa02c62d67899f8b1358414099735fbb1`.
- Maintained Product Core workflow `34758868087` passed dependency-light and real-runtime jobs after the public combined-Greek binding. The former exact-binding CI blocker is closed.
- Combined-Greek public replay workflow `34760443748` at the checkpoint completed with aggregate failure. All three replay jobs retained forensic artifacts, but that does not mean replay acceptance: the script records errors and returns zero. The aggregate rejected replica 1 because the returned translation run was 61 rather than expected 60. Independent census and canonicalization were skipped; no run60/run61 parent promotion is authorized.
- Replay artifacts: replica 1 `10318553699`, replica 2 `10318906287`, replica 3 `10318249430`. Previous local repair archive `RocketDict_run59_replay_repair.zip` is an unmerged proposal, not remote Product code or a replacement parent. Validate its code/evidence before any integration; preserve SQLite WAL-aware snapshots and do not relax identity checks to hide lineage drift.
- The generic default-OFF combined-Greek source-plan wrapper preserves technical structure and raw lexical rank0 provenance. Read-only DOE `34757359712`, artifact `10317379028`, is supporting research, not promotion authority. The 15/9/0/23 hard-count expectation remains unpromoted.
- Seq3009 complementary-question work remains unresolved. OPUS clause-first output introduced target-only quotes; TC-big follow-up failed before inference due to missing runtime dependencies. Do not confuse an environment failure with model-negative evidence.
- Historical TC-big parity workflow remains repurposed. Original blob `f677a98b18e18a9d3bf5bcbf88e1a9d1c4ebaf29` is known; restoration is not committed.

## Current task and next actions

1. Perform the requested requirements/architecture audit: compare the complete Product target with actual implementation, tests and persisted learner output, not just Stage12 counters. Determine what should be retained or redesigned before further narrow rescue work.
2. Keep canonical run59 immutable during the audit. Separate product gaps, evaluator defects, runtime reproducibility defects and corpus-specific research.
3. Validate the local replay-repair proposal and ancestry discrepancy only as needed for accurate audit conclusions; do not claim it is integrated.
4. Record the audit and synchronize mandatory L1/L2 files with verified facts and explicitly proposed design changes. No release acceptance threshold or Product default changes are authorized by a diagnostic result alone.
