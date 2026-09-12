# RocketDict project state — L1

> Volatile operational memory. Replace stale state; Git history contains chronology.

## Current state

- Repository: `oss-lk/gerkonkv-site`; engineering branch: `chatgpt/product-core-forward`.
- Engineering checkpoint authenticated here: `041b0293eecccc375c6264a39704e6b25d2b6665` (`Validate effective rank0 replay boundary`).
- Authoritative Product contract: `rocketdict/PRODUCT_TARGET.md`. Release still requires **0 unresolved numeric/symbol, punctuation and length hard failures** on the complete 90k+ corpus, then complete learner/export coverage and Windows clean-install validation.
- Historical run `23` remains immutable research evidence (**17 numeric / 14 punctuation / 0 length, 30 unique, 3337 rows**) but is not legal promotion lineage because historical automatic rank>0 choices were proven.
- The corrected full-Opticks rank0-clean replay is now authenticated and is the **only forward promotion parent**.

## Recovery protocol

Follow `AGENTS.md`: compare current HEAD with the checkpoint above, then route through `docs/memory/INDEX.md`. For current translation work load `docs/memory/TRANSLATION_QUALITY.md` and `docs/memory/DECISIONS.md`. L3 source/tests/CI/artifacts/SQLite outrank memory.

## Maintained identities

- OPUS: `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product Stage10/default: `structural-entity-term-discourse-pronoun-v1`, schema `rocketdict-product-stage10/1`. Research V2 remains explicit only.
- Stage12 planner: `rocketdict-stage12-protected-split/8`; numeric gate: `rocketdict-maintained-numeric-integrity/6`; emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- TC-big: `Helsinki-NLP/opus-mt-tc-big-en-zle`, revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0; offline manifest `85cf11ceb2eb401c83d1820672baaf745267e8b5edd71015a5a18e5bb49b752b`, payload tree `b725060c5d95ccc1f0082c0152e5ec79dd7815684ce89d6f658e5b97aeb2cba1`.

## Rank0-only policy

Automatic lower-beam fallback is forbidden. Persisted rescue output must be the unique raw rank0 hypothesis; missing/duplicate/malformed rank0 fails closed. Rank1+ may remain diagnostic only.

Current hardened wrappers include figure-reference `/2`, short-angular-DMS `/2`, angular-minute `/2`, illustration-label `/2`, TC-big target-delimiter `/2`, TC-big footnote-reference `/2`, TC-big semicolon-question `/2`, and TC-big equals-addition `/2`. Shared helper `translation_rank0.py` structurally enforces unique-rank0 selection. Product Core CI `34694302843` passed dependency-light and real-runtime jobs after hardening.

## Canonical complete Opticks identity

Complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`; normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`; `586543` chars.

## Authenticated rank0-clean baseline

Workflow `34695164876` completed successfully from engineering HEAD `041b0293eecccc375c6264a39704e6b25d2b6665`. Artifact `10297359600`, digest `sha256:e2d7549965d893c0b877cfe21057b8490134392a966e42fd72483ebb19836b4d`.

Replay evidence:

- schema `rocketdict-full-opticks-rank0-clean-lineage-replay/2`;
- historical container/source run `23`; replay root run `4`; historical clean boundary run `8`;
- recomputed `24→26` are translation/source/geometry-identical to historical `6→8`; identity SHAs: `093cbd882a44e1ca31ff30dcb95c71f33307da464ecb51338ba2d9e48734cba0`, `5586d6dc7716c258c492e2f7da803aa6ccdc5f48396e765b2fb4c6db78a6cb6d`, `43d05d6227aab8ba57c90f14db5b70bcfc153d32b39eafeb4ffc5d42750affdb`;
- first post-boundary run `27`; final clean run `41`; `18` newly recomputed runs from run4;
- all persisted rescue selections in the final lineage are rank0; `automatic_n_best_cherry_picking=false`; no source rewriting, target rewriting, literal injection, placeholders, corpus-specific target patches or evaluator weakening;
- byte-exact source coverage true; SQLite integrity `ok`; foreign-key violations `0`;
- final rows `3335`;
- final hard gates: **18 numeric/symbol / 16 punctuation / 0 length, 33 unique**;
- final translation-output SHA-256 `d8948e43158a126703a90e6ce1cd25725da8774e1db64410ca67e3ec7bb1a10f`;
- final text SHA-256 `23170683ddbe183b4da6b4097d72cedc86b9c98044e9f3e1dee015015e16e15e`;
- final SQLite SHA-256 `e48df8a90a3aa5e07bbc7e86c150d7b65ce450e7b6a0ec0d2e34a0caf9846e2e`;
- replay evidence SHA-256 `e7504ef18ead81e9c437ab8236b787a7d59082c272ef102fcc9bae6e281deac1`.

The independent read-only clean census authenticated the same run/database/output and remained byte-exact/read-only. Census evidence SHA-256 `b384ae0936f2ec792dd8ec6fbfcdf5da0dea1ba097df951c6049f2f2cbbb5319`. Residual sequences:
`[325,424,514,638,639,640,642,644,648,741,748,749,750,1497,1577,1753,1786,2108,2288,2344,2355,2373,2589,2719,2739,2887,2995,2998,3005,3009,3081,3209,3303]`.

Compared with historical run23, removal of illegal rank>0 selection makes three previously hidden failures visible again:

- seq `424`, span `72401:72443`, `[Illustration: FIG. 21.]\n\n_Illustration._` → punctuation failure because rank0 emits two bracketed illustration clauses;
- seq `514`, span `90105:90147`, `[Illustration: FIG. 24.]\n\n_Illustration._` → same punctuation family;
- seq `638`, span `110881:110918`, `Whence this Angle is 2 deg. 0'. 7''.` → numeric-prime failure because rank0 renders prime notation as feet.

These are real clean-frontier failures, not grounds for restoring rank3/rank2 selection.

## Historical run23 evidence retained

Workflow `34688874921`; artifact `10296696335`; ZIP SHA-256 `0df0625406349c4569df5a08f7cbd9952fe881b9c0a659e98ce643e8b4cca997`; SQLite SHA-256 `75ec63ea1b8b905af17a757a2a0dcd2697718945a6e9d354d494bb05d2364ca8`; translation output SHA-256 `976a7a39928cceda2459ab1b5d04f6996a4b2443efd31cbac6456c2c2e948493`; final text SHA-256 `ebb85aa3646b24c210eb6448e5938661550acaec851d83f9882889a45d77d0b6`; canonical evidence SHA-256 `0cdb6154289fc176cc75d1baad5a8607222bb92f8340295f5558ab46689ed40c`.

Historical run9 `illustration_label_rescue/1` selected ranks `[3,3,0]` for the two FIG spans plus one rank0 case; inherited short-angular DMS rescue selected rank2 at source start `110881`. Hence historical run23 must never parent promotion work.

## Exhausted/rejected evidence

- Sequence `2346` angle-list DOE (`34693396634`, artifact `10298311979`, evidence SHA `094140b1add91c3cdb6294319cfc691d38d488f97966c5cb41a9ae2386d055d6`): four source-owned geometries × raw rank0 OPUS/TC-big all mechanically inadmissible; two TC-big splits preserved prime pairs but corrupted `100000000` to `10000000`.
- Figure-reference seq `325`: tested lead-split and preceding-boundary-pair geometries are closed; isolated green mechanics broke syntax, restored boundary failed gates.
- Generic fallback, large-integer canonicalization, target repair/literal injection/source rewriting/placeholders/automatic n-best cherry-picking/evaluator weakening remain rejected.

## Active next actions

1. Treat run41 only as the parent/frontier; do not use historical run23 for promotion.
2. Inventory already-tested source-defined geometries for the returned clean failures seq `424`, `514`, `638` and avoid duplicate experiments.
3. Run the narrowest materially new raw-rank0 OPUS/TC-big DOE for the illustration-pair and short-DMS families. A candidate may advance only if the source predicate is generic, the raw rank0 aggregate passes all maintained gates, and semantic/boundary review is acceptable.
4. If a clean candidate exists, add a default-OFF fail-closed wrapper, tests and full compose/census regression from run41; otherwise record the family as exhausted and move to the next residual cluster.
5. Continue to zero hard failures, then complete downstream learner/export coverage and Windows clean-install/release validation.
