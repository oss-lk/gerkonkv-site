# RocketDict maintained translation quality — L2

This file stores durable conclusions from the **maintained Product** translation-quality work. It is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Source, tests, immutable CI artifacts and Git history are L3 authority and outrank this summary if they disagree.

## Current maintained contracts

- Production MT: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian, acceptance compute type `float32`.
- Stage12 maintained Product planner: `rocketdict-stage12-protected-split/8`.
- Structural-label contract: `rocketdict-stage12-block-structural-label-opus/2`.
  - 108 block `_Exper._/_Obs._/_Qu._` labels are isolated byte-exactly and translated only through strict raw-OPUS heading candidates.
  - 54 complete pinned-*Opticks* legacy Roman headings (`DEFIN.`, `AX.`, `PROP.`, `_PROP._ ... PROB./THEOR.`) are the same source-owned structural family, with their own strict raw-OPUS forms.
  - Inline linguistic references remain ordinary prose; a bare `IV.`/`II.` created by sentence segmentation is **not** sufficient evidence of a structural heading.
- Block section identifier contract: `rocketdict-stage12-block-section-identifier/1`; block IDs such as `1.B.` / `1.F.3.` are source-owned structure excluded from MT, while inline references remain ordinary prose.
- ASCII-table geometry and alpha-free structural cells remain source-owned; logical text groups use real OPUS.
- Stage12 backend execution contract: `rocketdict-stage12-bounded-request-batch/1`, default batch `48`, maximum `128`; backend batching must not change planner units/model inputs/order.
- Maintained numeric/symbol hard gate: `rocketdict-maintained-numeric-integrity/5`; prime/unit notation is fail-closed and the gate applies to **all** selected translation rows, not only rows whose source contains a digit literal.
- Research diagnostics are evidence surfaces, not Product selectors unless separately promoted.

## Current full contiguous Opticks baseline

Acceptance source: complete pinned Project Gutenberg *Opticks*, SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, `586543` immutable source characters.

The completed structural-label `/2` Product baseline is CI run `34575909618`, artifact `10190059238`. The parallel whole-context shadow is run `34575909649`, artifact `10190367866`.

Current persisted Stage12 facts:

- selected Stage12 segments: `3353`;
- structural-label units: `162 = 108 arabic-numbered + 54 legacy-Roman`;
- structural-label model requests: `165`; escalated structural-label units: `3`;
- table blocks: `6`; logical table groups: `116`;
- total model requests: `3445`;
- complete byte-exact source coverage; real MT enabled.

### Numeric-stress subset versus complete Product numeric/symbol gate

The historical field `product_numeric_failure_count = 27` in `rocketdict-full-opticks-numeric-stress/3` is **not** the complete Product numeric/symbol failure count. That harness first filters to source rows satisfying `extract_numeric_literals(source)` and therefore measures a literal-bearing stress subset. Keep the value for compatibility/research, but never cite it as the complete Stage15 numeric/symbol gate.

The complete Product gate is `evaluate_numeric_symbol_pair` / `rocketdict-maintained-numeric-integrity/5` over every selected Stage12 row. Direct recomputation from the immutable `/2` SQLite artifact gives:

- complete numeric/symbol failures: `30`;
- literal-bearing subset: `27` (the historical stress value);
- additional failures whose source has no extracted digit literal: sequences `617, 1798, 3013`;
  - `617`: target invents `=` in ordinary prose;
  - `1798`: source phrase `ten hundred thousand` becomes target literal `100 000`, an unlicensed and semantically unsafe numeric rendering;
  - `3013`: target invents `=` before `_per deliquium_`.

`audit_full_opticks_hard_gates.py` now uses `rocketdict-full-opticks-hard-gate-inventory/3`: it independently recomputes the complete gate while also proving that the exact historical 27-sequence literal-bearing subset is unchanged. This preserves backward evidence without hiding symbol-only / target-added-number failures.

The resulting complete maintained hard-gate inventory is:

- numeric/symbol failures: `30` (`27` literal-bearing + `3` non-literal-source);
- punctuation failures: `34`;
- length-ratio failures: `5`;
- unique segments failing at least one hard gate: `64`;
- split-context failures: `11` numeric/symbol, `14` punctuation, `3` length;
- `26` unique failing split segments in `24` Stage10 contexts.

The structural-label `/2` change removed exactly the intended legacy-heading length-loss class: the previous `/1` baseline had `24` length failures, of which `19` belonged to the newly isolated 54 legacy headings. The `/2` baseline has exactly `5`; the literal-bearing numeric stress remains `27` and punctuation remains `34`. The three newly surfaced numeric/symbol failures existed in the same Product output but were outside the old stress harness scope; they are not a regression caused by `/2`.

Heavy CI is being rerun with inventory `/3`; until those replacement runs complete, the `30/64/24` figures above are grounded in direct immutable-artifact recomputation rather than a green `/3` CI artifact.

## Whole-context content-loss research

The corpus-wide shadow `rocketdict-full-opticks-whole-context-shadow/2` evaluates unchanged Stage10 contexts against the immutable planner `/8` split baseline. It does not rewrite source/target and does not authorize Product selection.

Current `/2` shadow facts:

- split contexts within the mechanically proven 160-NLP-token cap: `451`;
- over cap: `20`;
- mechanically accepted by the existing strict selector: `234`;
- accepted with positive alphabetic-content gain: `213`;
- numeric-triggered contexts under the currently exposed opt-in Product path: `2`.

Generic alpha gain is **not** an acceptance rule. A stronger research cohort is defined by an independently existing Product defect: only split contexts that already contain at least one maintained hard-gate failure are considered. After correcting the complete numeric/symbol scope:

- `26` hard-failing split segments form `24` contexts;
- `23` contexts are within the 160-token shadow cap; `1` (`2730`) is over cap;
- the unchanged strict selector mechanically accepts `9` hard-failing contexts: `550, 669, 919, 1024, 1393, 2238, 2462, 2725, 2726`.

The added context `2725` is evidence-bearing rather than a bookkeeping artifact: its primary split target invents `=` before `_per deliquium_`; unchanged whole-context raw rank-0 removes the false symbol, preserves the complete question, passes the strict selector and increases alphabetic target content (`214→220`). No target rewrite, literal insertion or placeholder is involved.

Manual semantic inspection has found no obvious regression in the nine strict candidates and clear recovered content/boundaries in the strongest examples, but this is not enough for Product promotion. `audit_full_opticks_whole_context_hard_failures.py` consumes hard-gate inventory `/3`. `real_translation_full_opticks_whole_context_metricx_qe_audit.py` compares the unchanged primary split target with the unchanged raw whole-context target for every mechanically accepted hard-failure candidate. MetricX scores remain research ranking evidence only; no score threshold is an acceptance rule.

The currently exposed whole-context Product implementation remains **research opt-in** and still uses only the narrow isolated-missing-numeric trigger. Existing full-corpus evidence accepts known context `669`, rejects `2132`, preserves immutable primary lineage, and removes exactly one known literal-bearing numeric failure. Default Product behavior remains unchanged.

## Bare Roman fragments are a sentence-boundary problem, not structural labels

Two of the five current length failures are tiny rows `IV. ` and `II. ` translated as `IV. ПОЯСНИТЕЛЬНЫЕ ЗАМЕЧАНИЯ` / `II. ПОЯСНИТЕЛЬНЫЕ ЗАМЕЧАНИЯ` (ratio `12`). L3 source inspection shows they come from inline references such as `Sect. IV.` / `Sect. II.` inside footnotes after spaCy sentence segmentation.

Do **not** broaden the structural-label detector to bare Roman numerals. That would misclassify linguistic inline references as document structure. Product already has `protected_sentence_boundary_coalesced`, which successfully keeps an analogous protected `Sect. II./III.` source together; the useful next investigation is a narrow abbreviation/sentence-boundary context rule, not a new heading class.

## Punctuation residual is heterogeneous

The current 34 punctuation failures are not one repair class. Observed families include:

- lost square-bracket footnote markers (`[G]`, `[H]`, `[J]`, `[K]`, `[M]`, etc.);
- illustration/bracket payload mismatches;
- lost or added round parentheses, including real omitted parenthetical content and model hallucinations;
- `?` count changes and a few combined delimiter failures.

A universal punctuation fixer is unsafe. Source-owned footnote/illustration structure, split-context omissions and model hallucinations must be investigated separately.

## MetricX is research evidence, not a selector contract

Pinned MetricX-24 QE (`google/metricx-24-hybrid-large-v2p6-bfloat16`, revision `febb720e29a059df2e8af3ffd71dcdc9e0a24910`) previously scored the immutable 27-case literal-bearing TC-big cohort: 189 candidates across 27 cases; 13 cases had mechanically strict TC-big candidates, and MetricX preferred a strict TC-big candidate over failing OPUS in all 13. This shows QE can be informative, not that it is sufficient for Product selection.

The whole-context MetricX audit now targets the **nine** strict candidates from the complete already-hard-failing context cohort and compares each raw whole-context target with the unchanged concatenated primary target. `.github/workflows/rocketdict-full-opticks-whole-context-metricx-qe.yml` is wired to a successful whole-context DOE artifact; verify actual trigger/execution before treating MetricX results as available. The audit remains threshold-free and requires semantic review.

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
10. Full-gate reports must distinguish literal-bearing stress subsets from complete Product evaluators; subset metrics may not be relabeled as release-wide counts.
11. Expensive negative results belong here so future iterations do not repeat them blindly.
