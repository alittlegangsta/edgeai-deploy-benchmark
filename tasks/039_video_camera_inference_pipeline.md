# Task 039 — Video & Camera Inference Pipeline

Status: Completed
Dependency: Task 038
Recommended branch: `dev`

## Objective

Extend the unified `edgeai_demo` C++ application from single-image inference to
video-file and camera sources while reusing the existing `InferenceBackend`,
shared preprocessing/postprocessing and visualization. This task records
functional integration evidence only; cross-platform performance is reserved for
Task 040.

## Acceptance criteria

1. `edgeai_demo` accepts an image, video file, or camera source explicitly and
   rejects ambiguous source selections.
2. Video/camera frames use the same backend factory and YOLOv5n contract as the
   image path; no backend-specific video pipeline or implicit fallback is added.
3. Video output can be written with `VideoWriter` and reopened for frame/geometry
   validation.
4. Structured JSON records source metadata, captured/processed/dropped frames,
   stage timings, effective processing FPS, backend identity and detections.
5. The synchronous pipeline has explicit bounded semantics (`dropped_frames=0`)
   and does not accumulate an unbounded queue.
6. PC TensorRT FP16 video integration and the available ncnn/ORT video paths run
   with real output evidence; camera validation is attempted only where a real
   device is available.
7. Release CMake/CTest, focused tests, full Python tests, evidence validation,
   syntax/link/hygiene checks and `git diff --check` pass.

## Allowed files

`TASKS.md`, `README.md`, `cpp/CMakeLists.txt`, `cpp/apps/edgeai_demo.cpp`,
`cpp/src/backends/ncnn_detector.cpp`,
`scripts/validate_task039_video_camera.py`,
`tests/python/test_task039_video_camera.py`,
`tasks/039_video_camera_inference_pipeline.md`, `results/evidence/039/`.

## Forbidden changes

Do not modify Task 001–038 evidence, frozen model/preprocess/postprocess/Golden
contracts, backend algorithms or performance behavior, TensorRT engines, ncnn/ORT SDKs or
DR1 runtime files. Do not add implicit fallback, an unbounded queue, a new
benchmark protocol, or network/download behavior. Do not access or modify board
storage. Do not commit or push unless explicitly authorized.

## Execution record

Start: 2026-08-12 Asia/Shanghai

- Starting branch: `dev`; starting worktree was clean after Task 038.
- Task 038 backend adapters and the shared image contract were read before
  implementation.
- Initial implementation and all commands/results will be recorded below.

## Execution record

- Resumed: 2026-08-12 Asia/Shanghai; branch `dev`; the user corrected the
  interim status to `VIDEO_PIPELINE_READY` / `CAMERA_HARDWARE_VALIDATION_PENDING`.
  The PC/video evidence below remains frozen; this continuation adds only a
  bounded real-board USB-camera validation and must not alter Tasks 001–038.
- The accepted Task035 EQ artifact retains a FP32 tensor interface while its
  weights are quantized. The unified ncnn manifest loader previously rejected
  the explicit external `INT8` precision identity before model loading. A
  one-condition compatibility fix now accepts `FP32` or `INT8` manifest
  precision; no layer, option, threshold, tensor or performance behavior was
  changed. This is required for the requested explicit `--precision int8`
  camera path.
- Extended `cpp/apps/edgeai_demo.cpp` with explicit `--source`/`--camera`
  selection, `--output-video`, codec selection, bounded camera limits and a
  shared dynamic frame loop. Image inference remains on the original path;
  video and camera use the same `InferenceBackend` factory, preprocessing,
  decode/NMS and visualization. The dynamic path is synchronous and serialized,
  so its queue capacity is explicitly zero and `dropped_frames=0`; no unbounded
  queue was introduced.
- Release builds succeeded in `/tmp/task039-cmake` (ORT+ncnn+video) and
  `/tmp/task039-trt-cmake` (ORT+ncnn+TensorRT+video). CTest passed `16/16` in
  both configurations.
- The lossless repository FFV1 source
  `data/samples/videos/anlogic_arm_reference.avi` was used for the PC matrix:
  1280x960, 5 FPS, 30 frames, SHA256
  `3953653b6364a844e829be68df76fce8ce673add5c4bfaf9176c5fb205e5da49`.
  ORT FP32, ncnn FP32 and TensorRT FP16 each decoded, processed and wrote
  `30/30` frames with zero drops and five detections per frame. Their structured
  run evidence is in `results/evidence/039/` and output AVI hashes are recorded
  in `validation.json`; generated videos remain outside Git.
- TensorRT FP16 was executed with the approved GPU permission after the
  restricted run returned `cudaGetDevice failed: CUDA driver version is
  insufficient for CUDA runtime version`. The accepted Task037 COCO gate and
  strict single-image diagnostic remain separate; the video record intentionally
  uses `first_frame_golden=NOT_REQUESTED` rather than relabeling the known strict
  diagnostic as a pass.
- WSL had no `/dev/video*` or `/sys/class/video4linux` nodes. The board SSH
  wrapper returned `UtilBindVsockAnyPort:309: socket failed 1`, so no DR1 camera
  or ARM ncnn INT8 run was claimed. `validation.json` records this as an explicit
  infrastructure-limited camera probe and does not infer board camera state.
- Added README dynamic-input usage and the offline validator plus three focused
  tests. Task039 validator passed; focused tests passed `3/3`; full `.venv`
  Python suite passed `163/163`; JSON parsing, Python syntax, Markdown links,
  sensitive-material scan and `git diff --check` passed. Task030/033/034/035/037
  validators also passed, and no Task001–038 evidence was modified.
- The generated output videos are not checked in: their source paths, sizes,
  SHA256 and retention-outside-Git policy are frozen in
  `results/evidence/039/validation.json`.

## Execution record — DR1 camera validation

- Resumed: 2026-08-12 Asia/Shanghai; branch `dev`; the final P0 camera
  validation was performed without reopening backend tuning. The PC video
  evidence above remained frozen and no Task 001–038 evidence was changed.
- The Windows/vsock board wrapper remained unavailable with
  `UtilBindVsockAnyPort:309: socket failed 1`. A temporary-copy native SSH key
  path reached `root@192.168.50.2` over the configured DR1 network; the wrapper
  and board persistent storage were not modified. The VM was not used for this
  run.
- Read-only board enumeration identified `/dev/video0` as the capture node and
  `/dev/video1` as a non-capture node. The camera is Sonix `USB 2.0 Camera`
  (`SN0001`, `uvcvideo`, USB path `platform-f8180000.usb-usb-0:1.3:1.0`),
  with stable id
  `/dev/v4l/by-id/usb-Sonix_Technology_Co.__Ltd._USB_2.0_Camera_SN0001-video-index0`.
  V4L2 enumeration found MJPG and YUYV formats; the application run used the
  negotiated YUYV 640x480@25 FPS mode. The complete probe is retained outside
  Git at `/tmp/task039-board-camera-capabilities.json` (SHA256
  `8ab2721aa51c08cc65338ee2d82f506a2053d28688c3f4189fe83aecde5eea67`),
  with the checked-in summary in `results/evidence/039/dr_camera_capabilities.json`.
- An isolated AArch64 Release build used the official local Linaro 7.5.0
  toolchain (archive SHA256
  `3b6465fb91564b54bbdf9578b4cc3aa198dd363f7a43820eab06ea2932c8e0bf`),
  ncnn 20240410 commit `56775de50990ab7f16627efdcf5529b49541206f`,
  `NCNN_OPENMP=ON`, `NCNN_THREADS=ON`, `NCNN_SIMPLEOMP=OFF`, and
  `NCNN_INT8=ON`. The resulting `edgeai_demo` is an AArch64 ELF with SHA256
  `2548fce2678c0a88628b8fa9f311242fb47cc334731df586261dd1ec016a36a6`.
  The one-line ncnn manifest compatibility fix accepting the explicit `INT8`
  identity was required for this command and did not change model layers,
  thresholds, options or performance behavior.
- The exact bounded command run on the board was:

  ```text
  LD_LIBRARY_PATH=/tmp/task039-camera-lib /tmp/edgeai_demo \
    --backend ncnn --model /tmp/ncnn_manifest_int8.json \
    --camera /dev/video0 --precision int8 \
    --config /tmp/yolov5n_v7_inference.json \
    --output-video /tmp/task039-edgeai-camera-final/result.avi \
    --output-codec MJPG \
    --output-json /tmp/task039-edgeai-camera-final/result.json \
    --max-frames 3 --threads 2 --packing 1
  ```

  It exited `0` with `captured=3 processed=3 dropped=0`. The ncnn runtime
  reported `1.0.20240410/openmp`, explicit `recommended-dual-thread`,
  configured threads `2`, packing on, and `fallback=none`. The external EQ
  param/bin identities are recorded in the JSON and validation manifest
  (`b05bd424...b769a2c4` and `9ae93520...6c09f7`); the temporary INT8 manifest
  SHA256 is `89d0f2c2c6cb285dac9d40d08f3db0e0108d10a5740302e4d4567273b1c911b1`.
- The checked-in run evidence is
  `results/evidence/039/dr_camera_ncnn_int8.json` (SHA256
  `39823af6eb3450fb9aebd9f0d49b5da9ff2c966d60450ce7ed6a93a9aa2ddbe7`). It
  records 3 captured/3 processed/0 dropped/0 failed/3 written frames,
  source rate 25 FPS, effective processing rate `0.564866 FPS`, and means of
  34.735 ms preprocess, 1343.185 ms inference, 60.458 ms postprocess and
  1725.077 ms end-to-end. The camera scene produced no detections in these
  three frames; this is not treated as a semantic Golden because no camera
  ground truth exists. Raw output shape was `[1,25200,85]` for every frame.
  The annotated MJPEG output was 640x480, 25 FPS, 3 frames, and was decoded
  outside Git (SHA256 `3440ac126814fe0273813f9fc0ae91f4d304e4f9a0d86b6f2d2a9a7ff889b117`).
- This completes the final functional camera gate as `VIDEO_CAMERA_PIPELINE_READY`.
  The implementation remains synchronous with queue capacity `0`; `dropped=0`
  is scoped to this bounded run and is not a claim that all frames from a
  faster live camera source would be processed. No realtime camera benchmark,
  capture queue, zero-copy optimization or DR storage change was introduced.
- Final offline validation after the camera continuation: the Task039 validator
  passed (`PASS`), focused Python tests passed `4/4`, and the full `.venv`
  Python suite passed `164/164`. These checks were run after the explicit
  camera runtime-profile assertions were added; no board command was rerun.
