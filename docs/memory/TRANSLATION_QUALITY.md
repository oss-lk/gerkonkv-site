# RocketDict maintained translation quality — L2

This file stores durable conclusions from the **maintained Product** translation-quality work. It is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Source, tests, immutable CI artifacts and Git history are L3 authority and outrank this summary if they disagree.

## Current maintained contracts

- Production MT: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian, acceptance compute type `float32`.
- Stage12 maintained Product planner: `rocketdict-stage12-protected-split/8`.
- Structural-label contract: `rocketdict-stage12-block-structural-label-opus/2`.
  - 108 block `_Exper._/_Obs._/_Qu._` labels are isolated byte-exactly and translated only through strict raw-OPUS heading candidates.
  - 54 complete pinned-*Opticks* legacy Roman headings (`DEFIN.`, `AX.`, `PROP.`, `_PROP._ ... PROB./THEOR.`) are now the same source-owned structural family, with their own strict raw-OPUS forms.
  - Inline linguistic references remain ordinary prose; a bare `IV.`/`II.` created by sentence segmentation is **not** sufficient evidence of a structural heading.
- Block section identifier contract: `rocketdict-stage12-block-section-identifier/1`; block IDs such as `1.B.` / `1.F.3.` are source-owned structure excluded from MT, while inline references remain ordinary prose.
- ASCII-table geometry and alpha-free structural cells remain source-owned; logical text groups use real OPUS.
- Stage12 backend execution contract: `rocketdict-stage12-bounded-request-batch/1`, default batch `48`, maximum `128`; backend batching must not change planner units/model inputs/order.
- Maintained numeric hard gate: `rocketdict-maintained-numeric-integrity/5`; prime/unit notation is fail-closed.
- Research diagnostics are evidence surfaces, not Product selectors unless separately promoted.

## Current full contiguous Opticks baseline

Acceptance source: complete pinned Project Gutenberg *Opticks*, SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, `586543` immutable source characters.

The completed `/2` heavy baseline is CI run `34575909618`, artifact `10190059238`. The parallel whole-context shadow is run `34575909649`, artifact `10190367866`.

Current persisted Stage12 facts:

- selected Stage12 segments: `3353`;
- structural-label units: `162 = 108 arabic-numbered + 54 legacy-Roman`;
- structural-label model requests: `165`; escalated structural-label units: `3`;
- table blocks: `6`; logical table groups: `116`;
- total model requests: `3445`;
- complete byte-exact source coverage; real MT enabled.

Current complete maintained hard-gate inventory over the selected Stage12 rows:

- numeric failures: `27`;
- punctuation failures: `34`;
- length-ratio failures: `5`;
- unique segments failing at least one hard gate: `61`;
- split-context failures: `10` numeric, `14` punctuation, `3` length; `25` unique failing split segments in `23` Stage10 contexts.

The structural-label `/2` change removed exactly the intended legacy-heading length-loss class: the previous `/1` baseline had `24` length failures, of which `19` belonged to the newly isolated 54 legacy headings. The `/2` baseline has exactly `5`; numeric remains `27` and punctuation remains `34`. This is evidence of class-specific improvement without gate-count regression.

`rocketdict-workbench/tests/audit_full_opticks_hard_gates.py` is contract-relative (`rocketdict-full-opticks-hard-gate-inventory/2`) and independently recomputes the current persisted gate inventory. Heavy workflows now persist this JSON instead of relying only on numeric summaries.

## Whole-context content-loss research

The corpus-wide shadow `rocketdict-full-opticks-whole-context-shadow/2` evaluates unchanged Stage10 contexts against the immutable planner `/8` split baseline. It does not rewrite source/target and does not authorize Product selection.

Current `/2` shadow facts:

- split contexts within the mechanically proven 160-NLP-token cap: `451`;
- over cap: `20`;
- mechanically accepted by the existing strict selector: `234`;
- accepted with positive alphabetic-content gain: `213`;
- numeric-triggered contexts under the currently exposed opt-in Product path: `2`.

Generic alpha gain is **not** an acceptance rule. A stronger research cohort is now defined by an independently existing Product defect: only split contexts that already contain a maintained hard-gate failure are considered. On the current immutable evidence:

- `25` hard-failing split segments form `23` contexts;
- `22` contexts are within the 160-token shadow cap; `1` (`2730`) is over cap;
- the unchanged strict selector mechanically accepts `8` hard-failing contexts: `550, 669, 919, 1024, 1393, 2238, 2462, 2726`.

Manual semantic inspection found no obvious regression in these eight and clear recovered content/boundaries in the most severe examples, but that is not enough for Product promotion. `audit_full_opticks_whole_context_hard_failures.py` persists this cohort, and `real_translation_full_opticks_whole_context_metricx_qe_audit.py` is the next independent reference-free QE comparison of primary split vs raw whole-context targets. MetricX scores remain research ranking evidence only; no score threshold is an acceptance rule.

The currently exposed whole-context Product implementation remains **research opt-in** and still uses only the narrow isolated-missing-numeric trigger. Full-corpus evidence accepts known context `669`, rejects `2132`, preserves immutable primary lineage, and removes exactly one known numeric failure. Default Product behavior remains unchanged.

## Bare Roman fragments are a sentence-boundary problem, not structural labels

Two of the five current length failures are tiny rows `IV. ` and `II. ` translated as `IV. ПОЯСНИТЕЛЬНЫЕ ЗАМЕЧАНИЯ` / `II. ПОЯСНИТЕЛЬНЫЕ ЗАМЕЧАНИЯ` (ratio `12`). L3 source inspection shows they come from inline references such as `Sect. IV.` / `Sect. II.` inside footnotes after spaCy sentence segmentation.

Do **not** broaden the structural-label detector to bare Roman numerals. That would misclassify linguistic inline references as document structure. Future work should investigate Stage8/Stage10 abbreviation/sentence-boundary context preservation or another source-derived context mechanism.

## Punctuation residual is heterogeneous

The current 34 punctuation failures are not one repair class. Observed families include:

- lost square-bracket footnote markers (`[G]`, `[H]`, `[J]`, `[K]`, `[M]`, etc.);
- illustration/bracket payload mismatches;
- lost or added round parentheses, including real omitted parenthetical content and model hallucinations;
- `?` count changes and a few combined delimiter failures.

A universal punctuation fixer is therefore unsafe. Source-owned footnote/illustration structure, split-context omissions and model hallucinations must be investigated separately.

## MetricX is research evidence, not a selector contract

Pinned MetricX-24 QE (`google/metricx-24-hybrid-large-v2p6-bfloat16`, revision `febb720e29a059df2e8af3ffd71dcdc9e0a24910`) previously scored the immutable 27-failure TC-big cohort: 189 candidates across 27 cases; 13 cases had mechanically strict TC-big candidates, and MetricX preferred a strict TC-big candidate over failing OPUS in all 13. This shows QE can be informative, not that it is sufficient for Product selection.

The new whole-context MetricX audit intentionally scores only the eight strict candidates from the already-hard-failing context cohort and compares each raw whole-context target with the unchanged concatenated primary target. It must remain threshold-free and require semantic review.

## Durable negative evidence

Do not repeat unchanged without genuinely new evidence:

- prime-fragment structural decomposition: mechanically strong but semantically unacceptable (`53 deg.` → `53 балла`, `hundred Feet` → `сто ног`); whole-unit prime normalization/hints and broad staged n-best also do not solve the class;
- long-integer thousands grouping / `x→×`: rescued `0/4` baseline failures and regressed some successful cases;
- compact-formula operator spacing for the `3/8A ... ((61-1/2)/8)A` class: no rescue even with staged raw n-best;
- broad n-best fallback and historical numeric-island/target-repair approaches remain rejected.

Prime notation, formula/fraction corruption and very-large-integer corruption remain separate unresolved model/notation families.

## Promotion rules

1. Quality is a release invariant; never weaken evaluators to make a real loss green.
2. Identify planner, evaluator, source-selection, document-structure, resource or model defects before changing Product behavior.
3. Prefer source/planner fixes for pre-MT defects; select raw-model candidates only when evidence shows a semantically valid candidate exists.
4. Source-owned bytes may bypass MT only for exhaustively identified non-linguistic structure; inline linguistic references stay ordinary.
5. No post-hoc literal insertion, final placeholders, fabricated closing structure or corpus-specific target patch lists.
6. A promoted mechanism must preserve source identity, be versioned/replayable and have contiguous-corpus evidence.
7. Mechanical integrity is necessary but not sufficient; semantic review/QE evidence must not be collapsed into a single automatic threshold without validation.
8. Product promotion must preserve zero empty/backend failures and direct/unified real Stage8→25 behavior.
9. Narrow n-best or rescue escalation requires a source-defined trigger and explicit evidence; broad fallback remains rejected.
10. Expensive negative results belong here so future iterations do not repeat them blindly.
