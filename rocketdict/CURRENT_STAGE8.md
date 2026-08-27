# RocketDict Stage 8 — current continuation checkpoint

Last updated: 2026-08-27 UTC.

This file is the compact **latest-state pointer** for continuation sessions. Read it after `START_HERE.md` and before starting new experiments.

## Parent frontier

The last full deterministic challenge measurement remains **F96**:

- 5,000 source words;
- 109 source occurrences;
- 168 inference chunks;
- real official OPUS EN→RU, CTranslate2 float32;
- numeric mismatches = 3;
- critical-symbol mismatches = 0;
- length-ratio mismatches = 0;
- empty outputs = 0;
- backend-error units = 0;
- gate = FAIL only because numeric integrity must be zero.

The exact three F96 failure classes are documented in `RESEARCH_STATUS.md`:

1. occurrence 15697 — structural `[in _Fig._ 2.]` reference loss;
2. occurrence 16200 — short `15 ... 3` numeric loss;
3. occurrence 17795 — extreme `10^6 / 10^12 / 10^18` sequence corruption.

Do not restart at A/B/C/D/E.

## New work completed after the original handoff

### G — integrity-aware n-best mechanism: positive for 16200 class

GitHub Actions run: `33077361613` — success.
Artifact: `9648449421` (`rocketdict-stage8-g-nbest-probe`).
Artifact digest: `sha256:f0d022aa25edd3fee360848ee82a402c3604783f0b6f98f1ea0f432580b1b1b7`.

Exact probe source:
`15 Min. that of the exterior 3 Degr.`

Tested cells:
- beam 4 / n-best 4;
- beam 8 / n-best 8;
- beam 16 / n-best 8;
- beam 16 / n-best 16.

In every tested cell rank 0 was already integrity-valid:
`15 Мин. внешней части 3 дегр.`

Therefore G is a viable mechanism for the occurrence-16200 class. The same probe confirmed that ordinary n-best does **not** solve the extreme-sequence class even at beam 16 / n-best 16.

Durable evidence: `research/stage8-g-probe-2026-08-27.json`.

### H — structural figure-reference mechanism: positive mechanism evidence

A source-side structural parser extracts the figure-reference node before MT and renders it with source→target provenance. For the F96 15697 class it preserved:
`[in _Fig._ 2.]` → `[на рис. 2]`.

The mechanism probe passes, but it is **not promoted** yet because the structural split changes surrounding MT wording and aggregate quality must be checked on the identical F96 challenge.

### I — extreme sequence

#### I-v1 — rejected negative result

The first structural attempt protected only the three huge literals. Although those literals survived, the new segmentation introduced duplicated/garbled neighbouring `76 / 152 / 228` context. The branch was rejected rather than accepted on a locally-green check.

GitHub Actions run: `33077653753`.
Artifact: `9648579957`.
Digest: `sha256:0d1f2d5e3e3422f679268bcd125ba7758877f1457bd94290b16b49780d3cfa48`.

#### I-v2 — positive mechanism evidence

The structural boundary was widened to the coupled height/rarity relation:
- heights: `76, 152, 228 Miles`;
- rarity values: `1000000, 1000000000000, 1000000000000000000`;
- qualifier/comparative are represented by the structural node;
- all six protected values carry explicit source→target provenance.

GitHub Actions run: `33077965671` — success.
Commit: `f185fc59907695b4f9c3b58a4116f5f227d38ade`.
Artifact: `9648716848`.
Artifact digest: `sha256:118ceab38aef586c647aafbdadd0abd1b4a70e4ceee24f2571dc83e170bb8964`.

The v2 whole-passage local guard checked every explicit value in the tested passage:
`15`, `22-1/2`, `30`, `38`, `64`, `256`, `1024`, `76`, `152`, `228`, `1000000`, `1000000000000`, `1000000000000000000`.

Result:
- missing explicit values = 0;
- unlicensed/duplicate values = 0;
- baseline OPUS fails the same local guard;
- I-v2 passes.

This local guard is intentionally **not** called numeric-integrity/3.2. Full promotion still requires the real RocketDict evaluator on the identical challenge.

Durable evidence: `research/stage8-hi-probes-2026-08-27.json`.

## Handoff health blocker discovered

The public handoff is not yet bit-for-bit self-contained. `materialize_handoff.py` expects:

- 8 Stage 8 overlay parts;
- 11 Research Vault parts.

At the latest check, `main` contains only `payload/stage8-overlay/part-000.b64`; the remaining 7 overlay chunks and all 11 Research Vault chunks are absent.

See `HANDOFF_HEALTH.md` for the exact hashes and rules.

Consequences:
- the research direction, F96 results and new G/H/I mechanism evidence are durable in GitHub;
- the exact 0.30.40 Stage 8 source overlay and append-only Research Vault cannot currently be materialized from a fresh clone;
- do not fabricate those missing bytes or pretend the full ~5k rerun has been performed.

## Exact next action

1. Restore the missing verified Stage 8 overlay + Research Vault payload chunks (or an equivalent source snapshot verified against the recorded hashes).
2. Run `python rocketdict/materialize_handoff.py` and require all SHA/inventory/SQLite checks to pass.
3. Integrate G/H/I as explicit DOE cells/config identities into the real 0.30.40 pipeline.
4. Re-run the **identical F96 deterministic ~5k challenge** with `rocketdict-numeric-integrity/3.2`.
5. Acceptance remains:
   - numeric = 0;
   - critical = 0;
   - length = 0;
   - empty = 0;
   - backend errors = 0;
   - no material degradation in language/identity/semantic quality.
6. Only after that promote survivors to the 10k stratified screen. Do not jump directly to 10k or the full 104k corpus.

## Promotion status

**No Stage 8 branch is promoted yet.**

G, H and I-v2 are mechanism-positive evidence. I-v1 is a preserved negative branch. F96 remains the last full challenge measurement until the exact source snapshot is restored and the combined candidate is tested on the same challenge.
