#pragma once

#include "edgeai/common/detection.hpp"

#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

namespace edgeai::unified {

struct RawInferenceResult {
    std::vector<float> values;
    std::vector<std::int64_t> shape;
};

struct BackendInfo {
    std::string backend;
    std::string model_identity;
    std::string precision;
    std::string input_dtype;
    std::string output_dtype;
    std::vector<std::int64_t> input_shape;
    std::vector<std::int64_t> output_shape;
    std::string runtime;
};

struct BackendOptions {
    std::string backend;
    std::string precision{"fp32"};
    std::filesystem::path model;
    std::filesystem::path manifest;
    std::filesystem::path model_param;
    std::filesystem::path model_bin;
    int threads{2};
    bool packing{true};
};

class InferenceBackend {
public:
    virtual ~InferenceBackend() = default;
    virtual const BackendInfo& info() const = 0;
    virtual RawInferenceResult infer(const edgeai::common::InputTensor& tensor) = 0;
};

std::unique_ptr<InferenceBackend> make_inference_backend(const BackendOptions& options);

}  // namespace edgeai::unified
