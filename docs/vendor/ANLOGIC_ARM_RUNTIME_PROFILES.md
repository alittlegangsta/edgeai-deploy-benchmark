# Anlogic DR1 ARM runtime profiles

Task 019 freezes two explicit runtime profiles for the
MLK-F3P-CZ02-DR1M90. It does not replace Task 017 or Task 018 evidence and does
not introduce new benchmark data.

## Which profile to use

| Profile | Purpose | ncnn build | Threads | Parallel backend |
| --- | --- | --- | ---: | --- |
| `baseline-single-thread` | Reproduce the historical Task 017 baseline | OpenMP off | 1 | none |
| `recommended-dual-thread` | Recommended DR1 CPU/FP32 single-image deployment | OpenMP on, private libgomp | 2 | OpenMP |

The recommendation is board-specific. The generic PC CLI still defaults to its
existing one-thread behavior and reports `generic-default`; it does not silently
select the DR1 profile.

Task 018 measured the recommended build with both conditions and classified the
two-thread result `BENEFICIAL`: pipeline speedup `1.845334365x`, FPS gain
`84.533437%`, unchanged correctness, and two passing stability gates. This is
not ideal linear `2x` scaling, and it is not a claim about video, Vulkan,
quantization, or NPU performance.

## Frozen identities

Both profiles use ncnn tag `20240410`, commit
`56775de50990ab7f16627efdcf5529b49541206f`, CPU-only FP32, batch 1,
`640x640`, and the frozen Task 010–014 model/input contract.

The historical profile binds:

```text
libncnn.a:
5c905cd8f6824bc890a076a47fb540aecf9e676d27420ff3e5d6aed6737a0b8a
NCNN_OPENMP=OFF
NCNN_THREADS=ON
NCNN_SIMPLEOMP=OFF
```

The recommended profile binds:

```text
libncnn.a:
bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3

private libgomp.so.1:
87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91

NCNN_OPENMP=ON
NCNN_THREADS=ON
NCNN_SIMPLEOMP=OFF
effective_parallel_backend=openmp
configured_threads=2
```

Private libgomp is copied only into the isolated deployment package and loaded
with that package's `LD_LIBRARY_PATH`. No board system library is replaced.

## Offline checks

```bash
python3 scripts/vendor/validate_anlogic_arm_runtime_profile.py --check-all

bash -n \
  scripts/vendor/build_anlogic_aarch64_yolov5n.sh \
  scripts/vendor/deploy_anlogic_aarch64_yolov5n.sh
```

The validator rejects an OpenMP-off dual profile, an incorrect thread count or
ncnn identity, and a missing or hash-mismatched private libgomp.

## Build and deploy

The historical reproduction remains explicit:

```bash
bash scripts/vendor/build_anlogic_aarch64_yolov5n.sh \
  --execute \
  --runtime-profile baseline-single-thread

bash scripts/vendor/deploy_anlogic_aarch64_yolov5n.sh \
  --execute \
  --runtime-profile baseline-single-thread
```

The recommended DR1 path is:

```bash
bash scripts/vendor/build_anlogic_aarch64_yolov5n.sh \
  --execute \
  --runtime-profile recommended-dual-thread

bash scripts/vendor/deploy_anlogic_aarch64_yolov5n.sh \
  --execute \
  --runtime-profile recommended-dual-thread
```

The build entry verifies the exact static ncnn hash and records it in
`runtime_build_identity.json`. The recommended deployment entry additionally
verifies the private libgomp hash before transfer and on-package validation.
The application records `runtime_profile`, configured threads, compile-time
capabilities, effective backend, and observed process threads in stdout and
JSON.

If no `--runtime-profile` is supplied directly to `edgeai_ncnn_image`, it
retains one thread and reports `generic-default`. Passing `--threads` with an
explicit profile is allowed only when it matches that profile.

## Lightweight real-board gate

The Task 019 gate reused the already approved Task 018 ELF
`19d28afc324d52bf9b3cc5c14bb31268afe517424aeff35efe2578691e1a55c2`
and private libgomp in a new isolated directory. The VM was not rebuilt because
its SSH endpoint timed out, and rebuilding was unnecessary for this limited
runtime gate.

One non-benchmark diagnostic run reported:

```text
configured_threads=2
effective_parallel_backend=openmp
observed_process_threads=2
correctness_before=PASS_TARGET
correctness_after=PASS_TARGET
detections=5
exit_code=0
```

It used 2 warmups and 3 diagnostic iterations solely to prove runtime
capability and correctness. Its timing samples are not published as benchmark
results. See
[`results/evidence/019/board_runtime_validation.json`](../../results/evidence/019/board_runtime_validation.json).

## Boundaries

Task 017 remains the historical OpenMP-off single-thread baseline. Task 018
remains the paired OpenMP experiment and is the source of the recommendation.
The two tasks use different ncnn builds, so Task 017 is not one condition of
Task 018.

No model, input, threshold, PC golden, board governor, frequency, affinity,
service, SDK, or system library changed. Video, camera, Vulkan, quantization,
and NPU remain separate work; NPU is `HOLD`.
