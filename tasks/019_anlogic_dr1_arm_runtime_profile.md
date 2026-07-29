# Task 019

## Title

Anlogic DR1M90 dual-thread ARM runtime profile.

## Status

Completed

## Stage

Stage 2 ARM runtime profile

## Dependencies

Tasks 017 and 018 (`Completed`).

## Recommended Branch

`feature/arm-dual-thread-runtime-profile`

## Recommended Commit

`feat(arm): add DR1 dual-thread runtime profile`

## Goal

Freeze the Task 018 OpenMP-enabled two-thread configuration as the recommended
MLK-F3P-CZ02-DR1M90 CPU deployment profile while preserving the Task 017
single-thread baseline as an explicit historical profile. Add unambiguous
profile selection and fail-closed build/runtime identity checks without
changing generic PC defaults or duplicating inference code.

## Scope

Define exactly two ARM profiles:

```text
baseline-single-thread
recommended-dual-thread
```

The baseline profile reproduces Task 017 with one configured thread and the
original OpenMP-off ncnn build. The recommended profile uses the Task 018
OpenMP-enabled ncnn build, two configured threads, and a private
`libgomp.so.1` supplied only from an isolated deployment directory through
`LD_LIBRARY_PATH`.

Both profiles retain ncnn `20240410`, commit
`56775de50990ab7f16627efdcf5529b49541206f`, CPU-only FP32, batch 1,
`640x640`, the frozen model/input hashes, confidence threshold `0.25`, NMS IoU
threshold `0.45`, and the existing preprocessing, inference, postprocessing,
JSON, and visualization implementations.

This task does not add performance measurements, retune thread counts, modify
Tasks 017/018 evidence, alter PC defaults, convert models, or enter video,
camera, Vulkan, quantization, or NPU work.

## Frozen Profile Identities

Historical baseline:

```text
profile: baseline-single-thread
configured_threads: 1
NCNN_OPENMP: OFF
NCNN_THREADS: ON
NCNN_SIMPLEOMP: OFF
effective_parallel_backend: none
libncnn.a SHA256: 5c905cd8f6824bc890a076a47fb540aecf9e676d27420ff3e5d6aed6737a0b8a
source task: 017
```

Recommended profile:

```text
profile: recommended-dual-thread
configured_threads: 2
NCNN_OPENMP: ON
NCNN_THREADS: ON
NCNN_SIMPLEOMP: OFF
effective_parallel_backend: openmp
libncnn.a SHA256: bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3
private libgomp.so.1 SHA256: 87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91
Task 018 benchmark ELF SHA256: 19d28afc324d52bf9b3cc5c14bb31268afe517424aeff35efe2578691e1a55c2
source task: 018
```

The benchmark ELF hash identifies Task 018 evidence; it is not the Task 019
single-image executable and is never committed.

## CLI and Deployment Contract

The DR1 single-image application accepts:

```text
--runtime-profile baseline-single-thread
--runtime-profile recommended-dual-thread
```

The selected profile is emitted in stdout and structured JSON. A supplied
`--threads` value must equal the profile's configured thread count. The
recommended profile must reject an OpenMP-off or otherwise incompatible build;
its deployment must reject a missing or hash-mismatched private `libgomp.so.1`.

With no `--runtime-profile`, the generic CLI retains its existing one-thread
behavior and reports `generic-default`; it does not pretend to use a frozen DR1
build identity. DR1 deployment commands select a profile explicitly. DR1
documentation recommends `recommended-dual-thread`; historical single-thread
reproduction commands remain available.

## Allowed Files

```text
TASKS.md
ROADMAP.md
README.md
CHANGELOG.md
tasks/019_anlogic_dr1_arm_runtime_profile.md
configs/runtime_profiles/anlogic-dr1-baseline-single-thread.json
configs/runtime_profiles/anlogic-dr1-recommended-dual-thread.json
cpp/CMakeLists.txt
cpp/apps/ncnn_image.cpp
cpp/include/edgeai/backends/ncnn_detector.hpp
cpp/src/backends/ncnn_detector.cpp
cpp/tests/test_ncnn_detector.cpp
scripts/vendor/build_anlogic_aarch64_yolov5n.sh
scripts/vendor/deploy_anlogic_aarch64_yolov5n.sh
scripts/vendor/validate_anlogic_arm_runtime_profile.py
tests/python/test_anlogic_arm_runtime_profile.py
.knowledge/manifests/anlogic_arm_runtime_profiles.yaml
docs/vendor/ANLOGIC_ARM_RUNTIME_PROFILES.md
results/evidence/019/runtime_profile_validation.json
results/evidence/019/board_runtime_validation.json
results/evidence/019/board_correctness_comparison.json
```

Task-owned VM build output, isolated deployment packages, and transient logs
remain external and must not be committed.

## Forbidden Files and Actions

- Do not modify Task 017 or Task 018 formal evidence, manifests, task files, or
  published values.
- Do not modify the frozen model, input, thresholds, PC golden, ncnn revision,
  SDK, board system libraries, governor, frequency, affinity, or services.
- Do not commit ARM ELF, `libncnn.a`, `libgomp`, model `.param`/`.bin`, SDK
  content, deployment packages, large logs, or credentials.
- Do not add benchmark samples or performance claims.
- Do not change generic PC default behavior to two threads.
- Do not implement video, camera, Vulkan, quantization, or NPU functionality.

## Build Commands

Offline:

```bash
cmake -S cpp -B build/ci-default-options-release -DCMAKE_BUILD_TYPE=Release
cmake --build build/ci-default-options-release --parallel
```

If the lightweight real-board gate requires a current single-image ELF, use the
existing VM build entry with the explicit recommended profile. The independent
Task 017 build/output must not be overwritten.

## Run Commands

Offline profile validation:

```bash
python3 scripts/vendor/validate_anlogic_arm_runtime_profile.py --check-all
```

The optional real-board gate is limited to one recommended-profile single-image
run. It must report `effective_parallel_backend=openmp`, observe two process
threads, retain `PASS_TARGET` correctness, and exit zero. It is not a benchmark.

## Test Commands

```bash
bash -n \
  scripts/vendor/build_anlogic_aarch64_yolov5n.sh \
  scripts/vendor/deploy_anlogic_aarch64_yolov5n.sh
python3 -m py_compile \
  scripts/vendor/validate_anlogic_arm_runtime_profile.py \
  tests/python/test_anlogic_arm_runtime_profile.py
PYTHONPATH=python .venv/bin/python -m unittest \
  tests/python/test_anlogic_arm_runtime_profile.py -v
PYTHONPATH=python .venv/bin/python -m unittest discover \
  -s tests/python -p 'test_*.py' -v
ctest --test-dir build/ci-default-options-release --output-on-failure
git diff --check
```

## Acceptance Criteria

1. Both profiles are machine-readable, complete, and bind exact source,
   runtime, asset, thread, backend, and evidence identities.
2. The recommended profile requires the approved OpenMP-enabled ncnn build and
   private `libgomp.so.1`; missing, hash-mismatched, or OpenMP-off identities
   fail closed.
3. The historical profile remains explicitly reproducible and does not alter
   Task 017 evidence.
4. CLI/build/deployment behavior records the selected profile, passes the
   correct thread count, and leaves generic PC defaults unchanged.
5. The recommended profile is the documented DR1 default recommendation, not a
   universal platform default.
6. A lightweight board run using the recommended profile reports OpenMP, two
   observed process threads, five correct detections, `PASS_TARGET`, and exit
   code zero without changing board system state.
7. Offline profile, rejection, syntax, C++, Python, evidence, link, sensitive
   material, hygiene, and whitespace checks pass.
8. Task 017 and Task 018 tracked evidence is byte-unchanged and no new formal
   benchmark data is created.

All criteria passed, so Task 019 is `Completed`.

## Repair Rules

At most three complete diagnose/modify/rebuild/retest/rerun loops may repair
Task 019. Record each failing command and outcome below. Never weaken identity,
correctness, or scope gates to pass.

## Human Stop Conditions

Stop if completion requires changing frozen assets, Task 017/018 evidence,
board system state, credentials, `sudo`, flashing, a new dependency download,
or a different runtime/deployment route. Ordinary source, configuration,
path, build, transfer, and test errors are repairable.

## Evidence Brief

```text
task: Task 019 Anlogic DR1M90 dual-thread ARM runtime profile
board: MLK-F3P-CZ02-DR1M90
SDK tag: SDK_2025_07 local asset identity; exact official repository tag compatibility unproven
repository tag/commit: ncnn 20240410 / 56775de50990ab7f16627efdcf5529b49541206f
sources consulted: Tasks 017-018 formal task, manifest, raw, summary, validation, and build-provenance evidence
documented facts: Task 017 is the historical OpenMP-off single-thread baseline; Task 018 approved the OpenMP-enabled paired two-thread profile as BENEFICIAL
assumptions: none
conflicts: Task 017 and Task 018 use different ncnn builds and are not direct experimental groups
unresolved blockers: none
proposed action: use recommended-dual-thread for DR1 deployment and retain baseline-single-thread for Task 017 reproduction
```

## Execution Record

Started: `2026-07-29T10:03:33+08:00`

Branch: `feature/arm-dual-thread-runtime-profile`

Starting commit: `2fe4e94fa64668290c5ba155ae810f2a08c11ba2`

Starting status: clean; HEAD equals local `dev`.

Startup path discovery:

- three read-only probes used obsolete guessed Task 014 script names and failed
  with `No such file or directory`;
- `rg --files` located the actual build and deployment entry points;
- no file or external state was changed by those probes.

Implemented:

- added two machine-readable profile configurations and an offline validator;
- made `edgeai_ncnn_image` accept explicit runtime profiles while preserving
  its generic one-thread default;
- exposed ncnn/OpenMP build capabilities, frozen library identities, selected
  profile, configured threads, and observed process threads in stdout/JSON;
- made the dual profile reject OpenMP-off, wrong ncnn identity, missing/wrong
  private libgomp, and thread/profile mismatches;
- extended the existing build/deploy entry points instead of copying the
  inference pipeline;
- kept Task 017 and Task 018 tracked evidence byte-unchanged.

Repair attempt 1:

```text
failing command:
bash scripts/vendor/build_anlogic_aarch64_yolov5n.sh --check
  --runtime-profile recommended-dual-thread

first environment result:
WSL sandbox denied the Windows-vsock operation

retry after approved network access:
ssh: connect to host 192.168.244.128 port 22: Connection timed out

diagnosis:
the VM SSH endpoint was unavailable; the local route table also exposed no
VMware 192.168.244.0/24 path

repair:
use the user-approved Task 018 OpenMP ELF and private runtime already present
on the real board, copy them to a new Task 019 isolated directory, and perform
the permitted lightweight diagnostic without rebuilding or modifying Task 018

result:
PASS
```

Lightweight board gate:

```text
recorded_at: 2026-07-29T10:16:50+08:00
record time basis: WSL evidence time; board clock unsynchronized
directory: /root/edgeai/anlogic-arm-runtime-profile-task019
ELF SHA256: 19d28afc324d52bf9b3cc5c14bb31268afe517424aeff35efe2578691e1a55c2
libgomp SHA256: 87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91
configured threads: 2
effective backend: openmp
observed process threads: 2
CPU time / wall time: 1.849185675
correctness before/after: PASS_TARGET / PASS_TARGET
detections: 5
exit code: 0
formal benchmark: not run
```

Final validation:

```text
profile config validation: PASS (2/2)
profile rejection tests: PASS (7/7)
model-independent/full Release build: PASS
full CTest: PASS (12/12)
full Python unittest discovery: PASS (97/97)
JSON parse: PASS (79 files)
YAML parse: PASS (32 files)
tracked/non-ignored Bash syntax: PASS
tracked/non-ignored Python py_compile: PASS
Markdown local links: PASS (27 links)
frozen model/input/golden hashes: PASS
Task 017/018 evidence immutability: PASS
sensitive-material scan: PASS
git diff --check: PASS
```

Completed: `2026-07-29T10:21:58+08:00`
