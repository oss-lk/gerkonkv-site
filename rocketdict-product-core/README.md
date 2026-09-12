# RocketDict Product Core

Status: maintained forward Product runtime (`1.0.0.dev1`).

This package is the current RocketDict implementation. It is maintained forward code, not a reconstruction of an unavailable historical 0.30.x package.

## Maintained Product path

The maintained core owns the Product execution/storage path through Stage25:

`source → Stage8 production spaCy NLP → Stage10 context → Stage12 real OPUS EN→RU → Stage14 refinement boundary → Stage15 hard gates → Stage16 approval → Stage17 alignment → Stage18 lexical extraction → Stage19 sense induction → Stage20 contextual lexical OPUS → Stage21 CEFR-J → Stage22 CMUdict → Stage23 sense examples → Stage24 immutable cards/set → Stage25 JSON export`

The Workbench `rocketdict-product-run` drives the same public maintained API from source through Stage25 and resumes from immutable identities.

### Stage10 source-boundary policy

The Product/default Stage10 implementation is `structural-entity-term-discourse-pronoun-v1`, schema `rocketdict-product-stage10/1`. The low-level `run_stage10()` default and the Workbench Product Profile are intentionally aligned on V1 so direct callers do not silently opt into research resegmentation.

Research implementation `structural-entity-term-discourse-pronoun-v2`, schema `rocketdict-product-stage10/2`, uses boundary policy `rocketdict-stage10-lowercase-continuation-coalescer/1`. Stage8 parser sentences remain immutable evidence. V2 may coalesce only consecutive raw parser sentences when immutable source geometry proves that the gap is whitespace-only, contains no paragraph break, the left source has no terminal `.?!` after closing punctuation, and the first lexical character on the right is lowercase. Each removed boundary records its source offset/reason and the original spaCy sentence indices.

This remains an upstream source-evidence repair, not translation-side surgery: Stage10 never rewrites source bytes or patches a target. The exact complete-*Opticks* census contains **38** V2 predicate matches. Seven are already absorbed by protected Stage12 planning; **31** change Stage12 translation geometry. A complete real-MT V2 replay improved mechanical residuals from run16 **20 numeric / 18 punctuation / 0 length, 37 unique** to **20/16/0,36**, with zero target drift on 3264 unchanged geometries, but semantic review found material regressions on newly merged clean contexts, including loss of technical content. Broad V2 translation geometry is therefore **research evidence only and rejected as a Product/default replacement**.

### Stage12 translation and research layers

Stage12 uses `rocketdict-stage12-protected-split/8`. The real OPUS primary translation is immutable and cache-reusable. Rescue mechanisms are separate selection layers; they never rewrite the primary model result in place.

The public Stage12 operation currently exposes only the existing narrow default-OFF research surfaces:

- legacy selective resegmentation / whole-context research rescue;
- `rocketdict-stage12-length-failure-whole-context-rescue/1`;
- `rocketdict-stage12-citation-boundary-pair-rescue/1` for the proven inline `Sect. IV.` / `Sect. II.` sentence-boundary class.

Additional evidence-backed wrappers are implemented internally but remain **default OFF and not public-wired**:

- `rocketdict-stage12-numeric-hard-failure-whole-context-rescue/1`;
- `rocketdict-stage12-illustration-label-rescue/1`;
- `rocketdict-stage12-tc-big-target-delimiter-context-rescue/1`;
- `rocketdict-stage12-tc-big-footnote-reference-lead-rescue/1`;
- `rocketdict-stage12-tc-big-figure-reference-lead-rescue/1`;
- `rocketdict-stage12-tc-big-semicolon-question-substitution-rescue/1`;
- `rocketdict-stage12-tc-big-target-only-equals-addition-rescue/1`;
- `rocketdict-stage12-tc-big-angular-minute-prime-rescue/1`;
- `rocketdict-stage12-tc-big-short-angular-dms-rescue/1`;
- `rocketdict-stage12-tc-big-boundary-pair-punctuation-rescue/1`.

The boundary-pair punctuation wrapper deliberately does **not** switch Stage12 to broad V2 geometry. It considers only two complete adjacent V1 Stage12 rows whose exact immutable boundary is independently proven by the generic V2 source predicate, whose current defect family is punctuation-only (zero numeric/symbol and length hard failures), and whose combined source stays inside a conservative complexity cap. Only raw TC-big rank0 is considered; if strict maintained checks, emphasis preservation or completeness checks fail, both original rows remain source/target exact.

No rescue path may perform source rewriting, target surgery, placeholders, post-translation literal injection, corpus-specific target patches or evaluator weakening.

Stage15 remains fail-closed for numeric/symbol, punctuation and length integrity. A hard failure is evidence to improve planning/model selection; it is never repaired by inserting missing literals into the target.

## Current full-Opticks evidence

Large-corpus acceptance uses the complete pinned Project Gutenberg *Opticks* source, SHA-256 `1e25ec2c54fc6e9fa05d7f0a663e05cf2ee671231c65731f4845df2539dfb217`, normalized-text SHA-256 `436bfa539f5e8c84c5c3af71eff49a89858d3b2c4ad45ddd55144b6f4066c87a`, `586543` source characters, rather than a truncated sample.

The persisted research progression is:

- run `4`: **30 numeric / 34 punctuation / 5 length**, 64 unique failures;
- run `7`: **29/34/0**, 59 unique;
- run `8`: **25/33/0**, 55 unique;
- run `9`: **24/30/0**, 52 unique;
- run `10`: **24/25/0**, 47 unique;
- run `11`: **24/20/0**, 42 unique;
- run `12`: **23/19/0**, 41 unique;
- run `13`: **23/18/0**, 40 unique;
- run `14`: **22/18/0**, 39 unique;
- run `15`: **21/18/0**, 38 unique;
- run `16`: **20/18/0**, 37 unique;
- run `17`: **20/17/0**, 36 unique.

Run `17` is the current best persisted **research** residual basis. It composes the default-OFF run16 layers with exactly one accepted TC-big boundary-pair punctuation rescue at source boundary `522572`. The persisted replay changed two adjacent run16 rows into one raw rank0 translation, left **3342** other run16 rows source/target exact, reconstructed all `586543` source characters byte-exactly, and passed SQLite `integrity_check=ok` with zero foreign-key violations. Workflow `34656818930`, artifact `10285447200`, artifact ZIP SHA-256 `339b71584f35f6981e1bcfa2dfcd391f98807d12f864ffae3070d6737356387d`, final output SHA-256 `f7c04209d9e8d7ffab673a2987b0024c334f24fee59736466597ea99125f7ff1`, final SQLite SHA-256 `2cbf20b39168003e494b2fb73c9b9baea427283def04a076a673e5023d7346a4` and audit-evidence SHA-256 `a5d786f4d25ee35917014aae7e435ad1f311c1ffb80744a3a60cacd4c62d6843` identify this evidence.

The accepted source pair is `And whence is it but from that attractive Power, ... without a great Heat?`; the raw TC-big rank0 preserves the interrogative relation, attractive power, water, salt and heat content and passes the maintained strict/research/emphasis checks. This single-pair review supports run17 as a research basis; it does **not** authorize a Product default or public Stage12 surface.

For comparison, the broad Stage10-v2 full replay reached the mechanically lower punctuation count **20/16/0,36** but is not the accepted research basis because semantic regressions were observed outside the hard-failing pair.

These persisted improvements do **not** change Product defaults. Final approved heavy evidence still requires zero unresolved hard failures and complete semantic acceptance.

## External production assets

Processing is offline once assets are provisioned.

The accepted OPUS EN→RU archive is pinned to SHA-256:

`798027c7e4ae7ddf89fea13ce80de517b6726d7e710fa5a9b5a376316dbf1677`

Build a verified local asset from an already downloaded archive:

```text
rocketdict-assets build-opus-en-ru opus-2020-02-11.zip /path/to/opus-asset
```

Set `ROCKETDICT_OPUS_ASSET_DIR` to that directory. The loader verifies the official archive identity recorded in the manifest and recomputes the complete local payload-tree SHA-256 before treating the model as available.

Production NLP requires an installed accepted spaCy English model; the current baseline is `en_core_web_sm 3.8.0` (`en-sm`). Stage21 uses pinned CEFR-J Vocabulary Profile evidence. Stage22 uses exact CMUdict entries; generated fallback is not authoritative Product evidence.

## Optional independent TC-big asset

The active independent EN→RU comparator is pinned `Helsinki-NLP/opus-mt-tc-big-en-zle` revision `708be1d372fe4c358a352f404e6dc9ca0126ba48`, source weights SHA-256 `e68caa9a233c177a3489257b69c18cece6da97767ab2581918ce3fc3c3899416`, license `CC-BY-4.0`.

It is deliberately separate from the baseline production asset. Install runtime-only dependencies with the `alt-mt` extra; provisioning additionally needs builder dependencies. The baseline `production` extra does not silently include TC-big.

Provision an exact local CTranslate2 float32 asset from a downloaded pinned Hugging Face snapshot:

```text
rocketdict-assets build-tc-big-en-ru /path/to/pinned-hf-snapshot /path/to/tc-big-asset
```

Set `ROCKETDICT_TC_BIG_ASSET_DIR` to the resulting asset. The manifest contract is `rocketdict-tc-big-en-ru-asset/1`. Runtime verification pins repository/revision/source weights/license/`>>rus<<`, MarianTokenizer payload, manifest SHA and the complete CTranslate2 payload-tree identity.

Inference uses local Hugging Face `MarianTokenizer` semantics plus CTranslate2 float32 and does **not** require Torch. Corrected full-*Opticks* parity evidence gives 52/52 input-token parity, 49/52 exact rank0 parity and at least one exact n-best overlap in all 52 tested residual rows. The three remaining rank0 ordering differences are explicit backend-search differences, not normalized away.

## Narrow TC-big rescue policy

TC-big is not a generic fallback. A second model may be invoked only by an existing hard failure plus a source-defined, boundary-safe trigger.

The target-delimiter wrapper considers only exact Stage10 contexts whose aggregate current target adds `()[]{}` delimiters beyond immutable source counts. A candidate must be a raw TC-big hypothesis, pass all maintained strict checks, preserve Gutenberg emphasis, remove the added delimiter debt and stay within target/source alphabetic ratio `0.75..1.50`.

The footnote-reference wrapper considers only an exact single current row/Stage10 source lead matching `[A-Z] _..._` whose exact ASCII marker is lost. A raw candidate must restore the marker, preserve emphasis, pass strict checks and stay within source-relative alpha `0.70..2.00`.

The figure-reference wrapper is similarly source-defined: an exact current row/Stage10 context must start `[in _Fig._ N.]`, already hard-fail, and lose that leading source-owned reference. A raw TC-big candidate must preserve a leading bracketed reference containing the same `N` and emphasized translated label, preserve overall emphasis, pass strict checks and stay within source-relative alpha `0.75..1.50`.

The later semicolon→question, equals-addition and angular wrappers follow the same fail-closed geometry: a source-defined defect class must already hard-fail; only unmodified raw TC-big hypotheses are eligible; strict maintained checks plus family-specific source invariants must pass. The short-DMS wrapper additionally requires one short (≤12 alphabetic words) source statement containing `Angle` and exactly one `D deg. M'. S''` expression, excluding longer technical sentences where mechanical cleanliness was shown insufficient.

The boundary-pair punctuation wrapper adds one more fail-closed class: two exact adjacent V1 rows, an independently proven lowercase-continuation false parser boundary, punctuation-only current hard debt, at most 40 alphabetic source words, and raw TC-big rank0 only. It does not use corpus offsets, source phrases or expected Russian text in Product selection logic.

Exact replacement geometry is mandatory. If a source context cuts through a current translation row, the rescue skips fail-closed rather than slicing a target string.

## CLI/API

`rocketdict-core` exposes database bootstrap, source import/interpretation, project summary, live Lab Registry and generic operation calls. The Workbench uses the same public surface through `RocketDictCore`.

`rocketdict-assets` provisions verified offline model assets, including `build-opus-en-ru` and optional `build-tc-big-en-ru`.

`rocketdict.api.operations.OPERATIONS` publishes inspectable callable metadata plus `rocketdict_execution_contract`; Stage15 hard gates additionally publish exact `rocketdict_quality_gate_semantics`.

## Verification and release boundary

The maintained direct Stage8→25 path and unified `rocketdict-product-run` source→Stage25 path are continuously verified with the real pinned spaCy/OPUS/CEFR-J runtime. Optional TC-big wrapper code must not alter this default path when disabled.

A narrow rescue is not promoted merely because one corpus improves. Required evidence includes source-defined triggering, exact boundary geometry, unmodified raw candidates, semantic review, persisted full-corpus regression, byte-exact untouched/source checks, SQLite integrity, exact model/asset identity, license attribution and explicit release-size/performance assessment.

After the heavy translation gates reach zero unresolved failures, the next release frontier is complete downstream heavy validation and the Windows distribution/clean-install path. Historical 0.30.x recovery remains provenance evidence, not the maintained Product critical path.
