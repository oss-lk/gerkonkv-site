# RocketDict durable decisions — L2

Store only conclusions expensive or risky to rediscover. Git/L3 remains chronology and primary evidence.

## Quality/release invariants

**Decision.** Speed, storage and convenience may not reduce Product quality/evidence. Real EN→RU MT is mandatory; no fake/identity/mock/dictionary substitution, silent truncation, evaluator weakening, target literal injection, source rewriting, target surgery, placeholders or corpus-specific target patches.

`rocketdict/PRODUCT_TARGET.md` remains authoritative: final approved 90k+ heavy evidence needs zero unresolved numeric/symbol, punctuation and length failures, semantic acceptance, and successful complete learner-dictionary/export processing.

## Maintained implementation and assets

**Decision.** Forward work targets `rocketdict-product-core` + Workbench. Historical 0.30.x material is provenance/compatibility evidence only unless justified.

Production baseline is pinned OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian float32. TC-big comparator/rescue is pinned `Helsinki-NLP/opus-mt-tc-big-en-zle` revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0, offline/Torch-free.

## Translation-quality promotion

**Decision.** Promote only after classifying the defect, preserving immutable source ownership and validating contiguous/boundary-sensitive evidence. Mechanical hard-gate success is insufficient; semantic review is mandatory. MetricX/QE may rank immutable raw candidates but cannot establish acceptance alone.

Exact source spans may be replacement units only when representable by complete current Stage12 rows; never slice target strings. Existing narrow TC-big wrappers remain default OFF/not public-wired; corpus improvement never automatically changes Product defaults.

## Run-18 research basis

**Decision.** Run `18` supersedes run17 as the best accepted persisted **research** translation basis: **20 numeric / 16 punctuation / 0 length, 35 unique**. Identities: workflow `34675224977`, artifact `10292311024`, artifact ZIP SHA `ae4a32221985aaff2842a87bf9548698d8e76b33815633ddb67100b8fc9dea1d`, output SHA `666e8a2cae0bb6ff6f25b95475c2335ee5e3c98f7f2d6ab7deb9be92295be290`, SQLite SHA `803a2cbccb287ad0fadf4b14d932e1e33ebafef2ec5406619b0caf0898525143`, evidence SHA `61ddb44ceed56d0acb552a5cddecac1543e679c35ad450c41270136c5e014733`.

It composes directly over exact run17 and replaces one source-defined orphan-closing-parenthesis fragment at source start `417917` with raw TC-big rank0. Immutable source contains no round parentheses; the prior target had exactly one target-only closing parenthesis. The candidate preserves numeric order and all maintained strict/research/emphasis checks; 3342 other rows remain source/target exact, complete source coverage is byte-exact and SQLite/FK integrity passes. This remains default-OFF research evidence and does not authorize Product promotion without semantic acceptance.

## Generic punctuation fallback remains rejected

**Decision.** The exact run17-wide TC-big punctuation n-best DOE (`34674771224`, artifact `10292300428`) does not justify a generic row-local second-model fallback. Several raw hypotheses pass every current mechanical/structural gate, but manual semantic inspection exposes false positives, including degree/relation loss and untranslated archaic source wording. Therefore mechanical eligibility across punctuation residuals is candidate evidence only; selectors must stay defect-family-specific and source-defined.

## Source-defined orphan closing-parenthesis rescue

**Decision.** `rocketdict-stage12-tc-big-orphan-closing-parenthesis-rescue/1` is an accepted default-OFF research continuation because its trigger isolates a source-owned defect shape rather than a corpus row.

Eligibility requires a current split linguistic fragment whose immutable source has no round parentheses, whose target has exactly one closing `)` and no opening `(`, whose only Product-hard failure is punctuation, and which has no other delimiter/question/exclamation/numeric or maintained technical-token debt. Source complexity is capped. Only raw TC-big rank0 is eligible; it must exactly match source punctuation counts, pass numeric/symbol, strict research, emphasis and source-relative completeness checks. Any failed condition leaves the base row unchanged.

Full replay workflow `34675224977` proves exactly one run17 row is attempted/accepted and improves **20/17/0,36 → 20/16/0,35** with zero drift in the other 3342 rows. Product CI `34675206945` is green including real-runtime Stage8→25 and unified source→25.

## Stage10 V2 is research evidence, not Product translation default

**Decision.** False spaCy sentence splits are valid upstream evidence, and Stage10-v2 records/merges 38 source-defined lowercase-continuation boundaries. However, changing all 31 affected Stage12 translation geometries is **not** safe enough for Product/default use.

Full replay workflow `34652579262` proves mechanical improvement to **20/16/0,36** with zero drift on 3264 unchanged source geometries, but semantic review finds material regressions on newly merged clean contexts. Therefore Product/default translation geometry stays V1; V2 remains explicitly selectable research evidence.

## Source-defined boundary-pair punctuation rescue

**Decision.** A narrow default-OFF pair-level second-MT rescue is the accepted research continuation of the Stage10-v2 finding; wholesale V2 resegmentation is not. `rocketdict-stage12-tc-big-boundary-pair-punctuation-rescue/1` requires independent Stage8/V2 boundary proof, two complete adjacent V1 rows, punctuation-only hard debt, conservative complexity and raw TC-big rank0. Run17 replay `34656818930` improved run16 **20/18/0,37 → 20/17/0,36** without unrelated drift.

## Residual defects stay family-specific

**Decision.** No universal punctuation/numeric fixer. Current run18 residuals mix delimiter losses, question migration, square-bracket/reference forms and numeric-symbol corruption. A failed OPUS formulation does not forbid a materially different source-defined/model formulation; success on one narrow class does not license generic second-model fallback.

Before implementing another selector, inspect historical feasibility evidence and cluster the exact run18 residuals by source-owned defect family. Broad square-bracket-loss OPUS and generic TC-big directions remain rejected.

## Broad TC-big remains rejected

**Decision.** TC-big is an independent comparator/narrow rescue model, not generic fallback. Prior whole-context and run17-wide punctuation experiments show mechanically clean semantic false positives. Source-relative completeness bounds may be used only inside justified selectors.

## Audit failures are classified before Product changes

**Decision.** A red heavy workflow is not automatically a Product/model defect. Inspect persisted output/logs first. Repair harness-only defects without weakening Product acceptance semantics; never change evaluators merely to make a run green.

## Acceptance order

**Decision.** Real source→Stage25 smoke/replay must be green before full-corpus acceptance. Final complete public-domain translation evidence must reach zero hard failures and semantic acceptance before downstream heavy learner/export and Windows clean-install/distribution become the release frontier.

## Memory protocol

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Stale L1 is repaired from L3 before new work. Before user-facing development completion, synchronize L1/L2 to actual HEAD/CI/artifacts.
