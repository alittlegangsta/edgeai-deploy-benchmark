# Repository Instructions for Coding Agents

- Work on one task at a time and read the active task file completely before editing.
- Follow the task's allowed-file list and forbidden-change list exactly.
- Keep changes narrow; do not perform broad refactors outside the active task.
- Never fabricate build output, runtime results, logs, benchmark data, or screenshots.
- Do not download dependencies silently or add dependency-fetching mechanisms.
- Use C++17 for C++ code and prefer target-based CMake configuration.
- Keep inference-independent modules separate from inference-backend adapters.
- Do not commit or push unless the user explicitly requests it.
- Report commands actually run separately from commands not run.
- If an environmental dependency is missing, stop the affected operation and report
  the exact error without installing, downloading, or substituting the dependency.

## Task Execution Protocol

The PC-stage source of truth is `tasks/000_pc_stage_execution_protocol.md`. Every
execution turn must begin by reading this file, this repository instruction file,
and `TASKS.md`. Progress, attempts, evidence paths, and resume instructions belong
in the active task file; chat history is not a progress database.

### Task States

Every task must use exactly one of these states:

```text
Planned
In Progress
Blocked
Completed
```

Do not use approximate or compound states such as "almost complete", "pending
review", or "partially blocked".

### Task Selection

At the start of work, Codex must:

1. Read `AGENTS.md` completely.
2. Read `tasks/000_pc_stage_execution_protocol.md` completely.
3. Read `TASKS.md` completely.
4. Select the lowest-numbered `Planned` task whose dependencies are all
   `Completed`.
5. Read that task file completely before modifying any file.
6. Process only one task at a time unless the execution protocol explicitly
   permits sequential execution within the same batch.

An existing `Blocked` task is resumed only through the recovery protocol; it is
not skipped in favor of a later task.

### Completion Conditions

A task may be marked `Completed` only when all of the following are true:

- Every Acceptance Criterion has passed in a real execution.
- Every Build Command required by the task has run successfully.
- Every Run Command required by the task has run successfully.
- Every Test Command required by the task has run successfully.
- Real output is preserved or summarized in the task's Execution Record.
- `git diff --check` reports no errors.
- No Forbidden File has been modified.
- No fabricated data or result has been used.
- Every skipped item is explicitly reported; required items cannot be skipped.

Static review, expected output, or code inspection cannot replace actual builds,
runs, or tests. Update the active task file and `TASKS.md` together whenever a
state changes.

### Repair Loop

After a task command fails, Codex may perform at most three complete repair
attempts. Each attempt is:

```text
diagnose
-> modify
-> rebuild
-> retest
-> rerun
```

Record each attempt and its exact failing command in the active task file. If the
third complete attempt still fails, mark the task `Blocked`, write the required
blocking report, and stop. Never make a task pass by deleting tests, weakening a
critical tolerance, commenting out core logic, hard-coding detections, fabricating
output artifacts, skipping a failing command, or changing Acceptance Criteria.

### Git Rules

The PC-stage protocol authorizes one local atomic commit after a task has fully
passed, unless the user's current instruction forbids committing. For such a
commit Codex must:

- Stage only genuinely changed paths listed in the task's Allowed Files.
- Never use `git add .`.
- Run `git diff --cached --check` before committing.
- Create exactly one commit for the task.
- Use the Conventional Commit message specified by `Recommended Commit`.
- Never push, create a pull request, merge branches, rewrite history, use
  `--force`, use `reset --hard`, or delete user commits.

If the current branch does not match the execution protocol and active task,
stop and report it. Do not switch or create a branch without authorization.

### Evidence Authenticity

The following facts must come from actual commands and artifacts, never from
code inference or invented examples:

```text
detection boxes
classes
confidence scores
tensor shapes
tensor numeric statistics
latency
FPS
memory use
CPU utilization
model file size
output images
output videos
test pass status
```

Expected schemas and illustrative placeholders must be labeled as such and must
never be presented as measured evidence.
