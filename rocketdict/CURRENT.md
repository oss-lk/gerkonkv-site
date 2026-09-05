# RocketDict — CURRENT authoritative continuation state

Date: 2026-09-05
Repository: `oss-lk/gerkonkv-site`
Branch: `main`

## Active directive

The active development line is **Product completion**, not historical recovery.

Authoritative global target:

[`PRODUCT_TARGET.md`](PRODUCT_TARGET.md)

Historical checkpoint/core recovery is frozen as audit/research tooling. It is not a prerequisite, blocker, or default next task. Do not search for old archives or attempt to reconstruct missing 0.30.34/0.30.40 source unless the user explicitly asks for historical recovery.

The development rule is: **preserve history, build forward, finish the installable Product.**

## Global result

RocketDict must become a locally installable Product that turns supported English text/subtitle input into a high-quality context-aware EN→RU learner dictionary/card set using production NLP and real MT, preserves research/quality evidence, completes the full downstream lexical/sense/CEFR/pronunciation/examples/cards/export path, survives a complete 90k+ public-domain corpus run without silent truncation, and passes a clean Windows install/end-to-end smoke test.

Anything short of that is an intermediate checkpoint.

## Non-negotiable quality rules

- Translation quality > speed/storage optimization.
- Never accept fake/identity/mock/dictionary substitution as real MT.
- Never silently truncate source, heavy corpus, translation units, evidence or final exports.
- Never weaken hard gates merely to obtain green status.
- Distinguish evaluator defects from real translation defects.
- Final Product NLP cannot be tokenizer/code-only.
- Generated pronunciation fallback is not authoritative pronunciation evidence.
- Preserve failed experiments and immutable source/config/model/result identities.
- Read-only diagnostics must be actually read-only.
- Public repository remains project-only and contains no personal/private account information.

## Existing Product work to reuse

Workbench already contains substantial maintained Product logic and must be reused rather than replaced by another orchestration layer:

- Product profile/preflight and immutable Product-run state;
- live registry/API probing and exact callable binding/execution proofs;
- pre-quality Stage8 → 10 → 12 → 14 chain;
- Stage15 explicit hard-quality gate machinery;
- Stage16 → 17 → Workbench18 → 19 post-gate dependencies;
- real OPUS-backed Stage20 path and lexical-primary arbitration;
- pinned CEFR-J integration;
- CMUdict exact pronunciation path;
- sense-scoped examples;
- Stage24 cards/set assembly;
- Stage25 export;
- Research/evidence preservation and numerous fail-closed regression contracts.

Primary Product CLI remains `rocketdict-product-run` while the Product Core is made self-contained.

## Current architectural defect to fix

`rocketdict-workbench/src/rocketdict_workbench/core.py` still bridges to an externally installed historical `rocketdict` package for:

- database bootstrap;
- source import;
- source interpretation;
- public API/registry operations;
- experiment/runtime operations.

That dependency is now treated as a **missing maintained Product implementation**, not as a recovery problem.

Do not wait for an old wheel/ZIP. Implement the Product Core needed by the current contracts in the maintained repository and verify it with the existing Workbench runner/tests.

Do not claim new implementation is recovered historical code.

## Real model baseline

Accepted real EN→RU baseline remains:

- OPUS `opus-2020-02-11.zip`
- SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`
- CTranslate2 Marian
- quality acceptance compute type `float32`.

Historical real-model evidence remains useful and should be reused; obsolete experiments should not be restarted from scratch unless required to validate a changed production configuration.

## Hard quality gates

At minimum the existing gates remain mandatory for approved translation evidence:

- numeric/symbol preservation;
- punctuation preservation;
- length-ratio proxy.

Empty translation outputs and backend errors are release blockers.

Stage15 gate PASS semantics must remain explicit, exact and machine-readable.

## Heavy validation target

Use a complete public-domain corpus of at least 90,000 words. The established canonical corpus is Newton's *Opticks* (~104k words depending on the exact counting contract).

Final heavy acceptance requires, under the selected Product contracts:

- full source processed; no silent clipping;
- lost source content/tokens = 0;
- empty MT outputs = 0;
- MT backend errors = 0;
- unresolved hard translation-integrity failures = 0 for approved evidence;
- complete downstream alignment/lexical/sense/card/export coverage for the defined Product scope;
- full research/evidence database retained;
- defects found by the heavy run fixed and regression-tested;
- final complete heavy confirmation rerun.

## Installation/release target

The result is not a test suite or source archive alone.

The final release must include a practical Windows installation/distribution path and pass a clean-install end-to-end smoke test. After installation, a user must be able to process a supported source and receive the final dictionary/export without manually rebuilding stage state.

## Active critical path

1. Implement a maintained self-contained Product Core that satisfies the current Workbench/Product contracts needed for source/database/API/registry execution.
2. Wire the existing Workbench Product runner to that maintained core and remove historical-core availability from normal Product preflight.
3. Run real small end-to-end Product smoke with production NLP + real OPUS.
4. Fix all execution, lineage, quality and coverage defects revealed by the real run.
5. Finish/pin the evidence-backed production configuration without restarting obsolete DOE branches unnecessarily.
6. Run the complete 90k+ public-domain corpus and retain the full research/evidence DB and dictionary artifacts.
7. Fix heavy-run defects and perform final full-corpus confirmation.
8. Build Windows installer/release package.
9. Perform clean-install end-to-end validation and release the complete Product artifact.

Every `продолжай` should advance as far along this path as feasible. Do not create artificial micro-stages.

## Historical recovery — archived, not active

All recovery code and evidence under `rocketdict/recovered/` and the `rocketdict-recover-*` commands remain preserved for audit/research. They are not deleted, because they contain useful provenance and tested fail-closed logic.

However:

- recovery is **off the Product critical path**;
- missing historical bytes do not block implementation;
- do not repeat exhausted Git/File Library/Drive/Actions/web archive searches by default;
- do not make exact historical identity a release criterion;
- newly implemented maintained Product code may reuse validated requirements/tests/evidence, but must identify itself as current Product code.

## Latest verified pre-directive checkpoint

Before the Product-line directive change, recovery/tooling HEAD was fully green with installed CLI smoke and **203 passed, 1 skipped**. That evidence remains valid for the archived recovery subsystem.

From this point forward, success is measured against `PRODUCT_TARGET.md`, not against recovery completeness.

## Immediate next task

Start implementing the maintained Product Core required by the existing Workbench bridge/contracts. The first coherent milestone should make a supported source go through maintained database bootstrap → immutable import → interpretation → live registry/API surface without any historical RocketDict package dependency, with regression tests and an end-to-end Product-facing proof.

Then continue directly toward real Stage8→25 execution, heavy validation and the installer.