# RocketDict maintained translation quality — L2

This file stores durable conclusions from maintained Product translation-quality work. It is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Source/tests/CI/artifacts are L3 authority and outrank this summary if they disagree.

## Maintained contracts

- Production baseline MT: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian, acceptance `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Structural labels: `rocketdict-stage12-block-structural-label-opus/2`; bare Roman sentence fragments are not headings.
- Block section identifier: `rocketdict-stage12-block-section-identifier/1`.
- Numeric/symbol hard gate: `rocketdict-maintained-numeric-integrity/5` over every selected translation row.
- Length rescue: `rocketdict-stage12-length-failure-whole-context-rescue/1`, default OFF.
- Citation-pair rescue: `rocketdict-stage12-citation-boundary-pair-rescue/1`, default OFF.
- Numeric-hard whole-context rescue: `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1`, default OFF/not public-wired.
- Illustration-label rescue: `rocketdict-stage12-illustration-label-rescue/1`, default OFF/not public-wired.
- Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`, research veto rather than Product hard gate.
- Independent research MT: pinned `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, `model.safetensors` SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0; research-only unless separate Product evidence promotes it.

## Canonical contiguous Opticks evidence

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` source characters.

Progressive persisted frontier:
- structural-label `/2` baseline run `4`: **30 numeric / 34 punctuation / 5 length**, **64 unique**;
- length+pair-citation run `7`: **29/34/0**, **59 unique**;
- numeric-hard run `8`: **25/33/0**, **55 unique**;
- illustration composition run `9`: **24/30/0**, **52 unique**.

Run `9` is the current residual basis. Workflow `34610787826`, artifact `10268850347`; output SHA `c32d7522f8e5365f6d1ca2b581532139bdfc716530993e1a720e8b4a313079be`, SQLite SHA `9e79e95f67188c751cf50a348c5d7e54ffdef73cd423c7c92601f5cb8c6332ad`, `3346` segments. Source coverage is byte-exact, untouched rows base-exact, applied illustration targets exact raw hypotheses, SQLite integrity clean and unsafe rewrite/placeholder flags false.

## Post-run9 OPUS findings

### Footnote-definition paragraphs

The five current block-start marker failures `[G]/[H]/[J]/[K]/[M]` cannot be safely solved by the local marker/body split. Marker-only workflow `34611175668` mechanically suggests **24/25/0, 47 unique**, but semantic inspection catches `shewn`→`сшито` and `_See our_`→`Посмотри на нас.`.

The corrected complete-footnote-body formulation separates source-owned marker, linguistic body and trailing blank-line bytes. Workflow `34615540238`, artifact `10269324277`, artifact digest `8320b32015600e90ea06a1aba781e928cb0efc8e365bd6539cebddd249e0d264`; evidence file SHA `87474bdc7177b701c03bf9f0dc860d79db297daa1dc4b24a00935f10cb9d7c1a`, internal evidence SHA `6226b469de51b68dcbbb7a90473ee6aa618903104b9098b722d34fefeb5db652`. Result: **0/30** beam6/n6 candidates satisfy strict checks plus emphasis preservation, so the counterfactual remains exactly **24/30/0, 52 unique**.

A depth DOE then tested beam/n-best `6/6`, `12/12`, `24/24`. Workflow `34615819431`, artifact `10269174895`, digest `d710734a482d9172020a183f86e979d35900793c6418f5e5511d59f523acfaf2`, evidence file SHA `a0a234d46f5e01078bb908eca6a8b2a40697445b953795c629489c4b326a0190`, internal evidence SHA `e6ea6ded3f9443f2e3d4cce2798095e2c5a910cf5f252b260e3ca141f9f9003e`: **210 raw hypotheses, 0 mechanically admissible**. The same exact-source OPUS n-best direction is exhausted absent a materially new source representation/model hypothesis.

### Context 2730 question-mark migration

The exact Stage10 context is 339 NLP tokens, well above the maintained 160-token rescue cap. Whole-context workflow `34616386780`, artifact `10270386478`, evidence file SHA `21742d26c7227d6485e09295fcef68509baf021a8fbcaba90cfd8c7ca760aefc`, internal evidence SHA `e2e5263ae9a2d0e2eedb570312e9e6551c663a248e229f3c2546ca0e1408fbc0`: **0/6** admissible candidates and no gate gain; outputs show long-context semantic degradation.

Two disjoint windows of 138 and 132 NLP tokens were tested in workflow `34616665018`, artifact `10270681641`, digest `f09217edc12af92cd53796eeba7c7433aa34dc494f7303fac8320801f0eb2a27`, evidence file SHA `329128ebd2fece684302ac485175b31a687fc247f1318ab133a5fa72249a1ce7`, internal evidence SHA `5e6ded9ad3e95b78478a93e565820a94939f169234da5441988edcd2f5b70a20`. The opening window has mechanically admissible rank0 and would yield **24/29/0, 51 unique**, but semantic inspection shows repetition/distortion; the closing window has no admissible candidate and loses earlier context. Mechanical strictness therefore does not justify Product rescue here.

### Square-bracket losses

Four current rows lose source square-bracket structure/payload (`[in Fig.]`, inline `[G]`, `[Greek:a]` family). Raw OPUS beam6/n6 screening workflow `34617363701`, artifact `10270323366`, digest `73f939111f70e60ef677eee55f0898fee88d6646c81c49d4eaa9a1b5dab28780`, evidence file SHA `0aff04887c1b96099e907848441422f79973d7aa6bec8ec56ca0927d1bfa3c9f`, internal evidence SHA `76d578c3de6db93a0ebc3a3658077beff402e11c4b4530c532a4b1bc03f738a8`: **0/24** admissible candidates. This is a stable baseline-model behavior, not a rank0 accident.

### Target-only delimiter additions / hallucinations

Seven current run-9 rows have source without paired delimiters while the OPUS target invents them. OPUS n-best workflow `34616844554`, artifact `10271426528`, digest `5d9d1829d7d316b458378fa45acb5e8bda468c04a9078ed0bc641491b8d06fd8`, evidence file SHA `af17c5e88ccf33ae96d7d1aeb95cc84783b9890476dc2a3335dc119d25274721`, internal evidence SHA `465d2fca5e0787ad23210858dc1db3e37c004be141b7f56d010f3d5c5b1f0abd`:
- only metadata seq `3` has strict-clean raw alternatives (first strict rank2);
- six substantive rows have **0** strict-clean candidates in beam6/n6;
- the single metadata substitution would mechanically give **24/29/0, 51 unique**, but is too narrow to justify a general Product policy.

Several substantive baseline outputs contain obvious domain hallucinations such as religious terms unrelated to the source. Their persistence across the OPUS beam shows a model-basin problem rather than a bad single rank.

## Independent TC-big differential

The pinned independent TC-big model was rerun on those seven delimiter-addition rows in workflow `34617224048`, artifact `10271482215`, digest `1c1e5cda7283171acd732431133b13acbe4a27e9406fb1da1b085325123db7a5`; evidence file SHA `77afbcd5e406f54fd71c66e493d6636ab3788f342ab075f924622d7e7176fe8c`, internal evidence SHA `e39bcd40219edc642f8e8179669ff0ece3f024b8260cd443abf2b8ef431db798`.

Strict-clean raw TC-big alternatives exist for **6/7** rows: `3,1864,1878,2219,2382,2862`; seq `3220` remains without a strict-clean alternative. In the most important hallucination cases, TC-big rank0 restores source-domain meaning instead of merely avoiding delimiters. This is strong evidence that a material part of the residual frontier is baseline-model-specific.

This result does **not** yet make TC-big a Product fallback. It establishes the next research question: how much of all 52 run-9 hard failures has a mechanically and semantically superior raw candidate from the independently pinned model, and can a source-defined failure trigger select it without degrading clean Product rows or creating a large runtime/release burden?

## Active all-52 differential

`rocketdict-workbench/tests/real_translation_full_opticks_alternative_mt_current_hard_failures_run9.py` defines a read-only screen over all 52 current hard-failing rows using the same pinned TC-big identity and six raw hypotheses. The immediate next step is a reproducible GitHub Actions workflow against immutable run-9 DB, followed by survivor-family classification and semantic review. No automatic fallback/promotion is authorized before that evidence exists.

## Durable negative evidence / promotion rules

Do not repeat unchanged without a new hypothesis:
- generic whole-context strictness can hide semantic loss (context `2725`);
- marker-only footnote splitting is semantically insufficient;
- exact-source whole-footnote OPUS n-best through 24 hypotheses yields 0 safe candidates;
- whole 339-token context 2730 and its current <=160 pair formulation are semantically unsafe;
- OPUS n-best does not solve current square-bracket-loss cases;
- OPUS n-best remains trapped for six substantive target-only delimiter hallucination rows;
- prime-fragment decomposition, thousands grouping / narrow `x→×`, compact-formula spacing and broad citation/group coalescing remain rejected from earlier evidence;
- target repair, literal injection, placeholders, source rewriting and evaluator weakening remain forbidden.

Promotion principles:
1. Never weaken maintained evaluators to make a real loss green.
2. Classify planner/evaluator/source/document/model/resource defects first.
3. Preserve immutable source/model/config/result identities.
4. Select only unmodified raw model candidates; no target surgery.
5. Mechanical integrity is necessary but not sufficient; semantic review is mandatory.
6. Research gains do not authorize Product defaults automatically.
7. Any second-model Product role needs a narrow source/failure trigger, deterministic selector, full-corpus regression, offline asset/runtime plan, license/attribution handling and release-size/performance assessment.
8. MetricX/QE may rank research candidates but is not by itself an acceptance threshold.
