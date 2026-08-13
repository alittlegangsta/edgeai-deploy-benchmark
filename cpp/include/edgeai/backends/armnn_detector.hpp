#pragma once

#include "edgeai/common/detection.hpp"
#include "edgeai/common/filesystem.hpp"

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace edgeai::backends {

struct ArmnnTensorDescriptor {
    std::string name;
    std::vector<std::int64_t> shape;
    std::string dtype;
    std::size_t bytes{0};
    float quantization_scale{1.0F};
    std::int64_t quantization_offset{0};
};

struct ArmnnRawTensor {
    std::string name;
    std::vector<std::int64_t> shape;
    std::vector<float> values;
};

struct ArmnnRuntimeInfo {
    std::string version;
    std::string requested_backend{"Alnpu"};
    bool fallback_allowed{false};
    bool requested_backend_registered{false};
    std::string load_status;
    std::string load_error;
    std::vector<std::string> supported_backends;
    std::vector<std::string> optimizer_messages;
    ArmnnTensorDescriptor input;
    ArmnnTensorDescriptor output;
    std::vector<ArmnnTensorDescriptor> outputs;
};

struct ArmnnRawInferenceResult {
    std::vector<float> values;
    std::vector<std::int64_t> shape;
    std::vector<ArmnnRawTensor> tensors;
};

std::string armnn_sha256_file(const edgeai::filesystem::path& path);

class ArmnnDetector {
public:
    explicit ArmnnDetector(const edgeai::filesystem::path& model_path);
    ~ArmnnDetector();

    ArmnnDetector(ArmnnDetector&&) noexcept;
    ArmnnDetector& operator=(ArmnnDetector&&) noexcept;
    ArmnnDetector(const ArmnnDetector&) = delete;
    ArmnnDetector& operator=(const ArmnnDetector&) = delete;

    const ArmnnRuntimeInfo& runtime_info() const;
    const edgeai::filesystem::path& model_path() const;
    const std::string& model_sha256() const;
    ArmnnRawInferenceResult infer(const edgeai::common::InputTensor& tensor);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace edgeai::backends
