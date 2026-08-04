# Task 022

## Title

Anlogic DR1 NPU runtime and official YOLO one-shot feasibility audit.

## Status

Completed

## Stage

Stage 4 NPU runtime feasibility audit.

## Dependencies

Tasks 016 and 021 (`Completed`).

## Recommended Branch

`feature/anlogic-npu-runtime-audit`

## Goal

Audit the approved local Anlogic/DR1 materials, VM environment, and real
DR1M90 board state for a vendor-supplied NPU runtime and official YOLO
one-shot. This task does not convert the frozen project model, load modules,
write the board, or perform an NPU benchmark.

## Scope and invariants

- Preserve Tasks 017–021 evidence and the frozen YOLOv5n/ncnn contracts.
- Search only the approved vendor-material root, the repository vendor/knowledge
  paths, explicit VM vendor paths, and the explicit board paths required by the
  audit.
- Use document, source-code, VM-observation, and real-device-observation
  classifications; do not infer a runtime from filenames alone.
- Do not install, download, compile, load modules, modify system files, or run
  an unverified vendor executable.

## Acceptance criteria

1. Local vendor assets and source identities are inventoried with type, size,
   SHA256, provenance, and applicability status.
2. Official document requirements for HardNPU/SoftNPU, bitstream/device-tree,
   drivers, CMA, runtime, model format, and one-shot execution are extracted
   without promoting undocumented assumptions to facts.
3. VM and board audits are captured as structured JSON with command scope and
   unavailable values explicit.
4. A dependency matrix records each required asset, local/VM/board presence,
   version/hash evidence, and gap.
5. The feasibility verdict is one of the approved BLOCKED/PASS categories and
   is consistent with the evidence. An official one-shot is attempted only if
   every safety gate is satisfied.
6. Task 017–021 evidence hashes remain unchanged and offline repository checks
   pass.

## Allowed files

- `tasks/022_anlogic_npu_runtime_feasibility_audit.md`
- `TASKS.md`
- `README.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `docs/vendor/ANLOGIC_NPU_RUNTIME_FEASIBILITY.md`
- `.knowledge/manifests/anlogic_npu_runtime_audit.yaml`
- `scripts/vendor/audit_anlogic_npu_assets.py`
- `scripts/arm/audit_anlogic_npu_board.sh`
- `scripts/vendor/validate_task022_npu_audit.py`
- `results/evidence/022/*.json`
- Task 022 focused tests

## Forbidden changes

- Do not modify Task 017–021 task files, manifests, evidence, models, or
  runtime profiles.
- Do not add SDKs, runtimes, kernel modules, bitstreams, models, ELF files, or
  large vendor logs to Git.
- Do not use sudo, install packages, download assets, run vendor build scripts,
  load modules, alter the board, or execute an unverified one-shot.
- Do not commit, push, create a PR, merge, rebase, reset, or cherry-pick.

## Execution Record

- Start: 2026-08-03 Asia/Shanghai (recorded in the audit evidence).
- Branch: `feature/anlogic-npu-runtime-audit`.
- Starting worktree: clean; `dev..HEAD` empty.
- Progress: local vendor/document reconnaissance started. The WSL vsock issue
  was resolved for this recovery turn; the approved VM and board probes now
  reach their target shells and the full read-only audit can continue.

## Final status

The audit is `Completed` after user review of the automatic result. The NPU
deployment readiness conclusion remains `BLOCKED_DRIVER_OR_DEVICE`.

```text
Task 022: Completed
automated_audit: COMPLETE
audit_review: PASS
audit_review_source: user
candidate_approved: true
verdict: BLOCKED_DRIVER_OR_DEVICE
vendor_one_shot: NOT_EXECUTED
project YOLOv5n conversion readiness: NOT_READY
```

Approval recorded at `2026-08-04T10:21:18+08:00` in WSL. This is an audit
approval record time, not the VM audit time, board audit time, or an NPU program
runtime. The user approved the feasibility conclusion only; no driver loading,
one-shot execution, or project-model conversion was authorized.

## Historical Blocking Report (wrapper outage before recovery)

Current Task: 022 Anlogic DR1 NPU runtime and official YOLO one-shot feasibility audit
Current Status: Blocked
Last Successful Step: Verified the required branch/worktree baseline and performed bounded local vendor/document reconnaissance.
Failed Command: `/home/dministrator/bin/anlogic-vm-ssh '<read-only VM audit>'`; `/home/dministrator/bin/anlogic-board-ssh '<read-only board audit>'`; board probe retry `/home/dministrator/bin/anlogic-board-ssh 'echo board_ssh=PASS; uname -a; id'`
Exit Code: 1 for each wrapper invocation
Relevant Error: `<3>WSL (3 - ) ERROR: UtilBindVsockAnyPort:307: socket failed 1`
Files Changed: `tasks/022_anlogic_npu_runtime_feasibility_audit.md`, `TASKS.md`
Attempts Made: VM wrapper attempted twice with the same read-only audit; board wrapper attempted once with the full read-only audit and once with the minimal SSH probe. No VM or board command reached its target shell.
Why Automatic Recovery Is Unsafe: The approved wrappers are the unique access paths. Bypassing them would violate the task boundary, and no VM/board runtime or device state may be inferred from local files.
Exact Human Action Required: Restore the WSL vsock/VM-board SSH wrapper path (or confirm that the VM and board access services are available), then rerun the recorded probes without changing the board or SDK.
Commands to Resume: `/home/dministrator/bin/anlogic-vm-ssh 'uname -a; cat /etc/os-release; ...'`; `/home/dministrator/bin/anlogic-board-ssh 'echo board_ssh=PASS; uname -a; id'`
Git Status: Task 022 files are modified and unstaged; no commit, push, PR, merge, rebase, reset, module load, board write, or vendor executable run was performed.

## Recovery Record

- Recovery date: 2026-08-04 Asia/Shanghai.
- The original VM and board probes were rerun through the approved wrappers
  with controlled host access after the user confirmed availability.
- Board probe result: `board_ssh=PASS`, Linux `6.1.111-rt42`, `aarch64`, root.
- VM probe result: Ubuntu 18.04.4, kernel `4.15.0-91-generic`, `x86_64`.
- The vsock failure is resolved for this turn. The former Blocking Report is
  retained as history; it no longer blocks the audit.

## Execution Record (recovery and automatic audit)

- Recovery probes reached both approved wrappers on 2026-08-04. The VM is
  Ubuntu 18.04.4 x86_64 with GCC/G++ 7.5.0, glibc 2.27, no CMake, no Ninja,
  and no Docker. The board is the AArch64 DR1M90 image (Buildroot 2022.02.6,
  Linux 6.1.111-rt42, glibc 2.25).
- The bounded local/VM/board evidence is in
  `results/evidence/022/npu_asset_inventory.json`,
  `npu_document_requirements.json`, `npu_vm_audit.json`,
  `npu_board_audit.json`, and `npu_dependency_matrix.json`.
- Offline parser, validator, focused-unit, full-unittest, Release-build, CTest,
  link, immutability, sensitivity, and diff checks are summarized in
  `results/evidence/022/validation.json`.
- APUG1205_0.1 and IPUG166_1.0 were read from the approved local document
  collection. Their document facts require a version-matched SoftNPU
  bitstream, three Linux modules, CMA-backed runtime access, a versioned
  `npu_runtime` package, and official `rt.bin`/`weight.bin` artifacts. These
  requirements are not treated as current-board facts.
- The board currently has a hard_npu device-tree/platform node and 128 MiB
  CMA reservation, but no bound NPU driver, no NPU/CMA module loaded or found
  under `/lib/modules`, no `/dev/hard_npu`, `/dev/soft_npu`, or `/dev/cma_mem`,
  and no board-side runtime/model files in the bounded search.
- The VM SDK has AArch64 Arm NN/Alnpu candidate libraries and vendor demo
  source, but no standalone `libnpu_runtime`, no prebuilt NPU modules, no
  `convert_tool`/`al_ai_flow` executables, and no `rt.bin`/`weight.bin` pair in
  the searched paths. No vendor executable or script was run.
- The official one-shot safety gate therefore failed before execution. The
  recorded verdict is `BLOCKED_DRIVER_OR_DEVICE`; the one-shot evidence file
  was intentionally not created because no one-shot was run.
- No board, VM, SDK, model, Task 017–021 evidence, or system file was modified.

## Automatic audit result

```text
Task 022: Completed
automated_audit: COMPLETE
audit_review: PASS (user)
candidate_approved: true
NPU feasibility: BLOCKED_DRIVER_OR_DEVICE
official one-shot: NOT_EXECUTED (gate not satisfied)
project YOLOv5n NPU conversion: not ready
```

The primary verdict is a current driver/device readiness block, not a claim that
DR1M90 permanently lacks NPU support. Secondary blockers are
`BLOCKED_MISSING_VENDOR_ASSETS`, `BLOCKED_RUNTIME_ABI_OR_IDENTITY_UNVERIFIED`,
`BLOCKED_TOOLCHAIN`, `BLOCKED_DOCUMENTATION_GAP`, and
`UNKNOWN_BITSTREAM_DT_MAPPING`.

The current materials and board image do not safely satisfy the official
one-shot prerequisites. Project YOLOv5n conversion, NPU performance work, and
UVC-camera NPU inference are not ready.

## Vendor request checklist

Request a version-matched package for `MLK-F3P-CZ02-DR1M90`, AArch64,
Buildroot 2022.02.6, Linux 6.1.111-rt42, and glibc 2.25 containing:

1. `hard_npu.ko`, `soft_npu.ko`, and `cma_mem.ko`, plus complete matching
   source, Makefile, kernel configuration/build instructions, vermagic,
   module order/parameters, expected dmesg/device nodes, and rollback steps.
2. AArch64 `npu_runtime` libraries, C/C++ headers, version/API/error-code
   documentation, link instructions, dependencies, license, and the
   glibc/libstdc++ and kernel compatibility matrix.
3. The matching SoftNPU bitstream, HPF/hardware-platform file, Device Tree or
   overlay, kernel configuration, version mapping, safe load method, affected
   system functions, and rollback procedure.
4. The official one-shot source or ELF, test image, model identity,
   `rt.bin`, `weight.bin`, configuration, run script, expected output, hashes,
   and version information.
5. `convert_tool`, `al_ai_flow`, quantization/model compiler tools, supported
   operators, version matrix, host OS/Python requirements, format and YOLO
   limitations, and license/dongle requirements.

## Approval and offline closeout record

- User approval: `PASS`, source `user`, recorded at
  `2026-08-04T10:21:18+08:00` in WSL. This timestamp is not a VM audit time,
  board audit time, or NPU program runtime.
- `candidate_approved: true`; this approves the feasibility audit result only.
- `vendor_one_shot: executed=false, status=NOT_EXECUTED`.
- Offline validator, focused tests (7), full Python unittest (115), Release
  build, CTest (14), YAML/JSON parsing, syntax, hash/matrix, safety,
  immutability, sensitive-material, repository-hygiene, Markdown-link, and
  `git diff --check` validations passed. Details are in
  `results/evidence/022/validation.json`.
- No VM or board access occurred during approval closeout. No module, bitstream,
  system library, SDK, model, or Task 017–021 evidence was changed.
- Task 023 is only a future vendor-package intake/provenance task; no Task 023
  implementation files were created.
