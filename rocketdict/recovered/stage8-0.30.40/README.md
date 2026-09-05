# RocketDict 0.30.40 — exact recovery evidence

This directory is an **evidence namespace, not an active core checkout**.

On 2026-09-05 the surviving Stage8 overlay-prefix Actions artifact `9681838606` (`stage8-overlay-prefix`) was downloaded and unpacked. The decompressed tar prefix is exactly 51,590 bytes with SHA-256 `a6af982f442fdedadc6ba6bb9e91d7ca3b519e6d0f893b21537498741f7bf67a`; gzip EOF is absent, so the archive is intentionally treated as truncated evidence rather than a reconstructable source bundle.

Exactly two complete source members survive before the truncation boundary and both are now preserved here byte-for-byte:

- `src/rocketdict/__init__.py` — 502 bytes — SHA-256 `7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c`;
- `src/rocketdict/nlp/registry.py` — 29,072 bytes — SHA-256 `02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69`.

The package root proves `__version__ = "0.30.40"` and proves that this package expected `API_VERSION` from `rocketdict.api.contracts` and `RocketDictAPI` from `rocketdict.api.client`. The NLP registry proves the exact `spacy-registry/1.0` implementation, including deterministic model-tree SHA-256 support and read-only model inspection.

The next tar member is `src/rocketdict/lab/stage12_pilot.py` with declared size 51,356 bytes, but it is incomplete in the surviving prefix. No complete `rocketdict.api.contracts`, `rocketdict.api.client`, `rocketdict.api.cli`, structured callable mapping, or complete Stage8–19 implementation set is recovered here. Therefore these bytes cannot form a runnable Product core.

The same recovery record identifies a still-recoverable 343 MB offline OPUS runtime artifact and the successful real-OPUS gate artifact. They preserve accepted real-model/runtime evidence, including official OPUS archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, but they contain no missing RocketDict core source.

`recovery.json` is the machine-readable authority. Its `promotion_allowed=false`, `active_product_core_recovered=false`, and `runtime_blocker` fields are deliberate. Workbench CI hashes both preserved files and fails if this boundary is weakened or mutated.

Nothing in this directory authorizes Product execution. A real Product run requires an exact compatible RocketDict runtime that imports successfully and whose live Registry, API probe, structured callable metadata, binding metadata, execution contracts and quality PASS semantics all satisfy the Workbench fail-closed verifiers.
