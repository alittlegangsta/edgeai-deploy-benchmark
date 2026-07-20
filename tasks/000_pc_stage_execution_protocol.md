# PC Stage Execution Protocol

## Purpose

This file is the durable control plane for Tasks 002 through 012. It defines how
Codex selects work, records progress, recovers after interruption, preserves real
evidence, and stops for human decisions. Chat context must not be treated as the
source of truth.

## State Machine

The only valid task states are `Planned`, `In Progress`, `Blocked`, and
`Completed`.

```text
Planned
  | dependencies Completed, branch/worktree safe, task fully read
  v
In Progress
  |-- acceptance passes ------------------------------> Completed
  |-- recoverable failure, fewer than 3 attempts -----> In Progress
  |-- mandatory stop or third failed repair attempt --> Blocked
  |                                                       |
  |        human action recorded and failed command rerun |
  +-------------------------------------------------------+

Completed is terminal. Its evidence must not be rewritten.
```

Before the first task mutation, change the selected task from `Planned` to
`In Progress` in both its task file and `TASKS.md`. A stopped task must carry a
complete blocking report and resume commands in its task file. Only real command
success permits the transition to `Completed`.

## Startup and Task Selection

For every fresh or resumed execution:

1. Read `AGENTS.md`, this protocol, and `TASKS.md` completely.
2. Run `git branch --show-current` and `git status --short --untracked-files=all`.
3. If a task is `Blocked`, follow Recovery Protocol before selecting new work.
4. Otherwise select the lowest-numbered `Planned` task whose dependencies are
   all `Completed`.
5. Verify the branch matches the task's Recommended Branch and that unrelated
   changes are absent.
6. Read the entire selected task file.
7. Verify every intended path is in Allowed Files before changing state or files.

The user may explicitly select a different eligible task, but dependency checks
and all stop conditions still apply.

## Execution Batches

| Batch | Tasks | Recommended Branch | Required Stop |
| --- | --- | --- | --- |
| A | 002-005 | `feature/pc-batch-a-python-baseline` | Checkpoint A after Task 005 |
| B | 006-009 | `feature/pc-batch-b-cpp-ort` | Checkpoint B after Task 009 |
| C | 010-012 | `feature/pc-batch-c-ncnn-acceptance` | Checkpoint C after Task 012 |

Within a batch, Codex may proceed automatically to the next numbered task only
after the current task is truly `Completed`, its local atomic commit is complete
when commits are permitted, the next dependency is satisfied, the worktree has
no unrelated changes, and the branch matches the batch. Only one task is active
at any instant. Codex must stop at each batch checkpoint and wait for human
review; it must not begin the next batch automatically.

## Default Automatic Permissions

Subject to the active task's Allowed Files and the user's current instructions,
Codex may by default:

- Read repository files.
- Modify only the active task's Allowed Files.
- Create small text configuration files explicitly required by the active task.
- Create project source files explicitly required by the active task.
- Configure and compile the project.
- Run tests and existing project programs.
- Generate small result images and real JSON, CSV, and log evidence.
- Delete build artifacts created by the active task when the task identifies them
  as reproducible.
- Create one local atomic commit after every completion condition has passed.

Current user instructions override these defaults. Permission for one task never
expands the Allowed Files of another task.

## Default Prohibitions

Codex must not:

- Use `sudo` or `apt`, or otherwise modify the system environment.
- Access the network or download files.
- Install Python or system packages.
- Modify shell startup configuration.
- Read private files outside the repository.
- Upload files.
- Run `git push`, create a GitHub pull request, or merge branches.
- Delete user data.
- Modify the frozen model contract outside Task 002.
- Modify recorded benchmark results outside the task that produced them.
- Modify evidence belonging to a `Completed` task.

## Repair Attempts

One repair attempt is the complete sequence `diagnose -> modify -> rebuild ->
retest -> rerun`. The active task's Execution Record must identify attempts 1,
2, and 3 separately, including commands, exit codes, changes, and results. A
failure that triggers a mandatory stop is not automatically repairable. After a
third failed complete repair attempt, mark the task `Blocked` and stop.

Acceptance tests, tolerances, core behavior, and truthfulness constraints are
immutable during repair. Do not delete or skip a failing check, hard-code its
answer, or replace real output.

## Mandatory Stop Conditions

On any condition below, preserve the current state, write a Blocking Report in
the active task, and stop for the user.

### Environment and Dependencies

- A required system dependency is missing.
- Progress requires `sudo`, `apt`, `pip`, `uv sync`, `conda`, or any environment
  modification.
- Progress requires downloading a model, toolchain, ONNX Runtime, ncnn, or data.
- An installed local version is incompatible with the active task.

### Model Contract

- Actual ONNX input or output names differ from the frozen contract.
- Actual input shape, output shape, or dtype differs from the frozen contract.
- Whether the graph contains NMS cannot be confirmed.
- A model SHA256 differs from the manifest.
- Model provenance is unclear.
- A different model, opset, input size, or export strategy is needed.

Task 002 freezes the contract only after inspecting the real model. Before that
inspection, unknown names, dimensions, and candidate counts remain explicitly
unresolved rather than being guessed.

### Correctness

- Python and C++ input tensors exceed the specified tolerance.
- Python and C++ ONNX Runtime detections exceed the specified tolerance.
- ONNX Runtime and ncnn detections exceed the specified tolerance.
- An output image requires human visual judgment.
- Detections are clearly empty, malformed, or assigned implausible classes.
- Tests still fail after three complete repair attempts.

### Benchmark

- A Debug build is selected for a formal benchmark.
- Warmup count, repeat count, or thread count is unspecified.
- Latency contains conspicuous outliers requiring interpretation.
- The benchmark environment changes during a comparison.
- Preprocess, inference, postprocess, and pipeline total cannot be separated.
- A decision is required about including image read, drawing, or video encoding.
- Real performance results need human confirmation.

### Git and File Safety

- The worktree contains changes unrelated to the active task.
- The current branch is wrong.
- Progress requires deleting a file not created by the active task.
- Progress requires pushing, opening a pull request, merging, or changing a remote.
- Credentials, tokens, SSH keys, or a private SDK would be involved.
- A large model, video, or binary would need to be committed.

## Blocking Report Format

Every `Blocked` task must append and fill this exact structure in its task file:

```text
Current Task:
Current Status:
Last Successful Step:
Failed Command:
Exit Code:
Relevant Error:
Files Changed:
Attempts Made:
Why Automatic Recovery Is Unsafe:
Exact Human Action Required:
Commands to Resume:
Git Status:
```

Do not replace this report with a generic statement about the environment.

## Recovery Protocol

After human intervention, Codex must:

1. Re-read this protocol.
2. Check the current branch.
3. Check the complete Git status, including untracked files.
4. Read the `Blocked` task's Execution Record and Blocking Report.
5. Re-run the recorded failed command exactly, unless the user explicitly
   authorizes a documented replacement.
6. Treat the intervention as unverified until that command succeeds.
7. Resume the automatic task flow only after all remaining checks pass.

If recovery changes the model contract, benchmark methodology, or an already
completed task's evidence, stop and request a separate approved task.

## Evidence and Execution Record

Each task file begins with an empty Execution Record. During execution it must be
updated with:

- Start and completion timestamps with timezone.
- Branch and starting Git status.
- Actual environment and dependency versions.
- Exact build, run, and test commands with exit codes.
- Concise real output summaries and artifact paths.
- SHA256 values for evidence whose identity matters.
- Repair-attempt count and outcome.
- Skipped optional checks and exact reasons.
- Final `git diff --check` and Git status.
- Local commit hash when a commit is permitted and created.

Logs and structured evidence must be generated by the command they describe.
Expected schemas are not evidence. Never overwrite an earlier task's evidence.

## Local Commit Procedure

Only after all completion conditions pass:

1. Verify every changed path belongs to the active task's Allowed Files.
2. Stage explicit paths; never use `git add .`.
3. Run `git diff --cached --check` and inspect `git diff --cached`.
4. Commit once using the active task's Recommended Commit.
5. Record the commit hash in the task's Execution Record.

Do not commit when the user has prohibited it for the current turn. Never push.

## Mandatory Human Checkpoints

### Checkpoint A: after Task 005

Stop and present:

- Model provenance, version, and SHA256.
- Actual ONNX input and output contract.
- Python result image.
- Structured detections.
- Python test results.
- Known discrepancies and risks.

### Checkpoint B: after Task 009

Stop and present:

- Python/C++ preprocessing-alignment results.
- C++ ONNX Runtime detections.
- Video-inference result.
- Benchmark measurement boundaries.
- Warmup, repeat, and thread-count settings.
- Real performance summary.

### Checkpoint C: after Task 012

Stop and present:

- ONNX Runtime/ncnn detection alignment.
- Python ORT, C++ ORT, and C++ ncnn performance table.
- Result images or video.
- Complete README.
- PC-stage acceptance matrix.
- Unresolved risks.

Checkpoint approval is a human decision. Completion of a checkpoint task does
not authorize ARM-stage work.

## Resume Commands

Use these read-only commands to re-establish state from the repository root:

```bash
git branch --show-current
git status --short --untracked-files=all
sed -n '1,260p' AGENTS.md
sed -n '1,360p' tasks/000_pc_stage_execution_protocol.md
sed -n '1,260p' TASKS.md
```

Then read the selected or `Blocked` task file in full and execute only its
documented commands.
