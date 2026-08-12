#pragma once

#include "edgeai/common/detection.hpp"

#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

namespace edgeai::backends {

struct TensorRtGpuTimingsMs {
    double host_to_device{0.0};
    double inference{0.0};
    double device_to_host{0.0};
};

struct TensorRtRawResult {
    std::vector<float> values;
    std::vector<std::int64_t> shape;
    TensorRtGpuTimingsMs gpu_timings;
};

struct TensorRtRuntimeInfo {
    std::string engine_path;
    std::string input_name;
    std::string output_name;
    std::vector<std::int64_t> input_shape;
    std::vector<std::int64_t> output_shape;
    std::string input_dtype;
    std::string output_dtype;
    std::string precision_mode;
    std::string device_name;
    int compute_capability_major{0};
    int compute_capability_minor{0};
    std::size_t device_memory_bytes{0};
};

class TensorRtDetector {
public:
    explicit TensorRtDetector(const std::filesystem::path& engine_path);
    ~TensorRtDetector();

    TensorRtDetector(TensorRtDetector&&) noexcept;
    TensorRtDetector& operator=(TensorRtDetector&&) noexcept;
    TensorRtDetector(const TensorRtDetector&) = delete;
    TensorRtDetector& operator=(const TensorRtDetector&) = delete;

    const TensorRtRuntimeInfo& runtime_info() const;
    TensorRtRawResult infer(const edgeai::common::InputTensor& tensor);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace edgeai::backends
