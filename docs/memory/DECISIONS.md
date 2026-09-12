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

## Run-17 research basis

**Decision.** Run `17` supersedes run16 as the best accepted persisted **research** translation basis: **20 numeric / 17 punctuation / 0 length, 36 unique**. Identities: workflow `34656818930`, artifact `10285447200`, artifact ZIP SHA `339b71584f35f6981e1bcfa2dfcd391f98807d12f864ffae3070d6737356387d`, output SHA `f7c04209d9e8d7ffab673a2987b0024c334f24fee59736466597ea99125f7ff1`, SQLite SHA `2cbf20b39168003e494b2fb73c9b9baea427283def04a076a673e5023d7346a4`, evidence SHA `a5d786f4d25ee35917014aae7e435ad1f311c1ffb80744a3a60cacd4c62d6843`.

It composes directly over exact run16, merges one independently proven punctuation-only false-boundary pair into raw TC-big rank0, leaves 3342 other run16 rows source/target exact, reconstructs the complete source byte-exactly and passes SQLite/FK integrity. The accepted pair passed maintained strict/research/emphasis checks and focused semantic review. This is still default-OFF research evidence, not Product promotion.

## Stage10 V2 is research evidence, not Product translation default

**Decision.** False spaCy sentence splits are valid upstream evidence, and Stage10-v2 records/merges 38 source-defined lowercase-continuation boundaries. However, changing all 31 affected Stage12 translation geometries is **not** safe enough for Product/default use.

Full replay workflow `34652579262` proves mechanical improvement to **20/16/0,36** with zero drift on 3264 unchanged source geometries, but semantic review finds material regressions on newly merged clean contexts. Therefore Product/default translation geometry stays V1; V2 remains explicitly selectable research evidence.

Low-level `run_stage10()` was aligned to this decision in commit `d438da03cbbd0882b34c3caea58a651a92058253`: default V1, explicit V2 only.

## Source-defined boundary-pair punctuation rescue

**Decision.** A narrow default-OFF pair-level second-MT rescue is the accepted research continuation of the Stage10-v2 finding; wholesale V2 resegmentation is not.

The `rocketdict-stage12-tc-big-boundary-pair-punctuation-rescue/1` trigger requires:
- the boundary is independently proven by the generic Stage10-v2 source predicate from immutable Stage8 evidence;
- exactly two complete adjacent unsplit current Stage12 rows map to two consecutive exact V1 contexts;
- at least one current punctuation hard failure and **zero** current numeric/symbol or length failure across the pair;
- the combined immutable source is within the conservative complexity cap;
- only raw TC-big rank0 may be selected;
- strict maintained hard/research checks, emphasis preservation and source-relative completeness pass;
- otherwise both base rows remain exact.

The Product selector contains no corpus offset, `whence` source phrase or expected Russian target. Full replay workflow `34656818930` proves exactly one run16 pair is accepted at boundary `522572`, improving punctuation by one with no drift elsewhere. The initial beam6/beam8 expected-string audit mismatch was corrected only after inspecting the actual raw beam6 output; selector/gates were not changed.

## Residual defects stay family-specific

**Decision.** No universal punctuation/numeric fixer. Current run17 residuals still mix source-owned labels/references, delimiter losses/additions, target-only questions, numeric-symbol corruption and long-context notation. A failed OPUS formulation does not forbid a materially different source-defined/model formulation; success on one narrow class does not license generic second-model fallback.

Historical broad square-bracket-loss OPUS and generic TC-big directions remain rejected. Before implementing the next selector, inspect existing feasibility evidence and cluster the exact run17 residuals by source-owned defect family.

## Broad TC-big remains rejected

**Decision.** TC-big is an independent comparator/narrow rescue model, not generic fallback. Prior whole-context experiments show mechanically clean semantic false positives; context `2725` remains a counterexample. Source-relative completeness bounds may be used only inside justified selectors.

## Audit failures are classified before Product changes

**Decision.** A red heavy workflow is not automatically a Product/model defect. Inspect persisted output/logs first. Repair harness-only defects without weakening Product acceptance semantics; never change evaluators merely to make a run green. The run17 beam6 fixture correction is a concrete example: the first full replay failed on a stale expected target, while the produced raw candidate and invariants were independently inspected before the audit fixture changed.

## Acceptance order

**Decision.** Real source→Stage25 smoke/replay must be green before full-corpus acceptance. Final complete public-domain translation evidence must reach zero hard failures and semantic acceptance before downstream heavy learner/export and Windows clean-install/distribution become the release frontier.

## Memory protocol

**Decision.** Recovery is `PROJECT_STATE.md` → HEAD diff → `docs/memory/INDEX.md`/relevant L2 → unrestricted L3. Stale L1 is repaired from L3 before new work. Before user-facing development completion, synchronize L1/L2 to actual HEAD/CI/artifacts.
