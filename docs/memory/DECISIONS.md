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

## Run-16 research basis

**Decision.** Run `16` remains the best accepted translation basis: **20 numeric / 18 punctuation / 0 length, 37 unique**. Identities: workflow `34645769684`, artifact `10282227627`, output SHA `767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783`, SQLite SHA `573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11`, evidence SHA `86c865cef5a0081fd77aa8ad78c525ebb38a01e6f279cc560aea56bb84d4e37d`.

## Stage10 V2 is research evidence, not Product translation default

**Decision.** False spaCy sentence splits are valid upstream evidence, and Stage10-v2 correctly records/merges 38 source-defined lowercase-continuation boundaries. However, changing all 31 affected Stage12 translation geometries is **not** safe enough for Product/default use.

Full replay workflow `34652579262` proves mechanical improvement to **20/16/0,36** with zero drift on `3264` unchanged source geometries, but semantic review finds material regressions on newly merged clean contexts, including loss of technical identifiers/content. Therefore Product/default translation geometry stays V1; V2 remains explicitly selectable research evidence.

This supersedes the earlier decision that V2 itself should be the default Stage10 implementation for Product translation. Low-level API defaults must be aligned with Product Profile so accidental direct callers do not silently opt into broad V2 translation geometry.

## Source-defined boundary-pair rescue direction

**Decision.** The safe continuation of the Stage10-v2 finding is a narrow pair-level second-MT experiment, not wholesale V2 resegmentation.

A boundary-pair rescue may be attempted only when all of the following are true:
- the boundary is independently proven by the generic Stage10-v2 source predicate;
- the exact span is representable by two complete adjacent current Stage12 rows;
- at least one of those rows already fails a maintained Product hard gate;
- the combined source bytes equal the immutable source span exactly;
- the second model sees only that exact combined source;
- only an unmodified raw candidate may replace the pair;
- strict maintained hard checks, emphasis/technical-preservation diagnostics and conservative completeness constraints pass;
- otherwise the pair is left untouched.

Feasibility workflow `34654758870` establishes three qualifying run16 pairs (`54796`, `112001`, `522572`). The first two must currently fail closed. At `522572` (`And whence is it | but from ...`) TC-big ranks `0..5` are mechanically admissible and satisfy the diagnostic anchors. The next implementation should deterministically test TC-big rank0 only; the feasibility artifact itself does not authorize Product promotion.

## Residual defects stay family-specific

**Decision.** No universal punctuation/numeric fixer. Current residuals mix source-owned labels/references, symbol corruption, target-only additions, prime/DMS notation, parser boundaries and long-context punctuation migration. A failed OPUS formulation does not forbid a materially different source-defined/model formulation; success on one narrow class does not license generic second-model fallback.

## Broad TC-big remains rejected

**Decision.** TC-big is an independent comparator/narrow rescue model, not generic fallback. Prior whole-context experiments show mechanically clean semantic false positives; context `2725` remains a counterexample. Source-relative completeness bounds may be used only inside justified selectors.

## Audit failures are classified before Product changes

**Decision.** A red heavy workflow is not automatically a Product/model defect. Inspect persisted output/logs first. Repair harness-only defects without weakening Product acceptance semantics; never change evaluators merely to make a run green.

## Acceptance order

**Decision.** Real source→Stage25 smoke/replay must be green before full-corpus acceptance. Final complete public-domain translation evidence must reach zero hard failures and semantic acceptance before downstream heavy learner/export and Windows clean-install/distribution become the release frontier.

## Memory protocol

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Stale L1 is repaired from L3 before new work. Before user-facing development completion, synchronize L1/L2 to actual HEAD/CI/artifacts.
