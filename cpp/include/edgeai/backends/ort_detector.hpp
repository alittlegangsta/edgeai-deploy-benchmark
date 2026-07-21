#pragma once

#include "edgeai/common/detection.hpp"

#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

namespace edgeai::backends {

struct TensorDescriptor {
    std::string name;
    std::vector<std::int64_t> shape;
    std::string dtype;
};

struct OrtRuntimeInfo {
    std::string version;
    std::string execution_provider;
    int intra_op_threads{1};
    int inter_op_threads{1};
    std::vector<TensorDescriptor> inputs;
    std::vector<TensorDescriptor> outputs;
};

struct RawInferenceResult {
    std::vector<float> values;
    std::vector<std::int64_t> shape;
};

std::string sha256_file(const std::filesystem::path& path);

class OrtDetector {
public:
    OrtDetector(
        const std::filesystem::path& model_path,
        const std::filesystem::path& manifest_path,
        int intra_op_threads = 1,
        int inter_op_threads = 1
    );
    ~OrtDetector();

    OrtDetector(OrtDetector&&) noexcept;
    OrtDetector& operator=(OrtDetector&&) noexcept;
    OrtDetector(const OrtDetector&) = delete;
    OrtDetector& operator=(const OrtDetector&) = delete;

    const OrtRuntimeInfo& runtime_info() const;
    const std::string& model_sha256() const;
    RawInferenceResult infer(const edgeai::common::InputTensor& tensor);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace edgeai::backends
