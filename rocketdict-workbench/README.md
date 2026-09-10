# RocketDict Workbench

Product-first, evidence-driven local control plane over the maintained RocketDict Product Core.

The Workbench is the user-facing resumable orchestration layer for the **current maintained core**. Historical 0.30.x recovery remains useful provenance/compatibility evidence under `rocketdict/recovered/`, but it is not the Product critical path.

## Product path

`rocketdict-product-run` is the primary Product entry point. The maintained sequence is:

1. immutable Product preflight;
2. live maintained-core API/registry contract probe;
3. Stage8 production NLP → Stage10 context → Stage12 real OPUS → Stage14;
4. Stage15 hard-quality gates;
5. Stage16 approval → Stage17 alignment → Stage18 lexical extraction → Stage19 senses;
6. real OPUS-backed Stage20 contextual lexical processing/arbitration;
7. pinned CEFR-J → exact CMUdict → Stage23 sense-scoped examples;
8. Stage24 immutable cards/card set;
9. Stage25 JSON export and replay verification.

Typical entry points:

```bash
rocketdict-product-run --core-pythonpath /path/to/rocketdict-product-core init ./project
rocketdict-product-run --core-pythonpath /path/to/rocketdict-product-core advance ./project \
  --state ./project/experiments/product-run/<fingerprint>.json \
  --model-path /path/to/opus-en-ru-ct2 \
  --cefrj-asset /path/to/cefrj-vocabulary-profile-1.5.csv
rocketdict-product-run status ./project --state ./project/experiments/product-run/<fingerprint>.json
```

`advance` resumes as far as immutable inputs and proven contracts allow. Missing required external assets are explicit blockers. Runtime/contract drift is a correctness failure rather than something Workbench guesses around.

The older `rocketdict-workbench` CLI remains available for project/import/research/diagnostic operations.

## Product invariants

Product Mode is deliberately stricter than the research surface:

- real EN→RU MT only; fake/identity/mock/dictionary substitution is never Product translation;
- no silent source truncation;
- no target-side insertion of missing numbers or fabricated structure;
- no weakening hard gates merely to make a run green;
- no reuse of completed evidence after output-affecting input/runtime/configuration drift;
- no destructive overwrite of immutable successful stage evidence;
- mechanical quality gates are necessary but not sufficient for Product promotion when semantic review disagrees.

## Immutable preflight and resumability

Preflight freezes source identity, durable import/document IDs, exact core/API versions, registry/profile identities, selected implementations/parameters, hard-gate identity and Product policy.

The unified Product-run state is bound to that immutable preflight fingerprint. Stage execution evidence includes exact callable/contract identity, canonical request/result hashes and durable output revision IDs.

Completed Stage24 card results are journaled durably; Stage25 consumes the exact immutable card-set identity. Re-entry after a successful run verifies and reuses the same Stage25 export instead of reconstructing synthetic state.

## Stage12 translation boundary

Production translation uses the pinned official OPUS EN→RU `opus-2020-02-11` archive:

- archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`;
- CTranslate2 Marian;
- CPU acceptance compute type `float32`;
- maintained planner `rocketdict-stage12-protected-split/8`.

Primary Stage12 real-OPUS output is immutable and cache-reusable. Selection/rescue controls belong to a second immutable Stage12 selection run and do not alter the primary translation identity.

Selective source-derived resegmentation rescue remains **fail-closed / disabled by default**. Research on the complete pinned *Opticks* corpus proved that it can reduce a numeric hard-failure count mechanically while simultaneously degrading Russian semantics; therefore it is not Product policy.

## Stage15 hard-quality boundary

The required Product gates are:

- `rocketdict-numeric-symbol-preservation`;
- `rocketdict-punctuation-preservation`;
- `rocketdict-length-ratio-proxy`.

Stage15 numeric/symbol integrity currently uses `rocketdict-maintained-numeric-integrity/5`, including fail-closed numeric prime/unit semantics.

Stage16 is unlocked only by a complete aggregate Stage15 PASS fingerprint. A known hard failure remains blocked until a source/model/planner mechanism is proven; it is not hidden by post-hoc repair.

## Structure-aware translation

The maintained path distinguishes source-owned document structure from linguistic content:

- block Gutenberg section identifiers are preserved byte-exact only in the narrow block-start class;
- `_Exper._/_Obs._/_Qu._` block labels use narrow real-OPUS selection rather than identity passthrough;
- ASCII table geometry and alpha-free numeric/symbolic cells remain source-owned while logical text groups use real OPUS;
- inline references and ordinary prose stay on the linguistic MT path.

These narrow classes do not license generic numeric islands, arbitrary punctuation splitting or broad n-best fallback.

## Downstream evidence

Stage20 is real OPUS-backed and retains raw candidate/selection evidence. Stage21 binds pinned CEFR-J evidence with the maintained POS-aware path. Stage22 accepts exact CMUdict pronunciation evidence without generated authoritative fallback. Stage23 examples are sense-scoped. Stage24/25 retain immutable card/set/export identities.

## Verification status

The maintained core + Workbench path is no longer blocked on recovering an exact historical 0.30.40 runtime. Real-runtime CI verifies both:

- direct maintained-core Stage8→25;
- unified `rocketdict-product-run` source→Stage25 plus replay.

Large-corpus quality validation is performed on the complete pinned Project Gutenberg *Opticks* source, SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`.

For the latest exact run/artifact IDs and current hard-failure frontier, use repository L1 [`../PROJECT_STATE.md`](../PROJECT_STATE.md); raw Actions artifacts and SQLite evidence remain authoritative L3.

## Current hard boundary

Do not rebuild historical orchestration already replaced by the maintained core.

The active Product sequence is:

1. drive complete-corpus translation hard failures to zero without semantic regressions or synthetic repair;
2. rerun direct/unified real Stage8→25 whenever a Product translation mechanism changes;
3. extend the same heavy acceptance through alignment, lexical/sense/card/export outputs;
4. build and validate the Windows distribution and clean-install workflow.

Research branches may be broad, but Product promotion remains quality-first, source-derived, immutable and evidence-backed.
