# AGENTS.md — RocketDict autonomous development protocol

This repository contains unrelated historical website material as well as RocketDict. These instructions govern RocketDict development unless a task explicitly targets another area.

## Context recovery: progressive disclosure, not reduced reasoning

1. **Always start with `PROJECT_STATE.md`.** Treat it as volatile L1 operational memory, not as a source of historical truth.
2. **Check current HEAD.** If HEAD is newer/different than the checkpoint recorded in L1, inspect the changes after that checkpoint before relying on L1. Use targeted Git diff/commit inspection first.
3. **L1 catch-up is a start-of-iteration invariant.** If the preceding iteration did not successfully bring `PROJECT_STATE.md` to the actual repository state (for example because the tool session, context, or request ended before synchronization), the **very beginning of the next development request** must repair L1 from current HEAD/L3 **before starting new feature/research work**. Do this even when the user's next message is only `продолжай`. Do not carry a known-stale L1 forward for another iteration merely because the previous iteration already reported its engineering result.
4. **Then open `docs/memory/INDEX.md`.** Load only the L2 documents relevant to the task.
5. **Use L3 without restriction whenever needed.** Source code, tests, migrations, Git history/diff/blame, CI, logs, artifacts, experiments, recovered evidence, external documentation and other primary data are always available for verification, regression hunting, security, compatibility and confident engineering decisions.
6. Do **not** reread the whole repository, whole Git history, every document, or the complete requirements merely to reconstruct context already reliably summarized in L1/L2.
7. This is **not a reasoning-depth limit**. If correct work requires broad or exhaustive investigation, perform it. Progressive disclosure saves repeated recovery cost; it never justifies shallower analysis.
8. Prefer targeted search, Git diff, the narrowest relevant tests, and task-relevant documents first. Expand the search whenever evidence, uncertainty, safety, compatibility, or a failing test gives reason.
9. Before ending every substantial iteration, **replace stale content in `PROJECT_STATE.md` with the new current state**. Do not turn it into a diary.
10. Put new durable/non-obvious conclusions, rejected approaches, expensive research results, and architectural rationale into the appropriate L2 memory file, with links to evidence where useful.
11. Commit substantial engineering changes to Git together with relevant tests and documentation. Do not treat chat text as the project record.
12. Do not duplicate detailed chronology in L1/L2. Git history is the detailed history; L2 stores durable conclusions and routing only.
13. A concise user-facing report must never reduce internal analysis, verification, test depth, or willingness to inspect L3.

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

If synchronization nevertheless cannot be completed inside the current request because execution is interrupted or the available context/tool session ends, treat that as **explicit process debt, not a relaxed requirement**. At the start of the next development request, after reading L1 and current HEAD, clear that debt first: reconstruct the actual state from HEAD/L3, update stale L1 and any affected mandatory L2 files, commit the repair, and only then continue new development. The next request therefore acts as an automatic recovery boundary for any unfinished memory synchronization.
