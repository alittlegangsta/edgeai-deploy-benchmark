# Task 005

## Title

Add Python unit tests, a fixed sample contract, and a tolerant golden result.

## Status

Completed

## Batch

Batch A

## Dependencies

Task 004 (`Completed`).

## Recommended Branch

`feature/pc-batch-a-python-baseline`

## Recommended Commit

`test(python): add detection golden baseline`

## Goal

Lock the Python reference behavior with focused mathematical unit tests and one
real, auditable golden detection result suitable for later C++ comparisons.

## Why This Task Exists

Small deterministic tests locate geometry and NMS regressions, while a tolerant
end-to-end golden result proves the fixed model/image/configuration still behaves
reasonably without treating every floating-point tensor element as immutable.

## Knowledge Covered

- Testable preprocessing geometry.
- IoU and deterministic class-aware NMS behavior.
- Forward/inverse coordinate mappings and clipping.
- Empty-result handling.
- Stable golden-result design and tolerance-based matching.

## Scope

Add unit tests for pure Python preprocessing/postprocessing functions and an
end-to-end test using the exact model, image, hashes, and thresholds approved in
Tasks 002–004. Preserve a compact golden detection JSON of semantic results.

Do not store a full input/output tensor as golden data, add C++ tests, change the
frozen model, tune thresholds to force a pass, or introduce benchmark assertions.

## Allowed Files

```text
TASKS.md
tasks/005_python_tests_and_golden_result.md
tests/python/test_letterbox.py
tests/python/test_postprocess.py
tests/python/test_golden_detection.py
scripts/run_python_tests.py
tests/fixtures/python_ort_golden.json
tests/fixtures/reference_inputs.json
data/samples/images/pc_reference.jpg
results/images/python_ort_golden_check.png
results/evidence/005/python_ort_replay.json
results/evidence/005/python_test_summary.json
results/logs/005_python_tests.log
```

Implementation from Tasks 002–004 is read-only. A discovered implementation bug
requires returning to the owning task rather than expanding this Allowed list.

## Forbidden Files

- Full tensor dumps as golden artifacts.
- Changes to production implementation, model/manifest, or inference thresholds.
- C++/ncnn/video/benchmark files.
- Downloaded fixtures or large binaries.
- Any file outside Allowed Files.

## Inputs

- Completed and human-reviewed Task 004 result.
- The frozen ONNX and source-model SHA256 values.
- A licensed fixed image with recorded SHA256 and provenance.
- Frozen confidence, IoU, NMS mode, maximum detections, and input geometry.

## Expected Outputs

- Focused tests for letterbox parameters, IoU, NMS, coordinate mapping, empty
  detections, clipping, and output structure.
- `reference_inputs.json` pinning all hashes and thresholds.
- Compact real golden JSON with ordered class IDs/names, confidences, and boxes,
  plus explicit comparison tolerances.
- A machine-readable real test summary and log.

## Implementation Requirements

- Test letterbox scale and split padding for landscape, portrait, exact-size, and
  odd-rounding cases.
- Test IoU for identical, disjoint, partial-overlap, degenerate, and clipped boxes.
- Test deterministic NMS ordering, same-class suppression, different-class
  retention, threshold boundaries, and empty input.
- Test forward and inverse coordinate mapping and final image-bound clipping.
- Validate result schema, finite values, valid class IDs, confidence range, box
  ordering, source dimensions, model/image hashes, and configuration identity.
- Generate the golden result only from the approved real Task 004 invocation.
- Store semantic detections, not complete floating-point tensors or fabricated
  expectations.
- Match detections one-to-one by class, require IoU at least `0.99`, and absolute
  confidence difference at most `0.001`. Freeze these tolerances before the first
  acceptance run; never weaken them during repair.
- Exclude no threshold-edge detection after seeing a failure; any proposed golden
  update requires human review and a recorded reason.
- Produce the test summary from actual test execution, never by hand.

## Build Commands

```bash
python3 -m py_compile \
  scripts/run_python_tests.py \
  tests/python/test_letterbox.py \
  tests/python/test_postprocess.py \
  tests/python/test_golden_detection.py
```

## Run Commands

Re-run the exact frozen Task 004 CLI to a temporary reproducible result, then
compare it without overwriting the approved golden file:

```bash
mkdir -p results/images results/evidence/005 results/logs
PYTHONPATH=python python3 python/apps/ort_image.py \
  --model models/yolov5n-v7.0/yolov5n.onnx \
  --manifest models/yolov5n-v7.0/manifest.json \
  --config configs/yolov5n_v7_inference.json \
  --image data/samples/images/pc_reference.jpg \
  --output-image results/images/python_ort_golden_check.png \
  --output-json results/evidence/005/python_ort_replay.json
```

## Test Commands

```bash
set -o pipefail
PYTHONPATH=python python3 scripts/run_python_tests.py \
  --start-directory tests/python \
  --pattern 'test_*.py' \
  --output results/evidence/005/python_test_summary.json \
  2>&1 | tee results/logs/005_python_tests.log
PYTHONPATH=python python3 -m unittest tests/python/test_golden_detection.py
python3 -m json.tool tests/fixtures/python_ort_golden.json >/dev/null
python3 -m json.tool results/evidence/005/python_test_summary.json >/dev/null
git diff --check
```

## Acceptance Criteria

- All specified letterbox, IoU, NMS, mapping, empty-result, clipping, and schema
  cases execute and pass.
- Fixed model, image, and configuration hashes match the recorded inputs.
- Golden detections came from the real approved Task 004 run.
- Golden comparison passes with IoU `>= 0.99` and confidence delta `<= 0.001`.
- No complete tensor is stored as golden data.
- Tests demonstrate nonzero failure behavior for mismatched hashes and malformed
  results.
- Test summary/log is genuine and agrees with process exit status.
- `git diff --check` passes and only Allowed Files changed.
- No tolerance, threshold, or expected result was weakened after failure.
- Checkpoint A materials are complete, then Codex stops for human review.

## Evidence to Preserve

- Model/image/config hashes and fixture provenance.
- Exact golden-generation command and approved Task 004 artifact reference.
- Golden detections and frozen tolerances.
- Complete real unit-test log and machine summary.
- Repair attempts, final diff check, Git status, and local commit when permitted.

## Automatic Retry Rules

At most three full repair loops may correct test-code defects. A production-code
bug must be fixed under its owning task. Never delete tests, alter golden values,
loosen IoU/confidence tolerances, or change inference thresholds during repair.

## Human Stop Conditions

Stop for hash drift, a proposed golden update, any visual/detection plausibility
question, a production-code defect, missing dependencies, or three failed loops.
Task 005 completion also triggers mandatory Checkpoint A.

## Codex Responsibilities

Keep fixtures compact and traceable, run all tests, distinguish a test defect
from a product defect, preserve genuine output, assemble Checkpoint A, and stop.

## User Responsibilities

Approve the fixed image and its provenance, review the golden detections and
tolerances, inspect all Checkpoint A evidence, and explicitly authorize Batch B.

## Known Risks

- A golden result can overfit one runtime/library build.
- Threshold-edge detections can be unstable.
- Image licensing or accidental recompression can invalidate its hash.
- Unit tests cannot replace visual inspection of the real annotated output.

## Completion Report Format

Report files, pinned hashes/config, test case matrix, real pass/fail counts,
golden comparison/tolerances, Checkpoint A artifacts, attempts, skips, risks, and
final Git status. Stop and await explicit Batch B approval.

## Execution Record

Started: `2026-07-20T17:46:32+08:00`

Branch: `feature/pc-batch-a-python-baseline`

Starting commit: `6f13a27`

Starting Git status: clean (`git status --short --untracked-files=all` produced
no output).

Task 004 dependency: `Completed` in local commit `6f13a27` with human review
status `APPROVED_WITH_KNOWN_MODEL_FALSE_POSITIVE`.

Golden matching tolerances are frozen before the first Task 005 replay:

```text
minimum one-to-one class-matched IoU: 0.99
maximum absolute confidence difference: 0.001
```

The approved Task 004 semantic detections include keyboard, television, cup, one
correct mouse, and one retained low-confidence `mouse` false positive on an
earbud case. Task 005 will preserve all five; it will not exclude the known false
positive, tune thresholds, or edit production code.

Completed: `2026-07-20T17:53:56+08:00`

### Implementation

- Added focused unit coverage for landscape, portrait, exact-size, and odd-pad
  letterbox geometry.
- Added IoU, class-aware NMS, deterministic ordering, threshold-boundary,
  empty-input, inverse mapping, and clipping coverage.
- Added fixed-input and compact semantic-golden fixtures. No full tensor data is
  stored.
- Added a standard-library test runner that records the actual discovery inputs,
  test IDs, counts, duration, failures, errors, skips, environment, and success
  status in JSON.
- Kept Task 002–004 production code, model files, source image, inference config,
  thresholds, and output expectations unchanged.

### Frozen Inputs and Tolerances

```text
source model SHA256: 4f180cf23ba0717ada0badd6c685026d73d48f184d00fc159c2641284b2ac0a3
ONNX SHA256: 78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121
manifest SHA256: 764f3e4980c1f6b18ea245262af99703d13e817fedc52bf97bbfc5a1389f06c2
reference image SHA256: 625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071
configuration SHA256: 82ef24f773a6ffb8e06e26b94747bd1b581408b19adae293b3ecfd8b228ee96d
approved Task 004 PNG SHA256: 57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2
minimum one-to-one class-matched IoU: 0.99
maximum absolute confidence difference: 0.001
```

The Task 005 replay retained the five approved detections in the same order:
`keyboard`, `tv`, `cup`, `mouse`, `mouse`. The first mouse is a correct mouse
detection. The second, lower-confidence mouse is the already reviewed false
positive on an earbud case. It remains recorded as a YOLOv5n model limitation,
not a deployment implementation error.

### Commands and Results

- Build command: `python3 -m py_compile` for the runner and three new test files;
  exit `0` with no output.
- Run command: the exact frozen Task 004 CLI using `CPUExecutionProvider`; exit
  `0`, five detections, and generated both Task 005 replay artifacts.
- Full test command: exit `0`; `43` tests ran in `204.943936 ms`, with zero
  failures, errors, or skips.
- Independent golden test command: exit `0`; `4` tests passed.
- Both required `python3 -m json.tool` commands: exit `0`.
- Required `git diff --check`: exit `0` with no output.
- Read-only post-test comparison: five class-aligned detections, minimum matched
  IoU `1.0`, maximum absolute confidence delta `0.0`.
- OpenCV read-back: `1280x960`, three channels. `file` reported a non-interlaced
  8-bit RGB PNG.

The CLI printed single-run diagnostic timings only. They are not benchmark
results and are not used in the golden acceptance criteria.

### Evidence

```text
tests/fixtures/reference_inputs.json
  SHA256: 5fb080523380e22b602bbe4322227871ff13ba28c35c47ab2de1b7c728a117a9
tests/fixtures/python_ort_golden.json
  SHA256: 9a8fa96233aba0f77fd1196da9c48cc719bb361d97a656e6507ddd50f81dcc4f
results/images/python_ort_golden_check.png
  SHA256: 57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2
  size: 1260338 bytes, 1280x960
results/evidence/005/python_ort_replay.json
  SHA256: fdb9d635b427874b2dd277e240ede5d660fff1a5da2c3f22c21c5a5ec27cdbad
  size: 5798 bytes
results/evidence/005/python_test_summary.json
  SHA256: ce7c59354045a7353b3d206822024d99bff3b7de4be5a515b03f39da57e94e42
  size: 4337 bytes
results/logs/005_python_tests.log
  SHA256: 50cf45bdfe9846ade06582368e42ef1a0822402339947e5c37875ade5f89f99b
  size: 5528 bytes
```

The test log is preserved locally under the repository's ignored `*.log`
policy; it is not force-added. Its real result is also captured by the committed
machine-readable summary and this execution record.

### Attempts and Deviations

Formal repair attempts: `0`. All required build, run, and test commands passed on
their first execution. No tolerance, threshold, golden detection, or production
implementation was changed after the run.

Two supplemental read-only reporting scripts exited `1` because they initially
used `box_xyxy` instead of the actual `box_xyxy_source` key, then `successful`
instead of the actual nested `result.success` key. They did not modify files and
were not required Acceptance Criteria commands. The corrected supplemental audit
then exited `0` and produced the comparison and image dimensions recorded above.

No required item was skipped. Task 005 is `Completed`; mandatory Checkpoint A is
now active, so Batch B must not begin until explicit human approval.
