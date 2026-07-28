# Anlogic DR1 YOLOv5n ncnn single-image validation

## Outcome

The MLK-F3P-CZ02-DR1M90 ran the frozen YOLOv5n ncnn single-image pipeline on
its AArch64 CPU. The application exited zero, produced five valid detections,
and reached the pre-registered target comparison gate:

```text
minimum class-matched IoU: 0.999985507578
maximum confidence delta: 0.0000050067901611328125
comparison: PASS_TARGET
```

The returned PNG decodes as `1280x960x3` and its SHA256 is byte-identical to
the approved PC C++ ncnn PNG. Automated correctness passes, and the user
subsequently approved the visual result. Task 014 is `Completed`.

This run is functional evidence only. Its single diagnostic timings are not
benchmark results.

## Frozen lineage

The run reused ncnn tag `20240410`, commit
`56775de50990ab7f16627efdcf5529b49541206f`, and the Task 013 static library:

```text
libncnn.a
5c905cd8f6824bc890a076a47fb540aecf9e676d27420ff3e5d6aed6737a0b8a
```

No model conversion ran. The deployed inputs were:

| Input | SHA256 |
|---|---|
| ncnn param | `72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4` |
| ncnn bin | `658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0` |
| fixed JPEG | `625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071` |
| model manifest | `9b3fa287c109a9d2d8928ed959ac363e559e3feea24364b31977b0fc85020cff` |
| inference config | `82ef24f773a6ffb8e06e26b94747bd1b581408b19adae293b3ecfd8b228ee96d` |

The runtime contract remained CPU-only, FP32, batch 1, `640x640`, one thread,
input `in0`, output `out0`, confidence `0.25`, class-aware NMS IoU `0.45`, and
COCO-80.

## Shared implementation

The ARM target compiles the existing PC Stage 3 modules:

- configuration and frozen COCO-80 names;
- OpenCV letterbox, BGR-to-RGB, HWC-to-CHW, and FP32 normalization;
- the ncnn manifest/hash/blob/runtime adapter;
- YOLOv5 decode, thresholding, class-aware NMS, inverse mapping, and clipping;
- JSON serialization and OpenCV annotation.

The only compatibility addition is a filesystem namespace shim for the
validated GCC 7.5 toolchain. Newer compilers keep standard C++17
`std::filesystem`; GCC 7 uses its corresponding experimental implementation
and `libstdc++fs`. No ARM-specific inference algorithm was introduced.

Video targets are controlled by `EDGEAI_ENABLE_VIDEO`; Task 014 disables that
option and resolves only OpenCV `core`, `imgproc`, and `imgcodecs`.

## Cross-build

The VM used CMake 3.16.9, Linaro GCC/G++ 7.5.0, the glibc 2.25 sysroot, the
Task 013 ncnn install tree, and the SDK OpenCV 4.7.0 AArch64 package. The clean
Task 014 source archive hash was:

```text
ad7adebb6e4ad9a4b93c7db40ef8dd626bf3467b9350c87ff6eeda588d8a422e
```

The successful executable is:

```text
ELF64 AArch64
interpreter: /lib/ld-linux-aarch64.so.1
maximum GLIBC requirement: GLIBC_2.17
maximum GLIBCXX requirement: GLIBCXX_3.4.21
SHA256: a4d3f1a405284881d2c2bd9790033b3997d02de69142644b4d2c24dbb55056f1
```

Its direct dynamic dependencies are OpenCV `imgcodecs`, `imgproc`, and `core`
plus the target C/C++ system libraries. It has no Vulkan, Python, or OpenMP
runtime dependency. The OpenCV package config embedded its VM library path as
an RPATH; the board invocation deliberately uses the package-private `lib`
directory through `LD_LIBRARY_PATH`, and no board system library was changed.

## Deployment and board execution

The isolated board path is:

```text
/root/edgeai/yolov5n-ncnn-single-image
```

The deployment package records every file hash. Its manifest and SHA list are:

```text
deployment_manifest.json
6d02105089d6a79c420f19cb66373f410e7098bd0366784ddc61754d4f76b173

SHA256SUMS
ab50df6e0ce70ff45845a4e753b29a79d7c7d79f57381fd1a49bd3c5ca911ae1
```

Board-side hashes passed before and after the executable bit change. `ldd`
resolved the three packaged OpenCV SONAMEs from the private directory and all
remaining libraries from `/lib`; no entry was `not found`.

The board reported AArch64, Buildroot 2022.02.6, kernel 6.1.111-rt42, and
glibc 2.25. Its clock remains unsynchronized, so the WSL capture time rather
than the board date establishes evidence ordering.

The real stdout reported ncnn `1.0.20240410`, one thread, the expected model and
input hashes, the fixed blob contracts, and these detections:

| Rank | Class | Confidence |
|---:|---|---:|
| 1 | keyboard | 0.892053 |
| 2 | tv | 0.816357 |
| 3 | cup | 0.707961 |
| 4 | mouse | 0.394462 |
| 5 | mouse | 0.274514 |

The known low-confidence earbud-case `mouse` false positive remains present.
Stderr was empty and the exit code was zero.

## Correctness evidence

| Artifact | SHA256 |
|---|---|
| [board detections](../../results/evidence/014/anlogic_arm_ncnn_detections.json) | `e93a3489d24632a5ff9327a3364a9a62753cfb8d0969994bd62525dabe47dd2c` |
| [PC/ARM comparison](../../results/evidence/014/anlogic_arm_ncnn_comparison.json) | `fee041817ffd1bf36b9beae4bb98cc9cca7baad3773e19c006c3f0a01eac0e92` |
| [validation summary](../../results/evidence/014/anlogic_arm_ncnn_validation.json) | `e5f7c13831cb7134064e6ca180c5aab30f5c15fe7b19ccf05f4812a23985b342` |
| [annotated board image](../../results/images/anlogic_arm_ncnn_reference.png) | `57dd15410b66da0ef30c08ddb6d077c37698c6cfc9b4d876d8882270459645f2` |

The JSON parses, all values are finite, boxes are legal, count/classes match,
and the comparison reaches `PASS_TARGET`.

## Repair record

1. The first cross-build showed that GCC 7.5 lacks the standard
   `<filesystem>` header. A narrow compiler compatibility alias and old-GNU
   `stdc++fs` link were added; no algorithm changed.
2. The second cross-build showed that its experimental path type lacks
   `lexically_normal()`. Nonessential normalization was removed and paths
   remain absolute and hash-validated.
3. The third clean cross-build passed.
4. The first board orchestration attempt wrote environment evidence before
   creating `results/`; the ELF had not run. The script was corrected to
   create the directory and reuse only the hash-validated task package.
5. The second board attempt passed end to end.

## Human visual acceptance

The user inspected
[the returned board image](../../results/images/anlogic_arm_ncnn_reference.png)
and recorded `PASS`. The WSL record time is
`2026-07-28T16:11:11+08:00`; it is not a board runtime timestamp.

The user confirmed normal decoding and display, normal boxes/class/confidence
text, reasonable `keyboard`, `tv`, `cup`, and `mouse` placement, retention of
the known low-confidence earbud-case `mouse` false positive, no black frame or
visual/coordinate/text corruption, and visual consistency with the PC ncnn
golden.

```text
Task 014: Completed
automated correctness: PASS_TARGET
human visual check: PASS
human visual approval source: user
Task 015: Planned
NPU: HOLD
```

No formal benchmark, video, camera, Vulkan, FP16/BF16/INT8 inference, NPU
workflow, frozen model/input/threshold change, or PC-golden change occurred.
