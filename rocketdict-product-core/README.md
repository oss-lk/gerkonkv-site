# RocketDict Product Core

Status: maintained forward Product runtime (`1.0.0.dev1`).

This package is the current implementation of the RocketDict core. It is **new maintained code**, not a reconstruction of an unavailable historical 0.30.x package.

## Proven boundary

The maintained core owns source ingestion/interpretation and the Product execution path through Stage19:

`source → Stage8 production spaCy NLP → Stage10 context → Stage12 real OPUS EN→RU → Stage14 refinement boundary → Stage15 hard gates → Stage16 approval → Stage17 alignment → Stage18 lexical extraction → Stage19 sense induction`

The real-runtime GitHub gate provisions `en_core_web_sm 3.8.0` and the official OPUS `opus-2020-02-11` model, converts the latter to CTranslate2 float32, then executes the path above through the public `rocketdict.api` surface. Fake/identity MT is not accepted.

## External production assets

Processing is offline once assets are provisioned.

The accepted OPUS archive is pinned to SHA-256:

`798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`

Build a verified local asset from an already downloaded archive:

```text
rocketdict-assets build-opus-en-ru opus-2020-02-11.zip /path/to/opus-asset
```

Set `ROCKETDICT_OPUS_ASSET_DIR` to that directory. The loader verifies the official archive identity recorded in the manifest and recomputes the complete local payload-tree SHA-256 before treating the model as available.

Production NLP requires an installed accepted spaCy English model; the current baseline is `en_core_web_sm 3.8.0` (`en-sm`).

## CLI/API

`rocketdict-core` exposes database bootstrap, source import/interpretation, project summary, live Lab Registry and generic operation calls. The Workbench uses the same public surface through `RocketDictCore`.

`rocketdict.api.operations.OPERATIONS` publishes inspectable callable metadata plus `rocketdict_execution_contract`; Stage15 hard gates additionally publish exact `rocketdict_quality_gate_semantics`.

## Current next boundary

The product is **not done at Stage19**. The active critical path is to make the maintained schema/API support the existing Product Stage20–25 behavior (sense translation, CEFR, pronunciation, examples, immutable cards/set/export), then run the complete unified workflow, the 90k+ acceptance corpus, and finally build/validate the Windows distribution.
