#include "edgeai/backends/ncnn_detector.hpp"
#include "edgeai/common/filesystem.hpp"

#include <iostream>
#include <stdexcept>

namespace {

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

void run_test() {
    const edgeai::filesystem::path repository = EDGEAI_REPOSITORY_ROOT;
    const auto manifest = repository / "models/yolov5n-v7.0/ncnn_manifest.json";
    edgeai::backends::NcnnRuntimeOptions options;
    options.threads = 1;
    options.use_packing_layout = false;
    edgeai::backends::NcnnDetector detector(manifest, options);
    require(detector.runtime_info().threads == 1, "profiler thread option was not preserved");
    require(!detector.runtime_info().packing_layout, "packing option was not preserved");
    bool rejected = false;
    try {
        edgeai::backends::NcnnRuntimeOptions invalid;
        invalid.threads = 5;
        edgeai::backends::NcnnDetector bad(manifest, invalid);
    } catch (const std::runtime_error&) {
        rejected = true;
    }
    require(rejected, "profiler accepted a thread count outside [1,4]");
}

}  // namespace

int main() {
    try {
        run_test();
        std::cout << "arm CPU profiler tests: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "arm CPU profiler tests: FAIL: " << error.what() << '\n';
        return 1;
    }
}
