# RocketDict — CURRENT authoritative continuation state

Date: 2026-09-05
Repository: `oss-lk/gerkonkv-site`
Branch: `main`

This is the primary continuation boundary for the active Product line.

## Non-negotiable rules

- Translation quality dominates speed/storage optimization.
- Never present fake/identity/mock/dictionary lookup as real MT.
- Never silently truncate a required long source/corpus.
- Never infer executable operations or quality PASS semantics from names/status strings.
- Never manufacture missing 0.30.40 source from older checkpoints, Stage6Y, research overlays or inferred signatures.
- Preserve failed experiments, immutable hashes and lineage boundaries.
- Keep the public repository project-only; no personal/user/account/private-conversation data.

## Product implementation status

The Workbench Product pipeline is already evidence-driven and resumable through Stage25:

1. immutable Product preflight;
2. exact-runtime API/registry probe;
3. structured callable binding + execution proof;
4. Stage8 → 10 → 12 → 14;
5. Stage15 hard quality gates;
6. Stage16 → 17 → Workbench18 aligned lexical extraction → Stage19;
7. real OPUS-backed unified Stage20;
8. Stage20 lexical-primary arbitration → pinned CEFR-J → exact CMUdict → Stage23;
9. Stage24 cards + set assembly;
10. Stage25 export.

Primary CLI: `rocketdict-product-run` (`init`, `advance`, `status`).

Do not build another orchestration layer. The current hard blocker is the missing complete exact-compatible RocketDict core/public API.

## Product evidence identities

- Product preflight: `rocketdict-workbench-product-preflight/2`
- Product state: `rocketdict-workbench-product-run/1`
- API probe: `rocketdict-core-api-surface-probe/2`
- Stage20→23 downstream: `rocketdict-workbench-product-downstream/2`

Required Stage15 gates:

- `rocketdict-numeric-symbol-preservation`
- `rocketdict-punctuation-preservation`
- `rocketdict-length-ratio-proxy`

Each gate must publish a valid execution contract and explicit PASS semantics before dispatch. Generic `status="ok"` is not PASS.

Correct post-gate dependency is:

`16 finalization → 17 alignment → Workbench18 aligned extraction → 19 sense induction`.

## Real OPUS identity

Accepted EN→RU artifact:

- URL `https://object.pouta.csc.fi/OPUS-MT-models/en-ru/opus-2020-02-11.zip`
- SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`
- CTranslate2 Marian
- acceptance compute type `float32`

Historical real-model gate remains valid evidence:

- 120 representative sentences
- 4,488 representative words
- Opticks SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`
- Opticks regex words 104,275

Do not reconstruct historical F96 challenge selection from coincident counts.

## Exact 0.30.40 recovery boundary

Evidence namespace:

`rocketdict/recovered/stage8-0.30.40/`

It is not an active core checkout.

Surviving truncated Stage8 artifact prefix:

- artifact `9681838606` / `stage8-overlay-prefix`
- decompressed tar-prefix bytes 51,590
- SHA-256 `a6af982f442fdedadc6ba6bb9e91d7ca3b519e6d0f893b21537498741f7bf67a`
- `gzip_eof=false`

Exact complete members preserved:

1. `src/rocketdict/__init__.py`
   - 502 bytes
   - SHA-256 `7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c`
   - proves version `0.30.40`
   - proves lazy public references to `rocketdict.api.contracts.API_VERSION` and `rocketdict.api.client.RocketDictAPI`.

2. `src/rocketdict/nlp/registry.py`
   - 29,072 bytes
   - SHA-256 `02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69`.

Next member `src/rocketdict/lab/stage12_pilot.py` is truncated (declared 51,356 bytes).

Historical materializer analysis proves the intended Stage8 overlay contained 19 research/translation files and **did not contain `rocketdict.api.*`**. Therefore restoring the missing seven overlay chunks alone cannot restore the complete base core/public API.

Current overlay recovery math:

- intended members: 19
- exact target bytes available: 2
- exact target bytes missing: 17

Exact 0.30.40 public API bytes still missing:

- `rocketdict.api.contracts`
- `rocketdict.api.client`
- `rocketdict.api.cli`

No real Product Stage8 dispatch has been claimed from the recovered namespace.

## Recovery tooling

Operational guide:

`rocketdict-workbench/docs/CORE_RECOVERY.md`

Implemented commands:

- `rocketdict-recover-core` — inspect one source directory/ZIP candidate;
- `rocketdict-recover-plan` — deterministic read-only base→0.30.40 plan;
- `rocketdict-recover-scan` — batch discovery/ranking of historical ZIP/checkouts.

`rocketdict-recover-scan` schema is now `rocketdict-workbench-core-recovery-scan/2` and consumes:

`rocketdict/recovered/checkpoint-catalog.json`

Catalog rules:

- exact SHA/size identity is distinct from filename matching;
- a known filename alone is recovery triage only;
- checkpoints with no proven archive filename receive no guessed pattern;
- all entries retain `promotion_allowed=false`.

Known exact archive identity:

- `RocketDict_CURRENT_COMPACT.zip`
- version `0.30.8`
- bytes `125875993`
- SHA-256 `f948a9b59e4deb7b00a606fdb88973dd9a435c087c132f32f03d2d0c863b51ac`
- manifest files 666
- historical archive validation recorded a full source project, installable wheel, spaCy model, full Opticks, object store, compressed working SQLite, installer, recovery tooling and audit.

Later catalog entries include historical 0.30.9 / 0.30.19 / 0.30.32 archive-name evidence and 0.30.29 / 0.30.34 checkpoint evidence without invented archive identities.

## Exhausted recovery surfaces

Machine-readable record:

`rocketdict/recovered/search-exhaustion-2026-09-05.json`

Already checked and currently closed:

- parentless GitHub upload root `442e09db...`: website only;
- observed deleted refs `rocketdict-opus-gate-public` and `rocketdict-pr-actions-run`: website/workflows only;
- likely historical `api/client.py` Git paths under `src/`, `rocketdict/src/`, `rocketdict/active_source/src/`: zero reachable commits;
- GitHub Releases in `gerkonkv-site` and `spacy-project-vault`: none;
- checked `spacy-project-vault/rocketdict-stage06-spacy-model`: no RocketDict source package;
- File Library: 0.30.29/Stage6T README + heavy evidence recovered, but no checkpoint ZIP/API source bytes;
- the two currently preserved Stage31 transcript files: only one real sandbox checkpoint link, the known 0.30.8 `RocketDict_CURRENT_COMPACT.zip`;
- current ephemeral recovery workspace: ten ZIPs scanned by size/SHA/member inventory.

Workspace ZIP result:

- ZIPs: 10
- with any RocketDict package `__init__.py`: 1
- with required public API source modules: 0
- with RocketDict wheel: 0
- with nested RocketDict checkpoint ZIP: 0
- complete core candidates: 0

The one package-root hit is `stage8-overlay-prefix.zip`, already classified as the known truncated 0.30.40 evidence.

Do not repeat these searches unless new objects/refs/files become available.

## Latest verified checkpoint

Current latest evidence/code commit before this handoff update:

`ff9018516d924d56de6e6c4d267a91e5b920a5a6` — `Record exhausted exact-core recovery search surfaces`

Its parent functional scanner/catalog checkpoint:

`30add956042f8c85e6c7fb9d1c70d319124f29ac` — `Bind recovery scanner to historical checkpoint catalog`

Latest verified GitHub Actions:

- workflow `RocketDict Workbench`
- run `33965240536`
- job `101304088386`
- Ubuntu 24.04
- Python 3.13.15
- compile success
- **159 passed, 1 skipped in 2.11s**

Earlier red scanner run remains preserved as failed-experiment evidence; its duplicate-root and corrupt-ZIP defects were fixed and regression-tested.

## Separate Stage6Y maintenance lineage

RocketDict 0.30.34 / LAB Stage6Y is a verified parallel maintenance checkpoint, not Product source replacement.

Key evidence:

- working SQLite 881,905,664 bytes
- working SHA-256 `a0128b802930d350679c7d135bea9197fb9e202d863260c31a68d49681fbeafb`
- canonical heavy SHA-256 `3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274`
- SQLite quick_check ok
- FK violations 0
- Alembic `8b4e7c2a91d0`
- lexical entries 35,743
- 301 packaged runtime files matched source byte-for-byte.

Do not overwrite Product with Stage6Y without exact source-level compatibility and full regression.

## Immediate next Product task

The next required input is **new provenance-verifiable full RocketDict checkpoint/core bytes**. Existing in-scope Git, Releases, current recovery ZIPs, retained transcripts and File Library evidence do not contain them.

When new bytes become available:

1. run `rocketdict-recover-scan` on the containing directory;
2. run `rocketdict-recover-core` on the strongest candidate;
3. run `rocketdict-recover-plan` and inspect every missing/exact replacement;
4. never infer missing 0.30.40 overlay/API bytes;
5. only for a complete exact-compatible runtime: Workbench doctor → real source import → immutable Product preflight → live registry/API probe → exact binding/execution contract;
6. perform the first genuine `rocketdict-product-run advance` Stage8 dispatch;
7. continue the same immutable Product state through Stage25 with real OPUS + pinned CEFR-J;
8. run the full 90k+ public-domain corpus without truncation and retain the complete translation/research evidence database.

Until such bytes exist, keep `exact_core_incomplete` explicit. Do not spend another development turn rebuilding orchestration that is already implemented.
