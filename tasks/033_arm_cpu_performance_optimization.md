# Task 033

## Title

ARM CPU performance optimization and profiling.

## Status

Completed

## Dependencies

Task 030 (`Completed`). Tasks 028, 029, 031 and 032 remain frozen at their
vendor-handoff states and are not reopened by this task.

## Recommended Branch

`dev` (the user explicitly selected Task 033 on the current branch; no branch
switch is authorized).

## Goal

Profile the validated ARM ncnn YOLOv5n v7.0 CPU pipeline, attribute its stage
costs, and evaluate explainable single-variable CPU optimizations without
changing the frozen model, input, preprocessing, thresholds, or correctness
contract. Historical Task 017/018/030 evidence remains immutable.

## Frozen workload

The workload is the approved YOLOv5n v7.0 ARM ncnn representation and fixed
reference image from Task 018/030: batch 1, 640x640 FP32 input, confidence 0.25,
class-aware NMS IoU 0.45, and the existing five-detection golden comparison.
Image decoding, model load, rendering, and output writes are outside the timed
pipeline. No NPU, camera, video, Vulkan, quantization, kernel, boot, DTB, eMMC,
or SD change is in scope.

## Experiment contract

The Task 033 profiler must record exact command/config, model/input/param/bin
hashes, warmup/repeat counts, preprocess, inference, decode, NMS, postprocess,
and end-to-end timings, FPS, process CPU time/utilization, peak RSS, process
thread count, CPU frequency and temperature when readable, runtime capability,
affinity, and correctness. Thread candidates are selected from the real board
topology (at least 1/2/3/4 are attempted only when meaningful). Every accepted
change must pass the existing golden gate. Baseline and rejected/intermediate
experiments remain retained.

## Allowed Files

```text
TASKS.md
ROADMAP.md
README.md
CHANGELOG.md
tasks/033_arm_cpu_performance_optimization.md
docs/benchmark/ARM_CPU_PERFORMANCE_OPTIMIZATION.md
cpp/include/edgeai/backends/ncnn_detector.hpp
cpp/src/backends/ncnn_detector.cpp
cpp/include/edgeai/common/postprocess.hpp
cpp/src/common/postprocess.cpp
cpp/apps/arm_cpu_profiler.cpp
cpp/CMakeLists.txt
cpp/tests/test_arm_cpu_profiler.cpp
scripts/vendor/run_task033_arm_cpu_profiler.sh
scripts/validate_task033_arm_cpu_optimization.py
tests/python/test_task033_arm_cpu_optimization.py
.knowledge/manifests/arm_cpu_performance_optimization.yaml
results/evidence/033/**
```

## Forbidden Files and Actions

- Do not modify Task 017/018/030 raw or consolidated evidence, or any NPU task
  evidence.
- Do not change the frozen model, input, preprocessing, confidence/NMS
  thresholds, or correctness tolerances.
- Do not claim a performance result without a retained command output.
- Do not replace the ARM ncnn model with another backend/model.
- Do not modify kernel, boot, DTB, eMMC, SD, governor, frequency, or services.
- Do not download/install dependencies, use sudo/apt, or access NPU assets.
- Do not commit binaries, model files, SDKs, libraries, or private logs.
- Do not push, create a PR, merge, rebase, reset, or delete user data.

## Acceptance Criteria

1. A standalone profiler builds in Release mode and reports the frozen workload
   identity plus ncnn capability and stage timings.
2. Real ARM runs retain a baseline and every attempted thread/affinity/runtime
   option, with independent correctness validation and resource observations.
3. Decode and NMS are separately measurable; pipeline totals reconcile with all
   timed stages within the recorded clock granularity.
4. The optimization matrix identifies accepted and rejected changes and names
   the best correctness-preserving configuration without inventing speedup.
5. Task 017/018/030 evidence remains byte-for-byte unchanged and NPU task state
   remains frozen.
6. Focused tests, Python unittest, Release CMake build, CTest, JSON/YAML and
   syntax checks, repository hygiene, and `git diff --check` pass.

## Execution Record

Started: `2026-08-11` (Asia/Shanghai)

Branch: `dev`

Starting status: clean.

The profiler is intentionally separate from the historical Task 017/018
benchmark executable so its expanded options cannot alter a completed protocol.
Commands, artifacts, hashes, repair attempts, skipped checks, and final status
will be appended here as they occur.

## Execution Record (continued)

Environment timestamp: `2026-08-11` (Asia/Shanghai).

- `cmake -S cpp -B build/task033-host-release -DCMAKE_BUILD_TYPE=Release -DEDGEAI_ENABLE_ORT=OFF -DEDGEAI_ENABLE_NCNN=ON -DEDGEAI_ENABLE_VIDEO=OFF -DNCNN_ROOT=/home/dministrator/opt/ncnn/ncnn-linux-x64-20240410-local -DEDGEAI_NCNN_LIBRARY_SHA256=5c905cd8f6824bc890a076a47fb540aecf9e676d27420ff3e5d6aed6737a0b8a -DEDGEAI_PRIVATE_LIBGOMP_SHA256='' && cmake --build build/task033-host-release --target edgeai_arm_cpu_profiler edgeai_arm_cpu_profiler_tests edgeai_ncnn_detector_tests -j2` exited 0. Host compiler is GCC 13.3.0; host OpenCV is 4.6.0; pinned host ncnn is 1.0.20240410.
- `ctest --test-dir build/task033-host-release --output-on-failure` exited 0: 8/8 tests passed, including the new profiler and detector tests.
- The one-sample host smoke command exited 0 and passed the five-detection gate. The retained artifact is `results/evidence/033/host_profiler_smoke.json` (SHA256 `dbcf2f3f647b1d419dbe459670c108713ec0682670d8fd3a1d250ca63b352ae1`). It is explicitly host API/build smoke, not an ARM performance result.
- `python3 scripts/validate_task033_arm_cpu_optimization.py results/evidence/033/host_profiler_smoke.json` exited 0. The focused Python unittest exited 0 (2/2).
- `bash -n scripts/vendor/run_task033_arm_cpu_profiler.sh` and `python3 -m py_compile scripts/validate_task033_arm_cpu_optimization.py tests/python/test_task033_arm_cpu_optimization.py` exited 0.
- Host-only option smokes (not ARM evidence) exercised threads 1/2, `cpu0`, packing off, FP16 storage on and FP16 arithmetic on with one measured repeat each. All five commands exited 0 and passed the unchanged five-detection gate; their JSON outputs remain in `/tmp/task033-host-*.json` and are not presented as board performance.
- `scripts/vendor/run_task033_arm_cpu_profiler.sh --check` initially hit WSL interop (`UtilBindVsockAnyPort:307: socket failed 1`) in the restricted shell. A controlled external invocation restored the wrapper and exited 0, confirming CMake 3.16.9, Linaro GCC 7.5.0, AArch64 OpenMP ncnn 20240410, libncnn SHA256 `bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3`, and libgomp SHA256 `87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91`.
- `scripts/vendor/run_task033_arm_cpu_profiler.sh --execute` exited 0 in the isolated VM build directory. The AArch64 profiler ELF SHA256 is `90c71995e3c724c49e157084b81170acc2b31c8559ed0e6a1021f0b373941c14`; the external build-output identity JSON SHA256 is `79ba91d07a6ab73a167f7046a8d08c9b65e84e77ea0715f97c6087521ab23a62`.
- A read-only board probe through `/home/dministrator/bin/anlogic-board-ssh` timed out at `192.168.50.2:22`; a VM-side ping lost its packet and a TCP/22 probe was closed. No package transfer, board run, or board mutation was attempted.
- A temporary external package was prepared at `/tmp/task033-board-package-v1` with the profiler, private libgomp, OpenCV runtime, frozen ncnn model/manifest, input, config and golden; its file hashes were printed, but it was not copied to the unreachable board.
- `cmake --build build/ci-default-options-release -j2 && ctest --test-dir build/ci-default-options-release --output-on-failure` exited 0 with 15/15 tests passing. Full Python unittest discovery exited 0 with 151 tests passing. JSON/YAML parsing, Bash/Python syntax and `git diff --check` exited 0; the Task 017/018/030/NPU evidence scope check reported `IMMUTABILITY_SCOPE_PASS`.

### Repair attempts

Attempt 1 (environment diagnosis): inspected the VM wrapper, Windows OpenSSH
path, WSL interop sockets and direct Windows `cmd.exe`/`ssh.exe` calls. The
restricted shell saw a vsock binding error, but a controlled external wrapper
call restored VM access and the cross-build passed. The remaining blocker is
the independent board network timeout; no dependency was installed and no
network fetch was attempted.

### Pre-board status and resume note

Before the board SSH endpoint recovered, Task 033 was recorded as `In Progress`
with a network-only resume point. That condition is superseded by the board
continuation below; the task now has a real ARM matrix and is completed.

## Execution Record (board continuation)

The board SSH endpoint became reachable at `192.168.50.2`. A temporary package
was copied only to `/tmp/task033-profiler-v1`; its files were checked by
individual SHA256 recomputation. No persistent board path, SD/eMMC, kernel,
boot file, governor, service, or NPU asset was changed.

Read-only board identity:

```text
Linux buildroot 6.1.111-rt42 #3 SMP PREEMPT Wed Aug 5 18:19:39 CST 2026 aarch64
logical CPUs: 2
CPU part: 0xd04
features: fp asimd evtstrm aes pmull sha1 sha2 crc32 cpuid
```

The following real ARM rows completed with exit code 0 and `PASS_TARGET`:

```text
threads1_default_packing_on.json  repeat=10  mean pipeline=3514.946744 ms
threads2_default_packing_on.json  repeat=10  mean pipeline=1963.817618 ms
threads1_cpu0_packing_on.json     repeat=10  mean pipeline=3655.738104 ms
threads2_both_packing_on.json     repeat=10  mean pipeline=1977.549212 ms
threads1_default_packing_off.json repeat=5   mean pipeline=3823.488686 ms
threads2_default_packing_off.json repeat=5   mean pipeline=2120.144871 ms
threads2_fp16_packed_on.json      repeat=5   mean pipeline=1974.229028 ms
threads2_fp16_storage_on.json     repeat=5   mean pipeline=1989.556880 ms
threads2_fp16_arithmetic_on.json  repeat=5   mean pipeline=1985.126599 ms
```

Each row is independently validated by
`scripts/validate_task033_arm_cpu_optimization.py`. Threads 3 and 4 were
explicitly skipped because topology reports two logical CPUs. A read-only
probe found no readable cpufreq, thermal or governor sysfs values and the
board BusyBox image has no `taskset`; these are recorded as unavailable, not
fabricated. The full matrix, result hashes, classifications, speedups and
stage attribution are in `results/evidence/033/experiment_matrix.json` and
`results/evidence/033/optimization_summary.json`.

The accepted configuration is `threads=2`, default scheduling, packing on,
FP32 storage/arithmetic. It passed the frozen correctness gate with five
detections, minimum class-matched IoU `0.9999855075776749`, and maximum
confidence delta `0.0000050067901611328125`. It is a CPU profiling result, not
a new formal Task 017/018 benchmark and not an NPU result.

## Completion Record

All Task 033 acceptance criteria passed in real execution. The accepted row is
`threads2_default_packing_on`: pipeline mean `1963.8176175 ms`, P50
`1962.758989 ms`, P95 `1976.06648 ms`, inference mean `1873.4743716 ms`, FPS
`0.5092122563158541`, peak RSS `168064 KiB`, and mean process CPU utilization
`187.02447345462414%` on the one-core basis reported by the profiler. The
same-session one-thread baseline is `3514.9467439 ms` pipeline mean and
`0.28449933181361736` FPS, giving `1.7898539622913836x` pipeline speedup and
`78.98539622913836%` FPS gain. The inference-only speedup is
`1.8272052774207268x`; RSS changed by `+0.12152984630049435%`.

The retained rows, independent hashes, skipped topology candidates and
classification are frozen in `results/evidence/033/experiment_matrix.json`;
stage attribution and comparison are in
`results/evidence/033/optimization_summary.json`. Historical Task 017/018/030
evidence and all NPU evidence remain byte-for-byte outside this task's change
set. No commit, push, board persistent change, SD/eMMC write, kernel/boot
change, or NPU execution was performed.
