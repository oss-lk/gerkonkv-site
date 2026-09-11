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
- Length-failure whole-context rescue is exposed under `rocketdict-stage12-length-failure-whole-context-rescue/1` with selector `rocketdict-stage12-length-failure-whole-context-selector/1`. It is **opt-in and disabled by default**.
- Citation-boundary pair rescue is exposed under `rocketdict-stage12-citation-boundary-pair-rescue/1` with selector `rocketdict-stage12-citation-boundary-pair-selector/1`. It is **opt-in and disabled by default** and composes on top of the length-rescue stage.
- Research diagnostics are evidence surfaces, not Product selectors unless separately promoted.

## Canonical full contiguous Opticks baseline

Acceptance source: complete pinned Project Gutenberg *Opticks*, source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` immutable source characters.

The structural-label `/2` Product baseline is CI run `34575909618`, artifact `10190059238`. Baseline JSON SHA-256 is `48385b0b9e2539c9b82feb1f98fa68b660307aa1f76ce58e6e56ed6a93f32133`; baseline SQLite SHA-256 is `eaff048389e8cdabfd9dc47af0bc841e77657122883ee1bf10b26de7575d4b8c`. Canonical Stage12 run id is `4`, output SHA-256 `b5c42141767a9760495c84023349402bf637b6591f3fa60d723d42c7d5760e22`.

Canonical maintained hard-gate inventory:

- selected Stage12 segments: `3353`;
- complete numeric/symbol failures: `30`;
- punctuation failures: `34`;
- length-ratio failures: `5`;
- unique segments failing at least one hard gate: `64`.

The historical `product_numeric_failure_count = 27` remains only the literal-bearing stress subset. The complete Product gate adds three non-literal-source failures: sequence `617` invents `=`, sequence `1798` renders spelled `ten hundred thousand` as target literal `100 000`, and sequence `3013` invents `=` before `_per deliquium_`.

## Opt-in length-failure whole-context rescue

The narrow length rescue targets an already-maintained length hard failure inside a split Stage10 context, uses the exact whole context as model input, and accepts only an unchanged raw rank-0 OPUS candidate that clears the maintained Product hard gates. It does not rewrite source or target and performs no placeholder/literal injection.

Full-*Opticks* persisted Product audit: workflow run `34596212688`; the same path was rerun successfully through the later public Stage12 wrapper as `34597532192`.

Canonical evidence:

- accepted Stage10 contexts: `577`, `629`, `919`;
- resulting Stage12 run id: `6`;
- output SHA-256: `2224d71b20df64e853db1480380f4a78f01184d9021ef8e35142a66dd99d8437`;
- segments: `3350`;
- hard gates: `29` numeric/symbol, `34` punctuation, `2` length;
- unique hard-failing segments: `61`.

The mechanism therefore removes three current length failures and incidentally removes one numeric/symbol failure without weakening any evaluator. It remains opt-in because mechanical improvement alone is not sufficient promotion evidence.

## Bare Roman fragments are inline citation boundaries, not headings

Two canonical length failures were tiny rows `IV. ` and `II. ` translated as explanatory headings. L3 source inspection proves that both are sentence-split tails of inline references `Sect. IV.` / `Sect. II.`. Do **not** broaden structural-label detection to standalone Roman fragments.

A broad citation-context merge was tested earlier and is unsafe: one relevant whole-group candidate lost numeric content and a footnote marker. The safe research direction was therefore narrowed to the exact previous-row + Roman-fragment pair.

Pair feasibility run `34597127952`, artifact `10261744281`, evidence JSON SHA-256 `0f90314ad6831647234ae6576b25c407d5c5fdb66dd11fa6e9b71c06404fbc49`, established:

- `Sect. IV.` pair raw rank-0: `[А] В части I раздела IV нашего автора.`; Product hard gates and length pass; the only strict debt is the already-existing footnote-marker debt, so no new debt category is introduced;
- `Sect. II.` pair raw rank-0: `Раздел II части I.`; Product hard gates, length and strict checks all pass;
- 2/2 pairs are mechanically promising; 1/2 is fully strict-clean.

This evidence justified the narrow Product implementation `rocketdict-stage12-citation-boundary-pair-rescue/1`.

### Citation pair selector contract

Trigger remains deliberately closed:

- current row is only an uppercase Roman fragment matching `[IVXLCDM]+.\s*`;
- immediately previous ordinary row ends with `Sect.`;
- spans are contiguous source bytes;
- rows are not source-owned `ascii_table`, `structural_label`, or `block_section_identifier` units;
- the Roman-fragment row already fails the maintained length gate;
- exact pair source length is within the bounded cap.

Acceptance requires:

1. raw rank-0 OPUS output on the exact contiguous pair;
2. maintained Product hard gates pass;
3. maintained length gate passes;
4. strict-debt categories do not worsen relative to the original two rows.

No source rewrite, target rewrite, placeholders or post-translation literal injection are permitted. The accepted pair is persisted as one merged translation row covering exactly the original contiguous source bytes.

## Combined full-Opticks Product audit

The composed opt-in path enables both narrow length rescue and citation pair rescue while keeping both disabled by default in normal Product execution.

Heavy workflow run `34597648856` completed successfully; artifact `10263095872`, artifact digest SHA-256 `e2407b28bd7d9a6f76e614551117e8feb8d4729373911b6a33cf53aacacd2aa7`. Evidence JSON schema is `rocketdict-full-opticks-combined-length-citation-product-rescue-optin/1`, SHA-256 `5edfe5b917c2274332ff27ce1e3be5191c95a4a8879a9a643a29ecb2516316da`.

Composed result:

- baseline: `30` numeric / `34` punctuation / `5` length, `64` unique failures, `3353` segments;
- length rescue only: `29` / `34` / `2`, `61` unique failures, `3350` segments;
- length + citation pair: **`29` / `34` / `0`**, **`59` unique failures**, `3348` segments;
- combined Stage12 run id: `7`;
- combined output SHA-256: `b9e61f1f381ac9cd32e450e66c36a1f16d380eb2ef8b20c18ed7fc5bfc2c38e8`;
- accepted length contexts: `577`, `629`, `919`;
- accepted citation-pair source starts: `24799`, `151438`;
- copied length-base rows: `3346`; applied citation pairs: `2`;
- source coverage remains byte-exact;
- untouched rows are base-exact;
- applied targets are exact raw rank-0 hypotheses;
- all rewrite/placeholder safety flags are false;
- resulting SQLite SHA-256: `afc9eba1177e1ada86ae208d3f175cc34f84cd287145b236f4dad79fd73f7f67`;
- SQLite `integrity_check=ok`; foreign-key check is empty.

This closes the complete current length-hard-failure class in the opt-in composition and reduces the complete numeric/symbol gate by one. It **does not authorize default promotion**. The artifact explicitly keeps `promotion_allowed=false`, `automatic_product_default_allowed=false`, and requires semantic review.

## Current unresolved frontier

After the composed opt-in audit, the remaining hard-gate frontier is:

- `29` numeric/symbol failures;
- `34` punctuation failures;
- `0` length failures;
- `59` unique failing segments.

Because `29 + 34 - 59 = 4`, four residual segments fail both numeric/symbol and punctuation gates.

The next safe research step is to inventory these residuals by immutable source span/context identity on the composed run, not by assuming old sequence numbers survive row merges. Recompute which residuals still belong to split Stage10 contexts and cross-reference them against existing whole-context shadow evidence before proposing any broader selector.

## Whole-context content-loss research remains non-default

The corpus-wide shadow `rocketdict-full-opticks-whole-context-shadow/2` evaluates unchanged Stage10 contexts against the immutable planner `/8` split baseline. It does not rewrite source/target and does not authorize Product selection.

Durable baseline facts:

- split contexts within the mechanically proven 160-NLP-token cap: `451`;
- over cap: `20`;
- mechanically accepted by the existing strict selector: `234`;
- accepted with positive alphabetic-content gain: `213`.

Generic alpha gain is **not** an acceptance rule. In the canonical already-hard-failing split cohort, `26` failing segments formed `24` Stage10 contexts; `23` fit the 160-token cap, and the existing strict selector accepted nine contexts: `550, 669, 919, 1024, 1393, 2238, 2462, 2725, 2726`.

Context `2725` remains useful evidence: split output invents `=`, while unchanged whole-context raw rank-0 removes it, preserves the question, passes strict checks and increases alphabetic target content. But the composed run has already changed some rows/contexts (including `919`), so any future hard-failure whole-context mechanism must recompute the cohort against the **current composed source-span identities** rather than blindly reuse canonical sequence/context numbers.

The pre-existing whole-context Product implementation remains research opt-in and narrowly triggered. Broad fallback/rewrite/literal injection/placeholders remain forbidden.

## Punctuation residual is heterogeneous

The current 34 punctuation failures are not one repair class. Observed families include:

- lost square-bracket footnote markers (`[G]`, `[H]`, `[J]`, `[K]`, `[M]`, etc.);
- illustration/bracket payload mismatches;
- lost or added round parentheses, including real omitted parenthetical content and model hallucinations;
- `?` count changes and combined delimiter failures.

A universal punctuation fixer is unsafe. Source-owned footnote/illustration structure, split-context omissions and model hallucinations must be investigated separately.

## MetricX is research evidence, not a selector contract

Pinned MetricX-24 QE (`google/metricx-24-hybrid-large-v2p6-bfloat16`, revision `febb720e29a059df2e8af3ffd71dcdc9e0a24910`) may compare immutable raw candidates, but neither a score nor “MetricX prefers candidate” is sufficient for Product selection. Scores are ranking evidence only and require mechanical gates plus semantic review.

## Durable negative evidence

Do not repeat unchanged without genuinely new evidence:

- prime-fragment structural decomposition: mechanically strong but semantically unacceptable (`53 deg.` → `53 балла`, `hundred Feet` → `сто ног`); whole-unit prime normalization/hints and broad staged n-best also do not solve the class;
- long-integer thousands grouping / `x→×`: rescued `0/4` baseline failures and regressed some successful cases;
- compact-formula operator spacing for the `3/8A ... ((61-1/2)/8)A` class: no rescue even with staged raw n-best;
- broad n-best fallback and historical numeric-island/target-repair approaches remain rejected;
- broad citation/group coalescing is rejected for the Roman-inline-reference class because it can remove unrelated numeric and footnote content.

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
