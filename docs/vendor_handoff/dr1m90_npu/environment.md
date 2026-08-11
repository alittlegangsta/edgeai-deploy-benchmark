# Reproduction identity

All values below are copied from Task 028 evidence. Paths to vendor or VM
material are intentionally redacted to repository-relative labels.

## Board and hardware context

| Field | Recorded identity |
|---|---|
| Board | MLK-F3P-CZ02 |
| SoC/package context | DR1M90 / DR1M90GEG400 |
| Linux | `6.1.111-rt42`, AArch64 |
| OS | Buildroot `2022.02.6` |
| CMA | 128 MiB (`CmaTotal=131072 KiB` in the retained probe) |
| Tutorial platform bitstream | `e40536cdc035cb707a50dd86c5f1858a5d11e33cfd39faa03c8b0ab483b57fb5` |
| Tutorial system.dtb | `e1ddd7405245d7b9f644c64066bda64369edbac0d8e8676564261d9cfc22b979` |
| SoftNPU context | `NPU_SOFT=1`, `SOFT_NN=1`, `SOFT_YOLO=1`, `SOFT_RESIZE=1` |
| NPU state at retained probe | `cma_mem`, `hard_npu`, `soft_npu`; all three device nodes present |

The D20.1 AD101V20/DR1M90GEG484 package is not a substitute: Task 028 records
different SoftNPU address/IRQ, VDMA topology and `SOFT_RESIZE` settings.

## Source and host conversion identity

| Field | Value |
|---|---|
| Source repository | `dr1m90_npu` |
| Source branch | `release` |
| Source commit | `199ef4d71f453bb9a000102ff39def09c4cf73f9` |
| Exact tag at HEAD | none; nearest ancestor `SDK_2026.01` at `a06f09a23582900e2b8843d564ea28db679649a5` |
| `AL_onnx_pass.py` SHA256 | `f61bc7ab424726d08881f1e9ef8a3fbcfbee8fdcb612eeb6d944c450aed4540a` |
| Vendor requirements SHA256 | `c40f36e292ea2d3d921d8cada6016100fbacc399d260cb77e8d5d77b2a6a5c49` |
| Host pip freeze SHA256 | `7b077b4fcef14e44f97b9d4c64d3ef7d6768e18d8ce2252dcbe90b09e4da057b` |
| Host ONNX | `1.22.0` |
| Host ONNX Runtime | `1.28.0` |
| Host Python | `3.12.3` |
| CMake | `3.16.9` |
| AArch64 compiler | Linaro GCC `7.5.0` |

`AL_onnx_pass.py` is an Arm NN/ONNX preparation path. It does not emit
`rt.bin`/`weight.bin` and does not call a native `npu_runtime` API.

## Runtime and runner identity

| Asset | Version / SHA256 |
|---|---|
| Arm NN runtime | `v32.1.0`, marker `ed5ae24` |
| `libarmnn.so.32.1` | `5def7ba75e4b59644be6f58deaf8b2bb3791c62ed38b52b6aea08b11a8f728ce` |
| `libarmnnOnnxParser.so.24.6` | `dcb43bc092ec283364806e563fa6aa8d2404eb7c005db44081821da405c5ce99` |
| `libprotobuf.so.23` used in closure | `5d69d988c4b8309bb5dc9318c010bac6a16904549ffd38ce11f65a918376e265` |
| Arm NN archive | `867e347bb758f9b1b083c35e08a74f2b3cc39c2975ac0f8e18c25f7f35749526` |
| Diagnostic AArch64 runner | `c6c55b1df88d89a4507a2526f2198a7cbddb2ccc7bf8e881cf38d40e3f1a2d02` |
| Earlier AArch64 runner | `d50a243787f52e7ce8b11d2ff5ca54db53e401e1d7afc64ba3ac193d765e99b8` |

The release runtime objects compared byte-for-byte equal to the retained board
runtime. User-space runtime skew is therefore `NOT_PROVEN`, not a conclusion.

## Model and input identity

| Asset | SHA256 / contract |
|---|---|
| Frozen YOLOv5n v7.0 FP32 opset 12 | `78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121` |
| YOLOv5n input | `625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071` |
| YOLOv5n contract | FP32 `[1,3,640,640]` → `[1,25200,85]`, no graph NMS |
| Face positive control | `5ed304f1cfd37a6c4ddc789a58a4c98e3472efe31eff62fc9e447163ea60668` |
| Vendor YOLOv8n control | `5fa7e8ee047a118c500736cf6b1f24bf1d4ec5120661b10ba661e662f9371d96` |
