# Task 029

## Title

DR1 vendor NPU enablement handoff.

## Status

Completed

## Dependency and branch

Depends on Task 028 (`Completed`). Work is recorded on the current `dev` branch;
the handoff is documentation-only and does not require a board feature branch.

## Scope

Create a minimal, reproducible support handoff from the final Task 028 evidence.
The handoff must let Anlogic/Milianke support reproduce the observed face
positive control, the official `AL_onnx_pass` conversion, and the Alnpu
generic-layer rejection without receiving vendor binaries, models, SDKs,
datasets, credentials, or board access.

The handoff is updated with the completed Task 032 fusion audit. That audit
records that `yolo_face_uint8_15.onnx` has no ALHardNPU custom node, while the
audited `libarmnn.so.32.1` forms three `Alnpu|ALHardNPU` assignments during
Optimize. `ConvertConv2dIntoALHardNPUImpl`, `checkConv`, `checkAct` and
`checkPool` are present, but the complete fusion predicate is not recoverable
from the available public evidence. This does not establish that YOLOv5n is
inherently incompatible.

The handoff does not continue model editing, quantization tuning, Arm NN
modification, bitstream work, board execution, or benchmarking.

## Acceptance criteria

1. The reproduction identity records board/SoC/package, SDK/source checkout,
   runtime and library hashes, model/input hashes, converter version/hash, and
   exact redacted commands with Task 028 evidence references.
2. The causal chain distinguishes the face `ALHardNPU` positive control, the
   successful host `AL_onnx_pass` conversion, parser/network creation, the
   `AlnpuLayerSupport` boundary, and the vendor YOLOv8n control failure.
3. The capability matrix lists every audited `AlnpuLayerSupport` override and
   the generic `LayerSupportBase` rejection slots, with scope limitations, and
   incorporates the Task 032 fusion findings without claiming inherent
   YOLOv5n incompatibility.
4. `docs/vendor_handoff/dr1m90_npu/` contains the README, environment,
   reproduction, capability boundary, questions, Chinese support request, and
   a manifest that references only existing Task 028 and Task 032 evidence.
5. The handoff status is `WAITING_FOR_VENDOR_INPUT` after the package is
   prepared for support review.
6. A validator and focused Python tests reject missing handoff files, invalid
   SHA256 references, accidental binary/model material, and incomplete vendor
   questions.
7. Repository hygiene, syntax, JSON/YAML parsing, Markdown links and
   `git diff --check` pass. No Task 017--032 evidence is modified.

## Allowed files

- `tasks/029_dr1_vendor_npu_enablement_handoff.md`
- `TASKS.md`
- `README.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `docs/vendor_handoff/dr1m90_npu/README.md`
- `docs/vendor_handoff/dr1m90_npu/environment.md`
- `docs/vendor_handoff/dr1m90_npu/reproduction.md`
- `docs/vendor_handoff/dr1m90_npu/capability_boundary.md`
- `docs/vendor_handoff/dr1m90_npu/questions.md`
- `docs/vendor_handoff/dr1m90_npu/vendor_support_request.md`
- `docs/vendor_handoff/dr1m90_npu/manifest.json`
- `scripts/vendor/validate_task029_vendor_handoff.py`
- `tests/python/test_task029_vendor_handoff.py`
- `.knowledge/manifests/dr1_vendor_npu_enablement_handoff.yaml`
- `scripts/vendor/audit_task031_official_npu_assets.py` (validation-only
  compatibility for this explicit Task 032 handoff addendum)

## Forbidden changes

- Do not modify Task 017--028 task files, manifests, evidence, models, inputs,
  runtime scripts or benchmark results, nor any Task 031/032 evidence.
- Do not copy or commit vendor binaries, ONNX models, SDKs, libraries, modules,
  bitstreams, datasets, ELF files, private keys, credentials or large logs.
- Do not access the VM or board, run NPU/Arm NN workloads, change the model,
  quantization, Arm NN, bitstream, kernel, DTB or SD/eMMC.
- Do not claim a generic YOLO backend, native compiler, NPU benchmark or CPU
  fallback that is not present in Task 028 evidence.
- Do not push, create a PR, merge, rebase or reset.

## Execution record

- Start: 2026-08-11 Asia/Shanghai. `dev` contains the Task 028 local commit
  `6070bbc`; initial worktree was clean.
- Source evidence is limited to the immutable `results/evidence/028/` and
  `results/evidence/032/` records; no VM, board or network command is required
  for this task.
- Handoff files, manifest, validator and focused tests are maintained below;
  Task 032's immutable evidence is referenced by hash for the fusion addendum.
- The Task 031 validator was narrowly taught to accept this versioned handoff
  addendum without rewriting its historical Task 028/029 hash snapshot.

### Validation record

The focused validator and five focused tests passed. JSON/YAML parsing, Python
syntax, Markdown links, sensitive-material/repository hygiene, Task
028/031/032 evidence immutability and `git diff --check` passed. The full
Python suite, Release build and CTest also passed. No VM, board or network
command was run. No model, quantization, Arm NN, bitstream or benchmark work
was performed.

## Final disposition

Task 029 may be marked `Completed` only with:

```text
WAITING_FOR_VENDOR_INPUT
```

This means the package is ready to send to technical support. It does not mean
that a new backend, compiler, model conversion, board deployment or benchmark
has been approved.

Final state: `Completed`; readiness: `WAITING_FOR_VENDOR_INPUT`. The package is
ready to send, and this state means the next action is vendor response rather
than additional local reverse engineering.

## Resume / handoff files

The package root is `docs/vendor_handoff/dr1m90_npu/`. The validator command is:

```bash
python3 scripts/vendor/validate_task029_vendor_handoff.py
```

## Recommended Commit

`docs(npu): update DR1 vendor handoff with fusion findings`
