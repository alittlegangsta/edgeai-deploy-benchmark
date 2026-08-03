# Anlogic DR1 UVC camera inference (Task 021)

Task 021 is a bounded-latency functional validation on the real
MLK-F3P-CZ02-DR1M90. It is not a realtime or performance benchmark. The
automatic stage and the user representative-frame review are both `PASS`, so
Task 021 is `Completed`.

## Frozen runtime and board configuration

The run uses the explicit `recommended-dual-thread` profile from Task 019:

- ncnn `20240410`, commit
  `56775de50990ab7f16627efdcf5529b49541206f`;
- `NCNN_OPENMP=ON`, `NCNN_THREADS=ON`, `NCNN_SIMPLEOMP=OFF`, OpenMP backend;
- two configured ncnn threads, CPU-only FP32, batch 1, `[1,3,640,640]`;
- confidence threshold `0.25`, NMS IoU threshold `0.45`;
- private `libgomp.so.1` loaded only through the isolated deployment directory.

The board is AArch64, Buildroot 2022.02.6, Linux 6.1.111-rt42, glibc 2.25.
The camera audit found `/dev/video0` and `/dev/video1`, both named `USB 2.0
Camera: USB Camera` and driven by `uvcvideo`. V4L2 ioctl enumeration found
`MJPG` and `YUYV`. The stable selected configuration is:

```text
device: /dev/video0
backend: V4L2/OpenCV
pixel format: YUYV
size: 640x480
requested and negotiated FPS: 5
```

The board did not provide `v4l2-ctl`, ffmpeg, or GStreamer command-line tools;
the application’s V4L2 ioctl capability probe supplied the evidence without
installing software.

The camera ELF is an ELF64 AArch64 executable with interpreter
`/lib/ld-linux-aarch64.so.1`, SHA256
`2962d94e10f798daa389e9bf43d8c4ee88259479747967d311e9cf20d1e910a9`. The
validated build identities are:

```text
libncnn.a:      bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3
libgomp.so.1:   87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91
```

Board `ldd` resolved all private OpenCV/FFmpeg/libgomp dependencies from the
deployment directory and all system C/C++ libraries from the board. No system
library was replaced.

## Bounded-latency pipeline

One capture thread and one inference thread communicate through a mutex- and
condition-variable-protected slot with capacity one. Publishing a valid new
frame overwrites an unprocessed older frame (`latest-frame-wins`); there is no
unbounded queue. The final run (`20260803T082616Z`) recorded:

```text
captured: 113
published: 112
processed: 10
overwritten/dropped: 101
invalid capture: 0
pending at stop: 1
unpublished at shutdown: 1
processed source sequences: 0, 11, 22, 34, 45, 56, 67, 78, 89, 100
whole-process observed threads: 6
```

The observed six threads include capture, OpenCV/V4L2 and ncnn/runtime
threads; it is not a claim that ncnn inference used six threads. Capture and
inference ages and stage timings are diagnostic only and are not published as
camera FPS or realtime latency. Shutdown accounting is explicit:
`113 = 112 + 1` (`captured = published + unpublished_at_shutdown`) and
`112 = 10 + 101 + 1` (`published = processed + overwritten + pending_at_stop`).
The overwritten frames are expected latest-frame-wins behavior, not processing
failures.

## Offline replay validation

Each of the ten retained raw BGR PNGs was passed through the approved native
single-image ncnn executable using the frozen model and configuration. Live and
replay records were compared by class/rank, finite values, valid boxes, IoU and
confidence. All 10 frames passed:

```text
status: PASS_TARGET
minimum class-matched IoU: 0.9999769312514045
maximum confidence delta: 0.000006020069122314453
failed frames: 0
```

This proves that camera capture and bounded publication did not change the
inference path. It is not semantic ground truth for objects in an unconstrained
camera scene.

The measured frame age was 1.83–187.28 ms at inference start and
2396.90–2626.19 ms at result completion. The first value is below the selected
200 ms camera sampling period for these retained frames; the larger completion
age is principally the approximately two-second inference time. The 5 FPS
value is the camera capture configuration, not an inference FPS claim.

Representative files for user review are:

```text
results/images/021/first_raw.png
results/images/021/first_annotated.png
results/images/021/middle_raw.png
results/images/021/middle_annotated.png
results/images/021/last_raw.png
results/images/021/last_annotated.png
```

All are 640x480 RGB PNGs. Their hashes and the complete frame records are in
`results/evidence/021/camera_validation.json`,
`camera_run.json`, and `camera_replay_validation.json`.

## Reproduction entry points

The host-side checks and build/deployment commands are:

```text
bash scripts/vendor/audit_anlogic_arm_camera.sh --check
bash scripts/vendor/build_anlogic_aarch64_camera.sh --check
bash scripts/vendor/build_anlogic_aarch64_camera.sh --execute
bash scripts/vendor/deploy_anlogic_aarch64_camera.sh --check
bash scripts/vendor/deploy_anlogic_aarch64_camera.sh --execute
python3 scripts/vendor/replay_anlogic_arm_camera.py --execute
python3 scripts/vendor/validate_anlogic_arm_camera.py \
  --evidence-dir results/evidence/021 \
  --raw-dir results/logs/vendor/arm_uvc_camera/replay_frames/20260803T082616Z
```

Deployment is isolated under `/root/edgeai/yolov5n-ncnn-uvc-camera-*`; it does
not write `/lib`, `/usr`, eMMC, governor, frequency, or service configuration.

## Repair history and boundaries

The first board attempt (`20260803T082404Z`) retained its failure evidence
outside the Git evidence set. A JSON FileStorage array-shape mismatch stopped
evidence writing before completion; it was repaired and the final run was
performed independently, not spliced with the failed attempt. A preceding
shared-path transfer error also produced no board deployment. Neither is a
formal camera-frame failure.

Task 017–020 evidence remains unchanged. Task 021 does not include a formal
realtime benchmark, USB-camera benchmark, video streaming, asynchronous
pipeline, Vulkan, FP16/BF16/INT8, NPU, governor changes, system-library
replacement, or model/threshold changes. The board wall clock is unsynchronized
(the run evidence retains its 1970 board time); ordering uses monotonic board
timestamps and WSL evidence time.

## Human review record

The user inspected all six representative files as raw/annotated pairs for
orientation, color, box geometry, labels, text readability and temporal order.
The recorded result is `human_camera_review: PASS`,
`human_review_source: user`, and `candidate_approved: true`, recorded at
`2026-08-03T16:50:00+08:00` in WSL. This is an approval-record time, not a
camera capture or board inference time, and must not be attributed to Codex.
