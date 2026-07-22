# Task 010

## Title

Create the fixed TorchScript-to-pnnx ncnn model and verify model loading.

## Status

Completed

## Batch

Batch C

## Dependencies

Task 009 (`Completed`) and human approval of Checkpoint B.

## Recommended Branch

`feature/pc-batch-c-ncnn-acceptance`

## Recommended Commit

`feat(ncnn): add reproducible model conversion`

## Goal

Export the exact frozen YOLOv5n v7.0 weights to a fixed CPU/FP32 TorchScript
artifact, convert it with pnnx from the same pinned ncnn `20240410` revision used
at runtime, record every artifact identity, and prove the generated param/bin pair
loads before implementing the ncnn inference backend.

## Why This Task Exists

The frozen ONNX graph is valid for both ONNX Runtime implementations but is not
semantically convertible by the pinned `onnx2ncnn`. A separately frozen
TorchScript-to-pnnx path keeps one weight lineage while making the distinct
serialized-model contracts and their validation explicit.

## Knowledge Covered

- Shared source-weight lineage across distinct serialized-model contracts.
- TorchScript exporter and pnnx/runtime version identity.
- Reproducible model transformation and artifact hashing.
- ncnn param/bin structure and blob discovery.
- Native model-load error handling.
- Semantic comparison with the frozen ONNX Runtime baseline.

## Scope

Use the exact Task 002 `.pt` weights and read-only YOLOv5 v7.0 source to export a
static batch-1, FP32, `640x640` TorchScript model. Convert that artifact with the
locally built pnnx from ncnn tag `20240410`, revision
`56775de50990ab7f16627efdcf5529b49541206f`, using `device=cpu`, `fp16=0`,
`optlevel=2`, and no module/custom operators. Record exporter, converter, runtime,
source, command, hash, size, precision, and actual blob/tensor identities. Build
a C++ load-and-shape contract smoke test.

The Task 002 ONNX file remains frozen, read-only, and authoritative for Python
ORT and C++ ORT. It is not modified, replaced, or re-exported. The ncnn path is a
parallel conversion contract from the same weights and must be described as:

```text
The ORT implementations use the same frozen ONNX model. The ncnn model is
generated from the same YOLOv5n v7.0 weights through a separately frozen
TorchScript-to-pnnx conversion path and is validated for semantic equivalence.
```

Do not quantize, use FP16 or Vulkan, perform model surgery, replace the Detect
head, use `moduleop`/`customop`, run `ncnnoptimize`, or change the source weights,
input size, batch, thresholds, or frozen ONNX contract.

## Allowed Files

```text
.gitignore
TASKS.md
tasks/010_ncnn_model_conversion.md
cpp/CMakeLists.txt
cpp/apps/ncnn_model_smoke.cpp
models/yolov5n-v7.0/yolov5n.torchscript
models/yolov5n-v7.0/yolov5n.ncnn.param
models/yolov5n-v7.0/yolov5n.ncnn.bin
models/yolov5n-v7.0/torchscript_manifest.json
models/yolov5n-v7.0/ncnn_manifest.json
scripts/validate_torchscript_conversion.py
scripts/validate_ncnn_conversion.py
tests/python/test_torchscript_manifest.py
tests/python/test_ncnn_manifest.py
results/evidence/010/torchscript_validation.json
results/evidence/010/ncnn_model_load.json
results/logs/010_ncnn_conversion.log
results/logs/010_torchscript_export.log
results/logs/010_pnnx_conversion.log
```

The ONNX graph and every completed Task 002-009 artifact, manifest, contract, and
result are read-only. TorchScript, pnnx intermediate files, helper Python files,
and ncnn param/bin are generated model artifacts that remain ignored and
uncommitted. pnnx intermediates and debug files must be created only under a
dedicated `/tmp` working directory.

## Forbidden Files

- Changes to the source `.pt`, frozen `.onnx`, Tasks 002-009, or their hashes,
  contracts, evidence, and results.
- Downloaded/vendored ncnn or pnnx, alternate source revisions, graph optimizers,
  quantizers, model surgery, Detect-head replacements, detections, images, video,
  or benchmark results.
- Silent blob renaming or hand-editing converted artifacts.
- `moduleop`, `customop`, FP16, Vulkan, and generated helper-code execution.
- Any file outside Allowed Files.

## Inputs

- The exact Task 002 YOLOv5n v7.0 `.pt` weights with matching SHA256.
- The frozen Task 002 ONNX graph and manifest as read-only ORT baseline evidence.
- Read-only YOLOv5 tag `v7.0`, revision
  `915bbf294bb74c859f0b41f1c23bc395014ea679`.
- Project Python 3.12.3 environment with torch `2.2.2+cpu` and torchvision
  `0.17.2+cpu`.
- Locally built pnnx from the same pinned ncnn `20240410` source revision as the
  installed ncnn runtime.
- Existing C++17/CMake/Ninja/OpenCV toolchain.

If any fixed dependency is absent or incompatible, stop; do not download,
install, choose another pnnx, change source revision, or use `onnx2ncnn` again.

## Expected Outputs

- Generated TorchScript and ncnn param/bin artifacts tied to the same frozen
  YOLOv5n weight SHA.
- `torchscript_manifest.json` with exporter/source/environment identity, exact
  command, hashes, sizes, actual I/O, and frozen-ONNX comparison evidence.
- `ncnn_manifest.json` with TorchScript, pnnx, ncnn runtime, commands, hashes,
  sizes, conversion settings, and observed blob contract.
- `edgeai_ncnn_model_smoke` that loads both files and runs one deterministic
  zero-input shape/type probe without producing a correctness result.
- Real TorchScript validation, conversion, and load JSON/log evidence.

## Implementation Requirements

- Validate both source-weight and frozen-ONNX SHA256 values against Task 002
  immediately before export and again when creating both manifests.
- Export only with the fixed YOLOv5 v7.0 `export.py`, batch 1, `640x640`, CPU,
  FP32, TorchScript only, without half, int8, optimize, dynamic, model surgery,
  or Detect-head replacement.
- Load the TorchScript on CPU, run the fixed input, and record actual output
  count, shape, dtype, finite-value status, and numeric statistics. Compare its
  detection semantics with the frozen ONNX on the exact same input. Before the
  first comparison, freeze the equality requirements as equal detection count
  and classes, minimum class-matched IoU `0.99`, and maximum absolute confidence
  difference `0.001`; do not weaken these tolerances after observing results.
- Record pnnx/ncnn tag, revision, pnnx source-tree hash, build provenance, paths,
  executable/library SHA256 values, compiler/dependency identities, dynamic
  dependencies, and exact conversion command.
- Invoke pnnx in a dedicated `/tmp` directory with every output path explicit,
  `inputshape=[1,3,640,640]f32`, `device=cpu`, `fp16=0`, and `optlevel=2`.
- Do not use `moduleop`, `customop`, `ncnnoptimize`, quantization, FP16, Vulkan,
  or generated Python helper inference. Stop rather than adding them after failure.
- Treat pnnx ONNX emission as an observed optional capability. The pinned build's
  ABI guard may disable onnx-zero; check and record a missing `.pnnx.onnx` rather
  than fabricating it or changing Protobuf/Torch ABI.
- Hash and size the generated param/bin. Validate that paths are regular files,
  nonempty, and not symlinks escaping the repository.
- Parse generated pnnx/ncnn params as evidence but do not edit them. Observe rather
  than guess input/output blob names, counts, dims, shapes, types, custom layers,
  and whether the output is decoded candidates or raw Detect heads.
- The Python validators must validate manifest/source/artifact hashes. The smoke
  executable must call ncnn load APIs with Vulkan, FP16, BF16, and INT8 disabled,
  run one zero-input contract probe, report actual blob names/dimensions/types,
  and return nonzero on every load, extraction, non-finite-value, or contract
  failure. This probe is not Task 011 correctness inference.
- Keep ncnn discovery target-level and fail clearly without dependency fetching.

## Build Commands

```bash
# Repository-external pnnx build, authorized only for the fixed paths in the
# Execution Record. Configure must be followed by cache/Ninja audit before build.
/usr/bin/cmake \
  -S /home/dministrator/src/ncnn-20240410/tools/pnnx \
  -B /home/dministrator/src/ncnn-20240410/tools/pnnx/build-linux-x64-torch2.2.2 \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/home/dministrator/opt/ncnn/pnnx-linux-x64-20240410-torch2.2.2-local \
  -DCMAKE_C_COMPILER=/usr/bin/gcc \
  -DCMAKE_CXX_COMPILER=/usr/bin/g++ \
  -DCMAKE_MAKE_PROGRAM=/usr/bin/ninja \
  -DPython3_EXECUTABLE=<project-venv-python> \
  -DTorch_INSTALL_DIR=<project-venv-torch-root> \
  -DTorch_DIR=<project-venv-torch-cmake-dir> \
  -DTorchVision_INSTALL_DIR=<project-venv-torchvision-root> \
  -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF \
  -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF \
  -DCMAKE_IGNORE_PREFIX_PATH='/mnt/c/msys64;/mnt/c/msys64/ucrt64'
/usr/bin/cmake --build \
  /home/dministrator/src/ncnn-20240410/tools/pnnx/build-linux-x64-torch2.2.2 \
  --target pnnx --parallel 4
/usr/bin/cmake --install \
  /home/dministrator/src/ncnn-20240410/tools/pnnx/build-linux-x64-torch2.2.2

rm -rf build/pc-ncnn-release
cmake \
  -S cpp \
  -B build/pc-ncnn-release \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DONNXRUNTIME_ROOT=<verified-local-onnxruntime-root> \
  -DNCNN_ROOT=<verified-local-ncnn-root>
cmake --build build/pc-ncnn-release --parallel
```

## Run Commands

```bash
mkdir -p models/yolov5n-v7.0 results/evidence/010 results/logs
sha256sum \
  models/yolov5n-v7.0/yolov5n.pt \
  models/yolov5n-v7.0/yolov5n.onnx

.venv/bin/python \
  /home/dministrator/src/yolov5-v7.0/export.py \
  --weights models/yolov5n-v7.0/yolov5n.pt \
  --include torchscript \
  --imgsz 640 640 \
  --batch-size 1 \
  --device cpu \
  2>&1 | tee results/logs/010_torchscript_export.log

.venv/bin/python scripts/validate_torchscript_conversion.py \
  --weights models/yolov5n-v7.0/yolov5n.pt \
  --onnx models/yolov5n-v7.0/yolov5n.onnx \
  --onnx-manifest models/yolov5n-v7.0/manifest.json \
  --torchscript models/yolov5n-v7.0/yolov5n.torchscript \
  --yolov5-source /home/dministrator/src/yolov5-v7.0 \
  --image data/samples/images/pc_reference.jpg \
  --config configs/yolov5n_v7_inference.json \
  --export-log results/logs/010_torchscript_export.log \
  --manifest models/yolov5n-v7.0/torchscript_manifest.json \
  --output results/evidence/010/torchscript_validation.json

rm -rf /tmp/edgeai-task010-pnnx
mkdir -p /tmp/edgeai-task010-pnnx
cd /tmp/edgeai-task010-pnnx
LD_LIBRARY_PATH=<project-venv-torch-lib> "$PNNX" \
  <absolute-torchscript-path> \
  'inputshape=[1,3,640,640]f32' \
  device=cpu \
  fp16=0 \
  optlevel=2 \
  pnnxparam=/tmp/edgeai-task010-pnnx/yolov5n.pnnx.param \
  pnnxbin=/tmp/edgeai-task010-pnnx/yolov5n.pnnx.bin \
  pnnxpy=/tmp/edgeai-task010-pnnx/yolov5n_pnnx.py \
  pnnxonnx=/tmp/edgeai-task010-pnnx/yolov5n.pnnx.onnx \
  ncnnparam=<absolute-project-root>/models/yolov5n-v7.0/yolov5n.ncnn.param \
  ncnnbin=<absolute-project-root>/models/yolov5n-v7.0/yolov5n.ncnn.bin \
  ncnnpy=/tmp/edgeai-task010-pnnx/yolov5n_ncnn.py \
  2>&1 | tee <absolute-project-root>/results/logs/010_pnnx_conversion.log
cd <absolute-project-root>

./build/pc-ncnn-release/edgeai_ncnn_model_smoke \
  --param models/yolov5n-v7.0/yolov5n.ncnn.param \
  --bin models/yolov5n-v7.0/yolov5n.ncnn.bin \
  --output results/evidence/010/ncnn_model_load.json

.venv/bin/python scripts/validate_ncnn_conversion.py \
  --weights models/yolov5n-v7.0/yolov5n.pt \
  --onnx models/yolov5n-v7.0/yolov5n.onnx \
  --onnx-manifest models/yolov5n-v7.0/manifest.json \
  --torchscript models/yolov5n-v7.0/yolov5n.torchscript \
  --torchscript-manifest models/yolov5n-v7.0/torchscript_manifest.json \
  --pnnx "$PNNX" \
  --pnnx-source /home/dministrator/src/ncnn-20240410 \
  --pnnx-provenance /home/dministrator/opt/ncnn/pnnx-linux-x64-20240410-torch2.2.2-local/provenance.local.txt \
  --torch-lib <project-venv-torch-lib> \
  --ncnn-root "$NCNN_ROOT" \
  --ncnn-provenance "$NCNN_ROOT/provenance.local.txt" \
  --conversion-log results/logs/010_pnnx_conversion.log \
  --pnnx-param /tmp/edgeai-task010-pnnx/yolov5n.pnnx.param \
  --pnnx-bin /tmp/edgeai-task010-pnnx/yolov5n.pnnx.bin \
  --pnnx-onnx /tmp/edgeai-task010-pnnx/yolov5n.pnnx.onnx \
  --pnnx-py /tmp/edgeai-task010-pnnx/yolov5n_pnnx.py \
  --ncnn-py /tmp/edgeai-task010-pnnx/yolov5n_ncnn.py \
  --param models/yolov5n-v7.0/yolov5n.ncnn.param \
  --bin models/yolov5n-v7.0/yolov5n.ncnn.bin \
  --runtime-evidence results/evidence/010/ncnn_model_load.json \
  --manifest models/yolov5n-v7.0/ncnn_manifest.json
```

## Test Commands

```bash
.venv/bin/python -m unittest tests/python/test_torchscript_manifest.py
.venv/bin/python -m unittest tests/python/test_ncnn_manifest.py
python3 -m json.tool models/yolov5n-v7.0/torchscript_manifest.json >/dev/null
python3 -m json.tool models/yolov5n-v7.0/ncnn_manifest.json >/dev/null
python3 -m json.tool results/evidence/010/torchscript_validation.json >/dev/null
python3 -m json.tool results/evidence/010/ncnn_model_load.json >/dev/null
ctest --test-dir build/pc-ncnn-release --output-on-failure
git check-ignore \
  models/yolov5n-v7.0/yolov5n.torchscript \
  models/yolov5n-v7.0/yolov5n.ncnn.param \
  models/yolov5n-v7.0/yolov5n.ncnn.bin
git diff --check
```

## Acceptance Criteria

- Source `.pt` and frozen ONNX SHA values match Task 002 immediately before export
  and manifest generation; the frozen ONNX is unchanged.
- YOLOv5 exporter, Python/Torch environment, pnnx source/binary, and ncnn runtime
  are pinned with real tag/revision/path/hash/build-provenance evidence.
- TorchScript export succeeds with batch 1, FP32, CPU, and `640x640`; actual
  output count/shape/dtype and finite statistics are recorded.
- TorchScript and frozen ONNX candidate or detection semantics pass the fixed
  comparison on identical input.
- pnnx conversion exits zero with no unsupported/custom operator, uses exactly
  `inputshape=[1,3,640,640]f32`, `device=cpu`, `fp16=0`, `optlevel=2`, and no
  module/custom operator, quantization, model surgery, or Vulkan.
- Generated param/bin are nonempty and have recorded SHA256 and byte sizes.
- Actual input/output blob names, counts, dims, shapes, data types, and custom-layer
  status are observed and frozen, not guessed or edited.
- Release smoke target builds without project warnings, disables Vulkan and FP16
  storage/arithmetic, and loads both artifacts.
- TorchScript/ncnn manifest validation, smoke load, tests, JSON checks,
  ignore checks, and `git diff --check` pass.
- The failed direct `onnx2ncnn` identities and log remain recorded while its
  invalid param/bin have been deleted before pnnx conversion.
- TorchScript, pnnx intermediate/helper files, and ncnn param/bin remain ignored;
  no model binary is staged.
- Only Allowed Files changed.

## Evidence to Preserve

Source-weight and frozen-ONNX hashes, YOLO exporter and TorchScript identities,
TorchScript/ORT semantic comparison, pnnx/ncnn version/revision/tree/path/hashes,
exact commands and exits, optional pnnx-ONNX capability, all artifact hashes and
sizes, observed blobs/tensors/custom layers, CPU/FP32 settings, Release build/load
output, tests, attempts, diff check, ignore checks, and Git status.

## Automatic Retry Rules

At most three complete repair loops may address exporter invocation,
manifest/checker/smoke-code, or build orchestration bugs without changing the
contract. Do not retry by changing source weights/ONNX, pnnx/ncnn revision,
input/batch, optlevel, precision, module/custom operators, Detect head, thresholds,
or generated artifacts manually. Dependency/version/conversion/blob ambiguity is
an immediate mandatory stop.

## Human Stop Conditions

Stop for all model-contract/environment/file-safety conditions, any exporter,
pnnx, and runtime mismatch, changed source/ONNX hash, unsupported/custom operator,
unexpected or uninterpretable tensor/blob contract, non-finite output, failed
TorchScript/ORT semantic comparison, need for module/custom operators or manual
artifact editing, or any proposal to commit generated model files.

## Codex Responsibilities

Prove tool and model identity, execute only the approved fixed export/conversion,
validate TorchScript semantics and ncnn loading, observe the real output contract,
preserve actual evidence, and report incompatibility.

## User Responsibilities

Approve the parallel TorchScript-to-pnnx contract, provide/authorize the pinned
pnnx/ncnn environment, review any ambiguous output contract, and inspect blob and
semantic-comparison evidence.

## Known Risks

- pnnx output may be one decoded tensor, three raw Detect heads, or an unsupported
  custom operator; none may be assumed before inspection.
- TorchScript and pnnx optimization can preserve semantics while changing layout,
  names, ordering, or numerical rounding.
- The fixed Torch ABI requires runtime Torch shared-library path configuration for
  the pnnx host tool and disables optional pnnx ONNX emission in this build.
- Conversion can exit zero while producing an unusable graph, so load and later
  Task 011 correctness gates remain mandatory.

## Completion Report Format

Report files, weight/ONNX/TorchScript hashes, exporter/pnnx/ncnn identities,
commands, artifact hashes/sizes/blobs/tensors, semantic comparison, CPU/FP32
settings, build/load/tests, ignored-model check, attempts, stops/skips, risks,
and final Git status.

## Execution Record

Started: `2026-07-21T15:30:21+08:00`

Branch: `feature/pc-batch-c-ncnn-acceptance`

Starting commit: `136b52f`

Starting Git status: clean (`git status --short --untracked-files=all` produced
no output).

Dependencies: Tasks 001 through 009 are `Completed`; Task 009 records human
approval of Checkpoint B. Task 010 is restored only to `In Progress`; no ncnn
version, conversion artifact, blob name, or load result has been claimed.

### Local Toolchain Audit and Blocking Report

Stopped: `2026-07-21T15:32:31+08:00`

The frozen Task 002 ONNX file exists, is nonempty, remains Git-ignored, and has
the manifest-matching SHA256
`78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121`
and size `7921360` bytes. No ncnn param or bin artifact exists. The prospective
`.bin` path is covered by `.gitignore`; the prospective `.param` path is not
ignored and therefore requires the task's later user confirmation and license
review before it may be staged.

Read-only tool discovery produced this actual state:

```text
NCNN_ROOT: unset
onnx2ncnn in PATH: absent
ncnnoptimize in PATH: absent
pnnx in PATH: absent
pkg-config ncnn: not found
CMAKE_PREFIX_PATH: unset
CMake ncnn package discovery: not found (exit 1)
system libncnn loader entry: absent
```

The CMake package-discovery probe created
`CMakeFiles/CMakeSystem.cmake` as an incidental cache file. It was immediately
deleted together with the now-empty directory because it was generated by this
task, reproducible, and outside Allowed Files. It is not present in Git status.

Required human-provided toolchain specification:

```text
Required tools:
  - ncnn C++ runtime and development files
  - onnx2ncnn built from the exact same ncnn source revision/build
Official source:
  - https://github.com/Tencent/ncnn
Fixed tag/commit:
  - unresolved; neither the repository nor the local machine provides an
    approved ncnn tag and full commit SHA, so Codex must not invent one
pnnx:
  - not used by Task 010; the approved path is direct ONNX -> onnx2ncnn
  - no pnnx version may be substituted or invoked to bypass this block
Target platform:
  - Linux x86_64, Ubuntu 24.04.4 LTS under WSL2
  - GCC 13.3.0, CMake 3.28.3, Ninja 1.11.1, glibc 2.39
Recommended repository-external install root:
  - /home/dministrator/opt/ncnn/ncnn-linux-x64-<approved-tag>-<short-commit>
Required files under that root:
  - bin/onnx2ncnn (executable)
  - include/ncnn/net.h and the matching public ncnn headers
  - lib/cmake/ncnn/ncnnConfig.cmake (plus referenced CMake target files)
  - the matching lib/libncnn.so or lib/libncnn.a and its required build metadata
Required provenance:
  - exact official tag and full 40-character source commit
  - proof that runtime, headers, CMake config, and onnx2ncnn share that build
  - SHA256 of the original archive if a binary archive is used
  - SHA256 of bin/onnx2ncnn and the selected libncnn library
SHA256 verification method:
  - sha256sum <official-archive>
  - sha256sum "$ONNX2NCNN"
  - sha256sum "$NCNN_ROOT/lib/libncnn.so" (shared build), or
    sha256sum "$NCNN_ROOT/lib/libncnn.a" (static build)
Resume environment:
  - export NCNN_ROOT=/home/dministrator/opt/ncnn/<exact-approved-directory>
  - export ONNX2NCNN="$NCNN_ROOT/bin/onnx2ncnn"
  - export NCNN_SOURCE_TAG=<exact-approved-tag>
  - export NCNN_SOURCE_REVISION=<full-40-character-commit>
  - for a shared build only:
    export LD_LIBRARY_PATH="$NCNN_ROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

No download or build command is prescribed yet because an exact tag/commit is
not frozen. Supplying a guessed command with a placeholder or silently selecting
the newest release would violate the task's converter/runtime identity rule.

```text
Current Task: Task 010
Current Status: Blocked
Last Successful Step: branch/dependency/Checkpoint B audit passed and the frozen ONNX SHA256 was verified against the Task 002 manifest
Failed Command: cmake --find-package -DNAME=ncnn -DCOMPILER_ID=GNU -DLANGUAGE=CXX -DMODE=EXIST
Exit Code: 1
Relevant Error: ncnn not found; NCNN_ROOT is unset, onnx2ncnn is absent from PATH, pkg-config cannot find ncnn, and no system libncnn loader entry was found
Files Changed: TASKS.md; tasks/010_ncnn_model_conversion.md
Attempts Made: 0 repair attempts; missing dependency/version provenance is an immediate mandatory stop and is not eligible for automatic repair
Why Automatic Recovery Is Unsafe: progress requires selecting and obtaining an ncnn runtime/converter build; the repository freezes no ncnn tag or commit, and downloading, installing, source-building, or substituting pnnx is prohibited without human action
Exact Human Action Required: choose and state one exact official Tencent/ncnn tag plus its full commit SHA; prepare outside the repository the matching Linux x86_64 runtime headers/library/CMake config and onnx2ncnn from that same build; provide archive/tool/library SHA256 evidence; export NCNN_ROOT, ONNX2NCNN, NCNN_SOURCE_TAG, NCNN_SOURCE_REVISION, and LD_LIBRARY_PATH when applicable; do not prepare or select pnnx for Task 010
Commands to Resume: rerun the startup audit and recovery protocol; test -n "$NCNN_ROOT"; test -n "$ONNX2NCNN"; test -x "$ONNX2NCNN"; test -f "$NCNN_ROOT/include/ncnn/net.h"; test -f "$NCNN_ROOT/lib/cmake/ncnn/ncnnConfig.cmake"; sha256sum "$ONNX2NCNN"; git status --short --untracked-files=all; sha256sum models/yolov5n-v7.0/yolov5n.onnx; then prove the exact runtime/converter revision before restoring Task 010 to In Progress
Git Status: only TASKS.md and tasks/010_ncnn_model_conversion.md contain the legal Task 010 Blocked-state record; no conversion, build, model artifact, test, staging, or commit occurred
```

### Toolchain Recovery

Resumed: `2026-07-21T16:25:12+08:00`

The user fixed the ncnn source contract at official tag `20240410` and authorized
a local Linux build outside the project repository. The source top-level revision
was verified before and after the build as
`56775de50990ab7f16627efdcf5529b49541206f`. The pre-existing
`python/pybind11` submodule checkout differs from the tag's recorded submodule
pointer; it was not changed and was excluded by `NCNN_PYTHON=OFF`. No other
source-worktree change was observed.

The old cache contained `/mnt/c/msys64/ucrt64` in `protobuf_DIR`, Abseil and
utf8-range package paths, converter include/link/RPATH rules, and the ONNX/Caffe
generated-source commands. The old `build.ninja` invoked
`/mnt/c/msys64/ucrt64/bin/protoc.exe`. Both authorized old build/install
directories were removed, and ncnn was configured using an absolute Linux-only
toolchain and Ubuntu Protobuf 3.21.12.

The verified configuration is Release, Linux x86_64, static ncnn, Vulkan off,
tools on, examples/benchmark/tests/Python off, and explicitly sets
`NCNN_VERSION=20240410`. Lowercase Protobuf config-package discovery is disabled
so the source's uppercase `find_package(Protobuf)` fallback resolves
`/usr/bin/protoc`, `/usr/include`, and
`/usr/lib/x86_64-linux-gnu/libprotobuf.so`. Package registries are disabled and
`/mnt/c/msys64` is an ignored prefix.

Post-configuration `build.ninja` evidence:

```text
ONNX generator: /usr/bin/protoc --cpp_out ... tools/onnx/onnx.proto
Caffe generator: /usr/bin/protoc --cpp_out ... tools/caffe/caffe.proto
MSYS2 references used by build rules: none
Only remaining MSYS2 text: defensive CMAKE_IGNORE_PREFIX_PATH cache value
```

The `onnx2ncnn` verbose build, `ncnnoptimize` verbose build, complete build, and
install all exited zero. Installed paths and SHA256 values are:

```text
NCNN_ROOT: /home/dministrator/opt/ncnn/ncnn-linux-x64-20240410-local
onnx2ncnn: /home/dministrator/opt/ncnn/ncnn-linux-x64-20240410-local/bin/onnx2ncnn
onnx2ncnn SHA256: 14ad7ad2c535880d79bfd783a0d12c84b196cb99815972bdc0abd7208aed8375
ncnnoptimize: /home/dministrator/opt/ncnn/ncnn-linux-x64-20240410-local/bin/ncnnoptimize
ncnnoptimize SHA256: 4f1aa276303215ce8ef02e3f2a4393effd030f044266cbf519603269f700bfad
libncnn.a: /home/dministrator/opt/ncnn/ncnn-linux-x64-20240410-local/lib/libncnn.a
libncnn.a SHA256: f1936728d19ce288ad7180926670ac7f1833107a13cc9446d178d2bef340fcc1
ncnnConfig.cmake: /home/dministrator/opt/ncnn/ncnn-linux-x64-20240410-local/lib/cmake/ncnn/ncnnConfig.cmake
ncnnConfig.cmake SHA256: 8b132a0fa6e1335f1e33e49efd8b8fd009ba4869e89a47d6f2b45b6414a28e01
provenance.local.txt SHA256: 805e774c7b3f79e237b35a7041e0f92f39ca92a8e06466bedfb49f62188eaef1
```

Both tools are Linux x86-64 ELF executables and their installed copies match the
build-tree outputs byte for byte. `onnx2ncnn` resolves Ubuntu
`libprotobuf.so.32`; neither tool has a missing dependency, `libprotobuf.so.23`,
or an MSYS2 dependency. Both start normally, print usage, and return `255` for
the accepted no-argument usage check.

The original `cmake --find-package` recovery probe still returned `1` because
ncnn's config calls FindOpenMP/FindThreads while CMake 3.28's legacy
`--find-package` mode does not enable a real C/CXX language. A replacement
minimal CMake C++17 consumer in `/tmp` successfully found `ncnn`, linked the
installed static library, ran, and printed `ncnn_version=1.0.20240410` and
`ncnn_consumer_smoke=PASS`. This proves the installed CMake package through its
actual supported consumer path.

The project branch remains `feature/pc-batch-c-ncnn-acceptance`; Git status still
contains only `TASKS.md` and this task file, the frozen ONNX SHA256 remains
`78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121`,
and no SDK file exists inside the project. Task 010 is restored to `In Progress`.

### Direct Conversion Failure and Blocking Report

Stopped: `2026-07-21T16:27:09+08:00`

Immediately before conversion, the frozen ONNX SHA256 was reverified as
`78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121`.
The installed, hash-verified converter was invoked exactly once using the task's
required direct command:

```text
/home/dministrator/opt/ncnn/ncnn-linux-x64-20240410-local/bin/onnx2ncnn \
  models/yolov5n-v7.0/yolov5n.onnx \
  models/yolov5n-v7.0/yolov5n.ncnn.param \
  models/yolov5n-v7.0/yolov5n.ncnn.bin
```

The process returned zero but printed twelve unsupported/unknown diagnostics:

```text
Unsupported unsqueeze axes !                    (four occurrences)
Shape not supported yet!                        (two occurrences)
Cast not supported yet!                         (two occurrences)
Unknown data type 0                              (two occurrences)
Unsupported Resize scales and sizes are all empty! (two occurrences)
```

Because a zero exit status does not make a graph with unsupported operations
valid, the generated files are preserved only as failed-attempt evidence and
must not be described, loaded, manifested, staged, committed, or reused as a
successful conversion. Their observed identities are:

```text
param size: 32448 bytes
param SHA256: 18568fad950d54e18e2d3c25a98094c945911bc3ff86d52204536e7b65583fc6
bin size: 7873076 bytes
bin SHA256: 81855525ad59a0c394fbbe9fdbd7e58fa441752d3160f0cb3b374edc02545ff7
conversion log size: 374 bytes
conversion log SHA256: 6302d0e527b62890c03ea68d194ba3f96126596c72bf3be93d874fb7415eadf2
```

The `.bin` and log remain Git-ignored. The small `.param` is untracked and is
not approved for staging. The source ONNX hash is unchanged. No optimizer,
quantizer, pnnx, inference, manifest validator, load smoke, project build, test,
or benchmark was run after the converter diagnostics.

```text
Current Task: Task 010
Current Status: Blocked
Last Successful Step: ncnn 20240410 Linux toolchain and CMake consumer acceptance passed; frozen ONNX SHA256 matched immediately before direct conversion
Failed Command: /home/dministrator/opt/ncnn/ncnn-linux-x64-20240410-local/bin/onnx2ncnn models/yolov5n-v7.0/yolov5n.onnx models/yolov5n-v7.0/yolov5n.ncnn.param models/yolov5n-v7.0/yolov5n.ncnn.bin
Exit Code: 0, but semantic conversion validation failed because the converter reported unsupported operations and an unknown data type
Relevant Error: Unsupported unsqueeze axes; Shape not supported yet; Cast not supported yet (to=7); Unknown data type 0; Unsupported Resize scales and sizes are all empty
Files Changed: TASKS.md; tasks/010_ncnn_model_conversion.md; untracked failed models/yolov5n-v7.0/yolov5n.ncnn.param; ignored failed models/yolov5n-v7.0/yolov5n.ncnn.bin and results/logs/010_ncnn_conversion.log
Attempts Made: one approved direct conversion invocation; 0 automatic repair loops because unsupported-operator/model-conversion ambiguity is an immediate mandatory stop
Why Automatic Recovery Is Unsafe: continuing could silently accept a structurally incorrect model; every plausible workaround would change a forbidden contract item by editing/re-exporting/simplifying the ONNX, changing ncnn, patching the converter, manually editing param, optimizing, or switching to pnnx
Exact Human Action Required: inspect the preserved conversion log and choose whether Task 010 remains blocked or explicitly authorize a separate model/converter-contract change; under the current frozen ncnn 20240410 plus direct ONNX conversion contract there is no safe automatic workaround
Commands to Resume: rerun branch/status/protocol audit; verify the frozen ONNX, installed converter, failed param/bin, and conversion-log SHA256 values above; do not rerun or replace the conversion until the user explicitly approves a changed strategy; discard failed artifacts only after explicit authorization or immediately before an approved full replacement attempt
Git Status: TASKS.md and tasks/010_ncnn_model_conversion.md are modified; the failed param is untracked; the failed bin and log are ignored; nothing is staged or committed
```

### Approved Parallel pnnx Contract Recovery

Resumed: `2026-07-21T17:09:19+08:00`

The user explicitly approved replacing Task 010's failed direct-conversion
contract with a parallel ncnn conversion contract:

```text
same YOLOv5n v7.0 .pt weights
-> fixed CPU/FP32 TorchScript export
-> pnnx from ncnn 20240410 revision 56775de50990ab7f16627efdcf5529b49541206f
-> ncnn param/bin
```

The Task 002 ONNX remains unchanged and continues to serve both ORT backends.
The direct `onnx2ncnn` failure does not invalidate that frozen ONNX contract.
Task 010 and `TASKS.md` were restored together to `In Progress`, and targeted
ignore rules were added for TorchScript, pnnx, and ncnn model artifacts.

Before cleanup, all failed direct-conversion artifacts and the retained log were
reverified:

```text
invalid param SHA256: 18568fad950d54e18e2d3c25a98094c945911bc3ff86d52204536e7b65583fc6
invalid bin SHA256: 81855525ad59a0c394fbbe9fdbd7e58fa441752d3160f0cb3b374edc02545ff7
conversion log SHA256: 6302d0e527b62890c03ea68d194ba3f96126596c72bf3be93d874fb7415eadf2
log parse: Unsqueeze=4, Shape=2, Cast=2, Unknown-data-type=2, Resize=2
```

The retained log remained nonempty and parseable. These identities belong only
to the failed direct path and must never be reused as pnnx output identities.

### Fixed pnnx Toolchain Build

The project environment was audited before configuration:

```text
Python: 3.12.3
torch: 2.2.2+cpu
torchvision: 0.17.2+cpu
torch CMake/headers/libraries: present under the project .venv
torch compiled CXX11 ABI: 0
TorchVision CMake package/library: absent; optional in pnnx 20240410
GCC/G++: 13.3.0
CMake: 3.28.3
Ninja: 1.11.1
protoc: 3.21.12
```

The full pnnx CMake/README and its `PNNXPyTorch.cmake` module were read. No
FetchContent, ExternalProject, download, or network build rule exists. The
generated build uses `/usr/bin/g++`, C++17, and
`-D_GLIBCXX_USE_CXX11_ABI=0`; no compile/link/generation rule uses MSYS2. The
only `/mnt/c/msys64` text is the defensive ignored-prefix cache value.

Torch's ABI 0 differs from the host compiler/system Protobuf ABI. The pnnx
source's own ABI guard therefore configured `Building without onnx-zero`. This
is not a missing TorchScript-to-ncnn feature: it disables only optional pnnx ONNX
emission. TorchVision and Python development headers were also not required by
the built `pnnx` target. These observed optional omissions were not bypassed.

The fixed installed tool identity is:

```text
pnnx source tag: 20240410
pnnx/ncnn revision: 56775de50990ab7f16627efdcf5529b49541206f
pnnx source tree: db4f9e5bc6dff9d78e0eecb1ebc5d2b19a4f5893
pnnx path: /home/dministrator/opt/ncnn/pnnx-linux-x64-20240410-torch2.2.2-local/bin/pnnx
pnnx size: 6797712 bytes
pnnx SHA256: 978daf93358863bd6ebcceee6447d5a8db9b95c4aa1b25d34fdee71b816d052f
external provenance SHA256: dc0cc8f39e5e80de8d92dc809143f7d83e61308f1737628199f629ce491b07f1
```

The installed tool is Linux x86-64 ELF. With
`LD_LIBRARY_PATH=/home/dministrator/projects/edgeai-deploy-benchmark/.venv/lib/python3.12/site-packages/torch/lib`,
`ldd` resolves all Torch/system libraries and contains neither `not found` nor an
MSYS2 path. Without that explicit fixed path the installed `$ORIGIN/` RUNPATH
cannot locate the project Torch libraries, so the environment is mandatory and
recorded. The no-argument usage command printed normal help without loader error
or crash and returned the accepted status `255`.

#### Repair Attempt 1: build-session orchestration

```text
Failure: the first install could not find build-linux-x64-torch2.2.2/src/pnnx
Root Cause: the verbose build exceeded one tool wait window; the caller failed to retain the running session, and a tee pipeline exposed tee's zero status instead of a completed Ninja status
Files Modified: only authorized repository-external build/install artifacts and /tmp logs
Fix Applied: resumed with a persistent polled execution session, direct Ninja/CMake exit propagation, output redirected to a log, and parallelism reduced from 8 to 4
Commands Re-run: cmake --build ... --target pnnx --parallel 4; cmake --install ...
Result: all remaining 483 Ninja steps completed, link exited zero, and install exited zero
```

The build emitted warnings from the fixed pnnx source and PyTorch headers under
the upstream `-Wall -Wextra` configuration. No warning was hidden, no warning
flag was lowered, and no external source was changed. Repository-external logs
and provenance preserve the exact commands, results, hashes, dependency choices,
and loader environment.

### TorchScript Export and Frozen-ONNX Equivalence

Completed: `2026-07-21T17:26:56+08:00`

Immediately before export, the fixed source and artifacts were reverified:

```text
YOLOv5 tag: v7.0
YOLOv5 revision: 915bbf294bb74c859f0b41f1c23bc395014ea679
YOLOv5 source status: clean
weights SHA256: 4f180cf23ba0717ada0badd6c685026d73d48f184d00fc159c2641284b2ac0a3
frozen ONNX SHA256: 78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121
```

The fixed v7.0 exporter ran on CPU with batch 1, FP32, and `640x640`, using no
half, INT8, optimize, dynamic, quantization, Vulkan, model surgery, or Detect-head
replacement option. It exited zero and produced:

```text
TorchScript path: models/yolov5n-v7.0/yolov5n.torchscript
size: 7993343 bytes
SHA256: 1ea5813fac07158ca4ff5eb98b273353b1bf5baafdd46f1ced4ab33835247892
export log SHA256: 66f3749b7b3dde378e8cb0b3619722592aac1bef76cfe503de260c19a4a1cce0
```

`torch.jit.load(..., map_location="cpu")` passed. The real model returned one
finite FP32 tensor with shape `[1,25200,85]`. The pre-registered comparison used
the same deterministic reference-image tensor for TorchScript and explicit
`CPUExecutionProvider` ONNX Runtime 1.18.1. Both produced 5 detections with the
same classes. Minimum class-matched IoU was `0.9999971389770508` and maximum
absolute confidence difference was `0.000002`, passing the frozen `0.99` and
`0.001` gates. The raw maximum and mean absolute tensor differences were
`0.0017242431640625` and `0.0000010239697521250297`; they are preserved as
diagnostics, not presented as a bitwise-equality requirement.

```text
TorchScript manifest SHA256: 24401522387fd91d6afe6dfbc7029140aea564a8ea3cd09f0db55763ad14e8f2
TorchScript validation SHA256: 67f42f0f7f82c234213317f5ceebe214e85e464466ec90573ba0b6ca8f571286
```

### pnnx Conversion and Observed ncnn Contract

The invalid direct-`onnx2ncnn` param/bin were deleted only after their approved
hashes and the retained failure-log hash were recorded above. The failure log
remains at `results/logs/010_ncnn_conversion.log`. Neither failed artifact was
reused by pnnx.

The approved pnnx command ran once in `/tmp/edgeai-task010-pnnx` with the fixed
Torch library path and exactly:

```text
inputshape=[1,3,640,640]f32
device=cpu
fp16=0
optlevel=2
customop=(empty)
moduleop=(empty)
```

It exited zero, emitted no unsupported/unknown/custom operator, and did not use
`ncnnoptimize`. Optional `.pnnx.onnx` emission was skipped by the already recorded
onnx-zero ABI guard. Generated helper Python files were hashed but never run.
The fixed loader printed four `no attribute value in int list` fallback messages;
source inspection located this pinned-loader fallback, and the manifest records
it without hiding it. The final explicit pnnx graph shapes and independent ncnn
runtime probe both passed; Task 011 semantic equivalence remains mandatory.

```text
pnnx param: 30921 bytes, SHA256 32e10a83491e58afaffd48718ec24b6926354f2ccd08a84ac95032dc9338bd87
pnnx bin: 7896238 bytes, SHA256 7ceccfe635efb103cb207e6e847026b3ef4083448821ea75df074b6fd32b028a
ncnn param: 16885 bytes, SHA256 72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4
ncnn bin: 7873060 bytes, SHA256 658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0
pnnx conversion log SHA256: a9354cb789af90158fa1d2316e884c8e4716a065b141681357eccbd95ac6ff32
```

The parsed pnnx graph contains 179 layers and 184 blobs. It decodes the three
Detect scales (`19200`, `4800`, `1200` candidates at strides `8`, `16`, `32`)
and concatenates them as one `[1,25200,85]` FP32 tensor. The ncnn graph contains
207 layers and 237 blobs, uses only pinned-runtime built-in layer types, and has
zero custom layers. Its frozen observed blob contract is:

```text
input:  in0, logical [1,3,640,640], FP32
output: out0, ncnn dims=2, w=85, h=25200, d=1, c=1, elempack=1,
        elembits=32, logical [1,25200,85], FP32
form:   single decoded YOLOv5 candidate tensor, graph NMS absent
```

### Release Build, Load Probe, Tests, and Repairs

The full Release configuration used ONNX Runtime 1.18.1, OpenCV 4.6.0, and the
fixed ncnn 20240410 CMake package. The final clean configure and all 29 Ninja
steps completed without CMake or compiler warnings. The model smoke loaded both
artifacts, disabled Vulkan/FP16/BF16/INT8, used one thread, ran a deterministic
zero-input shape/type probe, and verified all 2,142,000 output scalars were finite.
This probe is not a detection-correctness result or benchmark.

```text
ncnn runtime version: 1.0.20240410
load_param status: 0
load_model status: 0
runtime evidence SHA256: 6860a7702ebf7fb3d57551831baf4cd7e3a6b1ac1edfb2a8a41ef9df23e99310
ncnn manifest SHA256: 9b3fa287c109a9d2d8928ed959ac363e559e3feea24364b31977b0fc85020cff
Task 010 focused Python tests: 8/8 passed
full Python suite: 58/58 passed
CTest: 8/8 passed
JSON parse checks: passed
generated-file whitespace checks: passed
git diff --check: passed
Git-ignore checks for TorchScript/param/bin: passed
completed Tasks 002-009 diff check: unchanged
```

#### Repair Attempt 2: CMake policy warning

```text
Failure: the first successful project build emitted a CMake CMP0144 developer warning because NCNN_ROOT was intentionally set
Root Cause: CMake 3.28 introduced CMP0144 after the project's 3.16 minimum and had no explicit policy selection
Files Modified: cpp/CMakeLists.txt
Fix Applied: select CMP0144 NEW only when that policy exists; keep explicit NO_DEFAULT_PATH ncnn discovery and all warning flags
Commands Re-run: delete build/pc-ncnn-release; complete Release configure; complete parallel build
Result: configure and all 29 build steps passed with no warning
```

#### Repair Attempt 3: explicit Input-layer parsing

```text
Failure: the first ncnn manifest-validator run reported an empty inferred input edge
Root Cause: the generic external-edge calculation did not account for ncnn representing its model input as an explicit Input layer
Files Modified: scripts/validate_ncnn_conversion.py
Fix Applied: derive ncnn input names from Input-layer tops while retaining terminal-output edge validation
Commands Re-run: Python compile check and the complete ncnn conversion-validation command
Result: in0 -> out0, artifact hashes, built-in layers, runtime evidence, and decoded output contract all passed
```

A later combined whitespace-check shell command exited `1` only because
`git diff --no-index` returns `1` when a compared untracked file differs from
`/dev/null`, even with no whitespace diagnostic. No file was modified for this
orchestration issue. The check was rerun by requiring empty diagnostic output;
all nine untracked text files passed.

Task 011's correctness gates are frozen in `ncnn_manifest.json` before any real
ncnn detection comparison: the target is minimum class-matched IoU `0.99` and
maximum confidence delta `0.01`; the hard floor is `0.98` and `0.02`, with the
required human-stop dispositions. The known earbud-case false positive must
remain semantically aligned and may not be hidden by threshold changes.
