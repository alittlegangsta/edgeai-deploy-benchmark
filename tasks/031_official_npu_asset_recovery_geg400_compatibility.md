# Task 031

## Title

Official NPU asset recovery and GEG400 compatibility.

## Status

Completed

## Dependencies

Tasks 028 and 029 (`Completed`).

## Recommended Branch

`dev` (the user selected this audit from the current clean `dev` branch).

## Recommended Commit

`docs(npu): audit official GEG400 NPU asset recovery`

## Goal

Exhaustively audit the locally cloned official `sdk`, `dr1m90_npu`, and
`dr1_demo_prjs` repositories and their complete Git history to determine whether
an official, version-matched path can reopen YOLOv5n NPU integration on the
DR1M90 GEG400 context. This task is read-only with respect to vendor trees,
models, board media, and the development board. Task 029's vendor handoff and
Task 028's frozen conclusion remain immutable.

## Required questions

The evidence must answer, without inference presented as fact:

1. Whether an ALHardNPU generation/fusion tool is present.
2. Whether `npuv1_release` or `release_2024_06_25` can be recovered from
   current, tagged, branched, deleted, LFS, or archive-referenced history.
3. Whether the official `yolov5s_sim_quant_uint8.onnx` positive model exists,
   and its complete ONNX provenance.
4. Whether any unique `libarmnn.so*` build has a materially different
   `AlnpuLayerSupport` capability set from the audited Task 028 binary.
5. Whether an official `DR1M90GEG400 + NPU_Yolo` HPF/TD design exists.
6. Why the face positive reaches ALHardNPU and whether that path is represented
   in the ONNX graph or synthesized by ArmNN/Alnpu optimization.
7. Whether the public software chain is internally self-consistent and whether
   newly found assets are sufficient to reopen YOLOv5n integration.

## Source classification

Every finding is classified as `document_fact`, `source_code_fact`,
`engineering_inference`, or `real_device_observation`. Unknowns and conflicts
remain explicit. Repository tags/commits are not substituted for one another.

## Safety boundary

Allowed operations are read-only file/Git archaeology, hashing, archive listing,
static ONNX/ELF/source analysis, and local evidence generation. Do not access
the VM or board, execute vendor ELF/installer/build scripts, alter models,
write SD/eMMC/bitstreams/DTBs, load modules, download assets, or reopen the
Task 028/029 runtime path.

## Allowed Files

```text
TASKS.md
README.md
ROADMAP.md
CHANGELOG.md
tasks/031_official_npu_asset_recovery_geg400_compatibility.md
docs/vendor/ANLOGIC_OFFICIAL_NPU_ASSET_RECOVERY_GEG400.md
.knowledge/manifests/official_npu_asset_recovery_geg400.yaml
scripts/vendor/audit_task031_official_npu_assets.py
tests/python/test_task031_official_npu_assets.py
results/evidence/031/official_repo_inventory.json
results/evidence/031/git_history_archaeology.json
results/evidence/031/face_onnx_provenance.json
results/evidence/031/armnn_backend_inventory.json
results/evidence/031/npu_yolo_hpf_matrix.json
results/evidence/031/software_chain_audit.json
results/evidence/031/compatibility_verdict.json
results/evidence/031/validation.json
```

The vendor trees, Task 028/029 evidence, models, libraries, archives, and
board artifacts remain outside this task's allowed repository changes.

## Acceptance Criteria

1. All three repository identities, branches/tags, submodules, licenses and
   dirty states are recorded without modifying their worktrees.
2. Current and historical/deleted/LFS/archive references for the named release,
   models, tools, runtime names, GEG400 and NPU_Yolo terms are recorded with
   explicit searched scope and no fabricated recovery.
3. The face ONNX is statically parsed and its domain/opset/operators/metadata/
   producer and absence/presence of ALHardNPU custom nodes are recorded.
4. Every unique available ArmNN binary is SHA256-deduplicated and its static
   AlnpuLayerSupport result is tied to a real file identity, or explicitly
   marked unavailable.
5. NPU-related HPF/TD evidence distinguishes GEG400 from AD101/AD103/GEG484
   and records whether a complete official YOLO design exists.
6. The AL_onnx_pass-to-Alnpu chain is audited for omitted conversion, fusion,
   compiler, or runtime steps; Task 028/029 remain unchanged.
7. The verdict explicitly states whether new assets are sufficient to reopen
   YOLOv5n NPU integration, and all JSON/YAML, focused tests, syntax, links,
   hygiene, immutability, and `git diff --check` validations pass.

## Execution Record

Started: `2026-08-11` (Asia/Shanghai)

Branch: `dev`

Starting commit: `47d5d22 docs(benchmark): consolidate ARM CPU profiling results`

Starting status: clean.

The audit used only the approved local repository trees and repository history.
No VM, board, network, model mutation, binary execution, media write, or Task
028/029 evidence rewrite was performed.

## Final findings

* `sdk` is the dirty `anlogic-linuxsdk` checkout at committed HEAD
  `5a693bed7d78e2e156e425ef57ebc8b7efad25cd`; `dr1m90_npu` is dirty `release`
  at `199ef4d71f453bb9a000102ff39def09c4cf73f9`; `dr1_demo_prjs` is dirty
  `2026.1` at `ee12dfde1d7ccef2cca0e6fccda66d4fb84671fa`. Their remotes, tags,
  submodules, licenses, status counts, LFS limitations and normalized source
  paths are in `official_repo_inventory.json`.
* Reachable-ref, deleted-name, LFS-pointer and documentation archaeology found
  only the `npuv1_release/release_2024_06_25` and
  `yolov5s_sim_quant_uint8.onnx` references; it recovered neither the native
  compiler/runtime nor the YOLOv5s positive model. No `convert_tool`,
  `al_ai_flow`, `nn_compiler`, `npu_runtime`, `tmfile`, `rt.bin`, `weight.bin`
  or `npu_c_api.h` payload was found.
* The face model is a real PyTorch 1.13.0, opset-14 ONNX blob with SHA256
  `5ed304f1cfd37a6c4ddc789a58a4c98e3472efe31eff62fc9e447163ea60668c`; it has
  no ALHardNPU custom node. ArmNN/Alnpu creates the measured fused/custom
  ALHardNPU assignments during optimization.
* Two SHA256-deduplicated ArmNN families were statically audited. Both expose
  the same ten Alnpu overrides and leave generic Conv2d, Activation, Splitter,
  Add and Mul methods on `LayerSupportBase`; neither is a materially broader
  backend. ALHardNPU fusion symbols are compiled into ArmNN, not a recovered
  standalone generator.
* SDK and D20 YOLO HPFs are AD101/AD103 and GEG484-family. Generic C20 metadata
  is not a YOLO SoftNPU design. No official GEG400 `NPU_Yolo` HPF/TD was
  recovered; the retained 05-5 GEG400 evidence remains immutable.

Final verdict: `BLOCKED_EXTERNAL_VENDOR_DEPENDENCY`;
`new_assets_sufficient_to_reopen_yolov5n: false`.

## Execution record

The evidence generator and validator are
`scripts/vendor/audit_task031_official_npu_assets.py`; focused tests are
`tests/python/test_task031_official_npu_assets.py`. Actual commands and their
results are recorded below:

* `python3 -m py_compile scripts/vendor/audit_task031_official_npu_assets.py` —
  PASS.
* `python3 scripts/vendor/audit_task031_official_npu_assets.py --write-evidence`
  — PASS; wrote the eight JSON files in `results/evidence/031/` from the
  approved static audit facts and immutable Task 028/029 hashes.
* `python3 scripts/vendor/audit_task031_official_npu_assets.py --validate` —
  PASS.
* No VM/board/network command, vendor executable, compiler, model conversion,
  module load or bitstream/media operation was run for Task 031.

* `PYTHONPATH=python .venv/bin/python -m unittest tests.python.test_task031_official_npu_assets -v`
  — PASS (6 tests).
* `PYTHONPATH=python .venv/bin/python -m unittest discover -s tests/python -p
  'test_*.py'` — PASS (144 tests).
* `cmake -S cpp -B build/task031-release -DCMAKE_BUILD_TYPE=Release
  -DONNXRUNTIME_ROOT=<local-approved-ort-root> -DNCNN_ROOT=<local-approved-ncnn-root>
  && cmake --build build/task031-release -j2` — PASS; all targets built.
  `ctest --test-dir build/task031-release --output-on-failure` — PASS (14/14).
  The first configure without explicit SDK roots failed with the real CMake
  guard; the existing local approved roots were then supplied, without any
  installation or download.
* A Python JSON/YAML parse pass covered the eight Task 031 JSON files and the
  manifest (9 files); Python syntax compilation, Markdown relative-link
  checking, sensitive-material scan, and `git diff --check` — PASS.
* The validator rechecked all retained Task 028 JSON and Task 029 handoff
  hashes; the immutable set is PASS. The three vendor checkout trees were only
  read and no file was changed by this task.

No vendor binary/model/archive is an allowed Git artifact. No board/VM/network
runtime command, vendor executable, compiler, model conversion, module load or
bitstream/media operation was run for Task 031.

Commands, actual findings, hashes, skipped scopes, and final validation results
will be appended here during execution.
