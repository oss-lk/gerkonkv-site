# RocketDict — global product target

Date: 2026-09-05
Status: **authoritative Product target**

This file defines the result the active development line must deliver. Historical source/checkpoint recovery is not on the critical path and must never block Product implementation or release.

## Global outcome

RocketDict must become a complete, locally installable product that converts English text or subtitle input into a high-quality, context-aware EN→RU learner dictionary and exportable card set.

The product must process the real source, preserve source coverage, use real NLP and real MT, retain quality/research evidence, and produce usable lexical entries rather than a translation dump.

Quality has priority over speed and storage optimization.

## Required end-to-end path

The production path is:

`immutable source ingestion → format/encoding interpretation → structural segmentation → production NLP → contextual structure/graph → real EN→RU MT → glossary/context refinement → hard quality validation → bilingual alignment → lexical extraction → sense induction → sense translation → CEFR → pronunciation → examples → immutable dictionary cards/set → exports`

The final product must execute this as one resumable workflow rather than requiring manual assembly of stage outputs.

## Input requirements

At minimum:

- ordinary English text;
- subtitle-oriented input supported by the Product importer/interpreter;
- no silent source truncation;
- immutable source identity/hash retained;
- deterministic interpretation of the selected source version;
- visible failure for unsupported/corrupt input instead of silent degradation.

## NLP requirements

Final Product output may not rely on code-only/tokenizer-only NLP.

A production NLP implementation must supply the linguistic evidence needed downstream: token/word structure, lemma/POS/dependency/context evidence and the entity/structure information required by lexical extraction and alignment.

Research may compare multiple NLP implementations, but release must pin a validated production configuration.

## Translation requirements

- Real EN→RU MT only.
- Fake, identity, mock, dictionary-substitution or synthetic translation may never be accepted as Product translation.
- Processing is offline after assets are installed/provisioned.
- The accepted OPUS EN→RU artifact remains the known real-model baseline:
  - `opus-2020-02-11.zip`
  - SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`
  - CTranslate2 Marian
  - quality acceptance compute type `float32`.
- Model/layout discovery must be evidence-driven; do not assume filenames that are not guaranteed by the model metadata.
- Long units must not be silently compressed/truncated by the planner or backend.

## Hard translation-quality gates

A Product run cannot continue as approved translation evidence with unresolved hard failures.

At minimum the existing hard gates remain mandatory:

- numeric/symbol preservation;
- punctuation preservation;
- length-ratio proxy.

Numeric evaluation uses the established semantics that distinguish evaluator defects from real translation defects. A gate may not be weakened merely to make a run pass.

Empty outputs and backend-error outputs are release blockers.

## Lexical/dictionary requirements

The final output is a learner dictionary, not a sentence list.

The Product path must provide:

- complete lexical extraction coverage for the accepted source/alignment scope;
- contextual lemma/POS information;
- sense induction/selection grounded in aligned context;
- EN→RU sense translation with explicit revision/approval lineage;
- CEFR-J from the pinned licensed dataset, not an invented frequency heuristic;
- pronunciation from exact accepted pronunciation data (CMUdict path already implemented); generated pronunciation fallback is not accepted as authoritative evidence;
- sense-scoped examples;
- immutable card/set assembly;
- exports suitable for downstream use, including the already supported structured export path and other formats retained by the Product implementation.

Duplicate/missing sense coverage and silently uncovered lexical items are release blockers.

## Research requirements

RocketDict remains an experimental/research product internally, but research exists to improve the final Product rather than postpone it indefinitely.

Required research behavior:

- preserve tested component/config combinations and negative branches;
- retain immutable configuration/model/source identities;
- preserve failures rather than overwriting them;
- compare candidates on common source units where possible;
- select quality-first survivors;
- promote only evidence-backed configurations into Product defaults.

Historical experiments remain useful evidence. Reconstructing missing historical source bytes is **not required** to finish the Product.

## Heavy acceptance corpus

The release candidate must be tested on a complete public-domain corpus of at least 90,000 words. The canonical established corpus is Newton's *Opticks* (~104k words depending on the exact counting contract).

Heavy-run requirements:

- process the complete selected corpus; no silent clipping to a sample;
- lost source tokens/content = 0 under the selected interpretation contract;
- empty translation outputs = 0;
- backend translation errors = 0;
- unresolved hard numeric/symbol/punctuation/length failures = 0 for approved translation evidence;
- downstream approved alignment/lexical/sense/card/export coverage must be complete for the Product-defined scope;
- all failures discovered by the heavy run must be investigated and fixed or explicitly demonstrated to be evaluator/input-policy defects before release;
- after fixes, rerun enough of the pipeline to prove the regression is gone, culminating in a complete final heavy confirmation.

The heavy run must retain the resulting research/evidence database and final dictionary/export artifacts.

## Installation/release requirements

The global result is not merely a green Python test suite.

A release candidate must include a practical local Windows installation/distribution path and pass a clean-install smoke test.

The installation must provision or clearly bind the required runtime/assets without silently replacing real model components with degraded fallbacks.

After installation, a user must be able to take a supported text/subtitle source through the Product workflow and obtain the final dictionary/export without reconstructing development-stage state manually.

Release artifacts must contain the code/configuration/assets or deterministic asset-install instructions required by the supported offline-processing contract.

## Reliability requirements

- resumable long-running processing;
- deterministic identities for source/config/model/result evidence;
- no silent destructive overwrite of immutable research baselines;
- read-only diagnostics are actually read-only;
- explicit error states instead of false success;
- database integrity and migration checks remain part of release validation;
- tests must cover the real production path, not only isolated mocks.

## Historical recovery policy

All existing recovery code/evidence is retained for audit/research purposes only.

Rules for the active Product line:

- do not search for missing historical checkpoint bytes unless the user explicitly asks for historical recovery;
- do not make exact 0.30.34/0.30.40 recovery a prerequisite for Product work;
- do not delay Product implementation waiting for old archives;
- do not claim newly implemented code is recovered historical code;
- reuse validated requirements, algorithms, tests, model identities and evidence where appropriate, but implement whatever Product code is currently missing.

In short: **preserve history, but build forward.**

## Current critical path

1. Replace the active Workbench dependency on an unavailable historical RocketDict core with a maintained Product Core implementation that satisfies the current public contracts needed by the Product runner.
2. Make source import, interpretation, database lifecycle, live registry/API and Stage8→25 execution self-contained in the maintained Product tree.
3. Run a real small end-to-end Product smoke test with production NLP + real OPUS.
4. Close all execution/contract/data-lineage defects discovered by that run.
5. Run the deterministic challenge/screening evidence needed to select/pin Product defaults without restarting obsolete experiments from scratch.
6. Run the complete 90k+ public-domain corpus and retain the full research/evidence database.
7. Fix heavy-run defects and perform final full-corpus confirmation.
8. Build the Windows release package/installer and perform clean-install end-to-end validation.
9. Release the complete Product artifact together with its pinned model/data identities and validation report.

## Definition of done

RocketDict is done for this development goal only when all of the following are true:

- the Product installs locally on the supported Windows target;
- supported text/subtitle input runs end-to-end without manual stage reconstruction;
- production NLP and real MT are used;
- translation hard gates pass on the accepted final heavy run;
- complete learner-dictionary/card/export output is produced for the defined scope;
- the full 90k+ corpus has been processed without silent truncation;
- the heavy-run evidence/research database is retained;
- discovered critical defects have regression coverage;
- clean-install smoke succeeds;
- release artifacts and continuation/audit documentation are complete.

Anything short of that is an intermediate development checkpoint, not the requested global result.
