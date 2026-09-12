# RocketDict Product Core

Status: maintained forward Product runtime (`1.0.0.dev1`).

This package is the current RocketDict implementation. The Workbench `rocketdict-product-run` drives the maintained source→Stage25 path from immutable source through real NLP/MT, hard gates, alignment, lexical/sense processing, cards and export.

## Translation architecture

Product/default Stage10 remains V1; broad Stage10-v2 is explicit research evidence only. Stage12 primary translation uses the pinned real OPUS EN→RU planner/runtime. Research rescue layers are separate immutable selection runs, default OFF/not public-wired, and never rewrite primary targets in place.

Recent source-defined research layers include bounded question-context and bounded parenthetical whole-context OPUS rank0 rescue. The latter contract is `rocketdict-stage12-parenthetical-whole-context-rescue/1`: a complete Stage10 context split across 2+ current rows, <=160 NLP tokens, exactly one short balanced source parenthetical pair, both source parentheses lost from the aggregate target, unrelated hard/research diagnostics clean, and deterministic raw OPUS rank0 only. Strict hard/research checks, Gutenberg emphasis, exact hard punctuation and conservative content-volume checks remain vetoes.

No rescue may perform source rewriting, target surgery, placeholders, post-translation literal injection, corpus-specific target patches, evaluator weakening or automatic n-best cherry-picking.

## Numeric integrity contract

The maintained Stage15 numeric/symbol hard gate is `rocketdict-maintained-numeric-integrity/6`. V6 keeps the existing literal, sign, grouping, ordinal, prime-notation and critical-symbol checks and adds only a conservative source-side licence for uninterrupted multiplicative English scale chains such as `ten hundred thousand` → `1000000`. It deliberately does not cross conjunction/disjunction boundaries such as `two and three hundred` or `three or four thousand`, so elliptical ranges do not collapse into invented compound values.

This is evaluator-semantics refinement, not target repair. The exact run20 read-only replay (`34680865586`) retained the same 20 failing numeric rows with zero pass/fail drift. It changed spelled-number licences on only four persisted rows; the existing erroneous `100000` translation of `ten hundred thousand` remains a hard failure, while a hypothetical correct `1000000` is now recognized. Artifact `10293504260`, artifact digest `593c56e8096b9f96c2df2053779f86dfb7dccf8ccb6c3cdf8fd1477df6413725`.

## Current full-Opticks evidence

The canonical heavy corpus is complete Project Gutenberg *Opticks*, normalized-text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` source characters.

Late persisted progression:

- run `16`: **20 numeric / 18 punctuation / 0 length**, 37 unique;
- run `17`: **20/17/0**, 36 unique;
- run `18`: **20/16/0**, 35 unique;
- run `19`: **20/15/0**, 34 unique;
- run `20`: **20/14/0**, 33 unique.

Run `20` is the current best persisted **research** residual basis. It composes directly over run19 and accepts exactly one bounded parenthetical context (`1393`) as unmodified OPUS rank0. Workflow `34678965465`, artifact `10292783763`, ZIP SHA-256 `0e30b3d63159a4f649d111da54f3d6eee10ad9ef3478374f748f940a6d4fc01e`, final Stage12 output SHA-256 `e06aa1620410698bac09a4cc46632aaf3d1c3d45de0f798d29521f722367db85`, final text SHA-256 `16ab4a3c3ef192662604e90e428933ab23423b7872bae2bd6de3478b3a46f8c8`, final SQLite SHA-256 `879ea83d0f6803e2fdce609e4ef0dc57017626e4fd0e007d3440b12c7f6f4f2d`, evidence SHA-256 `2f21b87327033aab76e5d3485c22cfbd6ea672cae9c4c5055a3d129b3f5054c1`.

The persisted run keeps 3340 other run19 rows source/target exact, reconstructs the complete source byte-exactly, and passes SQLite/FK integrity. Product CI `34678795359` is green for the parenthetical wrapper including real Stage8→25/unified Product execution. This remains research evidence; Product defaults do not change.

## Negative square-bracket evidence

Inline source marker `[G]` at Stage10 context `598` was tested both row-locally and as the complete 115-token Stage10 context. Corrected whole-context workflow `34679178153` tested six OPUS plus six TC-big raw hypotheses; artifact `10293031844`, ZIP SHA `b4e8e09c848ce4015a6d4db5a80a2007420f93384563663df5e260a09d4a1d00`, evidence SHA `5530b8235e8d39e44be77032320cf898516b7dc07831e9b4929cd9283a300a61`. Every hypothesis drops `[G]`, so no inline-footnote wrapper is authorized under current models/search.

An earlier DOE attempt failed before inference because its provisioning expected `pytorch_model.bin`; the pinned TC-big snapshot uses `model.safetensors`. The orchestration was corrected without changing any quality criterion.

## Assets and release boundary

The accepted OPUS archive SHA-256 is `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`. TC-big is optional, separately pinned/provisioned and remains a comparator/narrow rescue only.

The maintained Stage8→25 path and unified `rocketdict-product-run` are continuously tested with real pinned runtime. A narrow rescue is never promoted merely because one corpus improves. Final approved heavy evidence still requires zero unresolved hard failures and complete semantic acceptance; only then does downstream heavy learner/export plus Windows clean-install/distribution become the release frontier.
