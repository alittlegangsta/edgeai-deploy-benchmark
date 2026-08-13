# Final benchmark provenance (Task 040)

Task 040 freezes existing evidence; it does not rerun a workload. The authoritative
YOLOv5n contract is the frozen v7.0 ONNX model, batch 1, 640x640 FP32 input,
raw `[1,25200,85]` FP32 output without graph NMS, shared letterbox/preprocess,
confidence 0.25 and NMS IoU 0.45 for deployment outputs.

## Authority and scope

- **Formal benchmark:** Task030 PC C++ ORT; Task035 paired DR ncnn FP32/EQ
  INT8; Task037 TensorRT FP32/FP16. Each row retains its own warmup, repeat,
  stage and resource protocol. The final table does not claim a cross-hardware
  speedup.
- **TensorRT timing boundary:** Task037's `inference_wall_ms` is the host wall
  time of `TensorRtDetector::infer()` and includes asynchronous H2D, `enqueueV3`,
  asynchronous D2H, event synchronization and timing queries. It is the
  cross-backend `backend_inference_ms` field: FP32 `3.712445 ms`, FP16
  `3.716104 ms`. The separate `gpu_execution_ms` field is the CUDA event around
  `enqueueV3` only and excludes transfers: FP32 `1.674261 ms`, FP16
  `1.370379 ms`, a `1.221751x` GPU execution speedup. Pipeline remains
  `9.283727 ms` to `9.408935 ms`, so FP16 does not improve end-to-end timing.
  Task038's unified-app integration backend-call means (`4.255539 ms` FP32 and
  `7.397064 ms` FP16) use a different run and timing context and are retained
  only under integration evidence.
- **Optimization reference:** Task033 freezes the accepted DR ncnn runtime
  configuration (`threads=2`, default scheduling, packing on, FP32). Task035
  supplies the paired formal FP32/EQ numbers used for the final ARM trade-off.
- **Integration evidence:** Task038 unified C++ image timings and Task039
  video/camera timings show interface integration only. They do not replace
  formal backend benchmarks. The DR camera run is synchronous, queue capacity 0,
  and is not a realtime benchmark.
- **Functional control:** Task036 proves the vendor face model uses
  `Alnpu | ALHardNPU` with CPU fallback disabled. It is a different model and
  is not a YOLOv5n speed result.
- **Vendor-blocked:** custom DR YOLOv5n NPU remains `WAITING_FOR_VENDOR_INPUT`
  and `NOT_BENCHMARKED`; no CPU fallback or synthetic NPU performance is claimed.

## Reproducibility

`authoritative_results.json` contains a SHA256 and role for every source evidence
file. The validator recomputes those hashes and checks the fixed model contract,
formal/integration classifications, COCO gates, NPU boundaries and same-platform
trade-off arithmetic. Prior Task evidence is read-only for this task.

The `recorded_at_wsl` field is manifest-recording time, not a benchmark timestamp.
