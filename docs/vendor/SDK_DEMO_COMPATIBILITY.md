# SDK_2025_07 and Milianke Demo compatibility

## Result

Overall status: **DEMO_LIKELY_MATCHES_SDK_2025_07**.

The SDK identity is explicit (`buildroot/rel_ver` = `SDK_2025_07`). The Demo
does not contain an explicit SDK tag or release manifest. It does contain
`<IDE_Version>2025.07</IDE_Version>`, `SDK_VERSION=20250905`, DR1M90GEG400
project settings, and matching AArch64/FPSoC source conventions. Those facts
support a probable match only; they do not prove exact release compatibility.

The official `SDK_2026.01` repository was not used to fill gaps and must not be
mixed into this SDK_2025_07 decision.

## Compatibility matrix

| Component | SDK/Demo evidence | Status |
| --- | --- | --- |
| Release identity | SDK marker `SDK_2025_07`; Demo date markers only | probable_match |
| DR1M90GEG400 target | Demo settings and `CHIP=dr1m90` | matched |
| Linux AArch64 compiler | Matching archive; extracted compiler missing | unknown |
| Bare-metal AArch64 compiler | Matching archive; extracted compiler missing | unknown |
| Buildroot | AArch64/glibc/GCC7 defconfig present; generated outputs absent | probable_match |
| Arm NN | AArch64 Arm NN 32.1.0/parser 24.6.0 present | matched |
| Arm NN CMake closure | Serializer/deserializer and `libprotoc` gaps | mismatch |
| OpenCV | AArch64 OpenCV 4.7.0 package present | matched |
| OpenCV runtime closure | FFmpeg dependencies and build-host RPATH | unknown |
| NPU interface | Arm NN `Alnpu` backend; no standalone runtime | probable_match |
| Kernel modules | Source exists; zero `.ko` binaries | missing |
| HPF/bitstream | Artifacts exist; release provenance unknown | unknown |
| CMake | Minimum 3.15 in source; VM has no CMake | missing |

The detailed machine-readable matrix is
`.knowledge/manifests/sdk_demo_compatibility.yaml`.

## Decisions

| Action | Decision |
| --- | --- |
| Extract the required toolchain | GO in a separately approved next phase; not done here |
| Install CMake | HOLD; requires an explicit dependency/environment decision |
| Compile AArch64 Hello World | HOLD until compiler and sysroot are validated |
| Compile a minimal NPU Demo | HOLD until toolchain, CMake, package closure, drivers, HPF, and runtime are validated |
| Run NPU or load drivers | HOLD; no board runtime evidence was collected |

## Evidence boundary

No compiler, SDK script, build system, Demo executable, model, kernel module,
or NPU runtime was executed. No toolchain archive was extracted. The original
SDK archive hash remains unchanged. The absence of `.ko` files in the trees is
an inventory fact, not proof that a booted target lacks modules.
