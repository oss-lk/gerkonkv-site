# RocketDict Product Core

Status: maintained forward Product runtime (`1.0.0.dev1`).

This package is the current RocketDict implementation. It is maintained forward code, not a reconstruction of an unavailable historical 0.30.x package.

## Maintained Product path

The maintained core owns the Product execution/storage path through Stage25:

`source → Stage8 production spaCy NLP → Stage10 context → Stage12 real OPUS EN→RU → Stage14 refinement boundary → Stage15 hard gates → Stage16 approval → Stage17 alignment → Stage18 lexical extraction → Stage19 sense induction → Stage20 contextual lexical OPUS → Stage21 CEFR-J → Stage22 CMUdict → Stage23 sense examples → Stage24 immutable cards/set → Stage25 JSON export`

The Workbench `rocketdict-product-run` drives the same public maintained API from source through Stage25 and resumes from immutable identities.

Stage12 uses the maintained `rocketdict-stage12-protected-split/8` planner. The real OPUS primary translation is immutable and cache-reusable. Rescue mechanisms are separate selection layers and do not change primary Stage12 identity.

The public Stage12 operation currently composes these narrow rescue surfaces:

- legacy selective resegmentation / whole-context research rescue;
- `rocketdict-stage12-length-failure-whole-context-rescue/1`;
- `rocketdict-stage12-citation-boundary-pair-rescue/1` for the narrowly proven inline `Sect. IV.` / `Sect. II.` sentence-boundary class.

All rescue mechanisms remain **disabled by default** unless explicitly enabled. The citation-pair selector requires a contiguous previous row ending in `Sect.` plus a Roman-fragment row that already fails the length gate; its raw rank-0 pair candidate must pass Product hard gates, repair length, and introduce no new strict-debt category. No rescue path may perform source rewriting, target rewriting, placeholders or post-translation literal injection.

Full-*Opticks* opt-in composition currently improves the canonical `30 numeric / 34 punctuation / 5 length` hard-gate inventory to `29 / 34 / 0` while preserving byte-exact source coverage and raw model hypotheses. This is evidence, **not default-promotion authorization**; semantic review remains required and the default Product path is unchanged.

Stage15 remains fail-closed for numeric/symbol, punctuation and length integrity. A hard failure is evidence to improve planning/model selection; it is not repaired by inserting target literals or weakening evaluators.

The downstream path preserves immutable selection/evidence identities. Stage20 retains n-best candidate evidence; Stage21 binds pinned CEFR-J with POS-aware matching; Stage22 accepts exact CMUdict evidence without generated-pronunciation fallback; Stage23 remains sense-scoped; Stage24/25 retain immutable card/set/export identities.

## External production assets

Processing is offline once assets are provisioned.

The accepted OPUS EN→RU archive is pinned to SHA-256:

`798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`

Build a verified local asset from an already downloaded archive:

```text
rocketdict-assets build-opus-en-ru opus-2020-02-11.zip /path/to/opus-asset
```

Set `ROCKETDICT_OPUS_ASSET_DIR` to that directory. The loader verifies the official archive identity recorded in the manifest and recomputes the complete local payload-tree SHA-256 before treating the model as available.

Production NLP requires an installed accepted spaCy English model; the current baseline is `en_core_web_sm 3.8.0` (`en-sm`).

Stage21 uses pinned CEFR-J Vocabulary Profile evidence. Stage22 uses exact CMUdict entries; generated fallback is not authoritative Product evidence.

## CLI/API

`rocketdict-core` exposes database bootstrap, source import/interpretation, project summary, live Lab Registry and generic operation calls. The Workbench uses the same public surface through `RocketDictCore`.

`rocketdict.api.operations.OPERATIONS` publishes inspectable callable metadata plus `rocketdict_execution_contract`; Stage15 hard gates additionally publish exact `rocketdict_quality_gate_semantics`.

## Verification and current boundary

The maintained direct Stage8→25 path and unified `rocketdict-product-run` source→Stage25 path are verified with the real pinned spaCy/OPUS/CEFR-J runtime and immutable replay. Current large-corpus acceptance uses the complete pinned Project Gutenberg *Opticks* source (SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`) rather than a truncated sample.

The active Product frontier is translation-quality hardening on that complete corpus. After the composed opt-in length/citation audit, the unresolved hard-gate inventory is `29` numeric/symbol and `34` punctuation failures across `59` unique segments, with no remaining length failures in that opt-in composition. The next research step is to rebuild the residual cohort by immutable source span/context identity before proposing any broader selector. Numeric/symbol and punctuation hard failures remain fail-closed.

After the heavy translation gates reach acceptance, the next release frontier is complete downstream heavy validation and the Windows distribution/clean-install path. Historical 0.30.x recovery is provenance evidence, not the maintained Product critical path.
