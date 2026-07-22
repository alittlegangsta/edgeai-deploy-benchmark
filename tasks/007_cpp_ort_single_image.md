# Task 007

## Title

Implement C++ ONNX Runtime single-image detection and compare it with Python.

## Status

Completed

## Batch

Batch B

## Dependencies

Task 006 (`Completed`).

## Recommended Branch

`feature/pc-batch-b-cpp-ort`

## Recommended Commit

`feat(cpp): add ONNX Runtime image inference`

## Goal

Add a narrow C++ ONNX Runtime CPU adapter and single-image CLI that reuse Task
006, print actual model I/O, emit real detections, and agree with the approved
Python reference within frozen tolerances.

## Why This Task Exists

It validates native runtime integration while preserving a known-good model,
preprocessing pipeline, postprocessing contract, and comparison target.

## Knowledge Covered

- Target-level ONNX Runtime discovery and linking.
- Runtime sessions, tensor lifetime, and CPU provider options.
- Model metadata validation and raw-output decoding.
- Cross-language structured detection matching.
- Native error handling and artifact generation.

## Scope

Implement only C++ CPU ONNX Runtime single-image inference. Reuse Task 006 for
configuration, preprocessing, detection types, coordinate mapping, and drawing.
Add the minimum YOLOv5 raw-output decoder and comparison tooling.

Do not add video, ncnn, formal benchmark loops, downloads, dependency fetching,
or alternate model-contract handling.

## Allowed Files

```text
TASKS.md
tasks/007_cpp_ort_single_image.md
cpp/CMakeLists.txt
cpp/include/edgeai/backends/ort_detector.hpp
cpp/include/edgeai/common/postprocess.hpp
cpp/src/backends/ort_detector.cpp
cpp/src/common/postprocess.cpp
cpp/apps/ort_image.cpp
cpp/tests/test_postprocess.cpp
tests/python/compare_detections.py
results/images/cpp_ort_reference.png
results/evidence/007/cpp_ort_detections.json
results/evidence/007/python_cpp_ort_comparison.json
results/logs/007_cpp_ort_image.log
```

The ONNX Runtime installation, frozen model/manifest/config, common modules,
Python result, golden fixture, and reference image are read-only inputs.

## Forbidden Files

- Downloaded or vendored ONNX Runtime and FetchContent.
- Changes to Task 002 contract, Python reference/golden result, or Task 006
  preprocessing behavior.
- Video, ncnn, model conversion, or benchmark implementation.
- Global include/library directories when target-level settings work.
- Any file outside Allowed Files.

## Inputs

- Completed Task 006 common library and alignment evidence.
- A user-provided compatible local ONNX Runtime C/C++ installation.
- Frozen model, manifest, inference config, reference image, and Python golden
  detection result.

Missing/incompatible headers or libraries require a stop. CMake must not download
or substitute ONNX Runtime.

## Expected Outputs

- An `edgeai_ort_backend` target and `edgeai_ort_image` executable.
- Actual printed and structured session I/O metadata.
- A nonempty annotated C++ result image and structured detection JSON.
- Real Python/C++ comparison JSON with one-to-one matches and tolerance metrics.

## Implementation Requirements

- Discover ONNX Runtime from an explicit local installation/root and fail clearly
  when headers/library/version are missing or incompatible.
- Use C++17 target-level includes, links, features, warnings, and no extensions.
- Validate model SHA and manifest contract before inference.
- Use CPU execution, record the actual runtime version/provider, and make intra-
  and inter-op thread counts explicit.
- Enumerate and print actual input/output names, shapes, and dtypes; compare all
  values to Task 002 and stop on mismatch.
- Keep runtime-owned names and tensor buffers alive for the required duration.
- Reuse Task 006 input tensor without hidden transpose, normalization, or resize.
- Decode objectness and class scores, use combined confidence, convert `xywh` to
  `xyxy`, apply frozen class-aware NMS, inverse-map, clip, and deterministically
  order detections.
- Emit the same structured fields as Python, including model/image/config hashes.
- Compare one-to-one by class with identical detection count, IoU `>= 0.99`, and
  absolute confidence difference `<= 0.001`. Freeze these values before the first
  acceptance run and do not weaken them.
- Return nonzero for bad arguments, missing files, contract/SHA mismatch, runtime
  errors, non-finite output, or artifact-write failure.

## Build Commands

```bash
rm -rf build/pc-release
cmake \
  -S cpp \
  -B build/pc-release \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DONNXRUNTIME_ROOT=<verified-local-onnxruntime-root>
cmake --build build/pc-release --parallel
```

Record the resolved ONNX Runtime include, library, and version. Do not replace a
configuration failure with automatic fetching.

## Run Commands

```bash
mkdir -p results/images results/evidence/007 results/logs
./build/pc-release/edgeai_ort_image \
  --model models/yolov5n-v7.0/yolov5n.onnx \
  --manifest models/yolov5n-v7.0/manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --output-image results/images/cpp_ort_reference.png \
  --output-json results/evidence/007/cpp_ort_detections.json \
  2>&1 | tee results/logs/007_cpp_ort_image.log
PYTHONPATH=python python3 tests/python/compare_detections.py \
  --reference tests/fixtures/python_ort_golden.json \
  --candidate results/evidence/007/cpp_ort_detections.json \
  --min-iou 0.99 \
  --max-confidence-delta 0.001 \
  --output results/evidence/007/python_cpp_ort_comparison.json
test -s results/images/cpp_ort_reference.png
file results/images/cpp_ort_reference.png
```

## Test Commands

```bash
ctest --test-dir build/pc-release --output-on-failure
python3 -m json.tool results/evidence/007/cpp_ort_detections.json >/dev/null
python3 -m json.tool results/evidence/007/python_cpp_ort_comparison.json >/dev/null
test -s results/images/cpp_ort_reference.png
git diff --check
```

## Acceptance Criteria

- Release configure/build succeeds without warnings using the verified local
  ONNX Runtime installation.
- The executable prints real ONNX Runtime version/provider and complete model I/O.
- Runtime I/O and model SHA exactly match Task 002.
- The common Task 006 input tensor path is reused unchanged.
- Real inference, decoding, NMS, coordinate restore, clipping, and image writing
  succeed.
- The result image is nonempty/decodable and receives human visual approval.
- C++ and Python detection counts/classes match one-to-one; every matched IoU is
  at least `0.99` and confidence delta no more than `0.001`.
- Unit/integration/invalid-input tests and `git diff --check` pass.
- Only Allowed Files changed and all evidence is real.

## Evidence to Preserve

Compiler/CMake/OpenCV/ONNX Runtime versions and paths, Release build log, provider
and thread settings, model I/O, hashes, C++ detections/image, comparison matches
and worst deltas, test output, visual decision, attempts, and final Git status.

## Automatic Retry Rules

At most three full repair loops are allowed for adapter/decoder defects. Do not
change Python, model contract, thresholds, preprocessing, or tolerances. Missing
runtime dependencies, I/O/SHA mismatch, out-of-tolerance results, or visual doubt
requires an immediate stop.

## Human Stop Conditions

All protocol conditions apply, especially dependency/version issues, any model
I/O mismatch, Python/C++ comparison failure, abnormal/empty detections, image
review, or a request to change threading/model/preprocessing.

## Codex Responsibilities

Integrate only the local dependency, print and verify real I/O, reuse common code,
preserve true results, run comparisons/tests, and report failures exactly.

## User Responsibilities

Provide a compatible local ONNX Runtime installation, review the result image and
comparison, and make decisions about dependency or contract incompatibilities.

## Known Risks

- ONNX Runtime distributions expose different CMake/pkg-config layouts.
- C++ API behavior differs across runtime versions.
- NMS ordering can diverge for equal scores.
- Small resize or floating-point differences can move threshold-edge detections.

## Completion Report Format

Report files, dependency resolution/version, build/warnings, model I/O, provider
and threads, real detections/image, Python comparison metrics, tests, attempts,
stops/skips, risks, and Git status.

## Execution Record

Started: `2026-07-21T11:05:45+08:00`

Branch: `feature/pc-batch-b-cpp-ort`

Starting commit: `e4f9483`

Starting Git status: clean (`git status --short --untracked-files=all` produced
no output).

Dependency: Task 006 is `Completed` in local commit `e4f9483`.

Detection comparison tolerances frozen before the first acceptance run:

```text
detection count and class matching: exact
minimum one-to-one class-matched IoU: 0.99
maximum absolute confidence difference: 0.001
```

No C++ ORT detection, comparison, image, or timing has been produced. Repair
attempts: `0`.

### Dependency Audit

Stopped: `2026-07-21T11:07:23+08:00`

Real read-only checks established:

```text
ONNXRUNTIME_ROOT: UNSET
pkg-config --modversion onnxruntime: exit 1
ldconfig ONNX Runtime match: none
system onnxruntime_cxx_api.h / onnxruntime_c_api.h: none found
system libonnxruntime.so*: none found
project .venv C/C++ header or libonnxruntime.so* count: 0
Python onnxruntime: 1.18.1
Python package path: .venv/lib/python3.12/site-packages/onnxruntime/__init__.py
```

The first broad system-library scan also reported
`find: '/usr/lib/modules/6.6.87.2-microsoft-standard-WSL2/lost+found': Permission
denied` and exited `1` before its later checks. That error was preserved; the
audit was completed without elevation using explicit public system include and
library directories. Those searches exited `0` with no matching SDK artifacts.

The Python wheel cannot satisfy this task because it contains neither the C/C++
headers nor a linkable `libonnxruntime.so` artifact. No SDK was downloaded,
installed, copied, or substituted.

### Blocking Report

```text
Current Task: Task 007
Current Status: Blocked
Last Successful Step: Task 006 completed and committed as e4f9483; Task 007 dependency audit completed
Failed Command: local ONNXRUNTIME_ROOT header/library validation block recorded below
Exit Code: 1
Relevant Error: ONNXRUNTIME_ROOT is not set; no compatible C/C++ headers or libonnxruntime were found locally
Files Changed: TASKS.md; tasks/007_cpp_ort_single_image.md
Attempts Made: 0 repair attempts; dependency stop occurred before implementation or build
Why Automatic Recovery Is Unsafe: recovery requires a user-provided ONNX Runtime 1.18.1 C/C++ SDK or an environment change; downloading, installing, or substituting it is prohibited
Exact Human Action Required: provide an extracted official ONNX Runtime 1.18.1 Linux x86_64 C/C++ SDK outside the repository, verify its include/ and lib/ artifacts, set ONNXRUNTIME_ROOT to its absolute root, and authorize read-only use of that path
Commands to Resume: rerun the exact validation block below, then repeat startup audit and CMake configuration with -DONNXRUNTIME_ROOT="$ONNXRUNTIME_ROOT"
Git Status: only TASKS.md and tasks/007_cpp_ort_single_image.md contain the legal Task 007 Blocked-state record
```

Exact failed validation command to rerun after the user supplies the SDK:

```bash
if [ -z "${ONNXRUNTIME_ROOT:-}" ]; then
  echo 'ONNXRUNTIME_ROOT is not set' >&2
  exit 1
fi

test -f "$ONNXRUNTIME_ROOT/include/onnxruntime_cxx_api.h" || {
  echo "missing header: $ONNXRUNTIME_ROOT/include/onnxruntime_cxx_api.h" >&2
  exit 1
}

test -f "$ONNXRUNTIME_ROOT/include/onnxruntime_c_api.h" || {
  echo "missing header: $ONNXRUNTIME_ROOT/include/onnxruntime_c_api.h" >&2
  exit 1
}

test -e "$ONNXRUNTIME_ROOT/lib/libonnxruntime.so" || {
  echo "missing library: $ONNXRUNTIME_ROOT/lib/libonnxruntime.so" >&2
  exit 1
}
```

After that command passes, re-read the protocol and this record, verify the
actual runtime reports version `1.18.1`, and only then resume implementation.

### Recovery Audit

Resumed: `2026-07-21T11:20:59+08:00`

The Codex command process did not inherit the user's shell export, so the first
literal environment check again exited `1` and reported
`ONNXRUNTIME_ROOT is not set`. The user supplied and authorized the exact SDK
path; subsequent commands set that path only in their own process environment.
No shell configuration was changed.

Verified SDK root:
`/home/dministrator/opt/onnxruntime/onnxruntime-linux-x64-1.18.1`

```text
VERSION_NUMBER: 1.18.1
GIT_COMMIT_ID: 387127404e6c1d84b3468c387d864877ed1c67fe
resolved library: lib/libonnxruntime.so.1.18.1
library architecture: ELF 64-bit LSB x86-64
library SHA256: 1147caa734d19f7549f90a659aa9ca444366eeb80a596900d19d242145a9f4c9
ldd missing dependencies: none
minimum C++ probe output: ONNX Runtime version: 1.18.1
minimum probe linked library: authorized SDK libonnxruntime.so.1.18.1
Python ONNX Runtime: 1.18.1
Python providers: AzureExecutionProvider, CPUExecutionProvider
ONNX model SHA256: 78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121
manifest/model SHA match: true
```

The SDK was read only. No SDK file was changed, copied, or staged. The original
blocking record remains above. Task 007 is restored to `In Progress`; repair
attempts remain `0` because the prior stop was an external dependency condition.

### Implementation and Automated Verification

Automated verification stopped for human review at:
`2026-07-21T11:35:13+08:00`.

The implementation adds a target-scoped ONNX Runtime adapter, a single-image
CLI, backend-neutral YOLOv5 postprocessing, focused postprocessing tests, and a
semantic Python/C++ comparison tool. CMake requires the explicit authorized SDK
root and validates its headers, library, and `VERSION_NUMBER` before creating
the ORT targets. The executable embeds an RPATH to that exact SDK directory; a
real `ldd` check resolved `libonnxruntime.so.1.18.1` from that directory with no
missing dependencies.

Verified build environment:

```text
GCC: 13.3.0
CMake: 3.28.3
Ninja: 1.11.1
OpenCV C++: 4.6.0
ONNX Runtime C++: 1.18.1
ONNX Runtime provider: CPUExecutionProvider
intra-op threads: 1
inter-op threads: 1
execution mode: ORT_SEQUENTIAL
build type: Release
compiler warnings: none observed
```

The required clean Release configuration and build completed successfully. The
full CTest run passed `3/3`: common module tests, postprocessing tests, and the
invalid-argument CLI test.

Actual runtime model contract:

```text
model SHA256: 78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121
input: images, FLOAT, [1, 3, 640, 640]
output: output0, FLOAT, [1, 25200, 85]
```

Actual detections, rounded to the structured-output precision:

```text
1 keyboard confidence=0.892058 box=[420.918823, 636.482910, 786.872803, 747.389648]
2 tv       confidence=0.816359 box=[400.534912, 255.551636, 895.718262, 543.927490]
3 cup      confidence=0.707963 box=[252.854919, 613.533691, 348.214050, 771.307129]
4 mouse    confidence=0.394466 box=[870.526550, 716.008606, 970.289490, 787.967590]
5 mouse    confidence=0.274518 box=[185.716171, 676.066406, 253.752640, 712.830078]
```

The comparison passed with exact count/classes, minimum matched IoU
`0.9999999825368343`, and maximum absolute confidence difference
`1.648330683057253e-08`. These are within the pre-frozen `0.99` and `0.001`
tolerances. The annotated image decoded as `(960, 1280, 3)` BGR and is
`1,260,338` bytes. JSON syntax validation and `git diff --check` passed.

Generated evidence:

```text
results/images/cpp_ort_reference.png
  SHA256 57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2
results/evidence/007/cpp_ort_detections.json
  SHA256 6785523b60aa95d13ba696fd7ee42e2acac16f6fa9be18256e2adab7267e50f4
results/evidence/007/python_cpp_ort_comparison.json
  SHA256 bc25a2b0cc49eb72b031ccf7c686346728f900708798aaa78916d8e94b53587b
results/logs/007_cpp_ort_image.log
  SHA256 4f64b67ad9e912d8fab0193b160f9466bb0d20b307a6af64054ddc8f09717c95
```

The log exists and is nonempty but is hidden from ordinary Git status by the
repository's existing `*.log` ignore rule. No ignored SDK, model, build output,
or virtual-environment file was staged.

The single-run stage timings written by the application are diagnostic evidence
only. They are not a formal benchmark and are not approved as performance data.

### Repair Attempt 1

```text
Failure: the first real edgeai_ort_image run exited 1 during session initialization with "cannot create std::vector larger than max_size()"
Root Cause: GetTensorTypeAndShapeInfo returned a non-owning view from a temporary owning TypeInfo; the temporary was destroyed before GetShape read the input dimensions
Files Modified: cpp/src/backends/ort_detector.cpp; cpp/apps/ort_image.cpp (stage diagnostics)
Fix Applied: retain each owning input/output TypeInfo until its tensor shape and dtype have been copied; remove temporary detailed backend diagnostics
Commands Re-run: clean Release configure; full build; CTest; frozen single-image run; Python/C++ comparison; JSON validation; image decode validation; linked-library/RPATH checks; git diff --check
Result: PASS; build 17/17, CTest 3/3, inference succeeded, and semantic comparison passed
```

The initial failing pipeline did not use `pipefail`, so its outer shell status
did not represent the application failure after `tee` and later checks ran. The
application was immediately rerun by itself and its exit status `1` was
confirmed. The repaired acceptance run used `set -euo pipefail`.

An additional read-only evidence-summary helper exited with `KeyError:
'summary'` because it assumed a nonexistent JSON nesting level. This did not
alter artifacts and was not a product/test failure; the JSON schema was then
read directly and the summary plus all checks skipped by that early exit were
rerun successfully.

Total implementation repair attempts: `1` of `3`.

### Human-Review Blocking Report

```text
Current Task: Task 007
Current Status: Blocked
Last Successful Step: all automated acceptance checks passed, including Release build, CTest 3/3, real inference, image decode, and Python/C++ comparison
Failed Command: none; mandatory annotated-image human review is the active stop condition
Exit Code: N/A
Relevant Error: no automated error; visual_review remains PENDING_HUMAN_REVIEW
Files Changed: TASKS.md; tasks/007_cpp_ort_single_image.md; cpp/CMakeLists.txt; cpp/include/edgeai/backends/ort_detector.hpp; cpp/include/edgeai/common/postprocess.hpp; cpp/src/backends/ort_detector.cpp; cpp/src/common/postprocess.cpp; cpp/apps/ort_image.cpp; cpp/tests/test_postprocess.cpp; tests/python/compare_detections.py; results/images/cpp_ort_reference.png; results/evidence/007/cpp_ort_detections.json; results/evidence/007/python_cpp_ort_comparison.json; results/logs/007_cpp_ort_image.log (ignored but present)
Attempts Made: 1 successful complete repair loop of the maximum 3
Why Automatic Recovery Is Unsafe: the protocol requires a human to decide whether boxes, labels, coordinates, clipping, duplicates, and apparent detections are visually credible
Exact Human Action Required: inspect results/images/cpp_ort_reference.png against data/samples/images/pc_reference.jpg and approve or reject box placement, class labels, confidence labels, clipping, duplicate suppression, and the known low-confidence earbud-case mouse false positive
Commands to Resume: repeat startup audit; re-read this Blocked record; rerun the Release build, CTest, exact frozen inference command, comparison command, JSON checks, image decode check, and git diff --check; record the user's visual decision before changing the task state
Git Status: Task 007 allowed source/status/evidence files are modified or untracked; no files are staged and no Task 007 commit exists
```

Task 008 has not started. No video or formal benchmark implementation or result
was produced.

### Human-Review Recovery

Resumed: `2026-07-21T11:41:04+08:00`

The user reported that the `1280x960` annotated image opens correctly and gave
visual approval for all five detections. The keyboard, TV, cup, and real mouse
classes and boxes were judged correct. The second, lower-confidence `mouse`
detection remains on the left-side earbud case exactly as in the Python
baseline. The user classified it as a known model false positive, not a C++
preprocessing, ONNX Runtime, postprocessing, coordinate, clipping, duplicate-
suppression, or visualization difference. No duplicate boxes, systematic
coordinate shift, out-of-bounds boxes, clipped labels, or drawing defects were
reported. Single-run timings remain approved only as diagnostics, never as a
formal benchmark.

This human decision is recorded but completion remains conditional on a fresh
full Release build, CTest run, frozen inference, semantic comparison, artifact
consistency check, and Git checks. Before regeneration, the prior reviewed
evidence was copied read-only to `/tmp` for semantic comparison. Its repository
hashes still matched the preceding blocking record. Branch, Allowed Files,
ONNX Runtime C++ SDK `1.18.1`, Python ORT `1.18.1`, CPU provider availability,
SDK dynamic dependencies, and frozen ONNX SHA256 were revalidated. Task 007 is
therefore restored to `In Progress` without changing any model, image,
threshold, NMS setting, golden result, or tolerance.

### Final Acceptance

Completed: `2026-07-21T11:42:03+08:00`

The post-review recovery validation ran the required sequence from an empty
Release build directory:

```text
rm -rf build/pc-release                                      exit 0
cmake -S cpp -B build/pc-release -G Ninja
      -DCMAKE_BUILD_TYPE=Release
      -DONNXRUNTIME_ROOT=/home/dministrator/opt/onnxruntime/
       onnxruntime-linux-x64-1.18.1                          exit 0
cmake --build build/pc-release --parallel                    exit 0
ctest --test-dir build/pc-release --output-on-failure        exit 0 (3/3 PASS)
edgeai_ort_image with the frozen model/config/image           exit 0
compare_detections.py with IoU 0.99/confidence 0.001          exit 0 (PASS)
both python3 -m json.tool checks                              exit 0
PNG nonempty/file/OpenCV decode checks                       exit 0
reviewed-result semantic consistency check                   exit 0 (PASS)
ldd and RUNPATH checks for authorized ORT SDK                exit 0
git diff --check                                             exit 0
```

The clean rebuild completed all `17/17` Ninja steps with no compiler warnings.
CMake again resolved OpenCV `4.6.0` and ONNX Runtime `1.18.1` from the authorized
read-only SDK. The executable again used `CPUExecutionProvider`, explicit
intra-op/inter-op thread counts `1/1`, and the exact authorized SDK library via
embedded RUNPATH.

The regenerated evidence retained the same model hash, input/output contract,
configuration, source-image identity, letterbox metadata, candidate counts,
detection objects, match objects, tolerance values, and comparison metrics as
the evidence reviewed by the user. The regenerated annotated PNG is byte-for-
byte identical to the reviewed PNG:

```text
results/images/cpp_ort_reference.png
  SHA256 57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2
results/evidence/007/cpp_ort_detections.json
  SHA256 42892e2fcd911936cc81ef36756eda2b7675424154f43d95699b85715b485dd1
results/evidence/007/python_cpp_ort_comparison.json
  SHA256 59c1b1f31fb4ff5765df91e7f377da3ae76d0c5823fef51b685aa7e2f065fd3f
results/logs/007_cpp_ort_image.log
  SHA256 c3363fefd8bebca5c37928fe0ca202d78bde49036b09335f5d8ee60447acdcfe
```

The JSON/log hashes changed from the first run because they contain new real
single-run diagnostic timing values and, for the comparison file, the newly
generated candidate JSON hash. Those timings are explicitly not benchmark
results. Detection semantics and comparison metrics did not change:

```text
detection count: 5
classes: keyboard, tv, cup, mouse, mouse
minimum matched IoU: 0.9999999825368343
maximum absolute confidence difference: 1.648330683057253e-08
comparison status: PASS
image shape: 1280x960
```

Human visual acceptance is `PASS`. The low-confidence `mouse` on the left-side
earbud case matches the Python baseline and is recorded as a YOLOv5n model false
positive. It is not a C++ preprocessing, ONNX Runtime, postprocessing,
coordinate-restoration, clipping, NMS, or visualization discrepancy. The other
mouse, keyboard, TV, and cup detections were approved as correct. No new
duplicate, systematic coordinate shift, boundary error, label clipping, or
drawing defect was observed.

No model, input image, configuration threshold, NMS threshold, golden fixture,
or comparison tolerance was changed. No video work or formal benchmark was
started. No required Task 007 check was skipped. Final Acceptance Criteria:
all passed. Task 007 is `Completed`; the local atomic commit uses the required
message `feat(cpp): add ONNX Runtime image inference` and is the commit
containing this Execution Record.
