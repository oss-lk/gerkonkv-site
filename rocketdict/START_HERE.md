# START HERE — historical Stage 8 research handoff

> **Status (2026-09-05): historical research context, not the active continuation entrypoint.**
>
> The active Product directive is now [`PRODUCT_TARGET.md`](PRODUCT_TARGET.md) + [`CURRENT.md`](CURRENT.md): build forward to the complete installable RocketDict Product. Historical core/checkpoint recovery is not a Product prerequisite. The Stage8/F96 material below remains valuable evidence and must not be discarded, but it must not override the current global Product critical path.

## Purpose

RocketDict is a local/reproducible pipeline that turns English text/subtitles into a high-quality context-aware EN→RU learner dictionary. Quality is the priority; optimizations are not allowed to reduce output quality. Fake, identity, dictionary-only or synthetic MT must never be accepted as real translation.

The intended end-to-end product path is:

`ingestion/immutable source → structure/segmentation → language/NLP → context graph → real MT → glossary/context refinement → quality validation → bilingual alignment → lexical extraction → sense induction → sense translations → CEFR → pronunciation → examples → immutable dictionary cards/set → RocketEng/Anki/CSV/etc.`

The Stage 8 work broadened RocketDict into an **experimental/research product** that can run reproducible component/parameter matrices on one corpus, preserve all variants/failures, compare them, select Pareto survivors, and confirm winners on the full corpus.

## Corpus / heavy baseline

The canonical large test corpus is Isaac Newton's public-domain *Opticks*.

Historical heavy baseline facts:
- full corpus, no truncation;
- canonical historical regex count: **104,257 words** (the Project Gutenberg copy fetched by GitHub gate counted 104,275 with the gate's regex/version; do not silently conflate the two counting contracts);
- 216,351 contextual lexical candidates;
- 35,743 lexical entries;
- 43,073 wordforms;
- 104,078 word occurrences;
- lost tokens = 0;
- canonical immutable heavy SQLite SHA-256: `3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274`.

The historical working heavy database was derived from that snapshot. Never modify the immutable baseline in place.

## Real model / runtime

Official EN→RU model:
- release: `opus-2020-02-11.zip`;
- URL: `https://object.pouta.csc.fi/OPUS-MT-models/en-ru/opus-2020-02-11.zip`;
- official ZIP SHA-256 observed by successful GitHub run: `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`;
- model NPZ SHA-256: `c92e6575c8ca7816926ca045149e8376758d39b24d6c228d2c685cc9a623226b`;
- vocab SHA-256: `884159dda0857b7b3dd92d6b6ac1d000ee7d34cdf728c1a4c6c1e92a457d9f6d`;
- model layout must be discovered from `decoder.yml` (`models[]`, `vocabs[]`), not by assuming `model.npz`.

Runtime used successfully on GitHub:
- Python 3.13;
- CTranslate2 4.8.1;
- SentencePiece 0.2.2;
- NumPy 2.5.2;
- PyYAML 6.0.3;
- setuptools 84.0.0;
- compute type for quality acceptance: **float32**.

GitHub real-model gate run: **32991296384**, conclusion `success`.
It translated 120 representative sentences / 4,488 words of *Opticks* with real OPUS. Example smoke:
`The glass plate is 5/62 parts of an inch thick.` → `Стеклянная пластина толщиной 5/62 дюйма.`

## Important Stage 7/8 fixes already made

Do not reintroduce these defects:

1. **Stage 7C real-wheel RECORD parser**: a real setuptools wheel may contain vendored nested `.dist-info/RECORD`. Only the primary top-level distribution `.dist-info/{METADATA,WHEEL,RECORD}` defines the wheel itself.

2. **Read-only preflight**: diagnostic `preflight` must not write evidence into operational SQLite.

3. **Planner/service propagation**: `split_atomic_above_preferred` must actually propagate through `TranslationService` into the planner.

4. **Long atomic units**: very long 300+ word units can be severely compressed/truncated by OPUS. Preferred-budget splitting materially improves this.

5. **Numeric evaluator**: numeric integrity contract **v3.2** must correctly handle fractions, ordinals, grouped thousands, Russian decimal comma, licensed spelled-number normalization, old ordinal forms and Newton typography.

6. **Numeric islands are not a proven solution**: keep `numeric-islands-v1` as an experimental/fail-closed negative branch unless new evidence proves otherwise.

7. **Tables are structurally different from prose**: `table-cells-v1` preserves table geometry/numeric-only cells and sends textual cells to MT.

## Research architecture

Stage 8 introduced a separate append-only **Research Vault SQLite** for:

`corpus/version → exact component stack/config → experiment trial → source unit → all translation candidates → selected output → quality metrics → resource metrics → failures → comparisons`.

Required properties already implemented/tested include operational-DB immutability during export, append-only evidence, idempotent repeated export, retention of all candidates, deterministic shard merge and pairwise comparison on common source units.

## Historical experimental frontier

The deterministic Stage 8 challenge selection was approximately 5,000 words and intentionally over-sampled positional, numeric, long and critical-symbol cases.

The historically best measured structural branch was **F96**, but it still failed the zero-numeric-loss rule with three numeric mismatches while having zero critical-symbol, length, empty-output and backend-error failures.

That historical frontier remains evidence. **Do not restart from F96 merely because this file says so.** Under the current Product directive, reuse the evidence where relevant and continue from the maintained Product implementation/contracts toward the global release criteria.

## Current use of this file

Use this document to preserve:

- corpus identities/counting distinctions;
- OPUS/runtime identities;
- known evaluator/planner defects;
- negative experimental results;
- Research Vault semantics;
- quality principles.

Do **not** use its old stage-by-stage continuation instructions as the active project plan.

## Operating rules retained by the Product line

- Quality > speed.
- No silent truncation of the 104k corpus.
- No fake MT acceptance.
- No weakening acceptance thresholds merely to make a gate green.
- Distinguish model failure from evaluator failure.
- Preserve failed experiments.
- Use exact hashes/model revisions/config identities.
- Read-only commands must be physically/logically read-only.
- Prefer resumable/sharded long jobs where useful.

## Privacy

This handoff is public. It intentionally contains no personal profile, location, account information, unrelated project history, private conversations, credentials or secrets. Do not add such information later.