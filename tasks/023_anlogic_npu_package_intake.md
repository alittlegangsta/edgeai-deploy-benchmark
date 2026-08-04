# Task 023

## Title

Anlogic NPU official package intake and build-chain validation.

## Status

Completed

## Stage

Stage 4 NPU package intake.

## Dependencies

Task 022 (`Completed`).

## Recommended Branch

`feature/anlogic-npu-package-intake`

## Goal

Reconstruct the provenance and dependency chain of the user-provided
`NPU_info` package and the already indexed official Anlogic sources, then
decide whether a version-matched DR1M90 NPU build can safely proceed. This is a
static intake and build-chain validation task. It does not load a kernel
module, write a bitstream, change a board image, execute a vendor program, or
convert the project YOLOv5n model.

## Target and invariants

- Board target: `MLK-F3P-CZ02-DR1M90`, AArch64.
- Observed board ABI: Buildroot 2022.02.6, Linux 6.1.111-rt42, glibc 2.25.
- Preserve Tasks 017--022 evidence and the frozen ncnn/YOLOv5n contracts.
- Keep vendor binaries, modules, bitstreams, images, SDKs, and model files
  outside Git; record identity and provenance only.
- Classify findings as document fact, source-code fact, engineering inference,
  or real-device observation.

## Acceptance criteria

1. `NPU_info` is inventoried with bounded root, file count/size, selected
   hashes, archive contents, provenance, and distribution status.
2. Official AlWiki and Gitee source references are mapped to the local package
   without treating a documentation reference as an obtained binary asset.
3. The AD101V20, AD103V20, DR1M90GEG484-2, DR1M90GEG400, and the current
   MLK-F3P-CZ02 board/version differences are explicitly recorded.
4. Driver, Kconfig/Makefile, Device Tree/HPF, runtime, demo, model, and host
   tool relationships are captured from source or documents.
5. Static ABI, architecture, vermagic, dependency, and build-entry checks are
   recorded. No vendor executable or module is run or loaded.
6. A single package verdict and secondary blockers are consistent with the
   evidence. Because the current package has conflicting prebuilt/source build
   identities and no verified current-board mapping, the automatic conclusion
   remains blocked until a controlled, version-matched package is approved.
7. Task 017--022 evidence remains immutable and offline repository validation
   passes.

## Allowed files

- `tasks/023_anlogic_npu_package_intake.md`
- `TASKS.md`
- `README.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `docs/vendor/ANLOGIC_NPU_PACKAGE_AND_BUILD_CHAIN.md`
- `.knowledge/manifests/anlogic_npu_package_intake.yaml`
- `scripts/vendor/audit_anlogic_npu_package.py`
- `scripts/vendor/validate_task023_npu_package.py`
- `results/evidence/023/*.json`
- Task 023 focused tests

## Forbidden changes

- Do not modify Task 017--022 task files, manifests, evidence, models, or
  runtime profiles.
- Do not copy SDKs, runtime libraries, `.ko` files, bitstreams, HPFs, images,
  model files, or vendor executables into Git.
- Do not execute vendor binaries or build/install scripts, load modules,
  flash media, write FPGA configuration, change Device Tree, or alter a board.
- Do not use sudo, install packages, download dependencies, commit, push,
  create a PR, merge, rebase, reset, or cherry-pick.

## Execution Record

- Start: `2026-08-04T11:38:03+08:00` Asia/Shanghai.
- Branch: `feature/anlogic-npu-package-intake`.
- Starting worktree: clean; `dev..HEAD` empty.
- Approved package root: `<windows-user>/Desktop/fpga_info/02_F3P_DR1M90GEG400_FPGA/NPU_info` (Windows user segment redacted in repository records).
- Read-only knowledge source: `/home/dministrator/vendor/anlogic-dr1-knowledge`.
- Knowledge-base limitation: the skill-requested
  `.knowledge/manifests/versions.yaml` is absent; version statements use the
  knowledge `VERSION_MATRIX.md` and the recorded repository manifests instead.

## Reconnaissance and findings

The package root contains 1,800 regular files and 886,827,911 bytes. It has
15 HPF files, 5 bitstream files, 7 top-level `.bin` files, and large SD-image,
FPGA-project, and demo archives. Direct search found no `.ko`, `rt.bin`,
`weight.bin`, `convert_tool`, `al_ai_flow`, `libnpu*`, or standalone runtime
file; a nested `face_detection.tar.gz` does contain AArch64 prebuilt modules,
Arm NN/Alnpu libraries, a demo ELF, and ONNX inputs.

The Milianke `soc_prj.al` source identifies `DR1M90GEG400`. The D20 projects
identify `AD101V20` or `AD103V20`; IPUG166 documents `DR1M90GEG484-2`. These
are not interchangeable board proofs. The extracted face-detection package
has prebuilt module vermagic `6.1.111-rt42 SMP preempt mod_unload aarch64`,
but its Makefiles default to a 5.10.142 kernel and an unrecorded
`aarch64-anlogic-11.3` toolchain. This is a source/build provenance conflict,
not a reproducible current-board build.

The official `dr1m90_npu` mirror is the separate SDK_2026.01 source line; the
knowledge base records the local SDK as SDK_2025_07. Shared CMake files do not
prove that the derived Milianke archive, SDK, HPF, bitstream, and current
eMMC image are one versioned release.

The first sandboxed VM retry returned `UtilBindVsockAnyPort: socket failed 1`
before a shell was reached. An escalated retry of the same read-only wrapper
then succeeded; the error was a WSL/vsock sandbox connection failure, not a
project build failure. The VM is Ubuntu 18.04.4 x86_64, glibc 2.27, GCC/G++
7.5.0, with no system CMake or Ninja. A user-local CMake 3.16.9, the exact
SDK kernel source/defconfig, and the Linaro AArch64 toolchain were available.

An isolated source build was performed without touching the board: the three
driver objects built with `6.1.111-rt42` vermagic, but no `Module.symvers` was
present and modpost emitted unresolved-symbol warnings; the Arm NN
face-detection application and generic Arm NN demos configured and linked
successfully. These are source/link-closure results, not module-load or
deployment approval. The exact native APUG runtime path was not built because
`convert_tool`, `al_ai_flow`, `npu_runtime`, `rt.bin`, and `weight.bin` remain
unavailable.

## Automatic verdict

- Primary feasibility verdict: `BLOCKED_BOARD_HARDWARE_MAPPING`.
- Secondary blockers: `BLOCKED_NATIVE_RUNTIME_ASSETS`,
  `BLOCKED_ARMNN_BACKEND_INCOMPLETE`, `MODULE_SYMBOL_CRC_UNVERIFIED`,
  `BLOCKED_BUILD_REPRODUCIBILITY`, `BLOCKED_PREBUILT_DEMO_DEPLOYMENT`,
  `BLOCKED_MODEL_ASSET_INCOMPLETE`, `BLOCKED_PROVENANCE_OR_LICENSE`,
  `BLOCKED_PACKAGE_RELEASE_IDENTITY`, `BLOCKED_RUNTIME_INCOMPLETE`,
  `BLOCKED_TOOLCHAIN`, `ACTIVE_BITSTREAM_UNKNOWN`, and
  `ACTIVE_DEVICE_TREE_MAPPING_UNKNOWN`.
- Path status: native runtime is blocked by missing assets; the Arm NN path is
  buildable in isolation but not deployment-ready; driver static identity has
  AArch64/vermagic evidence but no symbol-CRC proof; source build status is
  partial; board mapping remains blocked. See
  `results/evidence/023/npu_build_attempt.json`.
- No driver was loaded, no bitstream or image was written, and no NPU program
  was executed.

## Audit approval

- `automated_audit`: `COMPLETE`.
- `audit_review`: `PASS`.
- `audit_review_source`: `user`.
- `candidate_approved`: `true` (approval covers the audit record only; it does
  not approve module loading, bitstream deployment, or NPU execution).
- Approval timestamp: `2026-08-04T13:45:30+08:00` Asia/Shanghai, recorded in
  WSL as the audit-approval record time, not a VM audit time, board time, or
  NPU program time.
- `deployment_readiness`: `BLOCKED`.
- `vendor_one_shot`: `NOT_EXECUTED`.
- `controlled_board_deployment`: `NOT_APPROVED`.
- `project_yolov5n_conversion`: `NOT_READY`.

Task 023 audit is complete; the Arm NN isolated build is verified, while board
deployment and NPU runtime execution remain blocked/not performed.

This verdict does not claim that DR1M90 hardware lacks NPU support. It states
that the supplied assets can be partially compiled but cannot yet be mapped
safely to the current board image. The Arm NN/ONNX demo path is distinct from
the native `npu_runtime`/`rt.bin`/`weight.bin` path, while both still require
the same version-matched driver, CMA, Device Tree and FPGA substrate. The next
safe step is a vendor package intake review with an explicit
board/kernel/SDK/bitstream/runtime matrix, followed by a separately approved
controlled deployment.

## Resume / next action

Obtain a version-matched package for `MLK-F3P-CZ02-DR1M90`, AArch64,
Buildroot 2022.02.6, Linux 6.1.111-rt42, and glibc 2.25. Require matching
driver source and modules, kernel source/config, HPF/bitstream/DT mapping,
runtime headers/libraries, official one-shot model assets, host converters,
licenses, and reproducible commands. Do not deploy any of those files until a
separate controlled deployment task is approved.

## Validation record

- `python3 scripts/vendor/audit_anlogic_npu_package.py --npu-info <approved-local-NPU_info-root> --knowledge-root <approved-knowledge-root> --output /tmp/task023-audit-generated-final.json` passed and reported 1,800 files, 886,827,911 bytes, and 65 selected-pattern paths; the output remained outside the repository.
- All nine Task 023 JSON evidence files and the YAML manifest parsed.
- The Task 023 validator passed; it validates the six path-readiness fields, recorded isolated-build limitations, one-shot absence, and safety fields.
- Twenty-three selected external-file SHA256 comparisons passed.
- `PYTHONPATH=python ./.venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'` passed: 118 tests.
- `cmake --build build/pc-all-release --config Release -j2` passed and `ctest --test-dir build/pc-all-release --output-on-failure` passed: 14/14. This was the existing PC build, not an NPU build.
- `bash -n scripts/vendor/*.sh scripts/arm/*.sh` passed; Python compilation passed; `git diff --check` passed.
- Task 017--022 files and evidence have no diff. No vendor program, module, bitstream, board, or image was modified.
- The system Python test invocation was not used as the final result because it lacked project dependencies; the repository `.venv` plus `PYTHONPATH=python` invocation passed. The initial sandboxed VM wrapper invocation failed before reaching its shell, but the escalated read-only invocation succeeded and the isolated build commands recorded in `npu_build_attempt.json` completed as stated.
- User approval was recorded in WSL after the offline checks; no VM or board was
  accessed during approval finalization.

## Commands not run

No native `npu_runtime`/converter build, SDK image build, `insmod`, vendor ELF
execution, bitstream write, board deployment, or project YOLOv5n conversion
was performed. The only builds were isolated SDK driver-source and Arm NN
application builds in VM user workspaces; their outputs remain outside Git.

## Completion record

- Final state: `Completed`.
- Final primary verdict: `BLOCKED_BOARD_HARDWARE_MAPPING`.
- Final deployment state: blocked; no controlled board deployment approved.
- Final commit is recorded by the repository history after the explicit
  Task 023 commit procedure.
