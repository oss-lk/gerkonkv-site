# RocketDict Stage 8 — current continuation checkpoint

Last updated: 2026-08-27 UTC.

This is the compact **latest-state pointer** for continuation sessions. Read it after `START_HERE.md`, then read `HANDOFF_HEALTH.md` before claiming that the exact Stage 8 payload is materializable.

## 1. True parent frontier remains F96

The last **full original Stage 8 deterministic challenge measurement** is still **F96**:

- 5,000 source words;
- 109 source occurrences;
- 168 inference chunks;
- official OPUS EN→RU / CTranslate2 float32;
- numeric mismatches = 3;
- critical-symbol mismatches = 0;
- length-ratio mismatches = 0;
- empty outputs = 0;
- backend-error units = 0;
- gate = FAIL only because numeric integrity requires zero.

Exact F96 failure classes from the original evidence:

1. occurrence 15697 — structural `[in _Fig._ 2.]` reference loss;
2. occurrence 16200 — short `15 ... 3` numeric loss;
3. occurrence 17795 — extreme `10^6 / 10^12 / 10^18` sequence corruption.

Do **not** restart DOE at A/B/C/D/E. Do **not** call any reconstruction run the F96 result.

## 2. Exact-handoff blocker is still active

`rocketdict/materialize_handoff.py` expects:

- 8 Stage 8 overlay chunks;
- 11 Research Vault chunks.

The public repository still has only `rocketdict/payload/stage8-overlay/part-000.b64`; the remaining 7 overlay chunks and all 11 Research Vault payload chunks are absent.

Therefore the exact RocketDict 0.30.40 Stage 8 source snapshot, original F96 selector and `rocketdict-numeric-integrity/3.2` evaluator cannot currently be reproduced bit-for-bit from a fresh clone. See `HANDOFF_HEALTH.md` for recorded SHA contracts.

Consequences:

- all work below is explicitly **NON-PROMOTIONAL reconstruction/mechanism evidence**;
- no 10k or 104k promotion is allowed from these reconstruction results;
- do not fabricate the missing source/vault bytes;
- once the missing verified payload is recovered, the identical F96 rerun remains mandatory.

## 3. Stable model/corpus identities

Official OPUS EN→RU archive:

`sha256:798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`

Official OPUS RU→EN archive used for pinned semantic-regression audits:

`sha256:b4bad9451bc4c4a1e292a33568a41db88a6b3349d6feaec97c4cd748305de243`

Public-domain Newton *Opticks* reconstruction corpus:

`sha256:1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`

## 4. Original G/H/I mechanism results

### G — integrity-aware n-best

Run `33077361613`, artifact `9648449421`, digest `sha256:f0d022aa25edd3fee360848ee82a402c3604783f0b6f98f1ea0f432580b1b1b7`.

For exact source `15 Min. that of the exterior 3 Degr.` all tested cells 4/4, 8/8, 16/8 and 16/16 already preserve `15` and `3` at rank 0. Ordinary n-best does **not** solve the extreme sequence class.

Evidence: `research/stage8-g-probe-2026-08-27.json`.

### H — source-side structural reference

Pre-MT figure-reference parsing preserves:

`[in _Fig._ 2.]` → `[на рис. 2]`

with source→target provenance. Mechanism-positive, not promoted.

### I — extreme numeric sequence

I-v1 is a preserved **negative** result: protecting only the three huge numbers introduced a neighbour regression around `76 / 152 / 228`.

I-v2 widened the AST to the coupled height/rarity relation and preserved the complete tested explicit numeric context without missing/duplicate values.

Run `33077965671`, artifact `9648716848`, digest `sha256:118ceab38aef586c647aafbdadd0abd1b4a70e4ceee24f2571dc83e170bb8964`.

Evidence: `research/stage8-hi-probes-2026-08-27.json`.

## 5. Frozen independent reconstruction screen

Because exact F96 bytes are unavailable, a separate deterministic regression screen was created. It is **not F96**.

Frozen identity:

- 5,044 source words;
- 80 units;
- selector SHA-256:
  `ea193d5f589dd053b768536c9f8bb4bac90316eed79f5244592357607e02b3fe`;
- the selector hard-fails if this SHA changes.

The screen deliberately contains numeric, structural, scientific and general prose cases. Every revision below uses the same frozen selection.

### Early reconstruction negatives

- run1 `33081805252`: exposed checker canonicalization defects plus a real G language regression; preserved as negative evidence;
- run2 `33082555130`: checker fixed; remaining true numeric failures reduced to two difficult scientific units 743 and 1797;
- v3: generic numeric-list AST reached numeric zero but manual review found a delimiter regression in 743; rejected;
- v4: added numeric-order and balanced delimiter checks and exposed hidden technical-token failures;
- v5: added `stage8-critical-technical-token-integrity/1`; objective integrity passed but manual review found language regressions;
- v6: added `stage8-no-new-unprotected-latin/1`; correctly rejected 743/941/1797 language residue;
- v7: clause-first context closed 941 and improved other technical prose, but 743/1797 still leaked archaically capitalized English words.

Keep these negatives. They explain why the later mechanism is layered rather than a single heuristic.

## 6. Clean v8 — objective integrity/language PASS

v8 introduced **N-v1 residual-driven archaic capitalization retry**:

- original source is always attempted first;
- only TitleCase source prose words that actually leak as ordinary Latin target words are eligible for lowercase retry;
- protected `[]` / `_..._` payloads are excluded;
- retry uses the same OPUS model and beam8/n-best8;
- no glossary and no target-word replacement;
- all inherited integrity/no-new-Latin gates remain fail-closed.

Clean run:

- GitHub Actions `33088908923` — SUCCESS;
- artifact `9653493129`;
- digest `sha256:6bb4c8d8c2ddb6dc62b9a0357aadc6066ddd388aef421f033e0893a769dbca29`.

Frozen 80-unit result:

- numeric failures = 0;
- numeric-order failures = 0;
- delimiter failures = 0;
- critical technical-token failures = 0;
- figure failures = 0;
- empty = 0;
- length anomalies = 0;
- identity failures = 0;
- mean Cyrillic share improved versus baseline;
- changed units = 10.

743 and 1797 are closed; 1797 preserves all 28 explicit numeric tokens in source order.

Evidence: `research/stage8-ghi-reconstruction-run8-2026-08-27.json`.

This PASS is objective-integrity/language evidence only. Manual review still found a local semantic problem in occurrence 444 (`Refraction` semantics degraded to `отвращение / Отклонение`).

## 7. O-v1 — sentence-level semantic proxy is useful but insufficient

O-v1 independently reproduces clean v8, back-translates baseline/candidate with the official pinned OPUS RU→EN line and compares against original English with:

- chrF++;
- token multiset F1;
- character-trigram Dice;
- descriptive paired composite.

Run `33089447807`, artifact `9653795260`, digest `sha256:5bc9e922890dc8b24b50b90a9fb98238686a5f35d185c1ddeae394b83f902726`.

Among the 10 v8 interventions:

- 6 improved paired composite;
- 4 worsened;
- mean composite delta ≈ +0.0329;
- mean chrF++ delta ≈ +3.37.

However occurrence 444 received a positive sentence-level score despite the obvious local `Refraction` terminology collapse. Therefore **O-v1 is diagnostic only and must never be used alone as a semantic hard gate**.

Evidence: `research/stage8-semantic-proxy-o1-2026-08-27.json`.

## 8. O-v2 — pinned high-confidence repeated-term collapse gate

O-v2 freezes a deliberately narrow local regression rule before its first run. It uses Porter stemming but **no translation glossary**.

A high-confidence collapse requires all of:

- source stem count ≥ 2;
- baseline RU→EN round-trip retention ≥ 75%;
- candidate retention ≤ 25%;
- absolute retained-occurrence loss ≥ 2;
- fixed common/function-word exclusions;
- pinned RU→EN archive SHA.

Run `33094686405` fails by design on exactly **one of 10** changed units:

- occurrence 444;
- stem `refract`;
- source surfaces: `Refraction`, `Refraction`, `refracting`, `Refraction`;
- source count = 4;
- baseline retains 3/4;
- clean-v8 candidate retains 1/4;
- absolute loss = 2.

743/941/2214 have weaker warnings but do not satisfy the frozen failure rule.

Artifact `9655951613`, digest `sha256:f3e7e121db4beafd3ca9773aa0cdb5bfea3e945a35f4d17b998664d368748446`.

Evidence: `research/stage8-semantic-term-retention-o2-2026-08-27.json`.

## 9. P/Q terminology-mechanism DOE for occurrence 444

### P-v1 — semantically useful, wrong integration layer

The source itself supplies a case-consistency signal: the same Porter stem appears as TitleCase `Refraction` and lowercase `refracting`. P-v1 lowercases only eligible TitleCase occurrences and asks OPUS beam16/n-best16 to regenerate the **whole sentence**.

Result:

- all 16 hypotheses change the bad noun behaviour to `рефракция`; several also generate `рефракционные углы`;
- zero ordinary Latin residue;
- but all 16 damage `_3p 3t_` → `3p 3t_`;
- critical-token gate correctly rejects every hypothesis.

Run `33095169270`, artifact `9656077784`, digest `sha256:27a326a696e2fe73171860e896c0fd9e59e279ba2e318f69a825544bb8cba8e1`.

Evidence: `research/stage8-term-case-consistency-p1-2026-08-27.json`.

### P-v2 — technical integrity fixed, semantic context lost

The same source normalization was moved inside the clause/AST pipeline.

Result:

- forward objective integrity passes;
- `_3p 3t_` survives;
- zero ordinary Latin residue;
- but shorter clause context generates `отвлечение`; O-v2 remains 3→1 for `refract` and fails.

Run `33095451279`, artifact `9656195443`, digest `sha256:ada8ffdf2a8b3281fee62835cb723ca5f16c7b9229786dbbc85dd40e88c8f28c`.

Evidence: `research/stage8-term-case-consistency-p2-2026-08-27.json`.

### Q-v1 — positive mechanism

Q-v1 combines the two required properties:

1. pre-parse symbolic source structure before MT;
2. retain whole-sentence normalized semantic context;
3. after model generation, canonicalize **only** the surrounding Gutenberg `_` delimiters/whitespace of a uniquely preserved exact symbolic payload;
4. payload letters/digits/order must be unchanged and unique, otherwise fail closed.

No glossary, missing-number append or arbitrary target prose edit is allowed.

Run `33095764749` — SUCCESS.
Artifact `9656334142`, digest `sha256:99b2edec17641ea439718defee4cd44d1dec24bfcc1ef5b82006ffaa91067391`.

Selected rank 0:

`... рефракция ... рефракция ... _3p 3t_ ... рефракцией ...`

Source-planned structural render is exactly:

- source node `_3p 3t_`;
- exact payload `3p 3t`;
- raw model surface `3p 3t_`;
- canonical surface `_3p 3t_`;
- unique payload match = true;
- payload modified = false.

Pinned O-v2 becomes 3/4 retained, with zero high-confidence collapses. All 16 forward-eligible Q hypotheses pass O-v2.

Evidence: `research/stage8-whole-context-structural-q1-2026-08-27.json`.

## 10. v9 — strongest current frozen reconstruction candidate

v9 integrates Q-v1 minimally and data-dependently:

1. reproduce clean v8 on the exact frozen 5044/80 selection;
2. pinned O-v2 audits only units that v8 actually changed;
3. Q-v1 is allowed only for an O-v2-proven high-confidence collapse **and** only when the source independently supplies a mixed-case stem signal;
4. after rescue, rerun the complete objective 80-unit aggregate and final O-v2 audit.

Run `33096154141` — **SUCCESS**.
Artifact `9656546120`.
Digest `sha256:c4945967e9a7ee223e39c5779950bf7bb0c6691d48d3b4f4e6c1e081d5eb0ac5`.

Observed automatically:

- clean-v8 changed units = 10;
- initial pinned O-v2 failed occurrences = `[444]`;
- Q rescues attempted/accepted = 1;
- rescued occurrences = `[444]`;
- selected Q rank = 0;
- final O-v2 failed occurrences = `[]`.

Final frozen 80-unit candidate:

- empty = 0;
- numeric fail units = 0;
- numeric missing values = 0;
- numeric duplicate values = 0;
- numeric-order fail units = 0;
- delimiter fail units = 0;
- critical-token fail units = 0;
- figure fail units = 0;
- length-anomaly units = 0;
- identity units = 0;
- strong intervention failures = 0;
- no-new-Latin intervention failures = 0;
- mean Cyrillic alpha share = `0.9632440623733534`;
- pinned O-v2 high-confidence term collapses = 0.

Interventions in the final frozen candidate:

- Q-v1 pinned-O2 rescue = 1;
- M-v1 clause-first integrity translation = 6;
- H-table = 1;
- I-v2 = 1;
- H-document-ID = 1.

Evidence: `research/stage8-v9-pinned-term-rescue-2026-08-27.json`.

### Correct interpretation of v9

v9 is the **strongest currently reproduced NON-PROMOTIONAL candidate on the independent frozen reconstruction screen**.

It demonstrates that the current mechanism stack can simultaneously achieve zero measured objective integrity/language failures and zero pinned high-confidence repeated-term collapses on this fixed 5044-word screen.

It does **not** prove universal semantic quality. O-v2 is deliberately narrow, and sentence-level O-v1 was already shown to be insufficient alone.

Most importantly, v9 does **not** replace F96 and does not authorize a 10k screen while the exact handoff payload is missing.

## 11. Current continuation rule / exact next action

### Research state to preserve

- F96 remains the last true original full challenge result.
- v9 is the best independent frozen reconstruction survivor.
- Preserve all negative branches; do not rewrite the history to show only successful mechanisms.
- Do not add more heuristics merely to improve one frozen score unless a new reproducible failure class justifies them.

### Priority A — recover exact payload

1. Restore the missing 7 verified Stage 8 overlay chunks and all 11 Research Vault chunks, or an equivalent source snapshot that passes the recorded handoff SHA contracts.
2. Run `python rocketdict/materialize_handoff.py` and require every SHA/inventory/SQLite integrity check to pass.
3. Integrate the surviving mechanisms/config identities into the real 0.30.40 Stage 8 pipeline.
4. Re-run the **identical original F96 deterministic challenge** with the actual `rocketdict-numeric-integrity/3.2` evaluator.
5. Promotion acceptance remains:
   - numeric = 0;
   - critical = 0;
   - length = 0;
   - empty = 0;
   - backend errors = 0;
   - no material language/identity/semantic regression.
6. Only then may survivors advance to the 10k stratified screen.

### Priority B — if exact payload still cannot be recovered

Do not invent F96. Keep v9 frozen and use it only for **new independent validation**, not threshold-tuning on the same 80 units. Suitable next work is an additional independent semantic/terminology validation set or external metric layer with its contract frozen before results are observed. Any such result remains non-promotional.

## 12. Promotion status

**No Stage 8 branch is promoted.**

Current labels:

- F96 — last true full original challenge, FAIL with 3 numeric mismatches;
- G/H/I-v2 — mechanism-positive;
- I-v1, reconstruction run1/run2 branches, P-v1/P-v2 — preserved negative evidence;
- clean v8 — objective frozen reconstruction PASS but O-v2 semantic collapse present;
- Q-v1 — positive local mechanism;
- **v9 — best current NON-PROMOTIONAL frozen reconstruction survivor**;
- 10k / 104k — still blocked pending exact F96 recovery and pass.
