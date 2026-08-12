# DR1 vendor face NPU closed loop (Task 036)

Task 036 closes a project-owned, image-based functional loop for the already
validated Anlogic face control. It does not reopen the frozen YOLOv5n NPU
investigation: custom YOLOv5n remains `WAITING_FOR_VENDOR_INPUT` under Tasks
028/029/032.

## Flow and identity

The external model is Anlogic `dr1m90_npu/face_detection`'s
`yolo_face_uint8_15.onnx`:

- SHA256: `5ed304f1cfd37a6c4ddc789a58a4c98e3472efe31eff62fc9e447163ea60668`
- input: quantized `uint8` NCHW `[1,3,416,416]`, scale
  `0.003921568859368563`, zero-point `0`;
- outputs: `uint8` `[1,18,26,26]` and `[1,18,13,13]` heads (strides 16 and 32);
- one class (`face`), confidence threshold `0.35`, NMS IoU `0.45`.

The project executable is `edgeai_armnn_face_image`. It is built as an AArch64
C++17 Release target against the existing ArmNN 32.1/OnnxParser and OpenCV
deployment libraries. Its board identity is recorded in
`results/evidence/036/artifact_manifest.json`; the ELF SHA256 is
`9306d119e556ca15f166d993356590e155ce537f8898aa6af85c51f6d95b184e`.

The implementation is deliberately small and reuses the project's ArmNN
adapter, tensor contract and visualization modules:

```text
image -> OpenCV BGR decode
      -> direct 416x416 resize (no letterbox), BGR->RGB, HWC->NCHW, /255
      -> ArmNN ONNX parser -> Optimize([Alnpu]) -> LoadNetwork
      -> CMA buffers -> EnqueueWorkload
      -> dequantized heads -> sigmoid/anchor decode -> confidence filter -> NMS
      -> JSON detections + annotated PNG
```

The vendor source audit and source-file hashes are retained in
`results/evidence/036/vendor_face_flow_audit.json`. The vendor camera program
uses a broader backend preference list; this project runner passes only
`Alnpu` and fails if it is not registered or if LoadNetwork does not succeed.

## Standalone board command

With the existing Task 026/027 runtime root and private library paths:

```sh
export LD_LIBRARY_PATH=/opt/face_detection/runtime-root/armnn_lib/lib:/opt/face_detection/runtime-root/ffmpeg_opencv4.7.0_aarch64/lib:/opt/face_detection/runtime-root/lib:$LD_LIBRARY_PATH
/tmp/task036/edgeai_armnn_face_image \
  --model /opt/face_detection/runtime-root/inputs/yolo_face_uint8_15.onnx \
  --image /tmp/task036/first_raw.png \
  --output-json /tmp/task036/result.json \
  --output-image /tmp/task036/annotated.png \
  --warmup 1 --repeats 3
```

The command is a temporary `/tmp` deployment; it does not modify eMMC, SD,
boot files, kernel, DTB, bitstream or persistent rootfs content. The runner
prints an explicit no-fallback policy and emits structured status.

## Backend proof and result evidence

The captured ArmNN process log contains `Alnpu | ALHardNPU` assignments, while
the runner stderr records `backend_request=Alnpu fallback_allowed=false`,
successful Optimize/Load/Enqueue stages, and `PASS_ALNPU_ONLY`. The structured
validator checks these independent signals and rejects a CPU fallback claim.
The board read-only state also records loaded `cma_mem`, `hard_npu`, and
`soft_npu`, all three device nodes, platform bindings, and 128 MiB CMA in
`results/evidence/036/board_runtime_state.json`.

Representative output is retained as
`results/images/036/face_annotated.png` and
`results/images/036/face_annotated_benchmark.png`.

## Functional-control benchmark

The bounded diagnostic used two warmups and ten measured image repeats on one
board image. It is not a YOLOv5n comparison and is not published as a general
NPU performance benchmark:

| stage | mean (ms) | P50 (ms) | P95 (ms) |
| --- | ---: | ---: | ---: |
| preprocess | 14.395077 | 14.177220 | 14.664900 |
| inference | 50.3471437 | 50.362290 | 50.421541 |
| postprocess | 1.236873 | 1.228740 | 1.270590 |
| end-to-end | 65.9801407 | 65.824171 | 66.289740 |

The derived diagnostic FPS is `15.15607559`, Peak RSS is `38056 KiB`, and the
process reported two threads. Per-sample process CPU time is retained in the
JSON; a host CPU-utilization percentage is not claimed. The image produced two
finite `face` detections and all raw output values were finite.

## Reproduction and scope

Run `python3 scripts/vendor/validate_task036_npu_face.py`; it validates the
model/runtime/tensor identities, captured ALHardNPU assignment, no-fallback
status, board device evidence, derived artifact hashes and the scope boundary.
The complete report is in `results/evidence/036/face_runner_benchmark.json`.

This is a closed functional deployment for the vendor face model. It does not
claim YOLOv5n NPU compatibility, does not compare face performance with the
ARM ncnn YOLOv5n CPU path, and does not change the vendor handoff state.
