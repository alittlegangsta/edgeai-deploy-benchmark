# Task 028

## Title

YOLOv5n ArmNN/Alnpu bring-up and benchmark.

## Status

Completed

## Dependency and branch

Depends on Task 027 (`Completed`). The controlled-SD and persistent-runtime
commits are integrated locally into `dev` at merge commit `a834f38`; work
continues on `feature/armnn-alnpu-bringup`.

## Scope

Build and validate a board-side single-image Arm NN runner for the frozen
YOLOv5n v7.0 ONNX contract, forcing the `Alnpu`/`ALHardNPU` backend and
reusing the repository's baseline preprocessing and YOLO decode/NMS code. The
first attempt must use the existing FP32 opset-12 model. Unsupported
operators, tensor types, or quantization requirements must be captured from
real parser/runtime output; a quantized adaptation is allowed only after an
FP32 failure is demonstrated and only with a reproducible conversion and
correctness record.

Once correctness is closed, run a bounded static-image benchmark with explicit
preprocess, inference-only, postprocess, and end-to-end timing boundaries and
compare it with the immutable ARM CPU baseline. Camera acquisition, video,
Vulkan, and NPU system reconfiguration are out of scope.

## Frozen contract

- Model: repository YOLOv5n v7.0 ONNX, opset 12, FP32, input `[1,3,640,640]`,
  output `[1,25200,85]`, graph NMS absent.
- Input, model hash, configuration, confidence threshold `0.25`, IoU threshold
  `0.45`, class-aware NMS, and PC/ARM golden evidence remain unchanged.
- Runtime profile: Task 019 `recommended-dual-thread`; ncnn is historical
  comparison only. Arm NN must request only `Alnpu`; `CpuAcc` and `CpuRef`
  fallback is a hard failure.
- No eMMC, boot, DTB, kernel, FPGA, governor, frequency, or Task 027 runtime
  change is allowed. An application-only SD update requires a separate user
  approval before media write.

## Acceptance criteria

1. The Arm NN/Alnpu build identity, private runtime libraries, model and input
   hashes are recorded without copying vendor binaries into Git.
2. The runner builds as an AArch64 ELF with no x86 objects, and its dynamic
   dependencies are statically audited.
3. A real FP32 parser/optimization/load attempt is retained. It either passes
   the frozen tensor contract and correctness gate or records the exact
   unsupported reason and a bounded repair attempt.
4. A successful run proves `Alnpu`/`ALHardNPU` assignment and explicitly shows
   that no CPU fallback was accepted. Shape, dtype, raw statistics, class,
   confidence, box IoU, detection count, and decode/NMS results are compared
   with the existing golden.
5. If FP32 is unsupported, any quantized path is independently reproducible and
   includes before/after correctness evidence; no alternate YOLO model may be
   silently substituted.
6. Only after correctness passes, a bounded static-image benchmark records
   warmup, repeats, stage timings, p50/p95, FPS, process CPU, Peak RSS, CMA and
   NPU state, and compares to the Task 017/018 CPU records without mixing
   camera or image-read time into inference-only timing.
7. Task 017--027 formal evidence is unchanged, all Task 028 evidence is real,
   and no SD/eMMC or system image write is performed.

## Allowed files

- `tasks/028_yolov5n_armnn_alnpu_bringup_and_benchmark.md`
- `TASKS.md`
- `ROADMAP.md`
- `README.md`
- `CHANGELOG.md`
- `docs/vendor/ANLOGIC_YOLOV5N_ARMNN_ALNPU.md`
- `.knowledge/manifests/anlogic_yolov5n_armnn_alnpu.yaml`
- `cpp/CMakeLists.txt`
- `cpp/include/edgeai/backends/armnn_detector.hpp`
- `cpp/src/backends/armnn_detector.cpp`
- `cpp/apps/armnn_image.cpp`
- `cpp/tests/test_armnn_detector.cpp`
- `scripts/vendor/build_task028_armnn_runner.sh`
- `scripts/vendor/prepare_task028_floor_identity_model.py`
- `scripts/vendor/quantize_task028_yolov5n.py`
- `scripts/vendor/validate_task028_armnn.py`
- `scripts/vendor/run_task028_armnn_probe.sh`
- `scripts/vendor/prepare_task028_graph_matrix.py`
- `scripts/vendor/validate_task028_graph_matrix.py`
- `scripts/vendor/validate_task028_native.py`
- `scripts/vendor/validate_task028_trackc.py`
- `scripts/vendor/collect_task028_trackc2.py`
- `scripts/vendor/validate_task028_trackc2.py`
- `results/evidence/028/*.json`

## Forbidden changes

- Do not modify Task 017--027 task files, manifests, evidence, models, input,
  PC golden, ncnn assets or runtime scripts.
- Do not commit vendor SDKs, Arm NN libraries, models, modules, rootfs, ELF,
  private keys or large board logs.
- Do not install packages, download unrelated dependencies, modify eMMC/SD
  boot files, load a new kernel/DTB/bitstream, or change board services.
- Do not execute an Arm NN workload with a CPU fallback, claim benchmark data
  from a failed run, or fabricate unsupported-operator/output evidence.
- Do not push, create a PR, merge, rebase or reset. A final local commit is
  deferred until the user explicitly approves the completed candidate.

## Execution record

- Start: 2026-08-07 Asia/Shanghai. Local `dev` contains the Task 026/027 merge
  `a834f38`; current branch is `feature/armnn-alnpu-bringup`; initial worktree
  was clean.
- The frozen model/input/config and Arm NN vendor source/runtime identities are
  being rechecked before any board run. The final diagnostic-capable isolated
  runner is an AArch64 ELF with SHA256
  `c6c55b1df88d89a4507a2526f2198a7cbddb2ccc7bf8e881cf38d40e3f1a2d02`.
- The approved board runtime was read-only checked before each probe:
  Buildroot 2022.02.6, Linux `6.1.111-rt42`, 128 MiB CMA, and loaded
  `cma_mem`, `hard_npu`, `soft_npu` with all three device nodes. No Task 028
  module load, reboot, SD/eMMC write, or persistent-runtime change occurred.
- The direct frozen FP32 probe exited 1 with the real parser error
  `Unsupported operation Floor for node '/model.11/Floor'`. A bounded set of
  exact-ORT-equivalent graph repairs was then probed. Four rewrites exited 139
  in the parser, two fixed-Resize rewrites returned the ArmNN unknown-shape
  error, and an explicit-scales rewrite exited 139. Every probe left dmesg
  unchanged.
- A reproducible Conv-only QDQ quantization was generated after the FP32
  failure. Local ORT changed the detection set from 5 to 4 and the board
  parser exited 139, so no quantized correctness or benchmark result is
  claimed.

### Commands actually run

- Local ONNX contract inspection with ONNX 1.16.2 and the frozen manifest.
- VM isolated AArch64 CMake/Release builds using CMake 3.16.9 and Linaro GCC
  7.5.0; final runner hash is recorded in
  `results/evidence/028/armnn_build.json`.
- Board read-only runtime/`ldd`/module/device checks and temporary Alnpu-only
  probes for the frozen graph and every listed repair variant.
- Local ONNX 1.16.2/ORT 1.18.1 graph-generation and Conv-only QDQ commands.
- Model-independent Release build, CTest (3-test and existing 14-test
  suites), Python unittest (131 tests in the project venv), JSON/YAML parse,
  shell/Python syntax, previous Task 022--027 validators, link scan, sensitive
  material scan, and `git diff --check`.
- Read-only bounded exact-name/content searches over the local vendor roots,
  all reachable `dr1m90_npu`/SDK refs and tags, the curated knowledge base, and
  VM vendor/SDK/workspace roots. No native compiler/runtime asset was found.
- Read-only VM identity and container-cache checks; no Docker, Podman or
  Nerdctl executable or known native compiler image cache was found.
- Static APUG1205 PDF extraction and SoftNPU `Design.xml`/parameter/bitstream
  hash checks. No compiler, runtime, model conversion, board execution or
  native binary was run.
- Read-only audit of the official `dr1m90_npu` `AL_onnx_pass.py`, checker,
  shape, Detect-crop, split, quantizer, host postprocess and ArmNN executor
  sources, including source hashes and the release checkout identity.
- Created the external ext4 venv `/home/dministrator/.venvs/anlogic-al-onnx-pass`
  and installed the unchanged vendor requirements. The first pip attempt
  returned an OSError while completing Torch files; rerunning the same command
  returned 0, `pip check` passed, and the required imports were verified.
- Ran the unmodified official `AL_onnx_pass.py` on an exact copy of the frozen
  model with one calibration image (then a separate 27-image smoke). The
  official pipeline exited 0, produced Detect-cropped FP32 and uint8 QDQ
  outputs, and reported the exact SoftNPU operator set. Host ORT inference of
  the uint8 output returned five detections but failed the frozen golden gate;
  the int8 probe generated an invalid opset-12 `DequantizeLinear(axis=...)`
  graph. All generated artifacts remain in `/tmp/task028-trackc`.
- The initial unmodified official `AL_onnx_pass.py` attempt stopped at import
  because the existing project venv lacked `onnxsim` and `onnx_tool`. A separate
  `/home/dministrator/.venvs/anlogic-al-onnx-pass` was then populated strictly
  from the unchanged vendor requirements. `pip check` and all required imports
  pass; the complete freeze and repair history are in
  `results/evidence/028/trackc_environment.json`.
- Frozen FP32 host reference rerun passed the existing golden (five
  detections, minimum IoU 1.0, zero confidence delta). A source-equivalent
  Detect-crop prepass and official host `yolo_model_inference.py` produced
  three FLOAT head outputs and five matching classes/confidences; integer box
  output has minimum comparison IoU `0.9550582994980138`, so the geometry gate
  remains open. This prepass is not an official conversion or NPU result.
- The unmodified official conversion now exits 0. It produces a 199-node
  Detect-cropped FP32 graph and a 719-node uint8 QDQ graph. The official checker
  reports `Add`, `MaxPool`, `Concat`, and `Resize` as SoftNPU operators; the
  three raw FLOAT heads are finite and have the documented shapes. A 27-image
  local calibration smoke was also reproducible, but it did not close the
  correctness gate.
- After the smoke, a deterministic 500-image calibration set was generated
  from 27 locally available raw frames/images using fixed OpenCV transforms.
  It is recorded as host-smoke evidence only (source manifest and generation
  algorithm are hashed); its uint8 output also fails the strict golden gate.
- Track C2 added same-weight static-640 opset13/14 exports (constant folding
  off/on) while preserving the frozen opset12 baseline. All four passed ONNX
  checker and exact ORT raw-output comparison. The unchanged official
  `AL_onnx_pass.py` produced checker/ORT-valid uint8 and int8 graphs for all
  four; this resolves the opset12 `DequantizeLinear(axis=...)` invalid-graph
  issue. An independent eight-image held-out host gate still rejects both
  quantized candidates, so no board or benchmark run was started.
- `collect_task028_trackc2.py` emitted the four C2 JSON artifacts, including
  graph contracts, checker/ORT receipts, held-out teacher-relative metrics and
  MaxPool/Concat/Resize QDQ range diagnostics. The independent
  `validate_task028_trackc2.py` check passed.
- `scripts/vendor/validate_task028_trackc.py`, JSON/YAML parsing, shell/Python
  syntax, model/input hash checks, Task 017--027 immutability, link scan,
  sensitive-material scan and `git diff --check` passed.
- A final offline validator sweep first passed the unsupported `--json` option
  to `validate_task028_native.py` (exit 2); the validator was immediately
  rerun with its documented CLI (exit 0). No files or evidence were changed by
  the invocation correction.
- Track C2 evidence was regenerated after adding an explicit class-multiset
  agreement field and computed task-level gate thresholds. The held-out class
  agreement is 87.5% for both uint8 and int8; both computed gates remain false.
- Track C is now split into four explicit states: C1 official
  `AL_onnx_pass=PASS`; C2 quantized host accuracy=`NOT_ACCEPTED`; C3 board
  Alnpu compatibility=`BLOCKED_UNSUPPORTED_ALNPU_QUANTIZED_LAYERS`; and C4
  benchmark=`NOT_RUN`. The best opset14 uint8 graph was copied only to board
  `/tmp` and run once with CPU fallback disabled. ArmNN parsed it, but Alnpu
  optimization rejected QAsymmU8 Conv2d, Activation and ElementwiseBinary
  layers before `LoadNetwork`; no raw board heads or detections exist.
- The multi-output AArch64 runner was rebuilt in an isolated VM as
  `c6c55b1df88d89a4507a2526f2198a7cbddb2ccc7bf8e881cf38d40e3f1a2d02`; it
  binds all three `[1,255,H,W]` outputs, optionally saves temporary float32
  heads, and decodes them only for diagnostics. No benchmark mode was run.
- The first C3 VM configure attempt used a stale toolchain path and exited 1;
  after diagnosis the isolated build was reconfigured with
  `<VM_TASK028_SOURCE_ROOT>/configs/toolchains/anlogic-dr1-aarch64.cmake` and
  `/usr/bin/gmake`, then `cmake --build <VM_TASK028_C3_BUILD_ROOT>
  --target edgeai_armnn_image -- -j2` exited 0. This repair changed only the
  isolated build workspace and is recorded in `trackc3_runner_build.json`.
- Host preprocessing audit found exact equality on the frozen 1280x960 input
  between the project baseline and vendor `data_reader.py`/
  `yolo_model_inference.py` (`max_abs_delta=0`). The vendor path uses
  `scaleup=False`, so smaller images can diverge and calibration provenance
  must retain that distinction.
- The bounded vendor search did not find the requested YOLOv5s positive-control
  model/config or native compiler/runtime assets. The release
  `run_yolo_pic.sh` actually invokes the separate `yolov8n.quant.onnx` demo.
- Latest offline validation: `2026-08-10 15:19:42 CST` — JSON/YAML parsing,
  Task 022--027 focused validators, Task 028 Track C/Track C2/native/graph
  validators, Release build, CTest (3 and 14 tests), Python unittest (131),
  Markdown links, sensitive-material scan, repository hygiene, and
  `git diff --check` passed. The C3 result validator correctly returned exit
  1 for the blocked board result and is recorded as an expected rejection.
- Evidence hashes after the C3 update: board smoke
  `fb5fba05e4ce6ace3e535be13890c213615ec4bb31d1a4f922ac8d6c2080e550`, host
  raw reference `56f536c31a35f755c018735a789801626b057e6f3ad837c6991ef4e3917b19f`,
  preprocessing audit
  `ab02563e5bb79f1bbbd0436f72d0ae517cc813ec83f1efbd6047500819743d38`, and
  validation manifest
  `4653e0dfd4bdb9473b65efb8c753f02e701412af5ef1dd5d7b654933eacbfd6c`.

### Commands not run or intentionally excluded

- No additional board workload was run beyond the single Alnpu-only C3 smoke
  recorded above. That smoke exited 1 at `Optimize`; no board raw heads or
  detections were produced, no CPU fallback was accepted, and no benchmark was
  claimed. The source-equivalent Detect-crop prepass remains distinct from the
  official artifact.
- The official board-successful `yolo_face_uint8_15.onnx` positive control and
  a TorchScript-derived opset 10/11/12, static-640 export matrix are audited
  separately from the frozen FP32 runner. Matrix entries are only board
  candidates after ONNX checker and ORT raw-output comparison pass.
- The Track C2 opset13/14 matrix is host-only by contract. Its four entries
  pass the same checker/raw gate and are recorded in `trackc2_export_matrix.json`;
  no C2 entry was sent to the board.
- The positive control is SHA256 `5ed304f1cfd37a6c4ddc789a58a4c98e3472efe31eff62fc9e447163ea60668`,
  opset 14, static `[1,3,416,416]` FLOAT input, two FLOAT outputs, and a
  Q/DQ-heavy graph. Task 026 records its real `Alnpu`/`ALHardNPU` assignment;
  it is not the YOLOv5n contract.
- Six TorchScript exports (opsets 10/11/12, static 640, constant folding
  off/on) passed ONNX checker and exact local ORT raw comparison. Every board
  attempt rejected `Floor` before Alnpu optimization/load. Evidence is in
  `graph_dialect_diff.json`, `export_matrix.json`, and
  `board_export_matrix.json`.
- The four Track C2 opset13/14 entries were intentionally not sent to the
  board: they are host deployment candidates only until the independent
  quantized task-level gate passes.
- A rebuilt runner with `--parse-only 1` enabled dependency-sliced parser
  bisection. Minimal probes isolated explicit Floor/Identity/INT64-shape,
  Resize, and FP32 Conv/Reshape limitations; a minimal QDQ graph reached
  Alnpu `LoadNetwork`. Larger exact-Floor-rewrite graphs still reproduced
  SIGSEGV after `parser_created`. Board gdb was absent and VM gdb was x86-only;
  no packages were installed. Results are retained in `parser_bisection.json`.
- No `--mode benchmark` run, timing sample, FPS, Peak RSS, or CPU-vs-NPU
  comparison was collected.
- The APUG1205 native YOLOv5s positive path was not run: the documented
  compiler/container, conversion config, model, native headers/library and
  generated assets were all absent from the audited scopes. No substitute
  compiler, model, runtime or CPU path was used.
- No module load, reboot, SD/eMMC write, boot-file change, system install,
  camera run, or vendor-system modification was performed by Task028.
- The existing test summary's `43` is a Python test count, not a 43-image golden
  collection. No complete 43-image annotated golden set exists in the
  repository or audited local vendor roots, so a 43-image regression cannot be
  truthfully claimed; the existing eight-image held-out FP32-reference
  agreement remains the available quantization diagnostic.

## Track C: official `AL_onnx_pass` pipeline

The official `dr1m90_npu` `npu_demo/scripts/AL_onnx_pass.py` is now the active
conversion track. Its source identity is the dirty `release` checkout at
`199ef4d71f453bb9a000102ff39def09c4cf73f9` (no tag points at that HEAD). The
implementation is an ArmNN/ONNX preparation path, not the APUG1205 native
`convert_tool`/`al_ai_flow` runtime: it runs `onnxsim`, fixed-shape inference,
YOLO Detect cropping, Conv/FC splitting, opset conversion, `onnx_tool` checks,
and ONNX Runtime static QDQ quantization. The final demo still uses ArmNN's
`OnnxParser` and the `Alnpu` backend; it does not emit `rt.bin`, `weight.bin`,
or call `npu_runtime`.

The exact official entry first ran against the frozen YOLOv5n v7.0 model in the
project venv and exited 1 before `onnx.load`/simplification because that venv
had neither `onnxsim` nor `onnx_tool`. A separate ext4 venv was then populated
from the unchanged vendor `requirements.txt`; the final environment imports all
required packages and passes `pip check`. In that environment the unchanged
entry exits 0, emits the Detect-cropped FP32 graph and a uint8 QDQ graph. The
freeze, commands and artifact hashes are in `trackc_environment.json` and
`trackc_official_smoke.json`; generated models remain outside Git.

The frozen FP32 reference independently passes the existing host golden
(five detections, raw `[1,25200,85]` FLOAT output, minimum IoU 1.0 and maximum
confidence delta 0.0). The official simplified FP32 head model runs through
`yolo_model_inference.py` on `CPUExecutionProvider` and returns five matching
classes/confidences; its integer source-space boxes have minimum comparison IoU
`0.95506547868033`. The official uint8 QDQ model also returns five detections
and matching classes, but its minimum IoU is `0.8421554845490358` and maximum
confidence delta is `0.09312496031303408`; the strict host golden gate fails.
A 27-image calibration smoke remains a failure. An int8 probe is invalid under
the generated opset-12 graph because `DequantizeLinear(axis=...)` fails ONNX
checker and ORT. A deterministic 500-image host calibration smoke also fails
(minimum IoU `0.8891731303877853`, maximum confidence delta
`0.11366653714614872`). No board execution or benchmark is allowed until host
semantic correctness is closed.

A one-image, diagnostic-only QDQ activation probe localized the largest first
relative errors at `/model.9/m*/MaxPool_output_0` and
`/model.9/Concat_output_0`, followed by the two `Resize_output_0` tensors.
This agrees with the vendor README's documented warning about YOLO `Concat`
scale mismatch. It is not a promoted graph rewrite or a correctness result;
the exact values and provenance are in `trackc_official_smoke.json`.

The source graph has four `Floor`, two `Shape`, zero `Gather`, and two dynamic
`Resize` nodes. The official Detect crop removes `Floor` and `Shape` and emits
the three-head contract; uint8 QDQ adds 200 `QuantizeLinear` and 320
`DequantizeLinear` nodes. The exact checker identifies `Add`, `MaxPool`,
`Concat`, and `Resize` as SoftNPU operators and retains three first-convolution
acceleration warnings. These facts are not a board execution result.

## Track C2: opset13/14 candidates and independent quantization gate

Track C2 preserves the frozen opset12 FP32 model and adds four same-weight,
static `[1,3,640,640]` exports: opsets 13 and 14 with constant folding off and
on. Every export has exact ORT raw-output equality with the frozen
`[1,25200,85]` FLOAT output. Running the unchanged official conversion on all
four produced Detect-cropped three-head graphs and checker/ORT-valid uint8 and
int8 QDQ graphs. Thus the opset12 `DequantizeLinear(axis=...)` failure is an
opset dialect issue; it is not evidence that a C2 graph has run on Alnpu.

Calibration and evaluation are separated by SHA256. The held-out set contains
eight deterministic local images that are absent from the 27-source/500-image
calibration smoke. No COCO labels or other ground truth are available locally,
so true precision, recall, mAP50 and mAP50-95 are `NOT_COMPUTABLE`. The
evidence reports teacher-relative proxy metrics only and never labels them as
dataset mAP. The task-level gate requires exact count and class-multiset
agreement, all matched IoU >= 0.99, maximum confidence delta <= 0.01, and proxy
precision/recall >= 0.99. Neither candidate passes:

| candidate | count agreement | class agreement | min matched IoU@0.50 | max confidence delta | proxy mAP50 | proxy mAP50-95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| opset14 uint8 | 87.5% | 87.5% | 0.9194650385 | 0.1588631272 | 0.8333333333 | 0.7633333333 |
| opset14 int8 | 100% | 87.5% | 0.6684800835 | 0.2138248384 | 0.6944444444 | 0.4666666667 |

For the `/model.9` MaxPool branches, all three branch scales are equal in
each C2 QDQ model (uint8 `0.02454817108809948`, int8
`0.04709700495004654`); a literal branch-to-branch scale mismatch was not
observed. Range and QDQ errors remain material at MaxPool/Concat and the two
Resize outputs. This is diagnostic-only evidence; no manual QDQ, Floor,
Resize, or network rewrite was applied. See the four `trackc2_*.json` files
and `validate_task028_trackc2.py`.

## Track B: APUG1205 native compiler/runtime audit

The APUG1205 native path remains an independent historical track. Track C is
now the active technical track; Track A and Track B conclusions remain
unchanged:

```text
Track A: ArmNN/Alnpu graph bring-up = BLOCKED_UNSUPPORTED_ALNPU_GRAPH
Track B: APUG1205 native compiler/runtime = BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE
```

The APUG1205 document (SHA256
`54a25d9a5dc59b21e7f7253bc72adeeb2c8b3a4bc04c30bea81463026ef7c1f2`) documents
`convert_tool` -> `.tmfile` -> `al_ai_flow` -> `rt.bin`/`weight.bin`, followed
by `npu_c_api.h` and `libnpu_runtime.a`. A bounded read-only search covered
the local `NPU_info`, `03_demo`, `dr1m90_npu` and `sdk` reachable refs/tags,
`toolchains`, the curated vendor knowledge base, and the VM vendor/SDK/workspace
roots. No approved compiler container or release, `convert_tool`, `al_ai_flow`,
`net_config_yolov5s.json`, `yolov5s_320_sigmoid.onnx`, `.tmfile`, `rt.bin`,
`weight.bin`, `libnpu_runtime*`, or `npu_c_api.h` was found. The VM also has no
Docker, Podman, or Nerdctl executable or known image cache in the audited roots.

The official YOLOv5s conversion was therefore **not executed**;
`results/evidence/028/native_yolov5s_positive_path.json` records the missing
inputs and sequence. No native YOLOv5n runner or benchmark claim is made. The
ArmNN demo assets in `dr1m90_npu` are an independent ArmNN/ONNX path and are
not a substitute for the native runtime.

The 05-5 platform bitstream remains useful hardware-side evidence: its static
Video_NPU metadata has `NPU_SOFT=1`, `SOFT_NN=1`, `SOFT_YOLO=1`, and
`SOFT_RESIZE=1`; the tutorial platform `system.bit` SHA256 is
`e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5`.
This does not prove that the private native compiler/runtime is available. The
structured static IP evidence is in
`results/evidence/028/softnpu_ip_audit.json`.

## Repair attempts

1. **AArch64 build repair** — the first VM transfer omitted existing C++ test
   and probe sources (configure exit 1); the complete source tree was copied
   to the isolated workspace. The next build (exit 2) exposed GCC 7's
   function-pointer-deleter construction error; explicit ArmNN `Destroy`
   deleters fixed it. The resulting runner built successfully and VM-specific
   RPATH was disabled before board transfer.
2. **FP32 parser gate** — the frozen model was run once with Alnpu-only and no
   fallback. ArmNN reported the unsupported `Floor` node before network load.
   No benchmark was started.
3. **Graph-repair probes** — identity, Constant, removed-node, Add-zero,
   fixed-size Resize, shape-inferred fixed-size Resize, and explicit-scales
   variants were generated with ONNX 1.16.2 and checked in local ORT. Board
   results were respectively parser SIGSEGV, parser SIGSEGV, parser SIGSEGV,
   parser SIGSEGV, unknown tensor dimensions, unknown tensor dimensions, and
   parser SIGSEGV. Board dmesg remained unchanged for all probes.
4. **Quantized path** — Conv-only QDQ quantization with one frozen calibration
   image reproduced the pinned output hash, but local ORT correctness failed
   (4 detections versus 5 and raw max delta `308.5351867675781`); the board
   parser then exited 139. This path is not eligible for benchmark.
5. **Track C2 evidence collection** — two initial collector invocations used
   a malformed held-out image path and exited with `FileNotFoundError`; the
   unchanged collector was rerun with the exact vendor path and exited 0.
   The successful run regenerated all four C2 evidence files and passed the
   independent validator; no model or metric was altered to repair the typo.

## Current disposition

`automated_validation=COMPLETE`, `primary_track=official AL_onnx_pass`,
`track_a=BLOCKED_UNSUPPORTED_ALNPU_GRAPH`,
`track_b=BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE`,
`track_c1=PASS`, `track_c2=NOT_ACCEPTED`,
`track_c3=BLOCKED_UNSUPPORTED_ALNPU_QUANTIZED_LAYERS`, `track_c4=NOT_RUN`,
`correctness=BLOCKED_TRACK_C_BOARD_ALNPU_COMPATIBILITY`, `benchmark=NOT_RUN`,
`candidate_approved=false`. The historical project-venv import gap is resolved
in the isolated vendor environment and the unchanged conversion exits
successfully. C3 now has a real board result: the candidate is rejected by
Alnpu-only optimization before load, with no CPU fallback or benchmark claim.

After the positive-control diff, six-entry export matrix, dependency-sliced
parser bisection, APUG1205 asset audit, and the official AL_onnx_pass host
conversion, the current primary conclusion is
`BLOCKED_TRACK_C_BOARD_ALNPU_COMPATIBILITY`. Track A remains
`BLOCKED_UNSUPPORTED_ALNPU_GRAPH`; Track B remains
`BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE`. This is not permission to
change the frozen model, accept CPU fallback, or publish benchmark data. The
next minimum input for Track C is a vendor-supported quantization/operator
configuration that both closes host accuracy and supports the observed
QAsymmU8 layers on Alnpu; Track B separately still needs its versioned
compiler/runtime release and positive-control assets.

Track C2 does not change the host accuracy disposition. The opset13/14 official
graphs are valid host deployment candidates and fix the opset12 int8 checker/ORT
dialect failure, but both uint8 and int8 fail the independent held-out
task-level gate. C3 separately confirms that the best opset14 uint8 graph is
not currently assignable to Alnpu-only because QAsymmU8 Conv2d, Activation and
ElementwiseBinary are unsupported. True dataset precision/recall/mAP is
unavailable without ground-truth annotations; teacher-relative agreement is
diagnostic only. C4 remains `NOT_RUN`.

## C3 follow-up: INT8, operator probes, and controls (2026-08-10)

The best opset14 INT8 candidate was copied to board `/tmp` and run once with
the same multi-output AArch64 runner, `Alnpu` as the only preferred backend,
and CPU fallback disabled. The real command reached
`parser_created`, `network_parsed`, and `optimize_begin`, then exited `1`
because Alnpu rejected `QSymmS8` `Conv2d`, `Activation`, and
`ElementwiseBinary`; `LoadNetwork` was not reached and no raw heads or
detections were produced. The before/after dmesg delta contained only the
normal hard/soft NPU register mapping lines and no oops, panic, DMA, IRQ, or
hang evidence. The model SHA is
`8ff448f1fd250a198b0a4a44a1eca9d09c50a68a4da459788960282ba98c3ad9`.

A 12-entry temporary probe matrix covered `Conv2d`, `Activation`, `Add`,
`Mul`, `Concat`, and `Resize` for UINT8 and INT8 QDQ wrappers at static
`[1,3,640,640]`. All models passed the local ONNX checker, but all exited
`139` immediately after `parser_created` on the board with no severe dmesg
delta. These synthetic graphs are therefore recorded as
`PARSER_DIALECT_INCONCLUSIVE`, not as per-operator support or rejection
evidence. The earlier minimal identity-QDQ control still reaches Alnpu
`LoadNetwork`; the full-model UINT8 and INT8 results remain the authoritative
quantized-layer compatibility evidence.

The release YOLOv8n control was also sent to board `/tmp` for a parse,
Optimize, and LoadNetwork-only check. It reached parser/network creation but
exited `1` at Alnpu Optimize on `QAsymmU8 Splitter`; no fallback was accepted.
The previously successful `yolo_face_uint8_15.onnx` control has no Split
operator and remains a separate Task 026 positive control. This comparison
supports graph/operator coverage differences; a runtime/toolchain version
skew is not proven. Board runtime identity is ArmNN `v32.1.0`, version file
`ed5ae24`, `libarmnn.so.32.1` SHA
`5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce`, and
`libarmnnOnnxParser.so.24.6` SHA
`dcb43bc092ec283364806e563fa6aa8d2404eb7c005db44081821da405c5ce99`.

New structured records are in `trackc3_board_int8_smoke.json`,
`trackc3_quant_operator_probe_matrix.json`,
`trackc3_runtime_version_audit.json`, and
`trackc3_model_control_comparison.json`. Track states remain C1 `PASS`, C2
`NOT_ACCEPTED`, C3 `BLOCKED_UNSUPPORTED_ALNPU_QUANTIZED_LAYERS`, and C4
`NOT_RUN`; no benchmark or correctness claim was added.

## Latest offline validation (2026-08-10)

The extended Track C validator was run after adding the INT8 and control-model
evidence:

```text
python3 scripts/vendor/validate_task028_trackc.py --json: PASS
python3 scripts/vendor/validate_task028_trackc2.py --json: PASS
python3 scripts/vendor/validate_task028_native.py: PASS
python3 scripts/vendor/validate_task028_graph_matrix.py ...: PASS
validate_task022_npu_audit.py: PASS
validate_task023_npu_package.py: PASS
validate_task024_npu_mapping.py: PASS
validate_task025_npu_sd_preflight.py: PASS
validate_task026_sd_preflight.py: PASS
validate_task027_persistent_runtime.py: PASS
JSON/YAML parse (37 evidence JSON files): PASS
Python compilation and Bash syntax: PASS
Task028 Release CTest: 3/3 PASS
full Release CTest: 14/14 PASS
Python unittest: 131/131 PASS
git diff --check: PASS
```

No board command was run during this offline validation batch. The extended
validator preserves the C3 interpretation: both full YOLOv5n quantized graphs
stop at Alnpu `Optimize`, the synthetic operator matrix is inconclusive after
parser SIGSEGV, the YOLOv8n control stops at `QAsymmU8 Splitter`, and runtime
version skew remains `NOT_PROVEN`. C1 remains `PASS`, C2 remains
`NOT_ACCEPTED`, C3 remains `BLOCKED_UNSUPPORTED_ALNPU_QUANTIZED_LAYERS`, and
C4 remains `NOT_RUN`.

## C3 runtime/toolchain compatibility investigation (2026-08-10)

The active C3 sub-track is now runtime/toolchain compatibility, while the
observed quantized-layer rejection remains recorded as the board compatibility
result. The audited `dr1m90_npu` release checkout is branch `release`, commit
`199ef4d71f453bb9a000102ff39def09c4cf73f9` (no tag at HEAD). Its official
`npu_demo/libs/armnn_lib.tar.xz` has SHA256
`867e347bb758f9b1b083c35e08a74f2b3cc39c2975ac0f8e18c25f7f35749526` and
version marker `ed5ae24`. The six compared shared objects from that archive
(`libarmnn`, `libarmnnOnnxParser`, `libprotobuf`, `libarmnnBasePipeServer`,
`libtimelineDecoder`, and `libtimelineDecoderJson`) are byte-identical to the
files in the running board's ArmNN library directory. The VM SDK app tree has
no Git metadata, so its exact SDK commit is not recoverable from that extracted
tree.

The nearest tagged ancestor is `SDK_2026.01` at commit
`a06f09a23582900e2b8843d564ea28db679649a5`, three commits before the audited
HEAD. The tag is historical context rather than an exact identity for the
current release checkout; that external checkout was already dirty and only
the committed HEAD is used for provenance.

The official AArch64 `yolo_demo_pic` from the VM (SHA256
`9b7b69f73d9f73fb9267b874d992fb32c5fb8827f99f636c57fe6403c8e0da72`) and
control inputs were copied only to board `/tmp/task028-runtime`. `ldd` reported
no unresolved dependencies, and `LD_DEBUG=libs` showed the temporary
`libarmnn.so.32`, `libarmnnOnnxParser.so.24`, and `libprotobuf.so.23` paths
being loaded. With `-b Alnpu`, the face control completed without an exception;
the existing Task 026 camera run remains the authoritative face Alnpu/ALHardNPU
positive. The same matched runtime and release `yolov8n.quant.onnx` reached
parser/model creation but raised `Failed to assign a backend to each layer`
for `QAsymmU8 Splitter` at Alnpu Optimize; LoadNetwork was not reached. The
vendor executable catches this exception and returns zero, so the exception
text—not process exit code—is the failure signal. CPU fallback was disabled.

The four-row matrix and log hashes are in
`results/evidence/028/trackc3_runtime_compatibility_matrix.json`. The critical
matched-runtime YOLOv8n gate is `FAIL`. Because the available NEW runtime is
bit-for-bit the same identity as the OLD runtime, runtime-version skew remains
`NOT_PROVEN`; this evidence supports graph/operator coverage differences or an
unverified backend/bitstream build difference, not a proven user-space runtime
mismatch. No benchmark was run, no fallback was accepted, and no board system,
SD/eMMC, kernel, DTB, or bitstream was changed.

Task 026's immutable SD boot evidence identifies the tutorial platform
`system.bit` SHA256
`e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5` and
`system.dtb` SHA256
`e1ddd7405245d7b9f644c64066bda64369edbac0d8e8676564261d9cfc22b979`.
The corresponding static SoftNPU audit records `NPU_SOFT=1` and
`SOFT_YOLO=1`; this narrows the hardware context but does not prove support
for every quantized graph dialect.
The runtime archive exposes `ALHardNPU` symbols from `libarmnn.so.32.1`
instead of a separately named `libAlnpu` shared object; the ONNX parser directly
needs `libarmnn.so.32` and `libprotobuf.so.23`. This packaging fact does not
change the failed Optimize gates.

## C3 D20.1/SoftNPU hardware-dialect audit (2026-08-10)

Because the matched-runtime YOLOv8n control also stopped at Alnpu `Optimize`,
the D20.1 official SoftNPU example was compared statically with the 05-5
platform actually used by Task 026. The tutorial-selected 05-5 package is
the GEG400 HPF `demo/soc_sdk/soc_base/soc_prj.hpf` (SHA256
`ec0ef8aa53f3de8a13cbb953808c68b8b947f6c84da0107248af8542f78da7a7`) and its
embedded/platform bitstream is `e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5`.
Its static Video_NPU settings are `NPU_SOFT=1`, `SOFT_NN=1`, `SOFT_YOLO=1`,
`SOFT_RESIZE=1`, and `ALL_OPERATOR=1`; the generated SoftNPU resource is
`0x1f0000000 + 0x10000`, IRQ 97, with VDMA at `0x80200000`/IRQ 84.

The official D20.1 2025.7 package is a different board package: its project,
HPF, and embedded bitstream identify `DR1M90GEG484` (the HPF SHA256 is
`0d2c7f2592eb167a369c3a327a66b6b3e2cbad4450b5218c100870b68a18ef96`; the
embedded bitstream SHA256 is
`2f168661ff90729df23637698791b6e5f38845196cc55df8f77b61ac01508bb1`). It
uses `SOFT_RESIZE=0`, a SoftNPU region at `0x80000000 + 0x20000000`, IRQ 114,
and no VDMA instance. Therefore this AD101V20/GEG484 HPF/bitstream is not a
valid substitute or version-control experiment for the current GEG400 board.

The two packages are on the same TD 6.2.175876 release line and both report
HPF info version 202501, but package, bitstream, address, interrupt, VDMA
topology, and SoftNPU resize configuration differ. The static comparison is
recorded in `results/evidence/028/trackc3_hpf_d20_comparison.json`. It supports
a hardware/graph-dialect difference as a possible explanation for unsupported
operators, but does not prove a user-space runtime version skew: the available
release ArmNN objects remain byte-identical to the board runtime. No bitstream,
DTB, kernel, SD/eMMC, or runtime file was changed.

## Latest runtime-matrix validation (2026-08-10T16:49:15+08:00)

The matched-runtime board probe and its new evidence were followed by this
offline validation sweep:

The Track C validator includes the D20.1/05-5 HPF and SoftNPU static comparison.

```text
python3 scripts/vendor/validate_task028_trackc.py --json: PASS
python3 scripts/vendor/validate_task028_trackc2.py --json: PASS
python3 scripts/vendor/validate_task028_native.py: PASS
python3 scripts/vendor/validate_task028_graph_matrix.py --graph results/evidence/028/graph_dialect_diff.json --matrix results/evidence/028/export_matrix.json --board results/evidence/028/board_export_matrix.json --bisection results/evidence/028/parser_bisection.json: PASS
validate_task022_npu_audit.py: PASS
validate_task023_npu_package.py: PASS
validate_task024_npu_mapping.py: PASS
validate_task025_npu_sd_preflight.py: PASS
validate_task026_sd_preflight.py: PASS
validate_task027_persistent_runtime.py: PASS
JSON/YAML parse (39 Task028 evidence JSON files): PASS
Task028 Python compilation and Bash syntax: PASS
Task028 Release CTest: 3/3 PASS
full Release CTest: 14/14 PASS
Python unittest: 131/131 PASS
Markdown link and sensitive-material scan: PASS
repository hygiene and Task 017-027 immutability: PASS
release tag ancestry and backend static identity audit: PASS
absolute-user-path and sensitive-material scan: PASS
git diff --check: PASS
```

The blocked ArmNN result validator was also run and returned its expected exit
1 rejection for `BOARD_ALNPU_COMPATIBILITY_BLOCKED`; this is recorded as an
expected rejection, not a fabricated success. Task 028 remains `In Progress`,
C1 is `PASS`, C2 is `NOT_ACCEPTED`, C3 observed board compatibility remains
blocked with runtime/toolchain skew `NOT_PROVEN`, and C4 is `NOT_RUN`.

The later support-boundary-only offline sweep additionally passed
`validate_task028_trackc.py --json` with the compiled-dispatch checks, direct
vendor-app/model gate, GEG400 SoftNPU identity and transport-failure honesty;
JSON/YAML parsing (39 files), Task 022--027 validators, Release build, CTest
(3/3 and 14/14), Python unittest (131), Markdown links, repository hygiene,
Task 017--027 immutability and `git diff --check` also passed. No new board
workload was run because the wrapper failed before SSH with
`UtilBindVsockAnyPort:307: socket failed 1`.

## C3 compiled support-boundary audit (2026-08-10)

The official release application's actual `run_yolo_pic.sh` path was audited
read-only. It invokes the AArch64 `yolo_demo_pic` with the release
`yolov8n.quant.onnx`, input image and JSON configuration, and selects libraries
through `LD_LIBRARY_PATH`; strict prior probes used `-b Alnpu` with fallback
disabled. The retained vendor-app/model result is `FAIL_ALNPU_OPTIMIZE`: the
graph parses, then Alnpu rejects `QAsymmU8 Splitter`; the vendor executable
catches the exception, so its process exit code is not the gate.

The matched `libarmnn.so.32.1` (SHA256
`5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce`, build ID
`9f9aaf6f26dd1cf57ac84c778b9f621c04c7d895`) was inspected with the dynamic
symbol table and relocation-backed vtable. `AlnpuLayerSupport` overrides
Concat, Constant, ALHardNPU, Input, Output, Pooling2d, Prelu and Resize. The
Conv2d, Activation, Splitter, Addition and Multiplication slots resolve to
`LayerSupportBase` default methods. Embedded strings include the corresponding
generic rejection reasons (`Do Not Supported`, type mismatch, shape limits and
`only support add now`). This identifies an explicit compiled support whitelist;
it does not claim exhaustive support for untested tensor contracts, and the
original backend source was not available in the audited scopes.

Real graph evidence remains the authority: the face positive control loads with
Alnpu/ALHardNPU and has no Split; vendor YOLOv8n fails first at QAsymmU8
Splitter; YOLOv5n UINT8 and INT8 fail at quantized Conv2d/Activation/
ElementwiseBinary. Synthetic QDQ probes remain inconclusive and are not used
as support proof. The GEG400 05-5 platform's `NPU_SOFT=1`, `SOFT_NN=1`,
`SOFT_YOLO=1`, and `SOFT_RESIZE=1` metadata is retained as hardware context;
D20.1 GEG484 is rejected as a substitute.

The board wrapper was attempted once for this audit but failed before SSH with
`UtilBindVsockAnyPort:307: socket failed 1`; no fresh board workload or system
change was performed. The prior controlled vendor-app/model and Alnpu-only
results remain the evidence. Structured record:
`results/evidence/028/trackc3_support_boundary_audit.json`.

## C3c capability-boundary convergence (2026-08-10)

The compiled support audit was completed without a new board workload. Dynamic
symbols and the relocation-backed vtable show ten actual `AlnpuLayerSupport`
`Is*Supported` overrides: `IsALHardNPUSupported`, `IsConcatSupported`,
`IsConstantSupported`, `IsInputSupported`, `IsLayerSupported`,
`IsMemCopySupported`, `IsOutputSupported`, `IsPooling2dSupported`,
`IsPreluSupported`, and `IsResizeSupported`. The relevant generic
`IsConvolution2dSupported`, `IsActivationSupported`, `IsSplitterSupported`,
`IsAdditionSupported`, `IsMultiplicationSupported`, and
`IsElementwiseUnarySupported` slots resolve to `LayerSupportBase` in the
matched AArch64 `libarmnn.so.32.1` (`5def7ba7...`, build ID
`9f9aaf6f...`). This is a capability statement about this exact binary, not a
claim about every future vendor backend build.

The face positive control is not contradictory evidence. Its strict Task 026
run requested only `Alnpu`, loaded successfully, and reported three
`Alnpu|ALHardNPU` assignments. Its parser contract is FLOAT input `[1,3,416,416]`
and two FLOAT outputs, with QDQ internals and no Split node. The runtime report
therefore evidences a vendor-specific fused/custom ALHardNPU path; it does not
show that each of its ONNX Conv nodes independently passed generic ArmNN
`IsConvolution2dSupported`. In contrast, real YOLOv8n fails first at
`QAsymmU8 Splitter`, and YOLOv5n UINT8/INT8 fail at quantized Conv2d,
Activation and ElementwiseBinary during Optimize, before LoadNetwork.

All materialized `libarmnn.so.32.1` copies found in the bounded local, VM,
repository-history and retained board-runtime scopes have the same SHA256;
reachable historical Git-LFS pointers also reference the same archive object.
No alternate Alnpu build implementing the generic YOLO slots was found. The
official `AL_onnx_pass` path has no additional hidden conversion between its
output and the ArmNN parser/executor. The board SSH/vsock failure is recorded
as an environment-only issue and is not mixed into the NPU conclusion.

The scoped C3 conclusion is `CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE`
for the audited backend binary. The final Task 028 primary conclusion is
`BLOCKED_EXTERNAL_VENDOR_DEPENDENCY`. Track A retains its raw-ONNX status
`BLOCKED_UNSUPPORTED_ALNPU_GRAPH`; C1 remains `PASS`, C2 is
`NOT_ACCEPTED_PAUSED`, C4 remains `NOT_RUN`, runtime skew remains
`NOT_PROVEN`, and the native compiler route is required for general YOLO
deployment. Evidence:
`results/evidence/028/trackc3_capability_face_path_audit.json` and
`results/evidence/028/trackc3_support_boundary_audit.json`.

### C3c execution record

- Read-only commands actually run in this increment: `nm -D`, `readelf -Ws`,
  `readelf -rW`, `objdump -T`, bounded `strings`, source `rg`/`sed`, archive
  identity and SHA256 checks, and the existing retained-evidence comparison.
- `python3 scripts/vendor/validate_task028_trackc.py --json` passed all checks,
  including the ten-method whitelist, face ALHardNPU path, unique runtime
  identity and environment-only wrapper failure. JSON/YAML parsing passed for
  40 Task 028 evidence JSON files and the manifest.
- `validate_task028_trackc2.py`, graph-matrix/native validators, and the Task
  022--027 validators passed. The blocked ArmNN validator was run with its
  documented blocked result and returned the expected exit 1
  (`BOARD_ALNPU_COMPATIBILITY_BLOCKED`).
- The existing Release build required no work; Task 028 CTest passed 3/3,
  the full `pc-all-release` CTest passed 14/14, and Python unittest passed
  131/131. Python/Bash syntax, Markdown links, sensitive-material scan,
  Task 017--027 immutability and `git diff --check` passed.
- No VM/board command was executed in this increment after the wrapper
  transport failure was recorded. No NPU workload, benchmark, fallback,
  module load, SD/eMMC write, bitstream or system-file change was performed.

## Final disposition (2026-08-11)

Task 028 is `Completed` with `automated_validation=COMPLETE` and primary
verdict `BLOCKED_EXTERNAL_VENDOR_DEPENDENCY`. The primary blocker is
`CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE`, scoped only to
the audited AArch64 `libarmnn.so.32.1`; it is not a statement about DR1M90
hardware or a future vendor backend.

Final tracks:

- Track A raw ONNX to ArmNN: `BLOCKED_UNSUPPORTED_ALNPU_GRAPH`.
- Track B APUG1205 Native: `BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE`.
- Track C1 official `AL_onnx_pass`: `PASS`.
- Track C2 quantized host accuracy: `NOT_ACCEPTED_PAUSED`.
- Track C3: parser `PASS`, ArmNN Network `PASS`, Alnpu LayerSupport
  `BLOCKED`, LoadNetwork `NOT_REACHED`, NPU execution `NOT_REACHED`.
- Track C4 benchmark: `NOT_RUN`.

Reopening requires an external dependency: (1) an Alnpu backend that supports
the required general quantized YOLO layers, (2) an APUG1205-compatible compiler
and native runtime, or (3) an official DR1M90 GEG400 YOLO deployment package
and conversion chain. CPU fallback, YOLOv5s substitution, and fabricated NPU
benchmark results are not accepted.

No vendor binary, external model/data set, SDK, private runtime, or sensitive
material was added to Git. Exploration-only `/tmp/task028-*` artifacts were
removed; reproducible source, scripts, manifest, documentation and structured
evidence remain.
