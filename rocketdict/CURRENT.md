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

Workbench already implements an evidence-driven resumable Product pipeline through Stage25:

1. immutable Product preflight;
2. exact-runtime API/registry probe;
3. structured callable binding + execution proof;
4. Stage8 → Stage10 → Stage12 → Stage14;
5. Stage15 hard quality gates;
6. Stage16 → Stage17 → Workbench18 aligned lexical extraction → Stage19;
7. real OPUS-backed unified Stage20;
8. Stage20 lexical-primary arbitration → pinned CEFR-J → exact CMUdict → Stage23;
9. Stage24 cards + set assembly;
10. Stage25 export.

Primary CLI: `rocketdict-product-run` (`init`, `advance`, `status`).

Do not build another orchestration layer. The current hard blocker is a complete exact-compatible RocketDict core/public API runtime.

Core evidence schemas:

- Product Profile `rocketdict-workbench-product-profile/6`
- Product preflight `rocketdict-workbench-product-preflight/2`
- Product run `rocketdict-workbench-product-run/1`
- API probe `rocketdict-core-api-surface-probe/2`
- Stage8 binding `rocketdict-workbench-upstream-binding/2`
- Stage20→23 downstream `rocketdict-workbench-product-downstream/2`

Stage15 must use explicit PASS semantics for:

- `rocketdict-numeric-symbol-preservation`
- `rocketdict-punctuation-preservation`
- `rocketdict-length-ratio-proxy`

Generic `status="ok"` is never PASS.

Correct post-gate dependency:

`16 finalization → 17 alignment → Workbench18 aligned extraction → 19 sense induction`.

## Real OPUS identity

Accepted EN→RU artifact:

- URL `https://object.pouta.csc.fi/OPUS-MT-models/en-ru/opus-2020-02-11.zip`
- SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`
- CTranslate2 Marian
- acceptance compute type `float32`

Historical real-model gate evidence:

- 120 representative sentences
- 4,488 representative words
- Opticks SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`
- Opticks regex words 104,275

Do not reconstruct historical F96 challenge selection from coincident counts.

## Exact 0.30.40 recovery boundary

Evidence namespace:

`rocketdict/recovered/stage8-0.30.40/`

It is not an active core checkout.

Surviving truncated Stage8 prefix:

- artifact `9681838606`
- decompressed tar-prefix bytes 51,590
- SHA-256 `a6af982f442fdedadc6ba6bb9e91d7ca3b519e6d0f893b21537498741f7bf67a`
- `gzip_eof=false`

Exactly preserved complete members:

1. `src/rocketdict/__init__.py`
   - 502 bytes
   - SHA-256 `7bf417eeda2104a06d9aaaaef4b79807698685ac4dc07539c2e887cd14e60b5c`
   - proves version `0.30.40` and lazy references to `rocketdict.api.contracts.API_VERSION` / `rocketdict.api.client.RocketDictAPI`.

2. `src/rocketdict/nlp/registry.py`
   - 29,072 bytes
   - SHA-256 `02cfbb2347f141d9b77f4fca143322a4e4d7773dcf535611b664473510fbaf69`.

Next member `src/rocketdict/lab/stage12_pilot.py` is truncated.

Historical materializer analysis proves the intended Stage8 overlay contained 19 research/translation files and **did not contain `rocketdict.api.*`**.

Current exact-target math:

- intended overlay members: 19
- exact target members available: 2
- exact target members missing: 17
- exact recovered 0.30.40 public API modules: 0

Still missing as exact 0.30.40 bytes:

- `rocketdict.api.contracts`
- `rocketdict.api.client`
- `rocketdict.api.cli`

No genuine Product Stage8 dispatch has been claimed from the recovered namespace.

## Corrected preferred historical recovery input

A previous recovery handoff incorrectly stated that Stage6Y final ZIP packaging did not finish. Historical project output recovered on 2026-09-05 proves that statement was wrong.

**Primary recovery target:**

- version `0.30.34`
- stage `LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE`
- full checkpoint `RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip`
- exact SHA-256 `3cd150c012c28d0e8c458ba25bff56a8e9c17789d2c6986d8b6b72e202d5c387`
- historical byte size is not recovered and is deliberately left unknown
- historical path was `/mnt/data/RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip`
- `unzip -t` passed
- new fault-injection tests `7/7` passed
- targeted regressions `34/34` passed
- compileall, wheel install check and source↔wheel parity passed
- the archive was explicitly handed off to the user.

**Alternate packaged-core target:**

- `rocketdict-0.30.34-py3-none-any.whl`
- SHA-256 `76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`

The ZIP is preferred because it can contain source, wheel, reports, manifests and continuation evidence beyond the installed package.

Recovery priority:

1. exact 0.30.34 full Stage6Y ZIP; exact 0.30.34 wheel as alternate;
2. exact 0.30.33 ZIP/wheel;
3. exact 0.30.32 ZIP/wheel;
4. 0.30.31;
5. 0.30.30;
6. 0.30.29;
7. exact 0.30.8 ZIP.

Machine-readable authority:

- `rocketdict/recovered/checkpoint-catalog.json`
- `rocketdict/recovered/late-stage6-artifact-identities-2026-09-05.json`
- `rocketdict/recovered/recovery-frontier-2026-09-05.json`

The actual Stage6Y ZIP/wheel bytes are **not currently recovered** in the active runtime.

## Recovery tooling

Operational guide:

`rocketdict-workbench/docs/CORE_RECOVERY.md`

Commands:

- `rocketdict-recover-core`
- `rocketdict-recover-plan`
- `rocketdict-recover-wheel`
- `rocketdict-recover-scan`

Important ZIP identity rule:

- exact SHA-256 is sufficient cryptographic identity when a historical byte size was not preserved;
- if a historical byte size is known, it must also match;
- filename alone never proves identity;
- an unknown size must never be guessed merely to satisfy the catalog.

Lower-level checkpoint scan schema is now `rocketdict-workbench-core-recovery-scan/3`.

Wheel proof remains fail-closed:

1. ZIP CRC + `METADATA` + `WHEEL` + mandatory `RECORD` integrity;
2. exact historical catalog identity when the basename is known;
3. packaged RocketDict structural source inspection;
4. deterministic historical-base→0.30.40 compatibility plan;
5. optional isolated/network-denied zipimport runtime proof.

Current wheel schemas remain:

- integrity `rocketdict-workbench-wheel-integrity/2`
- runtime `rocketdict-workbench-core-wheel-runtime-probe/2`
- full wheel proof `rocketdict-workbench-core-wheel-recovery/5`
- unified scan `rocketdict-workbench-core-recovery-scan/7`

All recovery outputs remain non-promotional. Historical base similarity never substitutes for the 17 missing exact 0.30.40 overlay members or missing exact 0.30.40 API bytes.

## Exhausted recovery surfaces

Read before repeating searches:

`rocketdict/recovered/search-exhaustion-2026-09-05.json` — schema `rocketdict-core-recovery-search-exhaustion/3`.

Checked without recovering the Stage6Y bytes:

- reachable Git history, known deleted refs and Stage6T–Y date-window commit stream;
- likely historical API paths;
- Releases in both RocketDict-related repos;
- known Actions artifact workflows/runs;
- historical `spacy-project-vault` Stage6 branch;
- File Library exact Stage6Y filename/SHA/date navigation;
- connected Google Drive exact/general RocketDict search;
- public exact filename/SHA search;
- current runtime workspace hashing;
- retained Stage31 transcripts.

Current runtime still has ten top-level ZIP/WHL artifacts, zero 0.30.34 ZIP SHA matches, zero 0.30.34 wheel SHA matches and zero complete core candidates. The 343,401,002-byte offline OPUS runtime remains useful for inference dependencies but contains no RocketDict package/API.

Do not repeat these surfaces unless new files/refs/objects become available.

## Latest verified corrected recovery checkpoint

Commit tested:

`c3b96263914c890502215b4fac60ad0c3bd82c33` — `Test corrected Stage6Y exhaustive recovery boundary`

GitHub Actions:

- workflow `RocketDict Workbench`
- run `33974220059`
- job `101327963291`
- Ubuntu 24.04.4
- Python 3.13.15
- compile success
- **193 passed, 1 skipped in 1.70s**

This green run includes the new SHA-first ZIP identity regression suite:

- exact SHA + unknown historical size can prove catalog identity;
- wrong SHA is rejected even when size is unknown;
- a known historical size remains a mandatory additional match;
- a size without an exact SHA is rejected;
- existing 0.30.8–0.30.33 and wheel recovery behavior remains covered.

Preserve the immediately preceding red runs as evidence: they exposed stale schema assertions, not a need to weaken recovery semantics.

## Separate Stage6Y vs Product lineage

The recovered 0.30.34 Stage6Y checkpoint identity is the best historical base-recovery target, **not** automatic Product replacement.

Verified Stage6Y maintenance evidence still includes:

- working SQLite 881,905,664 bytes
- working SHA-256 `a0128b802930d350679c7d135bea9197fb9e202d863260c31a68d49681fbeafb`
- canonical heavy SHA-256 `3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274`
- SQLite quick_check ok
- FK violations 0
- Alembic `8b4e7c2a91d0`
- lexical entries 35,743
- 301 packaged runtime files matched source byte-for-byte.

Do not merge Stage6Y into Product without exact compatibility proof and full regression.

## Immediate next Product task

The next useful input is the actual bytes of the exact full checkpoint:

`RocketDict_0.30.34_LAB_STAGE6Y_IO_FAULT_SAFE_COMPLETE.zip`

SHA-256:

`3cd150c012c28d0e8c458ba25bff56a8e9c17789d2c6986d8b6b72e202d5c387`

Alternate input:

`rocketdict-0.30.34-py3-none-any.whl`

SHA-256:

`76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`

When bytes become available:

1. run `rocketdict-recover-scan` on the containing directory and require exact catalog identity;
2. for the full ZIP, inspect its source/wheel/manifests and run `rocketdict-recover-core` + `rocketdict-recover-plan` before execution;
3. for the wheel alternate, use the existing integrity-gated proof and opt-in runtime probe;
4. never infer the missing exact 0.30.40 bytes from historical similarity;
5. only after an exact-compatible runtime exists: Workbench doctor → real source import → immutable Product preflight → live registry/API probe → exact binding/execution contract;
6. perform the first genuine Stage8 dispatch;
7. continue the same immutable Product state through Stage25 with real OPUS + pinned CEFR-J;
8. run the complete 90k+ public-domain corpus without truncation and retain the full translation/research evidence database.

Until those bytes exist, keep `exact_core_incomplete` explicit. Do not rebuild orchestration already implemented and do not repeat exhausted recovery searches.
