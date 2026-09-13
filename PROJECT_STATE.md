# RocketDict project state — L1

- Branch: `chatgpt/product-core-forward`. Engineering checkpoint before this sync: `2f075ce14857204198079531a8bf1237c0f97e26`. `rocketdict/PRODUCT_TARGET.md` remains authoritative; release still requires zero numeric/symbol, punctuation and length hard failures on the full 90k+ corpus.
- **Run59 remains the sole legal forward parent**: 3335 rows; hard counts **15 numeric / 10 punctuation / 0 length, 24 unique**. Canonical workflow `34753122528`, artifact `10316657472`, SQLite SHA `41bafa00619c83b87f55f7e452f8e9e27a1871d601bb5c846d3d561531dbb78d`, output SHA `5feeb168b77c3a763ab01fd5c9c0c25aa02c62d67899f8b1358414099735fbb1`. Parent replacement is verified.
- M2M100 arithmetic rescue remains accepted default-OFF and cross-platform reproducible. Disposable canonical/asset/CNR workflows and determinism/CNR harnesses were removed; Windows repro and run58 public-replay workflows remain cleanup debt. Historical Run20 workflow is textually restored but current blob identity still differs from the historical blob.
- Current quality frontier: punctuation seq3009. Its source begins with a short question tail `fix'd as Lead?` followed by a blank paragraph boundary and a long new paragraph. Planner-v8 leaves the prior row at its 64-token budget and places this 4-token tail at the next row start; OPUS drops the tail. Historical exact-row TC-big restores punctuation but leaves untranslated `fix'd`, so it is not promotion-quality evidence.
- A read-only baseline-OPUS forward-boundary DOE was added. Workflow `34755006902` failed before inference because the harness carried an incorrect run59 DB SHA; this is orchestration failure, not model evidence. Corrected launcher `real_translation_run59_forward_paragraph_boundary_resegmentation_doe_v2.py` at `2f075ce1…` changes only the immutable DB identity and has not yet completed a successful replay.

## Next actions

1. Wire and run the corrected v2 DOE against canonical run59.
2. If both raw OPUS rank0 resegmented rows and their aggregate are strict-clean, emphasis-preserving and semantically sound, implement a separate default-OFF wrapper and perform full run59 promotion plus independent census; otherwise close the direction.
3. Finish conservative cleanup, then continue residual-family work to zero hard failures.
