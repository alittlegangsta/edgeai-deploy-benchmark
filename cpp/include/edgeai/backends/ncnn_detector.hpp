#pragma once

#include "edgeai/common/detection.hpp"
#include "edgeai/common/filesystem.hpp"

#include <cstdint>
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
    bool openmp_compiled{false};
    bool threads_compiled{false};
    bool simpleomp_compiled{false};
    bool compiler_openmp{false};
    std::string effective_parallel_backend{"none"};
    std::string library_sha256;
    std::string private_libgomp_sha256;
    bool vulkan{false};
    bool fp16{false};
    bool packing_layout{true};
    bool fp16_packed{false};
    bool fp16_storage{false};
    bool fp16_arithmetic{false};
    bool bf16{false};
    bool int8{false};
    std::vector<NcnnTensorDescriptor> inputs;
    std::vector<NcnnTensorDescriptor> outputs;
};

// Task 033-only runtime controls.  The historical integer constructor below
// intentionally retains the Task 017/018 1-or-2-thread contract.
struct NcnnRuntimeOptions {
    int threads{1};
    bool use_packing_layout{true};
    bool use_fp16_packed{false};
    bool use_fp16_storage{false};
    bool use_fp16_arithmetic{false};
    bool use_bf16_storage{false};
    bool use_int8_inference{false};
    bool use_int8_packed{false};
    bool use_int8_storage{false};
    bool use_int8_arithmetic{false};
};

struct NcnnRawInferenceResult {
    std::vector<float> values;
    std::vector<std::int64_t> shape;
};

struct NcnnBuildCapabilities {
    bool openmp_compiled{false};
    bool threads_compiled{false};
    bool simpleomp_compiled{false};
    bool compiler_openmp{false};
    std::string effective_parallel_backend{"none"};
    std::string library_sha256;
    std::string private_libgomp_sha256;
};

struct NcnnRuntimeProfile {
    std::string name;
    int configured_threads{1};
    bool requires_frozen_identity{false};
    bool requires_private_libgomp{false};
    std::string expected_parallel_backend;
    std::string expected_library_sha256;
    std::string expected_private_libgomp_sha256;
};

NcnnBuildCapabilities ncnn_build_capabilities();
NcnnRuntimeProfile ncnn_runtime_profile(const std::string& name);
void validate_ncnn_runtime_profile(
    const NcnnRuntimeProfile& profile,
    const NcnnBuildCapabilities& capabilities
);

std::string ncnn_sha256_file(const edgeai::filesystem::path& path);

class NcnnDetector {
public:
    explicit NcnnDetector(
        const edgeai::filesystem::path& manifest_path,
        int threads = 1,
        const edgeai::filesystem::path& param_path = {},
        const edgeai::filesystem::path& bin_path = {}
    );
    explicit NcnnDetector(
        const edgeai::filesystem::path& manifest_path,
        const NcnnRuntimeOptions& options,
        const edgeai::filesystem::path& param_path = {},
        const edgeai::filesystem::path& bin_path = {}
    );
    ~NcnnDetector();

    NcnnDetector(NcnnDetector&&) noexcept;
    NcnnDetector& operator=(NcnnDetector&&) noexcept;
    NcnnDetector(const NcnnDetector&) = delete;
    NcnnDetector& operator=(const NcnnDetector&) = delete;

    const NcnnRuntimeInfo& runtime_info() const;
    const edgeai::filesystem::path& param_path() const;
    const edgeai::filesystem::path& bin_path() const;
    const std::string& param_sha256() const;
    const std::string& bin_sha256() const;
    NcnnRawInferenceResult infer(const edgeai::common::InputTensor& tensor);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace edgeai::backends
