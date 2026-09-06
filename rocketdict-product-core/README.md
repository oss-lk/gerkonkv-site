# RocketDict Product Core

Status: maintained forward Product runtime (`1.0.0.dev1`).

This package is the current implementation of the RocketDict core. It is **new maintained code**, not a reconstruction of an unavailable historical 0.30.x package.

## Maintained Product path

The maintained core now owns the Product execution/storage path through Stage25:

`source → Stage8 production spaCy NLP → Stage10 context → Stage12 real OPUS EN→RU → Stage14 refinement boundary → Stage15 hard gates → Stage16 approval → Stage17 alignment → Stage18 lexical extraction → Stage19 sense induction → Stage20 contextual lexical OPUS → Stage21 CEFR-J → Stage22 CMUdict → Stage23 sense examples → Stage24 immutable cards/set → Stage25 JSON export`

The downstream migration preserves the validated Workbench policies while removing historical ORM/storage assumptions from the Product critical path. Stage20 retains n-best candidate evidence and immutable selection identities; Stage21 binds the pinned CEFR-J source with POS-aware matching; Stage22 accepts exact CMUdict evidence without generated-pronunciation fallback; Stage23 remains sense-scoped; Stage24/25 retain immutable card/set/export identities.

The real-runtime GitHub gate provisions `en_core_web_sm 3.8.0` and the official OPUS `opus-2020-02-11` model, converts the latter to CTranslate2 float32, and executes the maintained public API from source through Stage25. Fake/identity MT is not accepted.

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

Stage21 uses the pinned CEFR-J Vocabulary Profile evidence bundled/provisioned by the maintained evidence layer. Stage22 uses CMUdict exact entries; generated fallback is not authoritative Product evidence.

## CLI/API

`rocketdict-core` exposes database bootstrap, source import/interpretation, project summary, live Lab Registry and generic operation calls. The Workbench uses the same public surface through `RocketDictCore`.

`rocketdict.api.operations.OPERATIONS` publishes inspectable callable metadata plus `rocketdict_execution_contract`; Stage15 hard gates additionally publish exact `rocketdict_quality_gate_semantics`.

## Current next boundary

The next Product boundary is no longer Stage20–25 migration. After validating the latest POS-aware CEFR/evidence patch on the full CI gate, the critical path is to make `rocketdict-product-run` drive the maintained source→Stage25 workflow directly and resumably, then scale real-corpus validation toward the complete 90k+ public-domain acceptance run, fix any quality/coverage defects found there, and finally build/validate the Windows distribution.
