# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`
- Engineering branch: `chatgpt/product-core-forward`
- Checkpoint before this state refresh: `f04e09a19d6a90a78314506a8085edff250ae4ee`
- Maintained Product Core + Workbench remain the forward implementation.
- Current frontier is full-corpus translation-quality hardening; Product behavior has **not** been broadened by the current research work.

## Recovery protocol

Follow `AGENTS.md`:
1. Compare current HEAD against the checkpoint above.
2. Use `docs/memory/INDEX.md` as L2 router.
3. Use source/tests/CI/artifacts as L3 authority.

## Maintained translation contracts

- Real EN→RU: pinned OPUS `opus-2020-02-11` → CTranslate2 Marian, acceptance `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`.
  - 108 `_Exper._/_Obs._/_Qu._` block labels.
  - 54 complete legacy Roman block headings.
  - total current full-*Opticks* structural units: 162.
- Block section IDs: `rocketdict-stage12-block-section-identifier/1`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`.
- Whole-context rescue remains research opt-in; default Product policy is unchanged.

## Current full-Opticks evidence

Pinned source SHA-256: `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, `586543` source characters.

Completed `/2` evidence:
- Product Stage12 audit run `34575909618`, artifact `10190059238`;
- whole-context shadow run `34575909649`, artifact `10190367866`.

Current selected Stage12 baseline:
- 3353 segments;
- 27 numeric failures;
- 34 punctuation failures;
- 5 length failures;
- 61 unique hard-failing segments.

Split-context residual:
- 25 hard-failing split segments in 23 Stage10 contexts;
- 22 of those contexts fit the 160-NLP-token whole-context cap;
- existing strict selector mechanically accepts 8: `550, 669, 919, 1024, 1393, 2238, 2462, 2726`;
- context `2730` is over cap.

The `/2` legacy-heading expansion removed the intended class exactly: length failures fell from 24 to 5 (19 removed), while numeric remained 27 and punctuation 34.

## Active investigation

Primary branch: **hard-failure-triggered whole-context semantic recovery**.

Rules:
- do not select from the 234 mechanically clean whole-context candidates corpus-wide merely because they are clean;
- restrict the next semantic/QE study to contexts that already fail a maintained Product hard gate;
- keep source bytes immutable and targets raw;
- no target repair, placeholders or literal injection;
- no Product promotion until independent semantic evidence exists.

New research surfaces:
- `rocketdict-workbench/tests/audit_full_opticks_hard_gates.py` — complete contract-relative Product hard-gate inventory;
- `rocketdict-workbench/tests/audit_full_opticks_whole_context_hard_failures.py` — exact 23-context hard-failure cohort;
- `rocketdict-workbench/tests/real_translation_full_opticks_whole_context_metricx_qe_audit.py` — prepared MetricX comparison for the eight mechanically accepted hard-failure candidates; not yet executed on that cohort.

Heavy workflow integration is committed. Validation runs currently in progress:
- Product hard-gate artifact run `34579882684`;
- whole-context hard-failure cohort run `34579912034`.

## Important residual classifications

- Bare `IV.` / `II.` length failures come from inline `Sect. IV.` / `Sect. II.` references split by sentence segmentation. They are **not structural headings**. Investigate Stage8/Stage10 context boundaries rather than broadening structural regexes.
- The 34 punctuation failures are heterogeneous: footnote markers, illustration brackets, parenthetical omission/addition and question-mark drift. Do not introduce one universal punctuation fixer.
- Prime/unit ambiguity, compact formula/fraction corruption and very-large-integer corruption remain separate unresolved classes with documented negative experiments in L2.

## Forbidden shortcuts

Never promote:
- target literal insertion or fabricated structure;
- corpus-specific target patches;
- identity/dictionary substitution as translation;
- evaluator weakening;
- generic structural-island rules for inline linguistic text;
- broad n-best or whole-context fallback without semantic evidence.

## Next useful actions

1. Consume runs `34579882684` and `34579912034`; verify persisted hard-gate/cohort JSON against the already reproduced `/2` counts.
2. If the cohort run is green, run the pinned MetricX whole-context audit on exactly the eight strict hard-failure candidates.
3. Use QE only as ranking evidence, then decide whether any source-defined trigger is strong enough for a Product experiment.
4. Separately investigate inline abbreviation/sentence segmentation for the residual `Sect. IV./II.` length failures.

## Hot paths

- `rocketdict-product-core/src/rocketdict/translation_stage.py`
- `rocketdict-product-core/src/rocketdict/translation_rescue_stage.py`
- `rocketdict-product-core/src/rocketdict/structural_labels.py`
- `rocketdict-product-core/src/rocketdict/legacy_block_headings.py`
- `rocketdict-workbench/tests/real_translation_full_opticks_*`
- `rocketdict-workbench/tests/audit_full_opticks_*`
- `.github/workflows/`
