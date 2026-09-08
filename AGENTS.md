# AGENTS.md — RocketDict autonomous development protocol

This repository contains unrelated historical website material as well as RocketDict. These instructions govern RocketDict development unless a task explicitly targets another area.

## Context recovery: progressive disclosure, not reduced reasoning

1. **Always start with `PROJECT_STATE.md`.** Treat it as volatile L1 operational memory, not as a source of historical truth.
2. **Check current HEAD.** If HEAD is newer/different than the checkpoint recorded in L1, inspect the changes after that checkpoint before relying on L1. Use targeted Git diff/commit inspection first.
3. **Then open `docs/memory/INDEX.md`.** Load only the L2 documents relevant to the task.
4. **Use L3 without restriction whenever needed.** Source code, tests, migrations, Git history/diff/blame, CI, logs, artifacts, experiments, recovered evidence, external documentation and other primary data are always available for verification, regression hunting, security, compatibility and confident engineering decisions.
5. Do **not** reread the whole repository, whole Git history, every document, or the complete requirements merely to reconstruct context already reliably summarized in L1/L2.
6. This is **not a reasoning-depth limit**. If correct work requires broad or exhaustive investigation, perform it. Progressive disclosure saves repeated recovery cost; it never justifies shallower analysis.
7. Prefer targeted search, Git diff, the narrowest relevant tests, and task-relevant documents first. Expand the search whenever evidence, uncertainty, safety, compatibility, or a failing test gives reason.
8. Before ending every substantial iteration, **replace stale content in `PROJECT_STATE.md` with the new current state**. Do not turn it into a diary.
9. Put new durable/non-obvious conclusions, rejected approaches, expensive research results, and architectural rationale into the appropriate L2 memory file, with links to evidence where useful.
10. Commit substantial engineering changes to Git together with relevant tests and documentation. Do not treat chat text as the project record.
11. Do not duplicate detailed chronology in L1/L2. Git history is the detailed history; L2 stores durable conclusions and routing only.
12. A concise user-facing report must never reduce internal analysis, verification, test depth, or willingness to inspect L3.

## Requirements and evidence authority

- [`rocketdict/PRODUCT_TARGET.md`](rocketdict/PRODUCT_TARGET.md) is the current authoritative Product contract and remains mandatory. The memory system does not shorten, replace, or relax it.
- Existing historical/research contracts remain evidence when relevant; route to them through `docs/memory/INDEX.md` rather than loading all of them by default.
- For what the software **actually does now**, source code, tests, CI results and artifacts (L3) outrank L1/L2 summaries.
- If L1/L2 contradicts L3 or the Product contract, investigate the discrepancy, follow the authoritative evidence/requirements, and update the stale memory.

## Quality guardrails

- Quality > speed/storage convenience.
- Never accept fake, identity, dictionary-only, mock or synthetic MT as real Product translation.
- Never weaken acceptance thresholds or bypass a real gate merely to make CI green.
- Never silently truncate the acceptance corpus/source.
- Preserve immutable identities, hashes, failed experiments and reproducible evidence where the Product/research contracts require them.
- Distinguish an implementation/model defect from an evaluator/orchestration defect before changing acceptance logic.
- Public repository memory must remain project-only; do not add personal profile, credentials, secrets or unrelated private conversation context.

## End-of-iteration memory hygiene

Update L1 only with the current goal/checkpoint/proven facts/blockers/hot paths/next actions. Move only durable reasoning to L2. Leave raw logs, large evidence, code excerpts and chronology in L3. A future agent should be able to recover the normal case as:

`PROJECT_STATE.md → HEAD diff if needed → docs/memory/INDEX.md → relevant L2 → targeted/unrestricted L3 as evidence demands`.

### Mandatory pre-response synchronization

After **every development iteration** and **before every user-facing result/report**, synchronize all three of these repository memory files to the actual current HEAD, CI/artifact evidence, active blockers and durable conclusions:

1. `PROJECT_STATE.md`
2. `docs/memory/TRANSLATION_QUALITY.md`
3. `docs/memory/DECISIONS.md`

This is mandatory even when only one of the files changed conceptually. Replace stale statements rather than appending a diary. If a file has no new durable decision, still verify it against current L3 and update any stale contracts/checkpoints before replying. Do not send the final user-facing development summary first and promise to repair memory later; the memory synchronization is part of completing the iteration.
