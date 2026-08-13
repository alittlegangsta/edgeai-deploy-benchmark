# Final demo capture guide

Status: `FINAL_DEMO_PACKAGE_READY`

This is a recording package, not a new inference campaign.  The four shots use
the already validated application/evidence and keep Task040's
`results/final/authoritative_results.json` as the only source for formal
benchmark numbers.  The commands below are intentionally marked
`PREPARED_NOT_RUN` in [`release/demo/manifest.json`](../release/demo/manifest.json):
screen recording is a manual operation and this Task does not access the board,
run NPU, rebuild an engine, or rerun a benchmark.

## Recording order (about two minutes)

| Time | Segment | What to show | Voiceover / caption |
|---:|---|---|---|
| 0–20 s | README and architecture | README title, contract and the two Mermaid diagrams | “One YOLOv5n v7.0 contract is carried through shared OpenCV preprocessing, explicit C++ backend adapters, shared decode/NMS and evidence.” |
| 20–48 s | PC TensorRT FP16 video | Annotated video and the on-screen backend/precision overlay | “TensorRT FP16 on the RTX 4060 Ti passes the frozen COCO gate. This is a video integration shot; formal numbers remain in Task040.” |
| 48–78 s | DR1 camera + ncnn EQ INT8 | UVC camera terminal and a short annotated output | “The same C++ pipeline runs the accepted EQ INT8 ncnn configuration on real DR1 ARM Linux. It is bounded camera integration evidence, not a realtime benchmark.” |
| 78–108 s | DR1 vendor face NPU control | Annotated face image plus the assignment log | “The separate vendor face contract reaches `Alnpu | ALHardNPU` with fallback disabled. It is functional NPU control, not YOLOv5n performance.” |
| 108–120 s | Close | Backend matrix, result manifest and handoff status | “Formal results are provenance-linked; custom YOLOv5n NPU remains `WAITING_FOR_VENDOR_INPUT`.” |

Keep the terminal cropped to repository-relative paths.  Do not show SSH keys,
hostnames, IP addresses, private vendor archives, SDK binaries or credentials.

## Segment 1 — README and architecture

Run locally in the repository root:

```bash
sed -n '1,150p' README.md
sed -n '1,150p' docs/PROJECT_PRESENTATION.md
```

Overlay/caption: `YOLOv5n v7.0 | [1,3,640,640] -> [1,25200,85] | C++17`.
Point to the shared `InferenceBackend`, OpenCV acquisition, ORT CPU,
TensorRT/CUDA and ARM ncnn branches, and the explicit no-fallback policy.
The architecture and deployment diagrams are already in the README and
presentation pack; no new diagram is generated here.

## Segment 2 — PC TensorRT FP16 video

This command is the reproducible application command.  It requires the
previously built Release binary, the locally built Task037 FP16 engine and the
frozen sample video; those generated assets remain outside Git.  Replace only
the angle-bracketed paths with the local paths that were used for the approved
run.

```bash
PC_BUILD=<release-build-root>
TRT_ENGINE=<task037-yolov5n-fp16-engine>
VIDEO=data/samples/videos/anlogic_arm_reference.avi
"$PC_BUILD/edgeai_demo" \
  --backend tensorrt --precision fp16 --model "$TRT_ENGINE" \
  --source "$VIDEO" --output-video "$PC_BUILD/demo/trt_fp16.avi" \
  --output-json "$PC_BUILD/demo/trt_fp16.json" \
  --output-codec MJPG --warmup 2
```

The application overlay contains `backend`, `precision`, per-frame inference
milliseconds, pipeline FPS and detection count.  The prepared command is not
a formal benchmark command: the formal TensorRT rows are the Task040 FP32 and
FP16 measurements, while the existing Task039 video file is integration
evidence only.  The formal FP16 result is `TENSORRT_FP16_READY`; CUDA execution
was faster, but the formal pipeline mean did not improve.

Show the re-decodable output only if it is already available in the local
runtime environment.  Do not create a new result or infer a benchmark number
from the video overlay.

## Segment 3 — DR1 UVC camera with ncnn EQ INT8

This is a bounded, manual board shot.  The runtime root, EQ INT8 manifest and
`edgeai_demo` binary are external deployment assets; the placeholders below
must be filled on the approved DR1 deployment without changing the frozen
model contract.

```bash
DR1_ROOT=/root/edgeai/<approved-runtime-root>
LD_LIBRARY_PATH="$DR1_ROOT/lib" "$DR1_ROOT/edgeai_demo" \
  --backend ncnn --precision int8 \
  --model "$DR1_ROOT/model/eq_int8_manifest.json" \
  --camera 0 --max-frames 3 \
  --output-video "$DR1_ROOT/demo/dr_camera_int8.avi" \
  --output-json "$DR1_ROOT/demo/dr_camera_int8.json" \
  --output-codec MJPG --threads 2 --packing 1
```

Required terminal evidence: `backend=ncnn`, `precision=int8`, fallback `none`,
and the JSON output.  The frozen Task039 integration identity is `/dev/video0`,
Sonix USB 2.0 Camera, `uvcvideo`, V4L2 YUYV `640x480@25 FPS`, with
`captured=3`, `processed=3`, `written=3`, synchronous `queue capacity=0` and
an output video that decoded successfully.  Its `0.564866` effective FPS is
integration evidence only; it must not be presented as 25-FPS realtime
processing or as a formal Task040 benchmark.

## Segment 4 — DR1 vendor face Alnpu control

The project-owned image runner is the final interface for this separate face
model.  It forces one backend preference (`Alnpu`) and rejects fallback; it is
not the YOLOv5n adapter.

```bash
FACE_ROOT=/root/edgeai/<face-runtime-root>
LD_LIBRARY_PATH="$FACE_ROOT/armnn_lib/lib:$FACE_ROOT/ffmpeg_opencv4.7.0_aarch64/lib:$FACE_ROOT/lib" \
  "$FACE_ROOT/edgeai_armnn_face_image" \
  --model "$FACE_ROOT/inputs/yolo_face_uint8_15.onnx" \
  --image "$FACE_ROOT/inputs/first_raw.png" \
  --output-json "$FACE_ROOT/demo/face.json" \
  --output-image "$FACE_ROOT/demo/face.png" \
  --warmup 2 --repeats 10
```

Accept the shot only when the captured log contains all of:

```text
Alnpu | ALHardNPU
backend_request=Alnpu fallback_allowed=false
status=PASS_ALNPU_ONLY
```

The recorded model is `yolo_face_uint8_15.onnx` (input uint8 NCHW
`[1,3,416,416]`, two uint8 output heads), Arm NN 32.1.0 and the recorded
`libarmnn.so`/parser hashes in Task036.  The control proves a real
`Alnpu | ALHardNPU` assignment with no CPU fallback; it is functional control
only and must not be compared with YOLOv5n CPU/GPU speed.

## Overlay and evidence contract

For `edgeai_demo`, retain the application overlay fields: `backend`,
`precision`, `inference ms`, `pipeline FPS` and `detections`.  For the face
runner, use the annotated image and the assignment log rather than inventing a
YOLO overlay.  Formal benchmark values shown in narration or slides must be
read from the authoritative manifest, not copied from Task038/039 integration
timings.

The manifest records the exact existing asset hashes.  Suitable small visual
assets are:

- [`results/images/021/first_annotated.png`](../results/images/021/first_annotated.png)
- [`results/images/021/middle_annotated.png`](../results/images/021/middle_annotated.png)
- [`results/images/021/last_annotated.png`](../results/images/021/last_annotated.png)
- [`results/images/036/face_annotated.png`](../results/images/036/face_annotated.png)
- [`results/videos/anlogic_arm_ncnn_reference.avi`](../results/videos/anlogic_arm_ncnn_reference.avi)

Text evidence and provenance:

- [`results/final/authoritative_results.json`](../results/final/authoritative_results.json)
- [`results/final/README_READY_TABLES.md`](../results/final/README_READY_TABLES.md)
- [`docs/FINAL_BENCHMARK_RESULTS.md`](FINAL_BENCHMARK_RESULTS.md)
- [`results/evidence/039/pc_tensorrt_fp16_video.json`](../results/evidence/039/pc_tensorrt_fp16_video.json)
- [`results/evidence/039/dr_camera_ncnn_int8.json`](../results/evidence/039/dr_camera_ncnn_int8.json)
- [`results/evidence/036/vendor_face_flow_audit.json`](../results/evidence/036/vendor_face_flow_audit.json)
- [`results/evidence/036/face_runner_benchmark.json`](../results/evidence/036/face_runner_benchmark.json)
- [`results/evidence/036/board_stdout.log`](../results/evidence/036/board_stdout.log)

## Release checklist

Before recording:

1. Run the Task042 validator and confirm the source-authority SHA256 matches the
   current Task040 manifest.
2. Confirm the four commands are still `PREPARED_NOT_RUN`; supply external
   model/engine/runtime paths without copying them into Git.
3. Confirm the screen recorder output is stored outside the repository until it
   has been manually reviewed.
4. Keep the final frame on the backend matrix and the
   `WAITING_FOR_VENDOR_INPUT` boundary.

After manual recording, review the four shots for readable overlays, correct
backend labels, no personal paths and no implication that custom YOLOv5n ran on
NPU.  The screen recording itself is intentionally not claimed by this task.

## Known boundaries

- Task040 formal tables are the only authoritative benchmark source.
- Task038 unified-app timings and Task039 video/camera timings are integration
  evidence, not formal throughput rows.
- The DR1 camera path is synchronous with `queue capacity=0`; no realtime or
  dropped-frame claim is made beyond the bounded run.
- The vendor face path is `Alnpu | ALHardNPU` functional control only.
- Custom YOLOv5n NPU remains `WAITING_FOR_VENDOR_INPUT`.
- No TensorRT engine, ncnn model, SDK, rootfs, board binary or private key is
  added by this release package.
