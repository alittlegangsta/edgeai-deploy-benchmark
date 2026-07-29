# Anlogic DR1 ARM video-file inference

Task 020 validates file-to-file YOLOv5n ncnn inference on the real
MLK-F3P-CZ02-DR1M90. Automated validation is `PASS_TARGET`; the user approved
full video playback and the representative frames, so Task 020 is `Completed`.

## Contract

The application uses Task 019's `recommended-dual-thread` profile:

```text
ncnn 20240410 / 56775de50990ab7f16627efdcf5529b49541206f
NCNN_OPENMP=ON
NCNN_THREADS=ON
NCNN_SIMPLEOMP=OFF
configured_threads=2
effective_parallel_backend=openmp
CPU-only FP32, batch 1, input tensor 640x640
confidence threshold 0.25
NMS IoU threshold 0.45
```

The executable binds `libncnn.a`
`bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3`
and private `libgomp.so.1`
`87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91`.
The board loaded libgomp and all OpenCV/FFmpeg dependencies only from the
isolated Task 020 directory through `LD_LIBRARY_PATH`; no system library was
replaced.

The generic PC command remains backward compatible. ARM runs select the profile
and threads explicitly:

```text
--runtime-profile recommended-dual-thread
--threads 2
```

`configured_threads=2` is the ncnn inference setting. The recorded
`observed_process_threads=5` is the thread count for the entire process,
including OpenCV/FFmpeg activity; it is not evidence that ncnn used five
inference threads.

## Reproducible input

The ignored input is generated from 30 copies of the frozen Task 014 image:

```bash
.venv/bin/python scripts/vendor/generate_anlogic_arm_reference_video.py \
  --source data/samples/images/pc_reference.jpg \
  --output data/samples/videos/anlogic_arm_reference.avi \
  --metadata results/evidence/020/video_contract.json
```

| Property | Value |
| --- | --- |
| Container / codec | AVI / lossless FFV1 |
| Geometry | 1280×960 BGR |
| Playback metadata | 5 FPS, 30 frames, 6 seconds |
| Decoded pixel delta from source | 0 |
| Size | 14,767,146 bytes |
| SHA256 | `3953653b6364a844e829be68df76fce8ce673add5c4bfaf9176c5fb205e5da49` |

FFV1 is intentional. The first real-board attempt used MJPEG input, and the
application successfully processed all 30 frames, but lossy encoding changed
the low-confidence detections: frame 0 had four rather than five detections.
That failed evidence remains in the external returned directory and was not
merged into the accepted run. A local FFV1 probe decoded all 30 frames with
zero pixel delta and one unique decoded-frame hash.

The annotated output remains MJPEG/AVI for playback compatibility. Input
correctness and output playback use separate codec decisions.

## ARM OpenCV and FFmpeg

The SDK-local OpenCV 4.7.0 bundle contains AArch64 `videoio` headers,
`libopencv_videoio.so.407`, and FFmpeg 58-series libraries. Read-only `file`,
`readelf`, and SHA256 checks established this private dependency closure:

| Library | SHA256 |
| --- | --- |
| `libopencv_core.so.407` | `d0e4f5942fd8bfbba43ff092cebf636f463362c14c3a24aaada48034f08aa297` |
| `libopencv_imgproc.so.407` | `86dc1d5631c2ee5f33fe844ae9932f274dae34fa2a9359d6a76674bb4f4996b7` |
| `libopencv_imgcodecs.so.407` | `cc793274dc28e5ea60563c3125ba92401b13ba48adbfa835366f99877bdefde8` |
| `libopencv_videoio.so.407` | `3f2c1d29ca682fe30225e090d0b716b7084796280f8813a7e633845d7d5550e8` |
| `libavcodec.so.58` | `b247826b0cc01e88486a637715b68789946163580e368478112b10cd4ca66ad3` |
| `libavformat.so.58` | `3c2dd5fe441d6119159a28def59fca8663f78c865054ebeecd0fbfef6bee5f8a` |
| `libavutil.so.56` | `76a38a56678051ed1769fd8ef56e96481a3084b90020ebd999fe7ebe849c4951` |
| `libswscale.so.5` | `20f0a1ae322fca1b7e39843a8e7bfdf09b39f2e8397374ce5028e65fa87cb27b` |
| `libswresample.so.3` | `16efc7de75606e2bb3c757674ae001970440571a65507c097fe1d2cd3fbf666a` |
| `libx264.so.157` | `9150dc1c04b7283a3fbf2d48d81cf687bc10733928c995f4300b4721d27a3170` |

This is evidence for the local `SDK_2025_07` asset. It does not prove an exact
public-repository tag relationship.

## Build and deployment

The VM build uses CMake 3.16.9, Linaro GCC/G++ 7.5.0, the glibc 2.25 sysroot,
the frozen OpenMP ncnn install, and the existing toolchain file:

```bash
bash scripts/vendor/build_anlogic_aarch64_video.sh --check
bash scripts/vendor/build_anlogic_aarch64_video.sh --execute
```

The resulting executable is ELF64 AArch64 with interpreter
`/lib/ld-linux-aarch64.so.1`:

```text
edgeai_ncnn_video SHA256:
8de717cc21e3a74f9072489d18bc32d56813d3bc37bef0f4782bf3cc8c725094
```

Deployment and collection use:

```bash
bash scripts/vendor/deploy_anlogic_aarch64_video.sh --check
bash scripts/vendor/deploy_anlogic_aarch64_video.sh --execute
```

The accepted board directory is:

```text
/root/edgeai/yolov5n-ncnn-video-file-20260729T025346Z
```

`ldd` resolved ncnn's OpenMP runtime, four OpenCV modules, five
FFmpeg/x264 libraries, and board system libc/libstdc++/libgcc without any
`not found`. The board remained Buildroot 2022.02.6, Linux 6.1.111-rt42,
AArch64, glibc 2.25. The board clock remains unsynchronized; the WSL run
identifier orders this evidence.

## Automated result

The application exited zero with empty stderr:

| Count | Value |
| --- | ---: |
| Declared input frames | 30 |
| Decoded | 30 |
| Processed | 30 |
| Written | 30 |
| Reopened/verified | 30 |
| Failed | 0 |

Every frame has five detections and preserves the `keyboard`, `tv`, `cup`, and
two `mouse` results, including the known low-confidence earbud-case `mouse`.
Independent WSL validation reports:

```text
frames validated: 30
minimum class-matched IoU against PC ncnn golden: 0.9999855075776749
maximum confidence delta: 0.0000050067901611328125
minimum cross-frame IoU: 1.0
maximum cross-frame confidence delta: 0.0
correctness: PASS_TARGET
```

The returned MJPEG/AVI is 1280×960, 5 FPS, 30 frames, and decodes 30/30 in WSL:

```text
output video SHA256:
2669ec2fd0bd4eaaa1bf06f5ef3636e2100023f32bc0a77622f01fab5673a8bc
```

Representative decoded images:

| Frame | Path | SHA256 |
| ---: | --- | --- |
| 0 | `results/images/020/frame_first.png` | `d595945e490cdc2b72083a0d32c7e69c115361c9d9e088cf60c621a1857f52a8` |
| 15 | `results/images/020/frame_middle.png` | `d58c42846dd63cdc75b80f0882930083952faa457fcdb94a0be5ab7f4acab671` |
| 29 | `results/images/020/frame_last.png` | `d58c42846dd63cdc75b80f0882930083952faa457fcdb94a0be5ab7f4acab671` |

Frame timing fields are retained only to diagnose stage boundaries. They are
not a formal video throughput benchmark, and the 5 FPS container value is
playback metadata rather than achieved inference FPS.

## Evidence and human review

- [Input contract](../../results/evidence/020/video_contract.json)
- [Board environment](../../results/evidence/020/video_environment.json)
- [Per-frame detections](../../results/evidence/020/video_frame_detections.json)
- [Independent validation](../../results/evidence/020/video_validation.json)

The generated input and output videos remain Git ignored. The output to review
is available locally at:

```text
results/videos/anlogic_arm_ncnn_reference.avi
```

The user played the full six-second video and inspected the returned first,
middle, and last frames. The user approved:

- normal playback, duration, ordering, and frame continuity;
- no black/corrupt/color-shifted frames;
- correct box placement and readable labels/confidences;
- stable annotations across the identical-frame sequence;
- acceptable MJPEG encoding quality.

The approval record is:

```text
automated_validation: PASS_TARGET
human_video_review: PASS
human_review_source: user
candidate_approved: true
recorded_at: 2026-07-29T11:18:31+08:00
time basis: WSL approval record time; not board run time
Task 020: Completed
```

The user—not Codex—performed the visual review. The review found continuous
30-frame playback, normal color/geometry, stable box placement, readable
labels/confidences, no corrupt frames or drawing pollution, and the expected
low-confidence earbud-case `mouse`.

## Boundaries

No formal video benchmark, camera, streaming, Vulkan, FP16/BF16/INT8 runtime,
quantization, or NPU work occurred. No model, input image, threshold, PC golden,
Task 017-019 evidence, board governor/frequency/service, SDK, or system library
was modified. NPU remains `HOLD`.
