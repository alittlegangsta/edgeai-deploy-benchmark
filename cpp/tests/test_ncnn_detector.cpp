#include "edgeai/backends/ncnn_detector.hpp"

#include <cmath>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

void run_contract_test() {
    const std::filesystem::path repository = EDGEAI_REPOSITORY_ROOT;
    const std::filesystem::path manifest =
        repository / "models/yolov5n-v7.0/ncnn_manifest.json";
    edgeai::backends::NcnnDetector detector(manifest, 1);
    const auto& runtime = detector.runtime_info();
    require(runtime.version == "1.0.20240410", "unexpected ncnn version");
    require(runtime.execution_provider == "ncnn CPU", "unexpected execution provider");
    require(runtime.threads == 1, "unexpected thread count");
    require(!runtime.vulkan && !runtime.fp16 && !runtime.bf16 && !runtime.int8,
            "non-FP32 CPU option is enabled");
    require(runtime.inputs.size() == 1U && runtime.outputs.size() == 1U,
            "unexpected blob count");
    require(runtime.inputs[0].name == "in0" && runtime.outputs[0].name == "out0",
            "unexpected blob names");

    const edgeai::backends::NcnnBuildCapabilities openmp_capabilities{
        true,
        true,
        false,
        true,
        "openmp",
        "bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3",
        "87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91",
    };
    edgeai::backends::validate_ncnn_runtime_profile(
        edgeai::backends::ncnn_runtime_profile("recommended-dual-thread"),
        openmp_capabilities
    );
    auto invalid_openmp_capabilities = openmp_capabilities;
    invalid_openmp_capabilities.openmp_compiled = false;
    invalid_openmp_capabilities.compiler_openmp = false;
    invalid_openmp_capabilities.effective_parallel_backend = "none";
    bool invalid_profile_rejected = false;
    try {
        edgeai::backends::validate_ncnn_runtime_profile(
            edgeai::backends::ncnn_runtime_profile("recommended-dual-thread"),
            invalid_openmp_capabilities
        );
    } catch (const std::runtime_error&) {
        invalid_profile_rejected = true;
    }
    require(invalid_profile_rejected, "OpenMP-off dual-thread profile was accepted");
    auto wrong_library_capabilities = openmp_capabilities;
    wrong_library_capabilities.library_sha256 = std::string(64U, '0');
    bool wrong_library_rejected = false;
    try {
        edgeai::backends::validate_ncnn_runtime_profile(
            edgeai::backends::ncnn_runtime_profile("recommended-dual-thread"),
            wrong_library_capabilities
        );
    } catch (const std::runtime_error&) {
        wrong_library_rejected = true;
    }
    require(wrong_library_rejected, "wrong ncnn library identity was accepted");
    auto missing_libgomp_capabilities = openmp_capabilities;
    missing_libgomp_capabilities.private_libgomp_sha256.clear();
    bool missing_libgomp_rejected = false;
    try {
        edgeai::backends::validate_ncnn_runtime_profile(
            edgeai::backends::ncnn_runtime_profile("recommended-dual-thread"),
            missing_libgomp_capabilities
        );
    } catch (const std::runtime_error&) {
        missing_libgomp_rejected = true;
    }
    require(missing_libgomp_rejected, "dual-thread profile without libgomp was accepted");

    edgeai::backends::NcnnDetector explicit_detector(
        manifest,
        1,
        repository / "models/yolov5n-v7.0/yolov5n.ncnn.param",
        repository / "models/yolov5n-v7.0/yolov5n.ncnn.bin"
    );
    require(
        explicit_detector.param_sha256() == detector.param_sha256() &&
            explicit_detector.bin_sha256() == detector.bin_sha256(),
        "explicit model paths differ from the manifest contract"
    );

    edgeai::backends::NcnnDetector two_thread_detector(
        manifest,
        2,
        repository / "models/yolov5n-v7.0/yolov5n.ncnn.param",
        repository / "models/yolov5n-v7.0/yolov5n.ncnn.bin"
    );
    require(
        two_thread_detector.runtime_info().threads == 2,
        "two-thread experiment setting was not preserved"
    );

    bool invalid_threads_rejected = false;
    try {
        edgeai::backends::NcnnDetector invalid_detector(manifest, 3);
    } catch (const std::runtime_error&) {
        invalid_threads_rejected = true;
    }
    require(invalid_threads_rejected, "unsupported ncnn thread count was accepted");

    edgeai::common::InputTensor input;
    input.shape = {1, 3, 640, 640};
    input.values.assign(1U * 3U * 640U * 640U, 0.0F);
    const auto output = detector.infer(input);
    require(output.shape == std::vector<std::int64_t>({1, 25200, 85}),
            "unexpected output shape");
    require(output.values.size() == 1U * 25200U * 85U, "unexpected output size");
    for (const float value : output.values) {
        require(std::isfinite(value), "non-finite output");
    }

    input.shape = {1, 3, 320, 320};
    bool rejected = false;
    try {
        static_cast<void>(detector.infer(input));
    } catch (const std::runtime_error&) {
        rejected = true;
    }
    require(rejected, "invalid input contract was accepted");
}

}  // namespace

int main() {
    try {
        run_contract_test();
        std::cout << "ncnn detector tests: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "ncnn detector tests: FAIL: " << error.what() << '\n';
        return 1;
    }
}
