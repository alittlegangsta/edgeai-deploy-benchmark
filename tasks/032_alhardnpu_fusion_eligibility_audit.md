# Task 032

## Title

ALHardNPU fusion eligibility audit.

## Status

Completed

## Dependencies and branch

Depends on Task 031 (`Completed`). The user selected the current `dev` branch;
no branch switch is authorized.

## Goal

Use a bounded static audit of the retained AArch64 ArmNN/Alnpu binaries and the
immutable Task 028/031 evidence to explain why the face positive control forms
three `Alnpu|ALHardNPU` assignments while YOLOv5n does not. The audit must not
modify models, quantization, bitstreams, board files, or runtime libraries and
must not access the VM or development board.

## Required scope

1. Audit `ConvertConv2dIntoALHardNPUImpl` and its directly named symbols using
   available source, `nm`, `readelf`, `objdump`, strings, RTTI and vtable data.
2. Separate proven capability facts from string-level indications and facts that
   are not recoverable without backend source or an AArch64 disassembler.
3. Preserve the measured face assignment count and explain the limits of
   mapping those assignments to exact original ONNX node ranges.
4. Compare the frozen YOLOv5n FP32, AL_onnx_pass and quantized graph patterns
   with the face graph and retained real Optimize failures.
5. Assess whether AL_onnx_pass creates, preserves or destroys a proven
   ALHardNPU fusion pattern; do not infer a precise predicate without evidence.

## Allowed files

```text
TASKS.md
ROADMAP.md
README.md
CHANGELOG.md
tasks/032_alhardnpu_fusion_eligibility_audit.md
docs/vendor/ANLOGIC_ALHARDNPU_FUSION_ELIGIBILITY.md
.knowledge/manifests/alhardnpu_fusion_eligibility.yaml
scripts/vendor/audit_task032_alhardnpu_fusion.py
tests/python/test_task032_alhardnpu_fusion.py
results/evidence/032/fusion_symbol_audit.json
results/evidence/032/face_fusion_regions.json
results/evidence/032/yolov5n_pattern_comparison.json
results/evidence/032/al_onnx_pass_pattern_audit.json
results/evidence/032/fusion_eligibility_verdict.json
results/evidence/032/validation.json
```

Task 028 and Task 031 files are immutable inputs and may only be read.

## Forbidden changes and actions

- Do not modify or regenerate Task 028/031 evidence, models, inputs or logs.
- Do not modify YOLO, QDQ, AL_onnx_pass, ArmNN, bitstream, kernel, DTB or
  runtime files.
- Do not access the VM or development board, run an NPU workload, benchmark,
  install dependencies, or search for additional vendor releases.
- Do not copy vendor binaries, models, SDKs, datasets, credentials or keys into
  Git. External identities may be recorded as portable paths, sizes and hashes.
- Do not push, create a PR, merge, rebase or reset. A local commit is allowed
  only after the acceptance criteria pass and the user explicitly authorizes
  it; the current finalization instruction provides that authorization.

## Recommended Commit

`docs(npu): audit ALHardNPU fusion eligibility`

## Acceptance criteria

1. A structured static symbol audit records the exact available
   `ConvertConv2dIntoALHardNPUImpl` symbols, the ten concrete Alnpu support
   overrides, the generic support methods that resolve to the base rejection
   path, archive/library/build identities, and the disassembly/source limits.
2. The face evidence records three retained fused assignments, graph-level
   candidate patterns and an explicit non-recoverable exact ONNX-node mapping
   if no assignment-to-node trace exists.
3. The YOLOv5n comparison records FP32, AL_onnx_pass and quantized operator,
   shape, dtype and QDQ differences, and distinguishes observed parser/Optimize
   gates from proven fusion predicates.
4. The AL_onnx_pass audit records its actual conversion sequence and whether a
   native ALHardNPU compiler or custom graph node is present (it is not).
5. The final verdict is exactly one of
   `FUSION_REQUIREMENTS_IDENTIFIED_AND_MODEL_COMPATIBLE`,
   `FUSION_REQUIREMENTS_IDENTIFIED_MODEL_INCOMPATIBLE`, or
   `FUSION_PREDICATE_NOT_RECOVERABLE`; absent source/disassembly evidence must
   not be promoted to a proven exact predicate.
6. The focused validator, Python tests, JSON/YAML parsing, syntax checks,
   Markdown/link/repository hygiene scans and `git diff --check` pass. Existing
   Task 028/031 paths remain byte-for-byte unchanged.

## Execution record

Start: 2026-08-11 Asia/Shanghai. Branch: `dev`. Initial worktree was clean at
the start of Task 032. No VM, board or network access is permitted.

Initial static extraction was performed outside the repository in
`/tmp/task032-armnn` from the already audited `armnn_lib.tar.xz`; no vendor
binary was executed. The AArch64 library is stripped and the current WSL image
has no AArch64-capable disassembler, so exact instruction-level predicate
recovery is an explicit audit limitation.

## Completion record

Completed: 2026-08-11 Asia/Shanghai. The external temporary library was read
with `file`, `readelf -h/-d`, `nm -D -C --defined-only`, `strings -tx` and host
`objdump -f`. The archive SHA256 is
`867e347bb758f9b1b083c35e08a74f2b3cc39c2975ac0f8e18c25f7f35749526`; the
audited `libarmnn.so.32.1` SHA256 is
`5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce` with
Build ID `9f9aaf6f26dd1cf57ac84c778b9f621c04c7d895`. No ArmNN backend source
or AArch64-capable disassembler was available, so the complete fusion
predicate and per-region face mapping remain explicitly not recoverable.

Actual commands and results:

- `python3 -m py_compile scripts/vendor/audit_task032_alhardnpu_fusion.py` —
  PASS.
- `python3 scripts/vendor/audit_task032_alhardnpu_fusion.py --write --archive
  <external-armnn-archive>` — PASS; wrote the five structured audit JSON
  files and validation evidence under `results/evidence/032/`.
- `python3 scripts/vendor/audit_task032_alhardnpu_fusion.py --validate` —
  PASS.
- `PYTHONPATH=python .venv/bin/python -m unittest
  tests/python/test_task032_alhardnpu_fusion.py -v` — PASS (4 tests).
- `PYTHONPATH=python .venv/bin/python -m unittest discover -s tests/python -p
  'test_*.py'` — PASS (148 tests).
- `python3 scripts/vendor/audit_task031_official_npu_assets.py --validate` —
  PASS; the immutable Task 031 audit remains valid.
- `cmake --build build/task031-release -j2` — PASS; existing model-independent
  Release build unchanged.
- `ctest --test-dir build/task031-release --output-on-failure` — PASS (14/14).
- JSON/YAML parse plus recursive SHA256 format check — PASS (7 Task032 files).
- Python syntax, Markdown relative-link scan, sensitive-material scan and
  `git diff --check` — PASS.
- `git diff --quiet -- results/evidence/028 results/evidence/031
  docs/vendor_handoff/dr1m90_npu` — PASS; prior evidence is unchanged.

Final finding: `FUSION_PREDICATE_NOT_RECOVERABLE`. Task 028 remains
`BLOCKED_EXTERNAL_VENDOR_DEPENDENCY`; no model, QDQ, runtime, board, bitstream
or benchmark was changed or run. The user explicitly authorized the local
commit recorded in the final handoff; no push or PR was attempted.

## Final status fields

```text
conclusion: FUSION_PREDICATE_NOT_RECOVERABLE
board_accessed: false
model_modified: false
benchmark_run: false
commit: see final handoff (`git rev-parse HEAD`)
```
