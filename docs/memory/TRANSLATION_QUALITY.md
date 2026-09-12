# RocketDict maintained translation quality — L2

Durable translation-quality conclusions only. This is not a changelog and does not replace [`../../rocketdict/PRODUCT_TARGET.md`](../../rocketdict/PRODUCT_TARGET.md). L3 source/tests/CI/artifacts outrank this file.

## Maintained contracts

- Production MT: pinned OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian `float32`.
- Product/default Stage10 is `structural-entity-term-discourse-pronoun-v1`, schema `rocketdict-product-stage10/1`. Research V2 is explicit only.
- Stage12 planner: `rocketdict-stage12-protected-split/8`.
- Numeric hard gate: `rocketdict-maintained-numeric-integrity/5`; Gutenberg emphasis diagnostic: `rocketdict-maintained-emphasis-markup-preservation/1`.
- Independent TC-big comparator/rescue is pinned `Helsinki-NLP/opus-mt-tc-big-en-zle` revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0, offline/Torch-free.
- Narrow research wrappers remain default OFF/not public-wired.

## Canonical complete Opticks basis

Pinned complete Project Gutenberg *Opticks*: source SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, normalized text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` chars.

Persisted progression: run `4` **30/34/5,64** → `7` **29/34/0,59** → `8` **25/33/0,55** → `9` **24/30/0,52** → `10` **24/25/0,47** → `11` **24/20/0,42** → `12` **23/19/0,41** → `13` **23/18/0,40** → `14` **22/18/0,39** → `15` **21/18/0,38** → `16` **20/18/0,37** → `17` **20/17/0,36** → `18` **20/16/0,35** → `19` **20/15/0,34**.

Run `19` is the best accepted persisted **research** translation basis. Workflow `34676310994`; artifact `10292442391`; artifact ZIP SHA-256 `51e00030d19799157d83db8a9dbc9093851da9be897619e465699b2cde72ef91`; output SHA `48096e0c1085c0598bc8abf212a2b2ba9a1109bb232fa2487c0472f35c06a1d9`; SQLite SHA `8519ea592b0bd948b68980ed19b710f05f20f9e0a60f0cb6c3e1a7763d5a8f76`; evidence SHA `ba6b24c0b4f628d908b5310aaf05268de2323033d7bbb629d081d755ddb8bf5f`.

Run19 composes directly over exact run18. The source-defined bounded-question wrapper attempts Stage10 contexts `2462` and `2726`. `2462` (71 NLP tokens) has one immutable terminal `?`, two current split rows and a premature extra target `?`; raw OPUS rank0 is mechanically/semantically clean and is accepted. `2726` (157 tokens) has a mechanically clean OPUS rank0 but fails the maintained Gutenberg emphasis-preservation contract, so it remains unchanged. The accepted source span is `477054..477373`; 3341 other run18 rows have zero target drift; full source is byte-exact; SQLite integrity is `ok`; FK violations are zero.

## Bounded question-context rescue

Contract: `rocketdict-stage12-question-mark-whole-context-rescue/1` with matching selector/trigger `/1`; default OFF and not public-wired.

Eligibility is source/geometry defined: a complete Stage10 context represented by 2+ current split rows, one source terminal question mark, extra premature target question debt, no unrelated hard/research debt, and `<=160` NLP tokens. Only raw OPUS rank0 is eligible. The candidate must pass maintained strict mechanical/research checks, preserve Gutenberg emphasis, retain sufficient alphabetic content and source coverage. Any failure preserves all base rows exactly.

Read-only DOE `34675824666` established the safe/unsafe split; Product CI `34676191351` passed dependency-light and real-runtime Stage8→25/unified Product execution. Full replay `34676310994` improves run18 **20/16/0,35 → 20/15/0,34**.

## Bounded parenthesis-context DOE

Read-only workflow `34676468786`, artifact `10292347874`, artifact ZIP SHA-256 `85014707fc29663cbc75075e3660c1f053921b0b1caa6a575584d8c8736e4274`, evidence SHA `77027658bc87890d7d861f944bd99a7ba3f926aa365973f432410e3986352c7f` tests four run19 split Stage10 contexts inside the proven 160-token cap: `668` (104 tokens), `1393` (108), `1977` (109), `2969` (136).

Counterfactual mechanical outcomes: OPUS rank0 selects only `1393` and would yield **20/14/0,33**; TC-big rank0 selects `668/1393/1977` and mechanically yields **20/12/0,31**; first-admissible OPUS also finds rank2 for `1977`. Semantic inspection rejects generic parenthesis whole-context promotion: TC-big `1393` loses the final compressed-between-glasses relation; TC-big `1977` drops the Island-Crystal exception; OPUS rank0 `668` preserves only one of two source parenthetical clauses; `2969` remains mechanically inadmissible. Higher-beam OPUS recovery for `1977` is research-only because automatic n-best cherry-picking is prohibited.

Therefore no generic bounded-parenthesis wrapper is authorized. `1393` may be investigated only if a generic source-owned trigger can distinguish it from the unsafe cohort without corpus-specific text/offset conditions.

## Earlier rescue evidence still binding

- run `10`: target-delimiter, **24/30/0,52 → 24/25/0,47**;
- run `11`: footnote-reference leads, **24/25/0,47 → 24/20/0,42**;
- run `12`: leading figure reference, **24/20/0,42 → 23/19/0,41**;
- run `13`: semicolon→question migration, **23/19/0,41 → 23/18/0,40**;
- run `14`: target-only equals addition, **23/18/0,40 → 22/18/0,39**;
- run `15`: angular-minute prime, **22/18/0,39 → 21/18/0,38**;
- run `16`: short DMS, **21/18/0,38 → 20/18/0,37**;
- run `17`: punctuation-only false-boundary pair, **20/18/0,37 → 20/17/0,36**;
- run `18`: orphan closing parenthesis, **20/17/0,36 → 20/16/0,35**;
- run `19`: bounded question whole-context OPUS rank0, **20/16/0,35 → 20/15/0,34**.

Persisted success is research evidence, not automatic Product-default authorization.

## Rejected/exhausted directions

- Broad Stage10-v2 translation geometry: rejected because semantic regressions occur despite improved hard counts.
- Generic OPUS/TC-big whole-context fallback: rejected; mechanically clean alternatives can lose semantics.
- Generic row-local TC-big punctuation fallback: rejected by exact residual DOE; mechanical eligibility produced semantic false positives.
- Generic bounded parenthesis whole-context fallback: rejected by run19 DOE; rank0 alternatives can omit source-owned clauses/relations.
- Broad context `2730` remains above the 160-token cap and unsafe.
- `2726` bounded question whole-context remains fail-closed because OPUS rank0 violates emphasis preservation and TC-big truncates content.
- Broad square-bracket-loss OPUS formulation: no admissible safe cohort.
- Never use target literal injection, corpus-specific target patches, placeholders, source rewriting, target surgery, n-best cherry-picking or evaluator weakening.

## Promotion rules

1. Never weaken maintained evaluators to make a real loss green.
2. Preserve immutable source/model/config/result identities.
3. Select only deterministic unmodified raw model candidates; no target surgery or automatic n-best cherry-picking.
4. Mechanical integrity is necessary but insufficient; semantic/boundary-aware review is mandatory.
5. A second MT or alternative geometry may be invoked only by a narrow existing-hard-failure/source-defined trigger; clean Product rows remain untouched unless separately justified.
6. Exact replacement geometry must be representable by complete current rows; otherwise skip fail-closed.
7. MetricX/QE is ranking evidence only.
8. Final approved heavy evidence requires zero unresolved hard failures.
