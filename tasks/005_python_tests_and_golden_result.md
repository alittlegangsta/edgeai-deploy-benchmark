# Task 005

## Title

Add Python unit tests, a fixed sample contract, and a tolerant golden result.

## Status

Planned

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

Not started. No golden detections or test results have been generated.
