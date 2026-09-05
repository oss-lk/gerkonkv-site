# RocketDict — CURRENT authoritative continuation state

Date: 2026-09-05
Repository: `oss-lk/gerkonkv-site`
Branch: `main`

This is the primary continuation boundary for the active Product line.

## Non-negotiable rules

- Translation quality dominates speed/storage optimization.
- Never present fake/identity/mock/dictionary lookup as real MT.
- Never silently truncate a required long source/corpus or diagnostic inventory.
- Never infer executable operations or quality PASS semantics from names/status strings.
- Never manufacture missing 0.30.40 source from older checkpoints, Stage6Y, research overlays or inferred signatures.
- Preserve failed experiments, immutable hashes and lineage boundaries.
- Keep the public repository project-only; no personal/user/account/private-conversation data.

## Product status

Workbench already implements an evidence-driven, resumable Product pipeline through Stage25:

1. immutable Product preflight;
2. exact-runtime API/registry probe;
3. structured callable binding + execution proof;
4. Stage8 → 10 → 12 → 14;
5. Stage15 hard quality gates;
6. Stage16 → 17 → Workbench18 aligned lexical extraction → Stage19;
7. real OPUS-backed Stage20;
8. lexical-primary arbitration → pinned CEFR-J → exact CMUdict → Stage23;
9. Stage24 cards/set assembly;
10. Stage25 export.

Primary Product CLI: `rocketdict-product-run`.

Do not build another orchestration layer. The hard blocker is still a complete exact-compatible RocketDict core/public API runtime.

Product identities:

- Product Profile `rocketdict-workbench-product-profile/6`
- Product preflight `rocketdict-workbench-product-preflight/2`
- Product run `rocketdict-workbench-product-run/1`
- API probe `rocketdict-core-api-surface-probe/2`
- Stage8 binding `rocketdict-workbench-upstream-binding/2`
- Stage20→23 downstream `rocketdict-workbench-product-downstream/2`

Stage15 hard gates must expose explicit PASS semantics:

- `rocketdict-numeric-symbol-preservation`
- `rocketdict-punctuation-preservation`
- `rocketdict-length-ratio-proxy`

Correct dependency after gates: `16 → 17 → Workbench18 → 19`.

## Real OPUS identity

Accepted EN→RU artifact:

- `https://object.pouta.csc.fi/OPUS-MT-models/en-ru/opus-2020-02-11.zip`
- SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`
- CTranslate2 Marian
- acceptance compute type `float32`

Historical successful gate: 120 representative sentences / 4,488 words. Opticks SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, 104,275 regex words.

Do not reconstruct historical F96 challenge selection from coincident counts.

## Exact 0.30.40 boundary

Evidence namespace `rocketdict/recovered/stage8-0.30.40/` is not an active core checkout.

Surviving truncated Stage8 prefix:

- artifact `9681838606`
- decompressed tar-prefix 51,590 bytes
- SHA-256 `a6af982f442fdedadc6ba6bb9e91d7ca3b519e6d0f893b21537498741f7bf67a`
- `gzip_eof=false`

Exact complete members:

1. `src/rocketdict/__init__.py` — 502 bytes — SHA-256 `7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c`; proves version 0.30.40 and lazy references to `API_VERSION` / `RocketDictAPI`.
2. `src/rocketdict/nlp/registry.py` — 29,072 bytes — SHA-256 `02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69`.

The next member, `src/rocketdict/lab/stage12_pilot.py`, is truncated. The intended Stage8 overlay had 19 members and did not contain `rocketdict.api.*`.

Current exact-target state:

- intended members: 19
- exact available: 2
- exact missing: 17
- exact 0.30.40 public API modules recovered: 0

Still missing as exact 0.30.40 bytes: `rocketdict.api.contracts`, `rocketdict.api.client`, `rocketdict.api.cli`.

No genuine Product Stage8 dispatch has been claimed.

## Best historical recovery input

A former handoff incorrectly stated that Stage6Y ZIP packaging did not finish. Historical project output proves the full archive existed, was verified and was explicitly handed off.

Primary target:

- `RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip`
- SHA-256 `3cd150c012c28d0e8c458ba25bff56a8e9c17789d2c6986d8b6b72e202d5c387`
- historical size unknown; never guess it
- historical `unzip -t` success
- 7/7 new fault-injection tests
- 34/34 targeted regressions
- compileall, wheel install and source↔wheel parity passed
- explicitly handed off.

Alternate packaged-core target:

- `rocketdict-0.30.34-py3-none-any.whl`
- SHA-256 `76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`.

The ZIP is preferred because it may contain source, wheel, reports, manifests and continuation evidence. Neither exact artifact's bytes are currently recovered in the active runtime.

Recovery priority: 0.30.34 full ZIP/wheel → 0.30.33 → 0.30.32 → 0.30.31 → 0.30.30 → 0.30.29 → 0.30.8.

Machine-readable authority:

- `rocketdict/recovered/checkpoint-catalog.json`
- `rocketdict/recovered/late-stage6-artifact-identities-2026-09-05.json`
- `rocketdict/recovered/recovery-frontier-2026-09-05.json` schema `/4`
- `rocketdict/recovered/search-exhaustion-2026-09-05.json` schema `/3`.

## Recovery tooling — current proof chain

Installed CLIs:

- `rocketdict-recover-core`
- `rocketdict-recover-plan`
- `rocketdict-recover-checkpoint`
- `rocketdict-recover-wheel`
- `rocketdict-recover-scan`
- `rocketdict-product-run`

Schemas:

- generic directory/ZIP candidate `rocketdict-workbench-core-recovery-candidate/1`
- base→0.30.40 plan `rocketdict-workbench-core-recovery-plan/1`
- lower ZIP scan `rocketdict-workbench-core-recovery-scan/3`
- **full checkpoint proof `rocketdict-workbench-full-checkpoint-recovery/2`**
- wheel integrity `rocketdict-workbench-wheel-integrity/2`
- wheel recovery `rocketdict-workbench-core-wheel-recovery/5`
- wheel runtime `rocketdict-workbench-core-wheel-runtime-probe/2`
- **unified scan `rocketdict-workbench-core-recovery-scan/8`**.

`rocketdict-recover-checkpoint` is read-only and never extracts or executes historical code. For one checkpoint ZIP it proves, in order:

1. outer ZIP path safety, duplicate-name and CRC status;
2. exact historical ZIP catalog identity;
3. unique RocketDict source root, version and SHA-256 inventory of `api/contracts.py`, `api/client.py`, `api/cli.py`;
4. any nested RocketDict wheel's CRC/METADATA/WHEEL/mandatory RECORD;
5. nested wheel's independent historical catalog SHA/optional-size identity;
6. complete source↔wheel package-byte parity;
7. README/report/manifest/state evidence inventory;
8. historical-base→exact-0.30.40 compatibility plan.

Checkpoint hard blockers include wrong outer SHA, missing/ambiguous source root, nested wheel integrity failure, wrong exact nested-wheel SHA and source↔wheel byte drift.

Evidence inventory is deliberately bounded but never silently truncated: it publishes eligible count, selected count, limit 200 and `truncated`; members over 8 MiB explicitly report skipped hashing.

`rocketdict-recover-scan` `/8` automatically attaches the full-checkpoint proof to every ZIP candidate. It separately preserves the existing fail-closed wheel pipeline; wheel runtime remains opt-in with `--probe-wheels`.

Archive identity remains SHA-first: exact SHA-256 is sufficient when historical size is unavailable; a known historical size must also match; filename alone is never proof.

All recovery outputs keep `promotion_allowed=false`; relevant unified/full outputs also keep `product_execution_allowed=false`.

## Exhausted recovery surfaces

Do not repeat without new evidence:

- reachable Git history, deleted refs and Stage6T–Y commit window;
- likely historical API paths and Releases;
- known Actions artifacts/workflows;
- historical Stage6 branch;
- exact File Library Stage6Y filename/SHA/date navigation;
- connected Google Drive exact/general searches;
- public exact filename/SHA search;
- current runtime artifact hashing;
- retained Stage31 transcript recovery;
- public Stage6Y mirror (`README`, report, continuation): it confirms 301 packaged runtime files matched source but explicitly is not a complete source/wheel mirror and does not preserve their individual paths/hashes/API bytes.

Current runtime still has zero exact Stage6Y ZIP/wheel byte matches and zero complete core candidates. The 343,401,002-byte offline OPUS runtime contains inference dependencies but no RocketDict package/API.

## Latest verified code checkpoint

`ed86467011efb5a680647e56007728d0cbb16157` — `Test explicit checkpoint evidence limits and catalog validation`

GitHub Actions:

- workflow `RocketDict Workbench`
- run `33975530978`
- job `101331437743`
- Ubuntu 24.04.4
- Python 3.13.15
- compile success
- installed CLI smoke success
- **203 passed, 1 skipped in 2.46s**.

This proves full-checkpoint outer identity, nested wheel RECORD + exact catalog SHA, source↔wheel drift blocking, public API hash inventory, malformed wheel-catalog rejection, non-silent evidence limits, unified scan `/8`, and installed CLI availability.

Preserve failed run `33975210119` (`1 failed, 200 passed, 1 skipped`): the new logic passed; one old test still expected unified schema `/7` and was corrected without weakening semantics.

## Stage6Y vs Product lineage

0.30.34 Stage6Y remains the strongest historical base-recovery target, not automatic Product source replacement.

Verified maintenance evidence includes:

- working SQLite 881,905,664 bytes
- working SHA-256 `a0128b802930d350679c7d135bea9197fb9e202d863260c31a68d49681fbeafb`
- canonical heavy SHA-256 `3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274`
- SQLite quick_check ok; FK=0; Alembic `8b4e7c2a91d0`; lexical entries 35,743
- 301 packaged runtime files matched source byte-for-byte.

Do not merge Stage6Y into Product without exact compatibility proof and full regression.

## Immediate next Product task

The genuine external byte-level input remains:

`RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip`

SHA-256 `3cd150c012c28d0e8c458ba25bff56a8e9c17789d2c6986d8b6b72e202d5c387`.

Alternate: `rocketdict-0.30.34-py3-none-any.whl`, SHA-256 `76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`.

When bytes appear:

1. run `rocketdict-recover-scan` — `/8` automatically performs checkpoint proof for ZIPs;
2. retain focused `rocketdict-recover-checkpoint` output for the exact Stage6Y ZIP;
3. verify outer SHA, source API hashes, nested wheel exact SHA/RECORD and source↔wheel parity;
4. inspect manifests/reports without silent evidence loss;
5. resolve base→exact-0.30.40 compatibility; never infer the 17 missing exact targets from similarity;
6. only after exact-compatible runtime proof: doctor → real import → immutable Product preflight → live registry/API probe → exact binding/execution → genuine Stage8;
7. continue the same immutable state through Stage25;
8. run the complete 90k+ public-domain corpus without truncation and retain the full translation/research evidence DB.

Until new provenance-verifiable bytes appear, keep `exact_core_incomplete` explicit. Do not rebuild already-complete orchestration and do not repeat exhausted recovery surfaces.
