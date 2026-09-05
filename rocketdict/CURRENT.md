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

- Product Profile: `rocketdict-workbench-product-profile/6`
- Product preflight: `rocketdict-workbench-product-preflight/2`
- Product state: `rocketdict-workbench-product-run/1`
- API probe: `rocketdict-core-api-surface-probe/2`
- Stage8 binding: `rocketdict-workbench-upstream-binding/2`
- Stage20→23 downstream: `rocketdict-workbench-product-downstream/2`

Required Stage15 gates:

- `rocketdict-numeric-symbol-preservation`
- `rocketdict-punctuation-preservation`
- `rocketdict-length-ratio-proxy`

Each gate must publish a valid execution contract and explicit PASS semantics before dispatch. Generic `status="ok"` is not PASS.

Correct post-gate dependency:

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

Historical materializer analysis proves the intended Stage8 overlay contained 19 research/translation files and **did not contain `rocketdict.api.*`**. Restoring missing overlay chunks alone therefore cannot restore the base public API.

Current overlay recovery math:

- intended members: 19
- exact target bytes available: 2
- exact target bytes missing: 17

Exact 0.30.40 public API bytes still missing:

- `rocketdict.api.contracts`
- `rocketdict.api.client`
- `rocketdict.api.cli`

No real Product Stage8 dispatch has been claimed from the recovered namespace.

## Preferred historical recovery input

The strongest known packaged-core lead is exact and machine-readable:

- version `0.30.34`
- filename `rocketdict-0.30.34-py3-none-any.whl`
- SHA-256 `76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`
- Stage6Y engineering completed historically, but final release ZIP packaging did **not** complete.
- Never invent a Stage6Y release ZIP.

Recovery priority:

1. 0.30.34 exact wheel;
2. 0.30.33 exact ZIP or wheel;
3. 0.30.32 exact ZIP or wheel;
4. 0.30.31;
5. 0.30.30;
6. 0.30.29;
7. 0.30.8 exact ZIP.

Exact identities are preserved in:

- `rocketdict/recovered/checkpoint-catalog.json`
- `rocketdict/recovered/late-stage6-artifact-identities-2026-09-05.json`
- `rocketdict/recovered/recovery-frontier-2026-09-05.json`

These records prove historical artifact identity only. Their bytes are **not currently recovered** in the active runtime.

## Recovery tooling — current wheel-first proof chain

Operational guide:

`rocketdict-workbench/docs/CORE_RECOVERY.md`

Current evidence schemas:

- directory/ZIP structural candidate: `rocketdict-workbench-core-recovery-candidate/1`
- base→0.30.40 plan: `rocketdict-workbench-core-recovery-plan/1`
- wheel integrity: `rocketdict-workbench-wheel-integrity/2`
- wheel runtime probe: `rocketdict-workbench-core-wheel-runtime-probe/2`
- full wheel recovery: `rocketdict-workbench-core-wheel-recovery/5`
- unified scan: `rocketdict-workbench-core-recovery-scan/7`

Commands:

- `rocketdict-recover-core` — inspect one source directory/ZIP candidate;
- `rocketdict-recover-plan` — deterministic read-only base→0.30.40 plan;
- `rocketdict-recover-wheel` — full wheel proof; `--probe-runtime` explicitly enables final runtime import proof;
- `rocketdict-recover-scan` — batch directory/ZIP/wheel discovery; `--probe-wheels` explicitly enables final wheel runtime proofs.

For wheels the proof order is fixed:

1. ZIP CRC + `METADATA` + `WHEEL` + mandatory `RECORD` integrity;
2. historical checkpoint catalog identity when the basename is known;
3. packaged RocketDict structural source inspection;
4. deterministic base→0.30.40 compatibility plan;
5. optional isolated/network-denied direct-zipimport runtime proof.

Fail-closed wheel rules:

- missing/corrupt `RECORD` blocks runtime;
- filename↔METADATA name/version mismatch blocks runtime;
- filename tag↔WHEEL `Tag:` mismatch blocks runtime;
- known historical basename with cataloged exact SHA/size but wrong bytes blocks runtime **before historical code import**;
- unknown intact wheels may be explored, but receive no known-checkpoint identity claim;
- integrity/structural/plan/runtime SHA observations must agree;
- runtime hashes the wheel before and after subprocess execution;
- Python runs with `-I` and a socket/DNS audit-hook denial;
- required and transitively loaded `rocketdict.*` modules must resolve from inside the wheel;
- a successful historical runtime proof is still not exact 0.30.40 compatibility and not Product promotion.

All recovery outputs retain `promotion_allowed=false`; full wheel/scan outputs also retain `product_execution_allowed=false`.

## Exhausted recovery surfaces

Authoritative machine-readable records:

- `rocketdict/recovered/search-exhaustion-2026-09-05.json` — schema `rocketdict-core-recovery-search-exhaustion/2`
- `rocketdict/recovered/runtime-artifact-rescan-2026-09-05.json` — exact current-runtime ZIP/WHL hashes.

Checked and currently closed:

- parentless GitHub upload root `442e09db...`: website only;
- observed deleted refs `rocketdict-opus-gate-public` and `rocketdict-pr-actions-run`: website/workflows only;
- likely historical `api/client.py` Git paths under `src/`, `rocketdict/src/`, `rocketdict/active_source/src/`: zero reachable commits;
- GitHub Releases in `gerkonkv-site` and `spacy-project-vault`: none;
- `spacy-project-vault/rocketdict-stage06-spacy-model`: no RocketDict source package;
- File Library recovery evidence: historical checkpoint identities/content evidence but no retained checkpoint/core bytes;
- retained Stage31 transcripts: no new full core beyond the already-known historical 0.30.8 link/evidence;
- GitHub Actions artifacts/workflows:
  - four accessible `spacy-project-vault` RocketDict real-OPUS runs (`32985777761`, `32985758628`, `32985715220`, `32985680517`) each have zero retained artifacts;
  - historical `gerkonkv-site` Workbench workflow had no `upload-artifact` step;
  - deleted public OPUS workflow uploaded only `work/evidence/**` and `work/output/**` with 14-day retention, not RocketDict core/wheel;
  - no currently listable runs remain for that deleted OPUS branch;
- current recovery runtime: all ten top-level ZIP/WHL artifacts re-hashed; exact 0.30.34 wheel SHA matches: 0.

Current runtime result:

- top-level ZIP/WHL artifacts: 10
- top-level RocketDict wheels: 0
- ZIPs with any RocketDict package `__init__.py`: 1
- with required public API source modules: 0
- with RocketDict wheel: 0
- with nested RocketDict checkpoint ZIP: 0
- complete core candidates: 0

The one package-root hit is `stage8-overlay-prefix.zip`, already classified as known truncated 0.30.40 evidence.

The 343,401,002-byte `rocketdict-offline-opus-runtime-cp313.zip` (SHA-256 `c8812631f65eb5f64c1e3d910d432a181bfa850af92637221b6fa926d9132b8c`) preserves CTranslate2/Numpy/PyYAML/SentencePiece/setuptools runtime wheels, but no RocketDict package/API. It is useful for real OPUS execution, not core recovery.

Do **not** repeat the closed searches above unless new refs/files/objects become available.

## Latest verified recovery checkpoint

Latest recovery logic checkpoint:

`202fbf58b450f35ef631009f65356d5cdf562547` — `Test catalog-bound historical wheel recovery identities`

That run:

- workflow `RocketDict Workbench`
- run `33968651171`
- job `101313136601`
- Ubuntu 24.04.4
- Python 3.13.15
- compile success
- **187 passed, 1 skipped in 3.29s**.

Latest handoff/frontier contract validation:

`1262fdcdb26cc8d3762946d98e339d100ab745ac` — `Align frontier identity assertion with exact wording`

- workflow `RocketDict Workbench`
- run `33968969686`
- job `101313979341`
- Ubuntu 24.04.4
- Python 3.13.15
- compile success
- **187 passed, 1 skipped in 2.42s**.

This validates the current code plus the machine-readable recovery frontier contract. Later commits only record search-exhaustion/runtime-rescan evidence and this handoff; they do not change Workbench executable code.

Preserved failed evidence includes:

- run `33967461124`: damaged 63-character historical SHA correctly rejected, then corrected from source evidence;
- run `33967891342`: SyntaxError in a new test fixture caught at pytest collection and corrected without weakening wheel integrity semantics;
- run `33968883529`: one frontier wording assertion failed (`wrong exact SHA` vs the more precise `SHA-256/size mismatch`); corrected to test the machine-relevant semantics and revalidated green in run `33968969686`.

## Separate Stage6Y maintenance lineage

RocketDict 0.30.34 / LAB Stage6Y remains a verified historical maintenance lineage, not automatic Product source replacement.

Key evidence:

- working SQLite 881,905,664 bytes
- working SHA-256 `a0128b802930d350679c7d135bea9197fb9e202d863260c31a68d49681fbeafb`
- canonical heavy SHA-256 `3be3669a3dad75ee39d9f6c55405036707bff524bbfb23290114537d3380b274`
- SQLite quick_check ok
- FK violations 0
- Alembic `8b4e7c2a91d0`
- lexical entries 35,743
- 301 packaged runtime files matched source byte-for-byte.

The recovered **0.30.34 wheel identity** is a valuable packaged-core recovery lead, but neither that identity nor a future successful runtime probe proves compatibility with missing exact 0.30.40 bytes.

## Immediate next Product task

There is now a genuine external byte-level blocker. The next useful input is provenance-verifiable historical RocketDict checkpoint/core **bytes**, preferably exactly:

`rocketdict-0.30.34-py3-none-any.whl`

SHA-256:

`76f7054f2a28a56a650f2fdf72175c3b993e252d020936b3b6084092d465a02a`

When new bytes become available:

1. run `rocketdict-recover-scan` on the containing directory;
2. for wheel runtime evidence use `--probe-wheels`; the tool will not execute a wheel before integrity/catalog/identity checks pass;
3. for a single wheel use `rocketdict-recover-wheel --probe-runtime`;
4. never infer missing 0.30.40 overlay/API bytes from historical base similarity;
5. only for a complete exact-compatible runtime: Workbench doctor → real source import → immutable Product preflight → live registry/API probe → exact callable binding/execution contract;
6. perform the first genuine `rocketdict-product-run advance` Stage8 dispatch;
7. continue the same immutable Product state through Stage25 with real OPUS + pinned CEFR-J;
8. run the full 90k+ public-domain corpus without truncation and retain the complete translation/research evidence database.

Until those bytes exist, keep `exact_core_incomplete` explicit. Do not spend another development turn rebuilding orchestration or repeating the recovery surfaces closed above.
