#pragma once

#include "edgeai/common/detection.hpp"

#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

namespace edgeai::backends {

struct NcnnTensorDescriptor {
    std::string name;
    std::vector<std::int64_t> logical_shape;
    std::string dtype;
    int dims{0};
    int w{0};
    int h{0};
    int d{0};
    int c{0};
    int elempack{1};
    int elembits{32};
};

struct NcnnRuntimeInfo {
    std::string version;
    std::string execution_provider{"ncnn CPU"};
    int threads{1};
    bool vulkan{false};
    bool fp16{false};
    bool bf16{false};
    bool int8{false};
    std::vector<NcnnTensorDescriptor> inputs;
    std::vector<NcnnTensorDescriptor> outputs;
};

struct NcnnRawInferenceResult {
    std::vector<float> values;
    std::vector<std::int64_t> shape;
};

std::string ncnn_sha256_file(const std::filesystem::path& path);

class NcnnDetector {
public:
    explicit NcnnDetector(const std::filesystem::path& manifest_path, int threads = 1);
    ~NcnnDetector();

    NcnnDetector(NcnnDetector&&) noexcept;
    NcnnDetector& operator=(NcnnDetector&&) noexcept;
    NcnnDetector(const NcnnDetector&) = delete;
    NcnnDetector& operator=(const NcnnDetector&) = delete;

    const NcnnRuntimeInfo& runtime_info() const;
    const std::filesystem::path& param_path() const;
    const std::filesystem::path& bin_path() const;
    const std::string& param_sha256() const;
    const std::string& bin_sha256() const;
    NcnnRawInferenceResult infer(const edgeai::common::InputTensor& tensor);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace edgeai::backends
