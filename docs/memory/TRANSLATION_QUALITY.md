# RocketDict maintained translation quality — L2

This file stores durable conclusions from the **maintained Product** translation-quality work. It is not a changelog and it does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Raw experiment JSON/SQLite, CI logs, source, tests and Git history remain L3 and outrank this summary if they disagree.

## Current maintained contracts

- Production MT baseline: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian, acceptance compute type `float32`.
- Stage12 planner: `rocketdict-stage12-protected-split/4` in `rocketdict-product-core/src/rocketdict/translation_stage.py`.
- Stage12 ASCII-table execution: explicit source-side table parsing/logical grouping; source-owned geometry and alpha-free numeric/symbolic cells are preserved from pre-MT spans while logical text groups use real OPUS. This removed the previous table-specific numeric failure class without translating a whole table as prose or injecting missing values after MT.
- Stage15 numeric/symbol evaluator: `rocketdict-maintained-numeric-integrity/4` in `rocketdict-product-core/src/rocketdict/numeric_integrity.py`.
- Research diagnostics remain measurement surfaces, not extra Product hard gates by themselves: numeric order `/2`, delimiter preservation `/1`, critical technical token `/2`, output artifact `/2`.
- Planner/evaluator semantics that can change output or cache interpretation are versioned. Do not silently reuse results produced under an older contract as equivalent current evidence.

## Proven Product baseline

The maintained direct real Stage8→25 path and the unified user-facing `rocketdict-product-run` source→Stage25 path, including replay of the same immutable Stage25 export, are green. The old L1 blocker claiming that unified Product orchestration was still red is retired.

After the full-Opticks structural-label research addition, Product Core workflow run `34194487158` again passed both dependency-light and real-runtime jobs, including the direct maintained-core Stage8→25 smoke and the unified real `rocketdict-product-run` smoke. Research additions therefore did not regress the existing end-to-end Product path.

## Frozen maintained R1 challenge

The deterministic R1 challenge is a **diagnostic stress set**, not a representative continuous corpus. Its distant excerpts can create synthetic joins, split Gutenberg emphasis and detach section labels from their prose. A policy that repairs R1 is not promotion evidence until the same failure class is shown on contiguous source.

Durable R1 conclusions still apply:

- protected-span-aware Stage12 planning is a real positive change;
- arbitrary punctuation-preferred cuts did not solve the difficult long colour/range case;
- fine-grained clause/list splitting can make integrity metrics greener while degrading Russian semantics or introducing output artifacts;
- raw n-best hypotheses are legitimate research candidates, but broad n-best is not a universal fallback;
- source-owned structural islands can be useful for unambiguous structure, but wholesale islanding is not Product policy.

Historical `numeric-islands-v1` remains a negative branch. Do not reintroduce numeric placeholders or post-hoc literal repair under another name.

## Full contiguous Opticks numeric evidence

The current primary heavy translation evidence is the complete pinned Project Gutenberg *Opticks* source (`SHA-256 1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`). Workflow run `34193562442` at commit `ca722e6f6442b1ce51cc5ad2c9713e7133fb4232` completed successfully and retained the research DB plus JSON evidence.

Under current Stage8/10 + Stage12 `/4` semantics:

- source characters: `586543`;
- Stage8 tokens: `129825`;
- Stage10 context sentences: `3001`;
- Stage12 planned units: `3320`, with byte-exact full-source coverage;
- numeric-bearing units translated with real rank0 OPUS: `671`;
- table numeric-bearing units: `6`;
- table rank0 numeric failures: `0`;
- ordinary rank0 numeric failures: `42` total numeric failures;
- failures isolated from punctuation/length/delimiter/critical-token/output-artifact concerns: `29`;
- beam6/n-best6 strict raw-model rescues: `10`;
- the Stage8/10 research DB hash was unchanged by inference.

This is contiguous full-corpus evidence, not the old discontinuous R1 selection. It proves that the table-specific structural fix generalizes, but it also proves that rank0 OPUS still has non-table numeric/structural failures on the acceptance corpus.

Primary L3: `rocketdict-workbench/tests/real_translation_full_opticks_numeric_stress.py`, `.github/workflows/rocketdict-full-opticks-numeric-stress.yml`, workflow run `34193562442`, artifact `10043196475`.

## Staged high-beam n-best result: useful evidence, not Product policy

The same full-corpus run escalated the `19` isolated failures not rescued by beam6 to raw OPUS beam12 and then beam16, using the unchanged complete strict verdict and no target rewriting.

- additional rescues: `7`;
- residuals after beam6→12→16: `12`;
- residual sequences: `494, 638, 739, 1132, 1541, 2280, 2336, 2365, 2622, 2643, 2737, 2885`.

Manual review shows why mechanical rescue is still insufficient. At least one high-beam candidate that passes the current selector for source angle notation `2'' 45'''` renders it as Russian `2 футов 45'` — a semantic unit error. Other selected hypotheses can preserve structural numbers while leaving weak/malformed section-label text. Therefore **do not promote staged high-beam n-best as Product fallback** from the current evidence.

The apostrophe/prime notation finding also exposes a diagnostic gap: maintained numeric `/4` interprets compact forms such as `4'58` as historical apostrophe-decimals, while *Opticks* also uses apostrophes as minute/second/third prime marks. A target can therefore preserve the digits yet corrupt the prime-unit semantics and still satisfy the current numeric/strict selector. Any future n-best promotion must first distinguish apostrophe-decimal notation from numeric prime notation and evaluate prime-mark semantics explicitly; do not weaken numeric matching to hide this class.

Primary L3: `rocketdict-workbench/tests/real_translation_full_opticks_nbest_escalation.py`; run `34193562442`; `full-opticks-nbest-escalation.json`.

## Explicit structural-label split: mechanically successful, semantically rejected

A follow-up full-Opticks research probe at commits `65e0a15a53bc31bdfb152ab4d021df6d63c2ab6c` / `4e735ff5d8f06415600538427f0999b49dca2238` isolated the five remaining staged-n-best residuals containing explicit `_Exper._`, `_Obs._` or `_Qu._` labels. It translated the surrounding prose and the label separately with real OPUS; it allowed only source-owned whitespace passthrough and explicitly prohibited placeholder round-trips, alphabetic source passthrough and post-translation literal injection.

Workflow run `34194513480` passed and the probe mechanically rescued all five residuals at beam6 rank0:

- scoped/rescued sequences: `494, 1132, 1541, 2622, 2643`;
- residual after the label split within that scope: `0`.

This mechanism is **not promoted**. Manual target review found `_Exper._ 11.` / `_Exper._ 15.` translated as `Специалист...` or `Эксперты...`, `_Qu._` rendered as `Q.`/`К.` or retained in English, and only `_Obs._` produced a superficially plausible abbreviation. The checker was green while the structural-label semantics were poor. This is exactly the failure mode the Product quality-first rule is meant to prevent.

The corpus also shows that these labels are genuine source structure rather than isolated test artifacts: the immutable Opticks text contains many emphasized numbered `Exper/Obs/Qu/Prop` labels, and Stage10 frequently splits their Gutenberg emphasis across context-sentence boundaries. Any future solution should operate on byte-exact immutable source structure before MT boundaries, but it must also define semantically acceptable target handling rather than merely preserving the number.

Primary L3: `rocketdict-workbench/tests/real_translation_full_opticks_structural_label_feasibility.py`; workflow run `34194513480`; artifact `10043544860`; `full-opticks-structural-label-feasibility.json`.

## Current residual frontier

After separating the five label cases conceptually, the staged-n-best residual set contains seven non-label cases:

- numeric prime/angle notation: `638`, `2336`;
- long-unit content loss including a numeric literal: `739`;
- fraction/formula corruption: `2280`;
- very large-number corruption: `2365`, `2737`, `2885`.

These are not one defect and must not be addressed by one broad fallback. The next high-value work is to make prime-notation diagnostics semantically correct, then re-score the raw full-corpus evidence before changing generation policy. Large-number/formula cases should remain a distinct model/planner research branch. Structural-label handling requires a source-structure plus semantic-target design, not label-only MT.

## Promotion rules for translation-quality changes

1. Never make a hard gate green by weakening the evaluator when source/target evidence shows a real loss.
2. Separate evaluator defects, planner defects, source-selection artifacts, structural-document semantics and model defects before changing Product behavior.
3. Prefer source/planner fixes when the defect is created before MT; prefer raw-model candidate selection only when evidence shows the model already produced a semantically better hypothesis.
4. No post-hoc literal injection, numeric placeholders presented as final MT, fabricated closing structure, or corpus-specific target patch lists.
5. A research candidate must preserve source identity and be replayable/config-versioned before Product promotion.
6. Mechanical integrity pass is necessary but not sufficient. Inspect target-language semantics and validate on contiguous source.
7. Product promotion must retain zero empty/backend failures and must not regress direct or unified real Stage8→25 gates.
8. High-beam/n-best selection must not be promoted until prime/unit notation and other known selector blind spots are represented in the evidence surface.
