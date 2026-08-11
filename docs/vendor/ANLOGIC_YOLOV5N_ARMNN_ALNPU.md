# Anlogic DR1 YOLOv5n ArmNN/Alnpu bring-up

Task 028 uses the frozen repository YOLOv5n v7.0 ONNX graph without changing
the model contract: opset 12, FP32, `[1,3,640,640]` input, `[1,25200,85]`
output, and no graph NMS. The board runner reuses the common letterbox and
YOLO decode/NMS implementation, requests only `Alnpu`, and rejects CPU
fallbacks. The AArch64 runner is built in the isolated VM with Linaro GCC
7.5.0 and the same Arm NN libraries used by the approved Task 026 vendor
runtime.

## Positive control and graph-dialect difference

The approved vendor camera Demo's positive-control model is retained outside
Git at the isolated face-detection input path. Its SHA256 is
`5ed304f1cfd37a6c4ddc789a58a4c98e3472efe31eff62fc9e447163ea60668`.
The static graph audit in `results/evidence/028/graph_dialect_diff.json` shows
that it is not the frozen YOLOv5n model: it is opset 14 with a static
`[1,3,416,416]` FLOAT input, two FLOAT outputs (`[1,18,26,26]` and
`[1,18,13,13]`), 33 `QuantizeLinear` and 59 `DequantizeLinear` nodes, and one
static nearest `Resize`. The frozen YOLOv5n is opset 12 with
`[1,3,640,640] -> [1,25200,85]`, 120 FLOAT initializers, four `Floor` nodes,
two `Shape`/dynamic `Resize` paths, and no Q/DQ nodes. Task 026's real board
evidence independently records the positive control as requested `Alnpu` and
assigned `ALHardNPU`, with CPU fallback disallowed; it is not a substitute
model or a proof that YOLOv5n is supported.

## Controlled export matrix and parser bisection

The frozen TorchScript artifact was exported at opsets 10, 11, and 12 with
static 640x640 inputs and `torch.onnx.do_constant_folding` off/on. All six
entries passed ONNX checker and local ORT raw-output comparison (exact array
equality against the frozen input); their hashes and board results are pinned
in `export_matrix.json` and `board_export_matrix.json`. Every entry reached
the board ArmNN parser but was rejected at a `Floor` node before Alnpu load.
No exporter result was silently downgraded or replaced.

The rebuilt AArch64 runner has a `--parse-only 1` diagnostic mode and accepts a
hash-pinned matrix model. Dependency-sliced minimal probes are recorded in
`parser_bisection.json`. They establish separate real failures: `Floor` and
`Identity` are parser-unsupported; INT64 shape tensors are rejected; FP32
`Resize` and `Conv`/`Reshape` patterns cannot be assigned to Alnpu; and a
minimal QDQ graph reaches `Optimize` and `LoadNetwork` on Alnpu. In contrast,
the larger exact-ORT-equivalent Floor rewrites still exit 139 immediately
after `parser_created`. Board `gdb` and a multiarch VM GDB client were not
available without installing packages, so the bounded dependency-slice
bisection is the reproducible crash localization method; no kernel/NPU dmesg
change occurred.

## What was proven

- The runner is an AArch64 ELF with interpreter
  `/lib/ld-linux-aarch64.so.1`. Board `ldd` resolved every dependency through
  the private Arm NN/OpenCV library paths; no vendor library or ELF is stored
  in Git.
- The board is healthy for this diagnostic: Buildroot 2022.02.6,
  `6.1.111-rt42`, 128 MiB CMA, `cma_mem`, `hard_npu`, and `soft_npu` loaded,
  and all three device nodes present. Probe before/after dmesg snapshots were
  identical and contained no new NPU, DMA, IRQ, oops, or panic error.
- The direct frozen FP32 attempt reached ArmNN OnnxParser and returned the
  real error `Unsupported operation Floor for node '/model.11/Floor'`. The
  runner requested only Alnpu and exited 1; it did not use CpuAcc/CpuRef.

## Bounded model repair audit

The four `Floor` nodes consume exact integer FLOAT constants (40.0 or 80.0)
in dynamic Resize shape paths. Identity, equivalent Constant, removed-node,
and Add-zero graph rewrites all matched the frozen graph exactly in local ORT,
but each crashed in the board parser immediately after `parser_created`.
Two fixed-Resize rewrites reached a deterministic ArmNN tensor-shape error;
an explicit-scales rewrite again crashed in the parser. These are parser
compatibility results, not kernel or NPU-driver faults.

A reproducible Conv-only QDQ conversion using ONNX Runtime 1.18.1 and ONNX
1.16.2 was also tested only after the FP32 failure. The resulting graph keeps
the required tensor shapes but its local ORT output changes the detection set
(5 golden detections to 4) and has a raw maximum absolute difference of
`308.5351867675781`; it therefore fails the frozen correctness gate. The
board parser also exits 139 before network load. No quantized benchmark was
run.

## Track C: official `AL_onnx_pass` ONNX pipeline

The official `dr1m90_npu` `npu_demo/scripts/AL_onnx_pass.py` is a third,
distinct path and is now the active Task 028 investigation. The source is the
dirty `release` checkout at commit
`199ef4d71f453bb9a000102ff39def09c4cf73f9`; no tag points at that checkout.
The script imports `onnxsim`, `check_onnx_model` (which imports `onnx_tool`),
`onnx_infer_shape`, `extract_model`, `split_convFC`, and `run_quant`. Its
sequence is:

```text
onnx.load
→ onnxsim.simplify
→ fixed-shape inference
→ YOLO Detect cropping
→ Conv/FC split
→ opset conversion
→ onnx_tool checker
→ ONNX Runtime static QDQ quantization
```

This is an ArmNN/ONNX preparation path, not the APUG1205 native
`convert_tool`/`al_ai_flow` runtime. The C++ demo links `armnn`,
`armnnOnnxParser`, `protobuf` and `fmt`; `executor.cpp` calls ArmNN
`OnnxParser`, `Optimize` and `LoadNetwork`, and uses CMA buffers. It has no
`npu_runtime`, `rt.bin` or `weight.bin` dependency. The demo's default backend
string includes `Alnpu,CpuAcc,CpuRef`, so a strict Task 028 run must continue
to request only `Alnpu` and reject fallback.

The unmodified official entry first stopped in the project venv with the real
`ModuleNotFoundError: No module named 'onnxsim'`; that venv also lacked
`onnx_tool`. A separate ext4 venv was then populated from the unchanged vendor
requirements. `pip check` and all imports pass, and the unchanged entry now
exits 0, producing the official Detect-cropped FP32 graph and a uint8 QDQ
artifact. The dependency freeze is in `trackc_environment.json`; command and
artifact hashes are in `trackc_official_smoke.json`.

The frozen FP32 host reference independently passes the existing golden (five
detections, `[1,25200,85]` FLOAT output, minimum IoU 1.0 and zero confidence
delta). The official simplified FP32 head model returns five matching classes
and confidences using `CPUExecutionProvider`; its integer box representation has
minimum comparison IoU `0.95506547868033`. The official uint8 QDQ model also
returns five detections and matching classes, but its minimum IoU is
`0.8421554845490358` and maximum confidence delta is
`0.09312496031303408`, so the strict host golden gate fails. A deterministic
500-image calibration smoke derived from 27 local source images also fails
(minimum IoU `0.8891731303877853`, maximum confidence delta
`0.11366653714614872`). An int8 probe is invalid under opset 12 because
`DequantizeLinear(axis=...)` fails ONNX checker and ORT. No board execution or
benchmark is permitted before host semantic closure.

A one-image, diagnostic-only QDQ activation probe localized the largest first
relative errors at `/model.9`'s three `MaxPool` outputs and
`Concat_output_0`, followed by the two `Resize` outputs. This is consistent
with the vendor script README's warning that YOLO quantization can lose
accuracy when `Concat` inputs have different scales. The probe did not modify
the vendor graph or promote a manual quantization strategy; exact values and
provenance are recorded in `results/evidence/028/trackc_official_smoke.json`.

The original graph has four `Floor`, two `Shape`, zero `Gather`, and two dynamic
`Resize` nodes. The official Detect crop removes `Floor` and `Shape` and emits
the three-head contract; uint8 QDQ adds 200 `QuantizeLinear` and 320
`DequantizeLinear` nodes. The exact checker identifies `Add`, `MaxPool`,
`Concat`, and `Resize` as SoftNPU operators and retains three first-convolution
acceleration warnings. These are host conversion facts, not board execution
evidence.

## Track C2: opset13/14 host candidates

The frozen opset12 FP32 graph remains the baseline. Using the same YOLOv5n
v7.0 TorchScript and static 640 export, Track C2 added opset13 and opset14
with constant folding off/on. All four exports pass ONNX checker and have
exact ORT raw-output equality with the frozen `[1,25200,85]` output. The
unchanged official `AL_onnx_pass.py` produces checker/ORT-valid uint8 and int8
QDQ graphs for all four; the int8 axis failure therefore belongs to the
opset12 graph dialect and is not evidence of Alnpu execution.

Calibration and held-out evaluation are hash-disjoint. The held-out list has
eight local images and no COCO or other ground truth annotations are available,
so true precision, recall, mAP50 and mAP50-95 are `NOT_COMPUTABLE`. The
teacher-relative proxies are diagnostic only. With the independent gate
(exact count and class-multiset agreement, all IoU >= 0.99, confidence delta
<= 0.01 and proxy values >= 0.99), both candidates fail:

| candidate | count agreement | class agreement | min IoU@0.50 | max confidence delta | proxy mAP50 | proxy mAP50-95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| opset14 uint8 | 87.5% | 87.5% | 0.9194650385 | 0.1588631272 | 0.8333333333 | 0.7633333333 |
| opset14 int8 | 100% | 87.5% | 0.6684800835 | 0.2138248384 | 0.6944444444 | 0.4666666667 |

The three `/model.9` MaxPool branch scales are equal per quantization type
(uint8 `0.02454817108809948`, int8 `0.04709700495004654`); no literal branch
scale mismatch was observed. Material range/QDQ errors remain at MaxPool,
Concat and Resize. This diagnostic did not modify the graph. Evidence and
the independent checker are `trackc2_export_matrix.json`,
`trackc2_official_smoke.json`, `trackc2_heldout_accuracy.json`,
`trackc2_qdq_ranges.json`, and `validate_task028_trackc2.py`.

## Current disposition

Task 028 remains `In Progress`. Track A is blocked by the fixed vendor ArmNN
OnnxParser/Alnpu graph support, specifically the frozen `Floor`/shape dialect
and reproducible parser failures for bounded repairs:
`BLOCKED_UNSUPPORTED_ALNPU_GRAPH`. Track B remains the independent APUG1205
native path with status `BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE`.
Track C is the current primary path and is split into four states: C1 official
`AL_onnx_pass=PASS`; C2 quantized host accuracy=`NOT_ACCEPTED`; C3 board
compatibility=`BLOCKED_UNSUPPORTED_ALNPU_QUANTIZED_LAYERS`; and C4
benchmark=`NOT_RUN`. The generated uint8 QDQ model fails the independent host
semantic gate, and the best opset14 uint8 candidate was rejected by Alnpu-only
optimization on the real board before `LoadNetwork`.

Track C2 improves graph validity but does not close accuracy: opset13/14 int8
graphs pass host checker/ORT, while both uint8 and int8 fail the separate
held-out task-level quantization gate. C3's one-shot board smoke used only
`/tmp`, requested `Alnpu` with CPU fallback disabled, and produced the real
errors `QAsymmU8 Conv2d`, `Activation`, and `ElementwiseBinary` unsupported on
Alnpu. No board raw head or detection comparison was possible, and no
benchmark is claimed.

The multi-output runner used for C3 was rebuilt as AArch64 ELF SHA256
`c6c55b1df88d89a4507a2526f2198a7cbddb2ccc7bf8e881cf38d40e3f1a2d02`. Its
temporary raw-head capture is diagnostic only. Host ORT reference heads for
the opset14 uint8 candidate are recorded without embedding binary tensors in
Git. The vendor preprocessing audit is exact on the frozen 1280x960 image
(max absolute delta 0), but vendor calibration uses `scaleup=False` while the
project baseline permits scale-up.

The requested YOLOv5s positive-control assets remain unavailable in the
bounded local scopes. The release `run_yolo_pic.sh` actually invokes the
separate `yolov8n.quant.onnx` ArmNN demo; this is not a YOLOv5n or YOLOv5s
positive control. The existing Python test summary's 43 is a test count, not
a 43-image golden set, so no 43-image regression is claimed.

APUG1205 (document SHA256
`54a25d9a5dc59b21e7f7253bc72adeeb2c8b3a4bc04c30bea81463026ef7c1f2`) describes
`convert_tool` -> `.tmfile` -> `al_ai_flow` -> `rt.bin`/`weight.bin`, followed
by `npu_c_api.h` and `libnpu_runtime.a`. A bounded read-only audit of the
approved local资料 roots, `03_demo`, all reachable `dr1m90_npu` and SDK refs and
tags, `toolchains`, the curated knowledge base, and VM vendor/SDK/workspace
roots found no compiler image or release, `convert_tool`, `al_ai_flow`,
`net_config_yolov5s.json`, `yolov5s_320_sigmoid.onnx`, `.tmfile`, `rt.bin`,
`weight.bin`, `libnpu_runtime*`, or `npu_c_api.h`. The VM also has no Docker,
Podman or Nerdctl executable or known image cache in the audited roots.

The documented YOLOv5s positive path was not executed, no native YOLOv5n
runner was built, and no benchmark was recorded. The ArmNN/ONNX demo assets
are an independent path and cannot substitute for the native runtime. The
05-5 tutorial platform bitstream's static metadata does confirm
`NPU_SOFT=1`, `SOFT_NN=1`, `SOFT_YOLO=1`, and `SOFT_RESIZE=1`; its bitstream SHA256
is `e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5`.
That is hardware-side evidence only, not compiler/runtime proof.

The exact native audit and non-execution record are in
`results/evidence/028/native_toolchain_audit.json`,
`results/evidence/028/native_yolov5s_positive_path.json`, and
`results/evidence/028/softnpu_ip_audit.json`. The minimum next input is a
versioned vendor compiler release/container with matching native runtime
headers/library and the APUG1205 YOLOv5s positive-control assets. A different
YOLO version, silent CPU backend, board-system change, or SD/eMMC update is
not an acceptable workaround.

## C3 runtime/toolchain compatibility audit

The release checkout is `dr1m90_npu` branch `release` at commit
`199ef4d71f453bb9a000102ff39def09c4cf73f9` (no tag points at that commit).
Its nearest tagged ancestor is `SDK_2026.01` at
`a06f09a23582900e2b8843d564ea28db679649a5`, three commits behind HEAD; this
does not establish that the current HEAD is an SDK_2026.01 release build.
Its ArmNN archive is `npu_demo/libs/armnn_lib.tar.xz`, SHA256
`867e347bb758f9b1b083c35e08a74f2b3cc39c2975ac0f8e18c25f7f35749526`, with
version marker `ed5ae24`. The six compared shared objects from that archive
are byte-identical to the corresponding files already loaded from the board's
`/opt/face_detection/runtime-root/armnn_lib/lib` directory:
`libarmnn.so.32.1`, `libarmnnOnnxParser.so.24.6`, `libprotobuf.so.23.0.0`,
`libarmnnBasePipeServer.so.32.1`, `libtimelineDecoder.so.32.1`, and
`libtimelineDecoderJson.so.32.1`. This makes the available release copy a
matched identity copy, not an independent NEW runtime version. The VM SDK
tree has no Git metadata, so its exact SDK commit cannot be recovered from the
published extracted tree.
Its `app/npu/build.sh` (SHA256
`252854d2b571c91cfa57ae578fb762b92721e5b267aae659ff6bcda211efde45`) differs
from the dirty release checkout script (SHA256
`d14a0df07f8e92780304ae448d3ac2ecb7a4eaa02515c4af4bde64f6ef62ef53`) in
relative toolchain path, pre-expanded archive handling, and an additional
`libprotoc` copy list. Those are packaging/build-script differences; the six
runtime objects used for the board comparison remain exact matches.

For a non-persistent check, the official AArch64 `yolo_demo_pic` (SHA256
`9b7b69f73d9f73fb9267b874d992fb32c5fb8827f99f636c57fe6403c8e0da72`) and
models were copied only to board `/tmp/task028-runtime`. `ldd` reported no
`not found` entries, and `LD_DEBUG=libs` showed the candidate paths
`/tmp/task028-runtime/libarmnn.so.32`,
`/tmp/task028-runtime/libarmnnOnnxParser.so.24`, and
`/tmp/task028-runtime/libprotobuf.so.23` being loaded. With `-b Alnpu`, the
face positive control completed parser/Optimize/LoadNetwork without an
exception (the repository reference image contains no face); the successful
Task 026 camera record remains the authoritative Alnpu/ALHardNPU positive
result. With the same matched runtime and the release `yolov8n.quant.onnx`
(SHA256 `5fa7e8ee047a118c500736cf6b1f24bf1d4ec5120661b10ba661e662f9371d96`),
the parser created the network but Alnpu Optimize raised
`Failed to assign a backend to each layer` for `QAsymmU8 Splitter`; LoadNetwork
was not reached. The vendor executable catches this exception and returns
zero, so the exception text—not its process exit code—is the compatibility
result. CPU fallback was not allowed.

The four-row matrix is in
`results/evidence/028/trackc3_runtime_compatibility_matrix.json`. Its critical
`NEW_MATCHED_RUNTIME_COPY + YOLOv8n` gate fails. Therefore runtime/toolchain
version skew is **not proven** and no alternative runtime was installed or
selected. The current evidence supports graph/operator coverage differences
or an as-yet unverified backend/bitstream build difference. Task 028 remains
In Progress, C1 remains PASS, C2 remains NOT_ACCEPTED, C3 remains blocked, and
C4 benchmark remains NOT_RUN. No SD/eMMC, kernel, DTB, bitstream, or system
file was modified.

## C3 D20.1 versus 05-5 SoftNPU package audit

The matched-runtime YOLOv8n failure prompted a static hardware-package
comparison; it did not authorize changing the current bitstream. The
tutorial-selected 05-5 package is the DR1M90GEG400 HPF
`demo/soc_sdk/soc_base/soc_prj.hpf` (SHA256
`ec0ef8aa53f3de8a13cbb953808c68b8b947f6c84da0107248af8542f78da7a7`) with
embedded/platform `system.bit` SHA256
`e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5`. Its
Video_NPU metadata enables `NPU_SOFT=1`, `SOFT_NN=1`, `SOFT_YOLO=1`,
`SOFT_RESIZE=1`, and `ALL_OPERATOR=1`; the generated SoftNPU resource is
`0x1f0000000`/IRQ 97 and the same package has a VDMA at `0x80200000`/IRQ 84.

The official D20.1 2025.7 example is not the same board package. Its HPF and
embedded bitstream identify `DR1M90GEG484`, with HPF SHA256
`0d2c7f2592eb167a369c3a327a66b6b3e2cbad4450b5218c100870b68a18ef96` and
embedded bitstream SHA256
`2f168661ff90729df23637698791b6e5f38845196cc55df8f77b61ac01508bb1`. It
uses `SOFT_RESIZE=0`, SoftNPU `0x80000000`/IRQ 114, and no VDMA instance.
Although both packages report TD 6.2.175876 and HPF info version 202501, the
package, bitstream, address, interrupt, topology, and SoftNPU configuration
differ. The AD101V20/GEG484 package is therefore rejected as a direct control
or substitute for the current GEG400 platform.

This comparison narrows the remaining unknown to graph/operator coverage or
an unverified backend/bitstream correspondence. It does not prove a runtime
version skew: the available release ArmNN objects are byte-identical to the
board runtime. Evidence: `results/evidence/028/trackc3_hpf_d20_comparison.json`.

## C3 INT8 and control-model compatibility follow-up

The best opset14 INT8 AL_onnx_pass candidate (`8ff448f1fd250a198b0a4a44a1eca9d09c50a68a4da459788960282ba98c3ad9`)
was copied only to board `/tmp`. With `Alnpu` as the sole requested backend,
ArmNN created and parsed the network, then failed at Optimize on `QSymmS8`
`Conv2d`, `Activation`, and `ElementwiseBinary`; `LoadNetwork` was not
reached. CPU fallback was disabled and no inference or benchmark was run.

A 12-entry static-640 synthetic QDQ matrix for Conv2d, Activation, Add, Mul,
Concat and Resize (UINT8/INT8) passed ONNX checker locally, but every entry
segfaulted immediately after `parser_created` on the board. The matrix is
therefore `PARSER_DIALECT_INCONCLUSIVE`, not per-operator support evidence;
the full-model UINT8 and INT8 failures above remain authoritative. See
`trackc3_quant_operator_probe_matrix.json`.

The release YOLOv8n quantized control (`5fa7e8ee047a118c500736cf6b1f24bf1d4ec5120661b10ba661e662f9371d96`)
was also parser/Optimize/LoadNetwork-probed without inference. It failed at
Optimize on `QAsymmU8 Splitter`. The already successful face positive control
has no Split operator, so the observed controls demonstrate graph/operator
coverage differences rather than proving runtime/toolchain version skew. The
board runtime identity remains ArmNN `v32.1.0`, version marker `ed5ae24`,
`libarmnn.so.32.1` SHA
`5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce`, and
`libarmnnOnnxParser.so.24.6` SHA
`dcb43bc092ec283364806e563fa6aa8d2404eb7c005db44081821da405c5ce99`.
The Task 026 SD boot evidence also identifies the tutorial platform
`system.bit` (`e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5`)
and `system.dtb` (`e1ddd7405245d7b9f644c64066bda64369edbac0d8e8676564261d9cfc22b979`);
the audited SoftNPU metadata has `NPU_SOFT=1` and `SOFT_YOLO=1`. This is
positive hardware-context evidence, not proof that every quantized graph
dialect is supported by the loaded backend.

The runtime archive has no separately named `libAlnpu` shared object; static
inspection finds `ALHardNPU` support symbols in `libarmnn.so.32.1`, while the
ONNX parser's direct runtime dependencies are `libarmnn.so.32` and
`libprotobuf.so.23`. This identifies the backend packaging layout but does not
change the failed model Optimize gates.

The source/runtime and static control records are
`trackc3_board_int8_smoke.json`, `trackc3_runtime_version_audit.json`, and
`trackc3_model_control_comparison.json`. Task 028 remains In Progress with
C1 PASS, C2 NOT_ACCEPTED, C3 BLOCKED_UNSUPPORTED_ALNPU_QUANTIZED_LAYERS and
C4 NOT_RUN.

## C3 compiled support boundary

The matched AArch64 `libarmnn.so.32.1` was inspected with `readelf -rW`,
`objdump -T`, `nm` and bounded `strings` (SHA256
`5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce`, build ID
`9f9aaf6f26dd1cf57ac84c778b9f621c04c7d895`). Its `AlnpuLayerSupport` vtable
overrides Concat, Constant, ALHardNPU, Input, Output, Pooling2d, Prelu and
Resize. The Conv2d, Activation, Splitter, Addition and Multiplication slots
resolve to `LayerSupportBase` implementations; the binary contains the generic
`Do Not Supported`, type-mismatch and `only support add now` rejection reasons.
This is a compiled dispatch/whitelist observation, not a claim that every
possible tensor shape or dtype was exhaustively tested. No backend source was
available in the audited SDK scopes.

The retained real-graph evidence is consistent with that boundary: the
official `yolo_demo_pic` plus vendor `yolov8n.quant.onnx` reaches parser and
model creation but fails Alnpu Optimize first on `QAsymmU8 Splitter`; the
opset14 YOLOv5n UINT8 and INT8 graphs fail at quantized Conv2d/Activation/
ElementwiseBinary (`QAsymmU8` and `QSymmS8`, respectively). The face positive
control loads with Alnpu/ALHardNPU and has no Split node. The 12 synthetic QDQ
probes remain `PARSER_DIALECT_INCONCLUSIVE` and are not used to define support.

The 05-5 GEG400 platform remains the only applicable hardware context in this
record: `system.bit` SHA256 `e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5`,
HPF SHA256 `ec0ef8aa53f3de8a13cbb953808c68b8b947f6c84da0107248af8542f78da7a7`,
and static `NPU_SOFT=1`, `SOFT_NN=1`, `SOFT_YOLO=1`, `SOFT_RESIZE=1` metadata.
The D20.1 GEG484 package is not a substitute. A fresh board replay was not
possible in this turn because the SSH/vsock wrapper failed before connection
with `UtilBindVsockAnyPort:307: socket failed 1`; the real vendor-app and
Alnpu-only results above are retained from the earlier controlled probes.

Structured evidence: `results/evidence/028/trackc3_support_boundary_audit.json`.

## C3c capability-boundary conclusion

The completed binary audit found ten actual `AlnpuLayerSupport` overrides:
`IsALHardNPUSupported`, `IsConcatSupported`, `IsConstantSupported`,
`IsInputSupported`, `IsLayerSupported`, `IsMemCopySupported`,
`IsOutputSupported`, `IsPooling2dSupported`, `IsPreluSupported`, and
`IsResizeSupported`. In the same matched `libarmnn.so.32.1`, the generic
Conv2d, Activation, Splitter, Addition, Multiplication and ElementwiseUnary
vtable slots resolve to `LayerSupportBase` methods. This is a scoped result for
the exact AArch64 binary (`5def7ba7...`, build ID `9f9aaf6f...`), not a claim
about a backend build that was not found.

The face positive control passes because its strict run reports three
`Alnpu|ALHardNPU` workloads with no CPU fallback, after the parser/Optimize/
LoadNetwork sequence. Its FLOAT input/output contract and QDQ internals are
recorded in the evidence, and it has no Split node. The runtime report is
evidence of a vendor-specific fused/custom ALHardNPU path; it must not be
interpreted as generic ArmNN Conv2d support for all ONNX Conv nodes. Real
YOLOv8n fails at QAsymmU8 Splitter and YOLOv5n UINT8/INT8 fail at quantized
Conv2d/Activation/ElementwiseBinary during Optimize.

All available materialized ArmNN library identities in the audited local,
repository-history, VM and retained board-runtime scopes are byte-identical;
no alternate backend build with generic YOLO-layer overrides was found.
`AL_onnx_pass` emits the graph consumed by the ArmNN parser and executor, with
no additional hidden native-runtime conversion step identified in source.
The wrapper error `UtilBindVsockAnyPort:307: socket failed 1` is recorded as an
environment-only transport issue, not as NPU evidence.

Accordingly, Track A and C3 converge to
`CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE` for this compiled
backend. C1 remains PASS, C2 remains NOT_ACCEPTED, C4 remains NOT_RUN, and
runtime skew remains NOT_PROVEN. Full structured evidence is in
`results/evidence/028/trackc3_capability_face_path_audit.json`.

## Task 028 final disposition (2026-08-11)

Task 028 is `Completed` with primary verdict
`BLOCKED_EXTERNAL_VENDOR_DEPENDENCY`. The primary blocker is the scoped
`CURRENT_ARMNN_ALNPU_BACKEND_NOT_GENERAL_YOLO_GRAPH_CAPABLE` result for the
audited AArch64 `libarmnn.so.32.1`; this must not be generalized to DR1M90
hardware or future vendor backend builds.

Track A remains `BLOCKED_UNSUPPORTED_ALNPU_GRAPH`; Track B remains
`BLOCKED_VENDOR_NATIVE_TOOLCHAIN_UNAVAILABLE`; C1 is `PASS`; C2 is
`NOT_ACCEPTED_PAUSED`; C3 reaches Parser and ArmNN Network successfully but
is blocked by Alnpu LayerSupport before LoadNetwork, so NPU execution is
`NOT_REACHED`; C4 is `NOT_RUN`. CPU fallback was never accepted and no NPU
benchmark was fabricated.

Reopening requires one of: a generic-quantized-layer Alnpu backend, an
APUG1205-compatible compiler/native runtime, or an official DR1M90 GEG400 YOLO
deployment/conversion package. `AL_onnx_pass` and YOLOv5s substitution are not
solutions to the recorded blocker.
