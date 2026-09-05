# RocketDict public handoff

This repository is the public, project-only continuation point for RocketDict.

## Read first

1. [`rocketdict/PRODUCT_TARGET.md`](rocketdict/PRODUCT_TARGET.md) — authoritative global result and definition of done.
2. [`rocketdict/CURRENT.md`](rocketdict/CURRENT.md) — current active implementation boundary.
3. Existing Workbench/Product source and tests under `rocketdict-workbench/`.

Historical recovery material under `rocketdict/recovered/` remains preserved for audit/research, but **historical recovery is not the active development task and is not a Product blocker**.

## Active directive

Build forward to the complete installable Product. Do not search for old checkpoint bytes or wait for a historical core unless the user explicitly requests historical recovery.

The current maintained Workbench already implements substantial Stage8→25 Product logic. The critical defect is that `rocketdict_workbench.core.RocketDictCore` still delegates database/import/interpretation/API work to an externally installed historical `rocketdict` package.

Treat that as missing Product implementation. Implement a maintained self-contained Product Core in this repository and satisfy the existing contracts/tests. Do not claim the new code is recovered historical source.

## Global result

RocketDict is complete for this project only when it:

- installs locally on the supported Windows target;
- accepts supported English text/subtitle input;
- processes it end-to-end without manual stage reconstruction;
- uses production NLP and real EN→RU MT;
- preserves source/quality/research identities and failures;
- passes hard translation-integrity gates on the accepted final heavy run;
- produces complete learner-dictionary/sense/CEFR/pronunciation/examples/cards/export output for the Product-defined scope;
- processes the complete 90k+ public-domain validation corpus without silent truncation;
- retains the heavy research/evidence database and final artifacts;
- fixes critical heavy-run defects with regression coverage;
- passes a clean-install end-to-end smoke test.

Anything short of this is an intermediate checkpoint.

## Required production path

`immutable source ingestion → interpretation/segmentation → production NLP → context structure → real MT → glossary/refinement → hard quality validation → alignment → lexical extraction → sense induction → sense translation → CEFR → pronunciation → examples → cards/set → export`

The established real MT baseline remains OPUS EN→RU `opus-2020-02-11.zip`, SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian, float32 for quality acceptance.

## Immediate continuation

1. Implement maintained Product Core database/source import/interpretation/API/registry capabilities required by the current Workbench bridge.
2. Remove historical-core availability from the normal Product critical path.
3. Prove a real small end-to-end Product run using production NLP + real OPUS.
4. Fix resulting execution/lineage/quality/coverage defects.
5. Pin validated production configuration.
6. Run the complete 90k+ public-domain corpus, preserving the full evidence database.
7. Fix heavy-run defects and rerun final confirmation.
8. Build the Windows release package/installer.
9. Pass clean-install end-to-end smoke and release the complete Product artifact.

Every `продолжай` should take the largest coherent verified step toward this result. Do not split work into artificial micro-stages.

## Non-negotiable rules

- Quality > speed.
- No fake/identity/mock/dictionary substitution accepted as MT.
- No silent truncation.
- No weakening hard gates for green status.
- Production NLP cannot be tokenizer-only.
- Preserve failed experiments and immutable evidence.
- Read-only diagnostics stay read-only.
- Recovery stays archived unless explicitly requested.
- Keep the public repository free of personal/account/private-conversation data.