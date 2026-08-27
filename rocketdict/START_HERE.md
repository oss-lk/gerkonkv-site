# START HERE — RocketDict Stage 8 continuation

## Purpose

RocketDict is a local/reproducible pipeline that turns English text/subtitles into a high-quality context-aware EN→RU learner dictionary. Quality is the priority; optimizations are not allowed to reduce output quality. Fake, identity, dictionary-only or synthetic MT must never be accepted as real translation.

The intended end-to-end product path is:

`ingestion/immutable source → structure/segmentation → language/NLP → context graph → real MT → glossary/context refinement → quality validation → bilingual alignment → lexical extraction → sense induction → sense translations → CEFR → pronunciation → examples → immutable dictionary cards/set → RocketEng/Anki/CSV/etc.`

The current work is deliberately broader than a single production path: Stage 8 turns RocketDict into an **experimental/research product** that can run reproducible component/parameter matrices on one corpus, preserve all variants/failures, compare them, select Pareto survivors, and only then confirm the winners on the full corpus.

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

The current working heavy database used by Stage 8 was derived from that snapshot. Never modify the immutable baseline in place.

## Real model / runtime — blocker is solved

The old blocker (this environment could not download official OPUS/model/runtime bytes) is solved through GitHub Actions.

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

1. **Stage 7C real-wheel RECORD parser**: a real setuptools wheel may contain vendored nested `.dist-info/RECORD`. Only the primary top-level distribution `.dist-info/{METADATA,WHEEL,RECORD}` defines the wheel itself. The old verifier falsely rejected setuptools for having a second vendored RECORD.

2. **Read-only preflight**: diagnostic `preflight` must not write evidence into the operational SQLite. Separate non-persisting `inspect_profile()` from persisting execution `check_profile()` for both NLP and translation registries. This was verified on the heavy DB with a real 313 MB OPUS model + managed runtime: repeated preflight left SQLite SHA and evidence row counts unchanged.

3. **Planner/service propagation**: `split_atomic_above_preferred` must actually propagate through `TranslationService` into the planner. A previous experimental direct planner call worked while production service silently ignored the knob.

4. **Long atomic units**: very long 300+ word units can be severely compressed/truncated by OPUS. Preferred-budget splitting materially improves this and is part of the active DOE.

5. **Numeric evaluator**: naive regex comparison produced false failures. The current integrity contract is **numeric v3.2** and must correctly handle fractions, ordinals, grouped thousands, Russian decimal comma, spelled-number licensing (`sixty → 60`), old ordinal `42d → 42-й`, and Newton typography such as `1'699`, `0'000625`, `4'27`.

6. **Numeric islands are not a proven solution**: OPUS does not reliably preserve arbitrary placeholder grammars, especially multiple markers. Keep `numeric-islands-v1` as an experimental/fail-closed negative branch unless new evidence proves otherwise.

7. **Tables are structurally different from prose**: `table-cells-v1` preserves table geometry/numeric-only cells and sends only textual cells to MT. A four-table probe achieved numeric integrity 100% and the production structural executor/planner were extended accordingly.

## Research architecture

Stage 8 adds a separate append-only **Research Vault SQLite**. Its role is not to replace operational RocketDict DB but to materialize experimental evidence:

`corpus/version → exact component stack/config → experiment trial → source unit → all translation candidates → selected output → quality metrics → resource metrics → failures → comparisons`.

Required properties already implemented/tested:
- operational DB remains byte-for-byte unchanged by export;
- append-only evidence (UPDATE/DELETE blocked);
- repeated export idempotent;
- all candidates retained, primary aggregates calculated on selected outputs;
- completed and failed/pruned Stage 28 trials can be materialized;
- independent shard vaults can be merged deterministically;
- pairwise comparisons are possible on common source units.

A compressed/current Research Vault payload and source payload are being materialized under `rocketdict/` in this repository. See `rocketdict/STATE.json` and `rocketdict/RESEARCH_STATUS.md`.

## Current experimental frontier

The deterministic Stage 8 challenge selection is approximately 5,000 words from latest heavy segmentation and intentionally over-samples positional, numeric, long and critical-symbol cases.

Completed real-OPUS variants include A/B/C/D/E and a later F96 refinement. The currently best measured structural branch is **F96** (same table-aware E design with a smaller preferred token budget), but it still fails the zero-numeric-loss acceptance rule.

Latest measured F96 metrics:
- 5,000 source words;
- 109 source occurrences;
- 168 inference chunks;
- 141.055 s;
- peak RSS 906,489,856 bytes;
- empty outputs = 0;
- backend errors = 0;
- numeric mismatches = **3**;
- critical-symbol mismatches = 0;
- length-ratio mismatches = 0;
- identity rate ≈ 0.06422;
- Cyrillic rate = 0.99;
- Cyrillic alpha share ≈ 0.97966;
- gate = FAIL only because numeric mismatch count must be 0.

The three remaining numeric integrity cases are the next research target. Recent probes include n-best investigation. One known n-best example (`15 Min. that of the exterior 3 Degr.`) has top hypotheses that retain both 15 and 3, showing that candidate selection constrained by integrity may solve some cases without rewriting target text. Another large-number example loses/extensively normalizes very large literals across all n-best hypotheses, so it likely needs a different integrity/structural strategy.

## Exact next task

A new chat should **not restart Stage 8 from A**.

Continue from F96 and the saved n-best/critical probes:

1. Load `rocketdict/RESEARCH_STATUS.md`, `rocketdict/STATE.json`, Research Vault and current source snapshot.
2. Identify the exact 3 F96 numeric failures from the saved journal/receipt or re-evaluate the identical deterministic selection using numeric-integrity/3.2.
3. Classify each failure into: structural reference (Fig/Obs/section), ordinary measurement/number, or extreme scientific/table numeric sequence.
4. Evaluate a quality-first **n-best integrity-aware selector** as a new DOE branch. It may select another model hypothesis only if it passes the same semantic/quality constraints; it must never fabricate/append a missing literal.
5. For failures where no n-best hypothesis preserves all required literals, test a separate deterministic structural/literal handling strategy. Keep it fail-closed and evidence-backed.
6. Re-run the exact same ~5k challenge set. Acceptance requires numeric=0, critical=0, empty=0, backend_errors=0, length_failures=0, while preserving language/identity quality.
7. Only then promote survivors to a 10k stratified screening campaign.
8. Use Research Vault for every trial, including negative branches.
9. After 10k screening/Pareto selection, confirm only survivors on the full 104k+ corpus.
10. Full 104k confirmation is not the end: continue downstream stages through glossary/refinement, alignment, lexical senses, sense translations, CEFR, pronunciation, examples, cards and export, with research comparisons retained.

## Operating rules

- Quality > speed.
- No silent truncation of the 104k corpus.
- No fake MT acceptance.
- No weakening acceptance thresholds merely to make a gate green.
- Distinguish model failure from evaluator failure.
- Preserve failed experiments in Research Vault.
- Use exact hashes/model revisions/config identities.
- Read-only commands must be physically/logically read-only.
- Prefer resumable/sharded GitHub jobs; merge research shards deterministically.
- If a long GitHub run is the only remaining action, do not idle a chat: tell the operator when to return in Moscow time. Otherwise continue immediately.

## Privacy

This handoff is public. It intentionally contains no personal profile, location, account information, unrelated project history, private conversations, credentials or secrets. Do not add such information later. Keep all public evidence project-only.
