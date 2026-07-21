#include "edgeai/common/benchmark.hpp"

#include <cmath>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

int failures = 0;

void check(bool condition, const std::string& description) {
    if (!condition) {
        ++failures;
        std::cerr << "FAIL: " << description << '\n';
    }
}

void expect_throws(const std::function<void()>& operation, const std::string& description) {
    try {
        operation();
        check(false, description);
    } catch (const std::exception&) {
        check(true, description);
    }
}

edgeai::common::Detection detection(
    int class_id,
    const std::string& class_name,
    float confidence,
    edgeai::common::Box box
) {
    edgeai::common::Detection value;
    value.class_id = class_id;
    value.class_name = class_name;
    value.confidence = confidence;
    value.box_xyxy_source = box;
    return value;
}

void test_sample_sum() {
    const auto sample = edgeai::common::make_benchmark_sample(11, 22, 33);
    check(sample.preprocess == 11, "preprocess nanoseconds are preserved");
    check(sample.inference == 22, "inference nanoseconds are preserved");
    check(sample.postprocess == 33, "postprocess nanoseconds are preserved");
    check(sample.pipeline_total == 66, "pipeline total is the exact stage sum");
    expect_throws(
        [] { static_cast<void>(edgeai::common::make_benchmark_sample(-1, 2, 3)); },
        "negative durations are rejected"
    );
}

void test_cpu_formula() {
    const double percent = edgeai::common::process_cpu_percent_one_core_basis(2.0, 4.0);
    check(std::abs(percent - 50.0) < 1e-12, "CPU formula uses one-core basis");
    expect_throws(
        [] { static_cast<void>(edgeai::common::process_cpu_percent_one_core_basis(1.0, 0.0)); },
        "zero wall time is rejected"
    );
}

void test_detection_comparison() {
    const std::vector<edgeai::common::Detection> reference{
        detection(1, "one", 0.8F, {0.0F, 0.0F, 10.0F, 10.0F}),
        detection(1, "one", 0.6F, {20.0F, 20.0F, 30.0F, 30.0F}),
    };
    const std::vector<edgeai::common::Detection> reordered{
        detection(1, "one", 0.6005F, {20.0F, 20.0F, 30.0F, 30.0F}),
        detection(1, "one", 0.8005F, {0.0F, 0.0F, 10.0F, 10.0F}),
    };
    const auto result =
        edgeai::common::compare_benchmark_detections(reference, reordered, 0.99, 0.001);
    check(result.detection_count == 2U, "all detections are compared");
    check(result.minimum_class_matched_iou == 1.0, "same-class matching uses best IoU");
    check(result.maximum_absolute_confidence_difference < 0.001,
          "confidence difference is recorded");
    expect_throws(
        [&] {
            static_cast<void>(edgeai::common::compare_benchmark_detections(
                reference,
                {reordered.front()},
                0.99,
                0.001
            ));
        },
        "detection count drift is rejected"
    );
}

}  // namespace

int main() {
    test_sample_sum();
    test_cpu_formula();
    test_detection_comparison();
    if (failures != 0) {
        std::cerr << failures << " benchmark helper checks failed\n";
        return 1;
    }
    std::cout << "edgeai_benchmark_tests: PASS\n";
    return 0;
}
