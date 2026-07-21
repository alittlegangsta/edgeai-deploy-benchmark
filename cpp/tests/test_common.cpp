#include "edgeai/common/config.hpp"
#include "edgeai/common/preprocess.hpp"
#include "edgeai/common/visualize.hpp"

#include <cmath>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include <opencv2/core.hpp>

namespace {

int failures = 0;

void check(bool condition, const std::string& description) {
    if (!condition) {
        ++failures;
        std::cerr << "FAIL: " << description << '\n';
    }
}

void check_near(double actual, double expected, double tolerance, const std::string& description) {
    check(std::abs(actual - expected) <= tolerance, description);
}

void expect_throws(const std::function<void()>& operation, const std::string& description) {
    try {
        operation();
        check(false, description);
    } catch (const std::exception&) {
        check(true, description);
    }
}

edgeai::common::InferenceConfig config_for(int width, int height) {
    edgeai::common::InferenceConfig config;
    config.input_size = {width, height};
    config.class_names = {"sample"};
    return config;
}

void check_letterbox(
    int source_width,
    int source_height,
    int resized_width,
    int resized_height,
    const edgeai::common::Padding& expected_padding,
    double expected_scale
) {
    const cv::Mat image(source_height, source_width, CV_8UC3, cv::Scalar(0, 0, 0));
    const auto result = edgeai::common::preprocess_image(image, config_for(640, 640));
    check(result.letterboxed_bgr.cols == 640 && result.letterboxed_bgr.rows == 640,
          "letterbox output is 640x640");
    check(result.metadata.resized_size.width == resized_width &&
              result.metadata.resized_size.height == resized_height,
          "letterbox resized dimensions match");
    check(result.metadata.padding.left == expected_padding.left &&
              result.metadata.padding.top == expected_padding.top &&
              result.metadata.padding.right == expected_padding.right &&
              result.metadata.padding.bottom == expected_padding.bottom,
          "letterbox split padding matches");
    check_near(result.metadata.scale, expected_scale, 1e-12, "letterbox scale matches");
}

std::filesystem::path write_config(const std::string& name, const std::string& contents) {
    const auto path = std::filesystem::temp_directory_path() / name;
    std::ofstream output(path, std::ios::trunc);
    output << contents;
    output.close();
    if (!output) {
        throw std::runtime_error("failed to write temporary test configuration");
    }
    return path;
}

void test_config() {
    const auto repository_config =
        edgeai::common::load_config(std::filesystem::path(EDGEAI_REPOSITORY_ROOT) /
                                    "configs/yolov5n_v7_inference.json");
    check(repository_config.input_size.width == 640 && repository_config.input_size.height == 640,
          "frozen input size loads");
    check(repository_config.class_names.size() == 80U,
          "frozen model class names are present");
    check(repository_config.class_names[64] == "mouse" &&
              repository_config.class_names[66] == "keyboard",
          "frozen class-name ordering matches the model contract");

    const std::string prefix =
        R"({"schema_version":1,"input_size":[640,640],"confidence_threshold":)";
    const std::string suffix =
        R"(,"iou_threshold":0.45,"class_aware_nms":1,"max_detections":1000,"class_names":["a","b"]})";
    const auto invalid_threshold = write_config("edgeai_invalid_threshold.json", prefix + "1.1" + suffix);
    expect_throws(
        [&] { static_cast<void>(edgeai::common::load_config(invalid_threshold)); },
        "invalid confidence threshold is rejected"
    );

    const auto duplicate_names = write_config(
        "edgeai_duplicate_names.json",
        R"({"schema_version":1,"input_size":[640,640],"confidence_threshold":0.25,"iou_threshold":0.45,"class_aware_nms":1,"max_detections":1000,"class_names":["same","same"]})"
    );
    expect_throws(
        [&] { static_cast<void>(edgeai::common::load_config(duplicate_names)); },
        "duplicate class names are rejected"
    );

    const auto invalid_letterbox = write_config(
        "edgeai_invalid_letterbox.json",
        R"({"schema_version":1,"input_size":[640,640],"confidence_threshold":0.25,"iou_threshold":0.45,"class_aware_nms":1,"max_detections":1000,"class_names":["a"],"letterbox":{"pad_color_bgr":[114,114,300],"interpolation":"cv2.INTER_LINEAR"}})"
    );
    expect_throws(
        [&] { static_cast<void>(edgeai::common::load_config(invalid_letterbox)); },
        "invalid letterbox color is rejected"
    );
    std::filesystem::remove(invalid_threshold);
    std::filesystem::remove(duplicate_names);
    std::filesystem::remove(invalid_letterbox);
}

void test_letterbox_geometry() {
    check_letterbox(600, 300, 640, 320, {0, 160, 0, 160}, 640.0 / 600.0);
    check_letterbox(300, 600, 320, 640, {160, 0, 160, 0}, 640.0 / 600.0);
    check_letterbox(640, 640, 640, 640, {0, 0, 0, 0}, 1.0);
    check_letterbox(640, 321, 640, 321, {0, 159, 0, 160}, 1.0);
}

void test_layout_and_invalid_input() {
    cv::Mat image(1, 1, CV_8UC3);
    image.at<cv::Vec3b>(0, 0) = {1, 2, 3};
    const auto result = edgeai::common::preprocess_image(image, config_for(1, 1));
    check(result.tensor.shape == std::array<std::int64_t, 4>{{1, 3, 1, 1}},
          "tensor shape is NCHW");
    check(result.tensor.values.size() == 3U, "tensor has three channel values");
    check_near(result.tensor.values[0], 3.0 / 255.0, 1e-8, "tensor red channel is first");
    check_near(result.tensor.values[1], 2.0 / 255.0, 1e-8, "tensor green channel is second");
    check_near(result.tensor.values[2], 1.0 / 255.0, 1e-8, "tensor blue channel is third");
    expect_throws(
        [] { static_cast<void>(edgeai::common::preprocess_image(cv::Mat{}, config_for(1, 1))); },
        "empty input image is rejected"
    );
    expect_throws(
        [] {
            const cv::Mat invalid(1, 1, CV_32FC3, cv::Scalar(0.0F, 0.0F, 0.0F));
            static_cast<void>(edgeai::common::preprocess_image(invalid, config_for(1, 1)));
        },
        "non-uint8 input image is rejected"
    );
}

void test_mapping_and_clipping() {
    edgeai::common::LetterboxMetadata metadata;
    metadata.original_size = {1280, 960};
    metadata.target_size = {640, 640};
    metadata.resized_size = {640, 480};
    metadata.scale = 0.5;
    metadata.padding = {0, 80, 0, 80};
    const auto restored = edgeai::common::restore_and_clip_box({-10.0F, 50.0F, 700.0F, 600.0F}, metadata);
    check(restored.has_value(), "valid clipped box remains present");
    check_near(restored->x1, 0.0, 0.0, "left coordinate clips to zero");
    check_near(restored->y1, 0.0, 0.0, "top coordinate clips to zero");
    check_near(restored->x2, 1280.0, 0.0, "right coordinate clips to image width");
    check_near(restored->y2, 960.0, 0.0, "bottom coordinate clips to image height");
    const auto empty = edgeai::common::restore_and_clip_box({-10.0F, 100.0F, -1.0F, 120.0F}, metadata);
    check(!empty.has_value(), "fully clipped box becomes empty");
    metadata.scale = 0.0;
    expect_throws(
        [&] { static_cast<void>(edgeai::common::restore_and_clip_box({0, 0, 1, 1}, metadata)); },
        "invalid mapping scale is rejected"
    );
}

void test_visualization_copy_and_empty_values() {
    const cv::Mat source(32, 32, CV_8UC3, cv::Scalar(10, 20, 30));
    const cv::Mat empty_result = edgeai::common::draw_detections(source, {});
    check(cv::norm(source, empty_result, cv::NORM_INF) == 0.0,
          "empty detection list preserves pixels");
    edgeai::common::Detection detection;
    detection.class_id = 1;
    detection.class_name = "sample";
    detection.confidence = 0.5F;
    detection.box_xyxy_source = {4.0F, 8.0F, 24.0F, 28.0F};
    const cv::Mat drawn = edgeai::common::draw_detections(source, {detection});
    check(cv::norm(source, drawn, cv::NORM_INF) > 0.0, "visualization changes output copy");
    check(source.at<cv::Vec3b>(8, 4) == cv::Vec3b(10, 20, 30),
          "visualization does not mutate source pixels");
}

}  // namespace

int main() {
    try {
        test_config();
        test_letterbox_geometry();
        test_layout_and_invalid_input();
        test_mapping_and_clipping();
        test_visualization_copy_and_empty_values();
    } catch (const std::exception& error) {
        std::cerr << "UNEXPECTED ERROR: " << error.what() << '\n';
        return 1;
    }
    if (failures != 0) {
        std::cerr << failures << " common-module checks failed\n";
        return 1;
    }
    std::cout << "edgeai_common_tests: PASS\n";
    return 0;
}
