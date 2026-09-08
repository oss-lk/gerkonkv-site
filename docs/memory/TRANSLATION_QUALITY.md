# RocketDict maintained translation quality — L2

This file stores durable conclusions from the **maintained Product** translation-quality work. It is not a changelog and it does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). Raw experiment JSON/SQLite, CI logs, source, tests and Git history remain L3 and outrank this summary if they disagree.

## Current maintained contracts

- Production MT baseline: pinned official OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian, acceptance compute type `float32`.
- Stage12 current Product planner: `rocketdict-stage12-protected-split/4` in `rocketdict-product-core/src/rocketdict/translation_stage.py`.
- Stage12 ASCII-table execution: explicit source-side table parsing/logical grouping; source-owned geometry and alpha-free numeric/symbolic cells are preserved from pre-MT spans while logical text groups use real OPUS. Table numeric failures are zero on the complete pinned *Opticks* evidence.
- Stage15 numeric/symbol evaluator: `rocketdict-maintained-numeric-integrity/5`. Numeric prime/unit notation is part of the Product hard gate.
- Maintained structural-label source/selector contract exists as `rocketdict-stage12-block-structural-label-opus/1` in `rocketdict-product-core/src/rocketdict/structural_labels.py`, but it is **not yet integrated into Product Stage12** at the current checkpoint.
- Research diagnostics remain measurement surfaces unless explicitly promoted. Broad raw n-best selection is not Product fallback policy.
- Planner/evaluator/execution semantics that can change output or cache interpretation must be versioned.

## Proven Product baseline

The maintained direct real Stage8→25 path and the unified user-facing `rocketdict-product-run` source→Stage25 path, including replay of the same immutable Stage25 export, are green. Product Core workflow run `34207018066` passed dependency-light and real-runtime jobs after the prime-v5 and structural-label research additions.

The old orchestration blocker is retired. Current work is translation-quality hardening on the contiguous acceptance corpus, not recovery of the unified runner.

## Frozen maintained R1 challenge

The deterministic R1 challenge is a diagnostic stress set, not a representative continuous corpus. Its distant excerpts can create synthetic joins, split Gutenberg emphasis and detach section labels from prose. Durable conclusions remain:

- protected-span-aware Stage12 planning is a real positive change;
- arbitrary punctuation-preferred cuts did not solve difficult long numeric/content-loss cases;
- fine-grained splitting can improve narrow integrity metrics while worsening Russian semantics;
- raw OPUS n-best hypotheses are legitimate research evidence, but broad n-best fallback is not Product policy;
- source-owned structural handling is acceptable only when evidence identifies genuine document structure before MT;
- historical `numeric-islands-v1` remains a negative branch; do not reintroduce placeholders or target-side literal repair.

## Full contiguous Opticks evidence under numeric `/5`

Primary acceptance-quality source: complete pinned Project Gutenberg *Opticks*, SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`.

Fresh `/5` heavy workflow run `34205049701`, artifact `10047696652`, completed successfully. Relevant facts:

- source characters: `586543`;
- Stage8 tokens: `129825`;
- Stage10 context sentences: `3001`;
- Stage12 `/4` planned units: `3320`, byte-exact full-source coverage;
- numeric-bearing units translated with real rank0 OPUS: `671`;
- table numeric-bearing units: `6`; table rank0 numeric failures: `0`;
- rank0 numeric hard failures under maintained numeric `/5`: `49` (old `/4` had reported `42`);
- the seven additional failures are real prime-notation false passes closed by `/5`, not threshold tightening for convenience;
- staged generic n-best beam6→12→16 leaves 10 residual sequences: `494, 739, 1132, 1541, 2280, 2365, 2622, 2643, 2737, 2885`.

The generic residuals are heterogeneous and must not be handled by one broad fallback. Five are structural-label cases (`494, 1132, 1541, 2622, 2643`); the other five include long-unit content loss, fraction/formula corruption and large-number corruption.

## Prime notation is now a Product hard-gate invariant

Full-corpus prime stress found 17 prime-bearing Stage12 units / 38 prime events. Rank0 OPUS corrupted prime semantics in 11 units; seven of those had passed numeric `/4`. Examples include minute/second marks becoming feet or losing prime count.

Therefore numeric `/4` was incomplete, and `/5` is the maintained Product contract. This was a hardening change, not checker weakening. Product Core direct and unified real Stage8→25 remained green after promotion.

Do not treat apostrophe decimals and prime/unit notation as the same phenomenon. Do not weaken prime matching to recover old pass counts.

## Generic n-best remains non-Product

Fresh `/5` evidence confirms that simply increasing beam is not a general solution. A previously selected high-beam hypothesis could translate `2'' 45'''` as `2 футов 45'` while satisfying old mechanical checks. Prime-aware diagnostics correctly reject such cases.

Raw n-best is allowed only when a narrowly scoped, source-defined mechanism has independent semantic evidence and a fail-closed selector. That principle is what permits the structural-label experiment below without licensing broad n-best fallback.

## Structural Gutenberg labels: source/planner defect proven on full corpus

Supported historical block labels are `_Exper._ N.`, `_Obs._ N.`, `_Qu._ N.`. The literal source-side expansions are `Experiment N.`, `Observation N.`, `Query N.`; required Russian structural terms are `Эксперимент`, `Наблюдение`, `Вопрос`.

### Why plain label splitting was rejected

An earlier probe translated the abbreviation itself separately. It mechanically preserved the number but produced poor semantics such as `_Exper._ → Специалист/Эксперты` and `_Qu._ → Q./К.`. That mechanism remains rejected.

Whole-unit canonicalization was also tested: replacing the abbreviation in the full old Stage12 unit while keeping the whole unit as one OPUS request rescued **0/5** known residuals. OPUS still dropped the structural label/number. Thus the defect is not solved by preprocessing the old unit; structural decomposition is required.

### Source-side canonicalization evidence

A separate research mechanism keeps immutable source spans unchanged but sends the isolated label to real OPUS using only a literal source-side abbreviation expansion. No placeholder round-trip, source alphabetic passthrough or target-side literal injection is allowed.

Known five residual labels were rescued with semantic + numeric acceptance using raw model hypotheses. More importantly, a complete inventory over all supported labels in the immutable *Opticks* source found:

- supported label events: **109**;
- beam6 provides an acceptable semantic+numeric raw candidate for **106/109**;
- all three beam6 unresolved events are the same canonical request `Observation 1.`;
- staged beam12 supplies raw `Наблюдение 1.` (rank5), giving **109/109 coverage** without target rewriting.

Primary runs/artifacts: canonicalization run `34207074507`, artifact `10048204602`; all-label inventory run `34208337952`, artifact `10048735151`; staged escalation run `34209680326`, artifact `10049272284`.

### Current planner `/4` is structurally wrong for this class

Planner inventory run `34210312015`, artifact `10049542652`, maps all 109 immutable-source labels to current Stage12 `/4` units:

- only **61/109** are wholly contained in one planned unit;
- **48/109 cross Stage12 unit boundaries**;
- 44 cross two units; 4 cross three units;
- among contained cases: 41 are suffix labels after prose, 19 are already label-only, and exactly 1 is inline;
- the single inline occurrence is `(_Exper._ 10. _Part_ 2.)` and must remain on the ordinary text path;
- the other **108** are block structural labels.

Therefore the next Product planner contract must change before execution selection: supported block labels must become byte-exact atomic standalone units. An execution-only special case layered over planner `/4` would be incorrect because almost half the source labels are already fragmented before MT.

## Structural-label Product promotion requirements

The maintained source-only/selector contract `rocketdict-stage12-block-structural-label-opus/1` is intentionally narrow:

1. recognize only supported **block** labels `_Exper._`, `_Obs._`, `_Qu._` with a number and trailing period;
2. preserve immutable source bytes/spans exactly;
3. isolate block labels in Stage12 planning; do not rewrite the single inline label case;
4. model input may expand only the source abbreviation to its literal English full form;
5. try raw OPUS beam6 first and beam12 only if that label remains unresolved;
6. accept only raw target of strict form `Эксперимент/Наблюдение/Вопрос N.` with the same number and numeric `/5` pass;
7. fail closed if no candidate exists;
8. do not inject target text, placeholders, fabricated punctuation or corpus-specific target patches;
9. do not generalize this mechanism into broad n-best fallback.

At the current checkpoint the contract/tests exist, but Product `translation_stage.py` still uses planner `/4`; promotion is the active implementation frontier.

## Current non-label residual frontier

Once structural labels are handled separately, remaining generic residual classes are:

- long-unit content loss including numeric literals (`739`);
- fraction/formula corruption (`2280`);
- very large-number corruption (`2365`, `2737`, `2885`).

These should remain separate research branches. Do not infer that structural-label success solves them.

## Promotion rules for translation-quality changes

1. Never make a hard gate green by weakening an evaluator when evidence shows real source/target loss.
2. Separate evaluator, planner, source-selection, document-structure and model defects before changing Product behavior.
3. Prefer source/planner fixes when the defect is created before MT; use raw-model candidate selection only when evidence proves a semantically valid candidate already exists.
4. No post-hoc literal injection, placeholders presented as final MT, fabricated closing structure or corpus-specific target patch lists.
5. A promoted mechanism must preserve source identity, be versioned/replayable and have contiguous-corpus evidence.
6. Mechanical integrity pass is necessary but not sufficient; inspect target semantics.
7. Product promotion must retain zero empty/backend failures and must not regress direct/unified real Stage8→25.
8. Narrow n-best escalation requires a source-defined class and explicit semantic selector; broad fallback remains rejected.
