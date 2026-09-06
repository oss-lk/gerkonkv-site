# RocketDict public handoff

This repository is the public, project-only continuation point for RocketDict.

## Read first

1. [`rocketdict/PRODUCT_TARGET.md`](rocketdict/PRODUCT_TARGET.md) — authoritative global result and definition of done.
2. [`rocketdict/CURRENT.md`](rocketdict/CURRENT.md) — current active implementation boundary and exact next path.
3. [`rocketdict-product-core/README.md`](rocketdict-product-core/README.md) — maintained core and real-runtime evidence boundary.
4. Existing Workbench/Product source and tests under `rocketdict-workbench/`.

Historical recovery material under `rocketdict/recovered/` remains preserved for audit/research, but **historical recovery is not the active development task and is not a Product blocker**.

## Active directive

Build forward to the complete installable Product. Do not search for old checkpoint bytes or wait for a historical core unless the user explicitly requests historical recovery.

The previous missing-core blocker is closed: `rocketdict-product-core/` is the maintained current `rocketdict` implementation. It is new code, not reconstructed 0.30.x source.

## Proven maintained boundary

The maintained core now provides:

`immutable source/import/interpretation → Stage8 production spaCy NLP → Stage10 context → Stage12 real OPUS → Stage14 refinement boundary → Stage15 hard gates → Stage16 approval → Stage17 alignment → Stage18 lexical extraction → Stage19 sense induction`

GitHub `RocketDict Product Core` real-runtime run `34028203744`, job `101472903537`, executed this chain with:

- `en_core_web_sm 3.8.0`;
- CTranslate2 4.8.2;
- SentencePiece 0.2.2;
- official OPUS `opus-2020-02-11.zip`, exact SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`;
- float32 CPU acceptance;
- offline processing after provisioning.

The observed Stage12 translation for the smoke source was real Cyrillic output: `Свет проходит через стеклянный призм и образует спектр`. Stage12 reported `real_mt=true`, `network_used=false`, 0 empty outputs and 0 backend errors. All Stage15 gates passed. Stage17 coverage was complete. Native Stage18 produced 6 lexical entries/occurrences with zero uncovered Product content tokens; Stage19 produced 6 durable lexical senses.

The OPUS provisioner does not assume a fixed Marian weight filename. The runtime verifies the complete local OPUS payload tree before use; mutated or extra model files fail closed.

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

The established real MT baseline is OPUS EN→RU `opus-2020-02-11.zip`, exact SHA above, CTranslate2 Marian, float32 for quality acceptance.

## Immediate continuation

Do **not** implement another orchestration layer and do **not** return to recovery.

1. Migrate the remaining Workbench Stage18 helper call to maintained `product.stage18.run`; the maintained core already has the proven native operation, so do not recreate the historical ORM for compatibility.
2. Migrate/implement Stage20 sense translation against maintained Stage19 lexical senses while retaining the existing validated contextual lexical OPUS/arbitration policy and immutable identities.
3. Migrate Stage21 CEFR-J, Stage22 exact CMUdict, Stage23 sense-scoped examples, Stage24 cards/set and Stage25 export to the maintained schema/API.
4. Make `rocketdict-product-run` execute the maintained path source→Stage25 as one resumable workflow using real assets.
5. Prove a real small end-to-end source→export run and fix all discovered lineage/quality/coverage defects.
6. Run the complete 90k+ public-domain corpus, preserving the full evidence database.
7. Fix heavy-run defects and rerun final confirmation.
8. Build the Windows release package/installer.
9. Pass clean-install end-to-end smoke and release the complete Product artifact.

Every `продолжай` should take the largest coherent verified step toward this result. Do not split work into artificial micro-stages.

## Non-negotiable rules

- Quality > speed/storage optimization.
- No fake/identity/mock/dictionary substitution accepted as MT.
- No silent truncation.
- No weakening hard gates for green status.
- Production NLP cannot be tokenizer-only.
- Preserve failed experiments and immutable evidence.
- Read-only diagnostics stay read-only.
- Recovery stays archived unless explicitly requested.
- Keep the public repository free of personal/account/private-conversation data.
