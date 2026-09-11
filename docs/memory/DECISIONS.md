# RocketDict durable decisions — L2

Store only conclusions expensive or risky to rediscover. Git/L3 remains chronology and primary evidence.

## Quality/release invariants

**Decision.** Speed, storage and convenience may not reduce Product quality/evidence. Real EN→RU MT is mandatory; no fake/identity/mock/dictionary substitution, silent truncation, evaluator weakening, target literal injection, source rewriting, target surgery, placeholders or corpus-specific target patches.

`rocketdict/PRODUCT_TARGET.md` remains authoritative: final approved 90k+ heavy evidence needs zero unresolved numeric/symbol, punctuation and length failures, semantic acceptance, and successful complete learner-dictionary/export processing.

## Maintained implementation and assets

**Decision.** Forward work targets `rocketdict-product-core` + Workbench. Historical 0.30.x material is provenance/compatibility evidence only unless justified.

Production baseline is pinned OPUS EN→RU `opus-2020-02-11`, archive SHA-256 `798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`, CTranslate2 Marian float32. TC-big comparator/rescue is pinned `Helsinki-NLP/opus-mt-tc-big-en-zle` revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, CC-BY-4.0, offline/Torch-free. It remains separate from baseline production assets.

## Translation-quality promotion

**Decision.** Promote only after classifying the defect, preserving immutable source ownership and validating contiguous/boundary-sensitive evidence. Mechanical hard-gate success is insufficient; semantic review is mandatory. MetricX/QE may rank immutable raw candidates but cannot establish acceptance alone.

Exact Stage10 source spans may be replacement units only when representable by complete current Stage12 rows; never slice target strings. Existing narrow TC-big wrappers remain default OFF/not public-wired; corpus improvement never automatically changes Product defaults.

## Run-16 research basis

**Decision.** Until the Stage10-v2 exact full replay is persisted and semantically reviewed, run `16` remains the best translation basis: **20 numeric / 18 punctuation / 0 length, 37 unique**. Identities: workflow `34645769684`, artifact `10282227627`, output SHA `767045235fd4bb797a9cba254b459ba3e84c9d693b382cd47b1f2d5aedb6d783`, SQLite SHA `573a32c5dd3ba46f6bb16a91d7a3ca949c521dcf4f033b4ff040bf498cc2ad11`, evidence SHA `86c865cef5a0081fd77aa8ad78c525ebb38a01e6f279cc560aea56bb84d4e37d`.

## False NLP boundaries belong upstream

**Decision.** Proven false spaCy sentence splits belong in Stage10 while immutable Stage8 parser evidence is retained. Do not add a `Whence`-specific MT patch.

Default Stage10 is `structural-entity-term-discourse-pronoun-v2` / `rocketdict-product-stage10/2`, policy `rocketdict-stage10-lowercase-continuation-coalescer/1`: consecutive parser sentences only, whitespace-contiguous source gap, no paragraph break, no left terminal `.?!` after closers, lowercase first lexical character on the right, with full persisted boundary provenance. V1 remains explicitly selectable.

**Corrected evidence.** The previous memory assertion “complete census = five” was wrong. Exact immutable run-16 Stage8 census proves **38** predicate matches, all source-reviewed as source-continuous false splits/markup continuations. Seven were already absorbed by Stage12 protected-span planning; **31** were real V1/run-16 Stage12 translation boundaries. Planner-impact workflow `34651300446` proves V1 `3353` → V2 `3325` units and removes all 31 such plan boundaries without invoking MT; artifact/evidence SHA are retained in `TRANSLATION_QUALITY.md`.

**Verification.** Audit/test commit `d9b58f81de90d76add54798b41f12e5f29dea7ef` pins the exact 38 offsets and generic regression classes. Product workflow `34652530247` is green: 293 Product Core tests, 213 Workbench passed + 1 skipped, and real Stage8→25/unified source→25 paths. Full real-MT comparison workflow `34652579262` is the acceptance experiment; do not promote final corpus counts before its persisted artifact and semantic review.

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
