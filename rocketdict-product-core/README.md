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

All rescue mechanisms remain **disabled by default** unless explicitly enabled. No rescue path may perform source rewriting, target rewriting, placeholders or post-translation literal injection.

Additional internal Stage12 wrappers exist for evidence-backed research but are **not public-wired** yet:

- `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1`;
- `rocketdict-stage12-illustration-label-rescue/1`;
- `rocketdict-stage12-tc-big-target-delimiter-context-rescue/1`.

The current persisted full-*Opticks* Product basis is Stage12 run `9`: **24 numeric/symbol / 30 punctuation / 0 length**, **52 unique hard failures**. Research counterfactuals do not replace that basis until they are persisted and fully verified.

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

## Optional independent TC-big asset

The active independent EN→RU comparator is pinned `Helsinki-NLP/opus-mt-tc-big-en-zle` revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, source weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, license `CC-BY-4.0`.

It is deliberately separate from the baseline production asset. Install runtime-only dependencies with the `alt-mt` extra; provisioning additionally needs `alt-mt-build`. The baseline `production` extra does not silently include TC-big.

Provision an exact local CTranslate2 float32 asset from a downloaded pinned Hugging Face snapshot:

```text
rocketdict-assets build-tc-big-en-ru /path/to/pinned-hf-snapshot /path/to/tc-big-asset
```

Set `ROCKETDICT_TC_BIG_ASSET_DIR` to the resulting asset. The manifest contract is `rocketdict-tc-big-en-ru-asset/1`; the loader verifies repository/revision/weight identity, license, `>>rus<<` target prefix, tokenizer files and the complete local payload tree.

Inference uses CTranslate2 plus local Hugging Face `MarianTokenizer` semantics and does **not** require Torch. Corrected full-*Opticks* parity evidence gives 52/52 input-token parity, 49/52 exact rank0 parity and at least one exact n-best overlap in all 52 tested residual rows. Three rank0 search-order differences remain explicit rather than being normalized away.

## Narrow TC-big target-delimiter research wrapper

`rocketdict-stage12-tc-big-target-delimiter-context-rescue/1` is an internal default-OFF research wrapper. It considers only original Stage10 contexts that:

- contain a current Product-hard-failing Stage12 row;
- are exactly replaceable by complete current Stage12 rows; and
- whose aggregate current target adds `()[]{}` delimiter characters not present in immutable source counts.

A raw TC-big candidate must pass all maintained strict mechanical checks, preserve Gutenberg emphasis shape, remove target-only delimiter additions and keep target/source alphabetic volume within `0.75..1.50`. There is no corpus-specific whitelist and no target repair.

On immutable run-9 research evidence this general selector triggers on seven contexts and accepts five, with a read-only counterfactual **24/30/0, 52 unique → 24/25/0, 47 unique**. This is not yet persisted Product evidence and does not authorize default promotion or public Stage12 wiring.

Exact replacement geometry is mandatory. A Stage10 context that cuts through a current Stage12 row is skipped fail-closed; the known run-9 context `2480` is the canonical example.

## CLI/API

`rocketdict-core` exposes database bootstrap, source import/interpretation, project summary, live Lab Registry and generic operation calls. The Workbench uses the same public surface through `RocketDictCore`.

`rocketdict-assets` provisions verified offline model assets, including `build-opus-en-ru` and the optional `build-tc-big-en-ru` command.

`rocketdict.api.operations.OPERATIONS` publishes inspectable callable metadata plus `rocketdict_execution_contract`; Stage15 hard gates additionally publish exact `rocketdict_quality_gate_semantics`.

## Verification and current boundary

The maintained direct Stage8→25 path and unified `rocketdict-product-run` source→Stage25 path are verified with the real pinned spaCy/OPUS/CEFR-J runtime and immutable replay. Product Core workflow `34628239731` is green for both dependency-light and real-runtime jobs after the optional TC-big runtime/wrapper code landed, so the default maintained path remains non-regressed.

Current large-corpus acceptance uses the complete pinned Project Gutenberg *Opticks* source (SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`) rather than a truncated sample.

The next immediate boundary is to add dedicated unit/runtime tests for the new TC-big delimiter wrapper and run it as a persisted full-corpus Stage12 layer above exact run `9`. Only after byte-exact source coverage, untouched-row invariance, raw-hypothesis provenance, database integrity and actual hard-gate counts are verified should public opt-in exposure even be considered. Product default promotion requires stronger semantic/release evidence, and the final heavy acceptance target remains zero unresolved hard failures.

After the heavy translation gates reach acceptance, the next release frontier is complete downstream heavy validation and the Windows distribution/clean-install path. Historical 0.30.x recovery is provenance evidence, not the maintained Product critical path.
