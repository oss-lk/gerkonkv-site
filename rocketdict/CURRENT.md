# RocketDict — CURRENT authoritative continuation state

Date: 2026-09-06
Repository: `oss-lk/gerkonkv-site`
Branch: `main`

## Active directive

The active development line is **Product completion**, not historical recovery.

Authoritative global target: [`PRODUCT_TARGET.md`](PRODUCT_TARGET.md).

Historical checkpoint/core recovery is frozen as audit/research tooling. It is not a prerequisite, blocker, or default next task. Do not search for old archives or attempt to reconstruct missing 0.30.x source unless the user explicitly asks for historical recovery.

The development rule is: **preserve history, build forward, finish the installable Product.**

## Global result

RocketDict must become a locally installable Product that turns supported English text/subtitle input into a high-quality context-aware EN→RU learner dictionary/card set using production NLP and real MT, preserves research/quality evidence, completes the full downstream lexical/sense/CEFR/pronunciation/examples/cards/export path, survives a complete 90k+ public-domain corpus run without silent truncation, and passes a clean Windows install/end-to-end smoke test.

Anything short of that is an intermediate checkpoint.

## Maintained Product Core now exists

The former missing-core critical blocker is closed.

`rocketdict-product-core/` is a new maintained implementation, version `1.0.0.dev1`, installed as the Python package `rocketdict`. It is explicitly **not recovered historical code**.

It currently owns:

- durable SQLite bootstrap/schema and immutable object storage;
- immutable source import;
- TXT/SRT/VTT/ASS/SSA interpretation without silent subtitle→TXT downgrade;
- public `rocketdict.api` contracts/CLI/live registry;
- fail-closed runtime discovery for production NLP and OPUS;
- native Stage8 production spaCy NLP;
- Stage10 contextual structure;
- Stage12 real offline OPUS EN→RU through CTranslate2 Marian float32;
- Stage14 conservative refinement boundary preserving real-MT lineage;
- three Stage15 hard quality gates;
- Stage16 translation approval;
- Stage17 alignment;
- native Stage18 aligned lexical extraction;
- native Stage19 deterministic sense induction and durable lexical/sense tables.

`rocketdict-assets` provisions the official OPUS archive into a verified local CTranslate2 asset. The accepted archive SHA-256 remains:

`798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`

The asset builder discovers the actual OPUS Marian layout from `decoder.yml` + NPZ + SentencePiece evidence rather than assuming a fixed weight filename. The runtime recomputes the entire provisioned payload-tree SHA-256 before accepting the model; changed model/SPM/config bytes, extra files or non-float32 manifests fail closed.

## First real maintained-core execution evidence

GitHub workflow `RocketDict Product Core`, run `34028203744`, real-runtime job `101472903537` executed the maintained core with real production dependencies:

- Python 3.12.14;
- spaCy 3.8.16;
- `en_core_web_sm` 3.8.0;
- CTranslate2 4.8.2;
- SentencePiece 0.2.2;
- official OPUS archive exact SHA verified;
- CTranslate2 asset payload: 313,227,941 bytes / 5 files;
- payload-tree SHA-256 `35c5982497fadf88d1748a67f969d4fd8d3ed8babc3c9bc1141223dbfaf0f3ce`.

The real smoke built an ordinary Workbench project and ran the maintained public API through Stage19. Evidence:

- Stage8: 10 real spaCy tokens, coverage complete;
- Stage10: context coverage complete;
- Stage12: `CTranslate2Marian`, `float32`, `real_mt=true`, `network_used=false`, 0 empty outputs, 0 backend errors;
- observed Stage12 target: `Свет проходит через стеклянный призм и образует спектр` for source `Light passes through a glass prism and forms a spectrum`;
- Stage14 retained real-MT lineage;
- all three Stage15 hard gates passed with zero failures;
- Stage16 approved the revision;
- Stage17 alignment coverage complete, zero uncovered segments;
- Stage18: 6 eligible content tokens → 6 aligned lexical occurrences / 6 lexical entries, zero uncovered;
- Stage19: 6 durable lexical senses, coverage complete, singleton policy `singleton-safe-v1-audited`.

The smoke explicitly rejects empty/non-Cyrillic/identity Stage12 output; therefore this is real MT execution evidence, not a contract-only mock.

The same current Product Core workflow also runs all dependency-light Product Core tests and the full Workbench regression suite against the newly installed maintained `rocketdict` package.

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

## Existing Workbench Product work to reuse

Workbench contains substantial Product logic that remains valuable downstream:

- Product profile/preflight and immutable Product-run state;
- exact callable binding/execution proofs;
- Stage15 aggregate PASS proof machinery;
- post-gate sequencing;
- real lexical OPUS Stage20 provider/arbitration;
- pinned CEFR-J integration;
- CMUdict exact pronunciation path;
- sense-scoped examples;
- Stage24 resumable cards/set assembly;
- Stage25 export;
- immutable evidence and fail-closed regression contracts.

The next job is to make those Stage20–25 capabilities operate on the maintained Product Core schema/API, eliminating remaining historical ORM/helper assumptions rather than replacing the proven algorithms.

## Remaining architectural migration

One Workbench path still deserves explicit cleanup: the legacy Workbench Stage18 helper contains imports against the old rich ORM model even though the maintained core now has native `product.stage18.run` and real Stage18 evidence. The Product critical path should call the maintained operation directly; do not rebuild the old ORM solely to keep that helper alive.

Likewise, current Workbench Stage20–25 helper implementations were written against historical database model classes. Preserve their validated policies/evidence semantics, but migrate execution/storage to the maintained schema/API.

## Real model baseline

Accepted real EN→RU baseline:

- OPUS `opus-2020-02-11.zip`;
- SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`;
- CTranslate2 Marian;
- quality acceptance compute type `float32`;
- processing offline after explicit provisioning.

## Hard quality gates

Approved translation evidence requires all current Stage15 hard gates:

- numeric/symbol preservation;
- punctuation preservation;
- length-ratio proxy.

Empty translation outputs and backend errors are release blockers. Gate PASS semantics remain explicit/exact/machine-readable.

## Heavy validation target

Use a complete public-domain corpus of at least 90,000 words. The established canonical corpus is Newton's *Opticks* (~104k words depending on the exact counting contract).

Final heavy acceptance requires:

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

The result is not a green test suite or source archive alone.

The final release must include a practical Windows installation/distribution path and pass a clean-install end-to-end smoke test. After installation, a user must be able to process a supported source and receive the final dictionary/export without manually rebuilding stage state.

## Active critical path

1. Migrate the remaining Workbench Stage18 call path to maintained native Stage18 execution.
2. Implement/migrate Stage20 sense translation against maintained Stage19 lexical senses while retaining real OPUS evidence, arbitration rules and immutable identities.
3. Implement/migrate Stage21 CEFR-J, Stage22 CMUdict, Stage23 examples, Stage24 cards/set and Stage25 export on the maintained schema/API.
4. Make `rocketdict-product-run` drive the maintained source → Stage25 path as one resumable workflow using real assets.
5. Run increasingly substantial real corpora, fix lineage/quality/coverage defects, then pin the evidence-backed production configuration.
6. Run the complete 90k+ public-domain corpus and retain the full research/evidence DB and dictionary artifacts.
7. Fix heavy-run defects and perform final full-corpus confirmation.
8. Build the Windows installer/release package.
9. Perform clean-install end-to-end validation and release the complete Product artifact.

Every `продолжай` should advance as far along this path as feasible. Do not create artificial micro-stages.

## Historical recovery — archived, not active

All recovery code/evidence under `rocketdict/recovered/` and `rocketdict-recover-*` commands remain preserved for audit/research only.

- recovery is off the Product critical path;
- missing historical bytes do not block implementation;
- do not repeat exhausted recovery searches by default;
- do not make exact historical identity a release criterion;
- newly implemented maintained Product code may reuse validated requirements/tests/evidence, but must identify itself as current Product code.

## Immediate next task

Continue forward from the proven real Stage19 boundary. Remove the last active old-ORM Stage18 bridge, then adapt the already developed Stage20–25 Product semantics to the maintained core and prove a real end-to-end source→export run before beginning the large acceptance corpus.
