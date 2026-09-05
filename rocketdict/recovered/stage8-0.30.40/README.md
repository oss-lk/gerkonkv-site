# RocketDict 0.30.40 — exact recovery evidence

This directory is an **evidence namespace, not an active core checkout**.

On 2026-09-05 the surviving Stage8 overlay-prefix Actions artifact was recovered and unpacked far enough to verify two complete source members byte-for-byte:

- `src/rocketdict/__init__.py` — SHA-256 `7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c`;
- `src/rocketdict/nlp/registry.py` — SHA-256 `02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69`.

The package root is preserved here because it is small and directly proves the 0.30.40 public-package identity. It states `__version__ = "0.30.40"` and lazily exports `API_VERSION` from `rocketdict.api.contracts` and `RocketDictAPI` from `rocketdict.api.client`.

The exact NLP registry is hash-addressed in `recovery.json` and remains retrievable from Actions artifact `9681838606`; it is not copied into the active source tree. The next tar member, `src/rocketdict/lab/stage12_pilot.py`, is incomplete in the surviving prefix, so the prefix cannot reconstruct the complete core.

The same recovery pass also verified that the 343 MB offline OPUS runtime artifact is still downloadable and contains the accepted model/runtime dependencies but **not** RocketDict core source. The real-OPUS gate artifact is also recoverable and preserves the successful real-model evidence.

Read `recovery.json` for hashes, artifact identities and the exact boundary. Nothing in this directory authorizes promotion of reconstructed source into Product execution. A real Product Stage8 call still requires a compatible core runtime whose live Registry, API callable metadata and public execution contract pass the Workbench fail-closed verifiers.
