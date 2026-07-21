#include "edgeai/common/postprocess.hpp"

#include <cmath>
#include <iostream>
#include <limits>
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

void check_near(float actual, float expected, float tolerance, const std::string& description) {
    check(std::abs(actual - expected) <= tolerance, description);
}

template <typename Operation>
void expect_throws(Operation operation, const std::string& description) {
    try {
        operation();
        check(false, description);
    } catch (const std::exception&) {
        check(true, description);
    }
}

edgeai::common::InferenceConfig config() {
    edgeai::common::InferenceConfig value;
    value.input_size = {640, 640};
    value.class_names = {"zero", "one"};
    return value;
}

edgeai::common::LetterboxMetadata metadata() {
    edgeai::common::LetterboxMetadata value;
    value.original_size = {1280, 960};
    value.target_size = {640, 640};
    value.resized_size = {640, 480};
    value.scale = 0.5;
    value.padding = {0, 80, 0, 80};
    return value;
}

void test_geometry() {
    const edgeai::common::Box converted =
        edgeai::common::xywh_to_xyxy({10.0F, 20.0F, 4.0F, 8.0F});
    check_near(converted.x1, 8.0F, 0.0F, "xywh x1 converts");
    check_near(converted.y1, 16.0F, 0.0F, "xywh y1 converts");
    check_near(converted.x2, 12.0F, 0.0F, "xywh x2 converts");
    check_near(converted.y2, 24.0F, 0.0F, "xywh y2 converts");
    check_near(
        edgeai::common::box_iou({0, 0, 10, 10}, {0, 0, 10, 10}),
        1.0F,
        0.0F,
        "identical IoU is one"
    );
    check_near(
        edgeai::common::box_iou({0, 0, 10, 10}, {20, 20, 30, 30}),
        0.0F,
        0.0F,
        "disjoint IoU is zero"
    );
    check_near(
        edgeai::common::box_iou({0, 0, 10, 10}, {5, 5, 15, 15}),
        25.0F / 175.0F,
        1e-6F,
        "partial IoU matches"
    );
}

void test_decode_nms_mapping_and_empty() {
    const std::vector<float> raw{
        100, 120, 20, 20, 0.9F, 0.9F, 0.1F,
        101, 121, 20, 20, 0.8F, 0.9F, 0.1F,
        100, 120, 20, 20, 0.85F, 0.1F, 0.9F,
    };
    const auto result = edgeai::common::decode_yolov5_output(
        raw, {1, 3, 7}, config().class_names, metadata(), config()
    );
    check(result.raw_candidate_count == 3U, "raw candidate count matches");
    check(result.threshold_candidate_count == 3U, "threshold candidate count matches");
    check(result.nms_candidate_count == 2U, "same-class NMS suppresses only one");
    check(result.detections.size() == 2U, "two mapped detections remain");
    check(result.detections[0].class_id == 0 && result.detections[1].class_id == 1,
          "class-aware NMS retains different class");
    check_near(result.detections[0].box_xyxy_source.x1, 180.0F, 1e-5F,
               "inverse mapping restores x1");
    check_near(result.detections[0].box_xyxy_source.y1, 60.0F, 1e-5F,
               "inverse mapping removes top padding");

    auto high_threshold = config();
    high_threshold.confidence_threshold = 1.0;
    const auto empty = edgeai::common::decode_yolov5_output(
        raw, {1, 3, 7}, high_threshold.class_names, metadata(), high_threshold
    );
    check(empty.detections.empty(), "empty threshold result is preserved");
}

void test_invalid_output() {
    auto invalid = std::vector<float>{100, 100, 20, 20, 0.9F, 0.9F, 0.1F};
    invalid[0] = std::numeric_limits<float>::quiet_NaN();
    expect_throws(
        [&] {
            static_cast<void>(edgeai::common::decode_yolov5_output(
                invalid, {1, 1, 7}, config().class_names, metadata(), config()
            ));
        },
        "non-finite output is rejected"
    );
    expect_throws(
        [&] {
            static_cast<void>(edgeai::common::decode_yolov5_output(
                std::vector<float>(7U, 0.0F),
                {2, 1, 7},
                config().class_names,
                metadata(),
                config()
            ));
        },
        "non-batch-one output is rejected"
    );
    expect_throws(
        [&] {
            static_cast<void>(edgeai::common::decode_yolov5_output(
                std::vector<float>(6U, 0.0F),
                {1, 1, 7},
                config().class_names,
                metadata(),
                config()
            ));
        },
        "buffer and shape mismatch is rejected"
    );
}

}  // namespace

int main() {
    test_geometry();
    test_decode_nms_mapping_and_empty();
    test_invalid_output();
    if (failures != 0) {
        std::cerr << failures << " postprocess checks failed\n";
        return 1;
    }
    std::cout << "edgeai_postprocess_tests: PASS\n";
    return 0;
}
