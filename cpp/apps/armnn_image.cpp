#include "edgeai/backends/armnn_detector.hpp"
#include "edgeai/common/config.hpp"
#include "edgeai/common/postprocess.hpp"
#include "edgeai/common/preprocess.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <vector>

#include <opencv2/core/persistence.hpp>

namespace {

using Clock = std::chrono::steady_clock;
constexpr const char* kExpectedModelSha256 =
    "78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121";
constexpr const char* kExpectedFloorIdentityModelSha256 =
    "755fb5adc596eee7a7255bc29c48b86f1895df1e8fa1577d785cb431d233bcf2";
constexpr const char* kExpectedFloorConstantModelSha256 =
    "e6066c047c2fc6bd37bd3ffa5322fa85a62873c5c9751e57ac8a569faf6201b7";
constexpr const char* kExpectedFloorRemovedModelSha256 =
    "e0720ffe896ed1919dba35699e703025b0bfad906bdcf97e4f2ab81e66df92e0";
constexpr const char* kExpectedFloorAddZeroModelSha256 =
    "9f330839f3130f0af0fb7c5ab4c3f761ff6fd7f625c46298ef17a99caab40811";
constexpr const char* kExpectedFloorFixedResizeModelSha256 =
    "a8cd7290ee2d592ffd994d79dfceee3bf9dfd0eebe6a58b77624e2b6019a9de8";
constexpr const char* kExpectedFloorFixedResizeInferredModelSha256 =
    "f29c4b85f4d2ebc16095ac9849319bc1e0ff3863001b1d38f4f28db508e86ead";
constexpr const char* kExpectedFloorFixedResizeScalesModelSha256 =
    "acfad8dbd631d61f47458a6a5639ed6804c3f1c53f6a177e2af08c7078b034da";
constexpr const char* kExpectedQuantizedFloorRemovedModelSha256 =
    "3ce1e58b3d024ac890eef24e0704265aae12a7c58d005aeed288ff4c4aba4b76";
constexpr const char* kExpectedInputSha256 =
    "625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071";
constexpr const char* kExpectedConfigSha256 =
    "82ef24f773a6ffb8e06e26b94747bd1b581408b19adae293b3ecfd8b228ee96d";

struct Arguments {
    edgeai::filesystem::path model;
    edgeai::filesystem::path config;
    edgeai::filesystem::path image;
    edgeai::filesystem::path output_json;
    std::string model_variant{"frozen"};
    std::string expected_model_sha256;
    std::string mode{"correctness"};
    int warmup{0};
    int repeats{1};
    bool parse_only{false};
    edgeai::filesystem::path raw_head_dir;
};

int parse_positive(const std::string& value, const char* option, bool allow_zero = false) {
    std::size_t consumed = 0U;
    int parsed = 0;
    try {
        parsed = std::stoi(value, &consumed);
    } catch (const std::exception&) {
        throw std::runtime_error(std::string(option) + " must be an integer");
    }
    if (consumed != value.size() || parsed < 0 || (!allow_zero && parsed == 0)) {
        throw std::runtime_error(std::string(option) + " must be a non-negative integer");
    }
    return parsed;
}

Arguments parse_args(int argc, char* argv[]) {
    if (argc < 9 || (argc - 1) % 2 != 0) {
        throw std::runtime_error(
            "usage: edgeai_armnn_image --model PATH --config PATH --image PATH "
            "--output-json PATH [--model-variant frozen|floor-identity|floor-constant|floor-removed|floor-add-zero|floor-fixed-resize|floor-fixed-resize-inferred|floor-fixed-resize-scales|quantized-floor-removed|matrix] "
            "[--expected-model-sha256 HEX] [--parse-only 0|1] "
            "[--mode correctness|benchmark] [--warmup N] [--repeats N] "
            "[--raw-head-dir PATH]"
        );
    }
    const std::vector<std::string> allowed{
        "--model", "--config", "--image", "--output-json", "--model-variant",
        "--expected-model-sha256", "--parse-only", "--mode", "--warmup", "--repeats",
        "--raw-head-dir",
    };
    std::map<std::string, std::string> values;
    for (int index = 1; index < argc; index += 2) {
        const std::string option = argv[index];
        if (std::find(allowed.begin(), allowed.end(), option) == allowed.end()) {
            throw std::runtime_error("unknown argument: " + option);
        }
        if (!values.emplace(option, argv[index + 1]).second) {
            throw std::runtime_error("duplicate argument: " + option);
        }
    }
    for (const char* required : {"--model", "--config", "--image", "--output-json"}) {
        if (values.count(required) == 0U) {
            throw std::runtime_error(std::string("missing required argument: ") + required);
        }
    }
    const std::string mode = values.count("--mode") ? values.at("--mode") : "correctness";
    if (mode != "correctness" && mode != "benchmark") {
        throw std::runtime_error("--mode must be correctness or benchmark");
    }
    const std::string model_variant = values.count("--model-variant")
                                          ? values.at("--model-variant")
                                          : "frozen";
    if (model_variant != "frozen" && model_variant != "floor-identity" &&
        model_variant != "floor-constant" && model_variant != "floor-removed" &&
        model_variant != "floor-add-zero" && model_variant != "floor-fixed-resize" &&
        model_variant != "floor-fixed-resize-inferred" &&
        model_variant != "floor-fixed-resize-scales" &&
        model_variant != "quantized-floor-removed" && model_variant != "matrix") {
        throw std::runtime_error(
            "--model-variant must be frozen, floor-identity, floor-constant, floor-removed, floor-add-zero, floor-fixed-resize, floor-fixed-resize-inferred, floor-fixed-resize-scales, quantized-floor-removed, or matrix");
    }
    const std::string expected_model_sha256 = values.count("--expected-model-sha256")
                                                  ? values.at("--expected-model-sha256")
                                                  : "";
    if (expected_model_sha256.size() != 64U && !expected_model_sha256.empty()) {
        throw std::runtime_error("--expected-model-sha256 must be a 64-character SHA256");
    }
    const bool parse_only = values.count("--parse-only")
                                ? values.at("--parse-only") == "1"
                                : false;
    if (values.count("--parse-only") != 0U && values.at("--parse-only") != "0" &&
        values.at("--parse-only") != "1") {
        throw std::runtime_error("--parse-only must be 0 or 1");
    }
    const int warmup = values.count("--warmup")
                           ? parse_positive(values.at("--warmup"), "--warmup", true)
                           : 0;
    const int repeats = values.count("--repeats")
                            ? parse_positive(values.at("--repeats"), "--repeats")
                            : 1;
    return {
        values.at("--model"), values.at("--config"), values.at("--image"),
        values.at("--output-json"), model_variant, expected_model_sha256, mode, warmup,
        repeats, parse_only,
        values.count("--raw-head-dir") ? edgeai::filesystem::path(values.at("--raw-head-dir"))
                                        : edgeai::filesystem::path{},
    };
}

const char* expected_model_sha256(const Arguments& arguments) {
    if (!arguments.expected_model_sha256.empty()) {
        return arguments.expected_model_sha256.c_str();
    }
    if (arguments.model_variant == "floor-identity") {
        return kExpectedFloorIdentityModelSha256;
    }
    if (arguments.model_variant == "floor-constant") {
        return kExpectedFloorConstantModelSha256;
    }
    if (arguments.model_variant == "floor-removed") {
        return kExpectedFloorRemovedModelSha256;
    }
    if (arguments.model_variant == "floor-add-zero") {
        return kExpectedFloorAddZeroModelSha256;
    }
    if (arguments.model_variant == "floor-fixed-resize") {
        return kExpectedFloorFixedResizeModelSha256;
    }
    if (arguments.model_variant == "floor-fixed-resize-inferred") {
        return kExpectedFloorFixedResizeInferredModelSha256;
    }
    if (arguments.model_variant == "floor-fixed-resize-scales") {
        return kExpectedFloorFixedResizeScalesModelSha256;
    }
    if (arguments.model_variant == "quantized-floor-removed") {
        return kExpectedQuantizedFloorRemovedModelSha256;
    }
    return kExpectedModelSha256;
}

double elapsed_ms(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

double cpu_ms() {
    struct rusage usage{};
    if (getrusage(RUSAGE_SELF, &usage) != 0) {
        return -1.0;
    }
    return static_cast<double>(usage.ru_utime.tv_sec) * 1000.0 +
           static_cast<double>(usage.ru_utime.tv_usec) / 1000.0 +
           static_cast<double>(usage.ru_stime.tv_sec) * 1000.0 +
           static_cast<double>(usage.ru_stime.tv_usec) / 1000.0;
}

int observed_process_threads() {
    std::ifstream status("/proc/self/status");
    std::string label;
    while (status >> label) {
        if (label == "Threads:") {
            int count = 0;
            status >> count;
            return count;
        }
        std::string ignored;
        std::getline(status, ignored);
    }
    return -1;
}

struct TimingSample {
    double preprocess{0.0};
    double inference{0.0};
    double postprocess{0.0};
    double end_to_end{0.0};
    double process_cpu{0.0};
};

struct Summary {
    double mean{0.0};
    double p50{0.0};
    double p95{0.0};
    double min{0.0};
    double max{0.0};
    double sample_sd{0.0};
};

Summary summarize(std::vector<double> values) {
    if (values.empty()) {
        throw std::runtime_error("cannot summarize an empty timing vector");
    }
    if (!std::all_of(values.begin(), values.end(), [](double value) {
            return std::isfinite(value) && value > 0.0;
        })) {
        throw std::runtime_error("timing contains a non-finite or non-positive value");
    }
    std::sort(values.begin(), values.end());
    const double mean = std::accumulate(values.begin(), values.end(), 0.0) /
                        static_cast<double>(values.size());
    double variance = 0.0;
    if (values.size() > 1U) {
        for (const double value : values) {
            const double delta = value - mean;
            variance += delta * delta;
        }
        variance /= static_cast<double>(values.size() - 1U);
    }
    const auto nearest_rank = [&values](double quantile) {
        const std::size_t rank = static_cast<std::size_t>(std::ceil(quantile * values.size()));
        return values[std::max<std::size_t>(1U, rank) - 1U];
    };
    return {mean, nearest_rank(0.50), nearest_rank(0.95), values.front(), values.back(),
            std::sqrt(variance)};
}

void write_shape(cv::FileStorage& output, const std::vector<std::int64_t>& shape) {
    output << "[";
    for (const auto dimension : shape) {
        output << static_cast<int>(dimension);
    }
    output << "]";
}

void write_descriptor(cv::FileStorage& output, const edgeai::backends::ArmnnTensorDescriptor& value) {
    output << "{" << "name" << value.name << "dtype" << value.dtype << "shape";
    write_shape(output, value.shape);
    output << "bytes" << static_cast<double>(value.bytes) << "}";
}

void write_box(cv::FileStorage& output, const edgeai::common::Box& box) {
    output << "[" << box.x1 << box.y1 << box.x2 << box.y2 << "]";
}

void write_detections(cv::FileStorage& output, const edgeai::common::PostprocessResult& result) {
    output << "[";
    for (const auto& detection : result.detections) {
        output << "{" << "rank" << static_cast<int>(detection.rank)
               << "candidate_index" << static_cast<int>(detection.candidate_index)
               << "class_id" << detection.class_id << "class_name" << detection.class_name
               << "objectness" << detection.objectness << "class_score" << detection.class_score
               << "confidence" << detection.confidence << "box_xyxy_source";
        write_box(output, detection.box_xyxy_source);
        output << "box_xyxy_input";
        write_box(output, detection.box_xyxy_input);
        output << "}";
    }
    output << "]";
}

double sigmoid(float value) {
    if (!std::isfinite(value)) {
        throw std::runtime_error("ArmNN raw head contains a non-finite value");
    }
    if (value >= 0.0F) {
        const double exponent = std::exp(-static_cast<double>(value));
        return 1.0 / (1.0 + exponent);
    }
    const double exponent = std::exp(static_cast<double>(value));
    return exponent / (1.0 + exponent);
}

edgeai::backends::ArmnnRawInferenceResult decode_al_onnx_heads(
    const edgeai::backends::ArmnnRawInferenceResult& raw
) {
    if (raw.tensors.size() != 3U) {
        throw std::runtime_error("AL_onnx_pass head decode requires exactly three output tensors");
    }
    struct Head {
        const edgeai::backends::ArmnnRawTensor* tensor;
        int stride;
        int height;
        int width;
        int anchor_offset;
    };
    std::vector<Head> heads;
    heads.reserve(raw.tensors.size());
    for (const auto& tensor : raw.tensors) {
        if (tensor.shape.size() != 4U || tensor.shape[0] != 1 || tensor.shape[1] != 255 ||
            tensor.shape[2] <= 0 || tensor.shape[3] <= 0) {
            throw std::runtime_error("AL_onnx_pass output head shape is not [1,255,H,W]");
        }
        const int height = static_cast<int>(tensor.shape[2]);
        const int width = static_cast<int>(tensor.shape[3]);
        if (height != width || (640 % height) != 0) {
            throw std::runtime_error("AL_onnx_pass output head is not a square 640-grid");
        }
        const int stride = 640 / height;
        const int anchor_offset = stride == 8 ? 0 : (stride == 16 ? 6 : (stride == 32 ? 12 : -1));
        if (anchor_offset < 0 || tensor.values.size() != static_cast<std::size_t>(255 * height * width)) {
            throw std::runtime_error("AL_onnx_pass output head dimensions are unsupported");
        }
        heads.push_back({&tensor, stride, height, width, anchor_offset});
    }
    std::sort(heads.begin(), heads.end(), [](const Head& left, const Head& right) {
        return left.stride < right.stride;
    });
    static constexpr std::array<float, 18> anchors{{
        10.0F, 13.0F, 16.0F, 30.0F, 33.0F, 23.0F,
        30.0F, 61.0F, 62.0F, 45.0F, 59.0F, 119.0F,
        116.0F, 90.0F, 156.0F, 198.0F, 373.0F, 326.0F,
    }};
    edgeai::backends::ArmnnRawInferenceResult decoded;
    decoded.shape = {1, 25200, 85};
    decoded.values.resize(static_cast<std::size_t>(25200 * 85));
    decoded.tensors.push_back({"decoded_al_onnx_heads", decoded.shape, decoded.values});
    std::size_t row = 0U;
    for (const auto& head : heads) {
        for (int anchor = 0; anchor < 3; ++anchor) {
            for (int y = 0; y < head.height; ++y) {
                for (int x = 0; x < head.width; ++x) {
                    const std::size_t output_offset = row * 85U;
                    const auto& values = head.tensor->values;
                    const auto value_at = [&](int channel) {
                        const std::size_t offset =
                            (static_cast<std::size_t>(anchor * 85 + channel) *
                             static_cast<std::size_t>(head.height) + static_cast<std::size_t>(y)) *
                                static_cast<std::size_t>(head.width) + static_cast<std::size_t>(x);
                        return values.at(offset);
                    };
                    decoded.values[output_offset] = static_cast<float>(
                        (sigmoid(value_at(0)) * 2.0 + static_cast<double>(x)) * head.stride);
                    decoded.values[output_offset + 1U] = static_cast<float>(
                        (sigmoid(value_at(1)) * 2.0 + static_cast<double>(y)) * head.stride);
                    const float anchor_width = anchors[static_cast<std::size_t>(head.anchor_offset + anchor * 2)];
                    const float anchor_height = anchors[static_cast<std::size_t>(head.anchor_offset + anchor * 2 + 1)];
                    const double width = std::pow(sigmoid(value_at(2)) * 2.0, 2.0) * anchor_width;
                    const double height = std::pow(sigmoid(value_at(3)) * 2.0, 2.0) * anchor_height;
                    decoded.values[output_offset + 2U] = static_cast<float>(width);
                    decoded.values[output_offset + 3U] = static_cast<float>(height);
                    for (int channel = 4; channel < 85; ++channel) {
                        decoded.values[output_offset + static_cast<std::size_t>(channel)] =
                            static_cast<float>(sigmoid(value_at(channel)));
                    }
                    ++row;
                }
            }
        }
    }
    if (row != 25200U) {
        throw std::runtime_error("AL_onnx_pass head decode produced an unexpected row count");
    }
    decoded.tensors.front().values = decoded.values;
    return decoded;
}

void write_raw_tensor_stats(
    cv::FileStorage& output,
    const edgeai::backends::ArmnnRawTensor& tensor
) {
    const auto minmax = std::minmax_element(tensor.values.begin(), tensor.values.end());
    const double mean = tensor.values.empty()
                            ? 0.0
                            : std::accumulate(tensor.values.begin(), tensor.values.end(), 0.0) /
                                  static_cast<double>(tensor.values.size());
    double variance = 0.0;
    for (const float value : tensor.values) {
        const double delta = static_cast<double>(value) - mean;
        variance += delta * delta;
    }
    if (tensor.values.size() > 1U) {
        variance /= static_cast<double>(tensor.values.size() - 1U);
    }
    output << "{" << "name" << tensor.name << "shape";
    write_shape(output, tensor.shape);
    output << "dtype" << "float32" << "element_count" << static_cast<double>(tensor.values.size())
           << "finite" << std::all_of(tensor.values.begin(), tensor.values.end(), [](float value) {
                  return std::isfinite(value);
              })
           << "min" << (tensor.values.empty() ? 0.0 : static_cast<double>(*minmax.first))
           << "max" << (tensor.values.empty() ? 0.0 : static_cast<double>(*minmax.second))
           << "mean" << mean << "sample_sd" << std::sqrt(variance) << "}";
}

std::vector<edgeai::filesystem::path> write_raw_tensor_files(
    const Arguments& arguments,
    const edgeai::backends::ArmnnRawInferenceResult& raw
) {
    std::vector<edgeai::filesystem::path> paths;
    if (arguments.raw_head_dir.empty()) {
        return paths;
    }
    edgeai::filesystem::create_directories(arguments.raw_head_dir);
    paths.reserve(raw.tensors.size());
    for (std::size_t index = 0; index < raw.tensors.size(); ++index) {
        const auto path = arguments.raw_head_dir / ("head_" + std::to_string(index) + ".f32");
        std::ofstream output(path.string(), std::ios::binary | std::ios::trunc);
        if (!output) {
            throw std::runtime_error("failed to open raw head output: " + path.string());
        }
        const auto& values = raw.tensors[index].values;
        if (!values.empty()) {
            output.write(
                reinterpret_cast<const char*>(values.data()),
                static_cast<std::streamsize>(values.size() * sizeof(float))
            );
        }
        if (!output) {
            throw std::runtime_error("failed to write raw head output: " + path.string());
        }
        paths.push_back(path);
    }
    return paths;
}

void write_json(
    const Arguments& arguments,
    const edgeai::common::InferenceConfig& config,
    const edgeai::backends::ArmnnDetector& detector,
    const edgeai::common::PreprocessResult& preprocess,
    const edgeai::common::PostprocessResult& postprocess,
    const edgeai::backends::ArmnnRawInferenceResult& raw,
    const edgeai::backends::ArmnnRawInferenceResult& decoded,
    const std::vector<edgeai::filesystem::path>& raw_head_files,
    const std::vector<TimingSample>& samples,
    double model_load_ms,
    const std::string& status
) {
    if (!arguments.output_json.parent_path().empty()) {
        edgeai::filesystem::create_directories(arguments.output_json.parent_path());
    }
    cv::FileStorage output(
        arguments.output_json.string(), cv::FileStorage::WRITE | cv::FileStorage::FORMAT_JSON);
    if (!output.isOpened()) {
        throw std::runtime_error("failed to open result JSON: " + arguments.output_json.string());
    }
    const auto& runtime = detector.runtime_info();
    output << "schema_version" << 1 << "application" << "edgeai_armnn_image"
           << "status" << status << "mode" << arguments.mode;
    output << "runtime" << "{" << "armnn_version" << runtime.version
           << "requested_backend" << runtime.requested_backend
           << "fallback_allowed" << runtime.fallback_allowed
           << "requested_backend_registered" << runtime.requested_backend_registered
           << "load_status" << runtime.load_status << "load_error" << runtime.load_error
           << "supported_backends" << "[";
    for (const auto& backend : runtime.supported_backends) {
        output << backend;
    }
    output << "]" << "optimizer_messages" << "[";
    for (const auto& message : runtime.optimizer_messages) {
        output << message;
    }
    output << "]" << "output_descriptors" << "[";
    for (const auto& descriptor : runtime.outputs) {
        write_descriptor(output, descriptor);
    }
    output << "]" << "assignment_evidence"
           << "only Alnpu was passed to ArmNN Optimize; CpuAcc/CpuRef fallback was disabled"
           << "}";
    output << "model" << "{" << "path" << detector.model_path().string()
           << "variant" << arguments.model_variant << "sha256" << detector.model_sha256()
           << "expected_sha256" << expected_model_sha256(arguments)
           << "source_sha256" << kExpectedModelSha256
           << "repair" << (arguments.model_variant == "floor-identity"
                                  ? "constant FLOAT Floor nodes replaced with Identity; values are exact integers"
                                  : arguments.model_variant == "floor-constant"
                                        ? "constant FLOAT Floor nodes replaced with equivalent Constant nodes"
                                        : arguments.model_variant == "floor-removed"
                                              ? "constant FLOAT Floor nodes removed and consumers rewired to Constant inputs"
                                              : arguments.model_variant == "floor-add-zero"
                                                    ? "constant FLOAT Floor nodes replaced with exact-value Add-zero nodes"
                                                    : arguments.model_variant == "floor-fixed-resize"
                                                          ? "dynamic Resize shape subgraphs folded to fixed [1,C,H,W] sizes"
                                                          : arguments.model_variant == "floor-fixed-resize-inferred"
                                                                ? "dynamic Resize shape subgraphs folded to fixed sizes with ONNX shape inference"
                                                          : arguments.model_variant == "floor-fixed-resize-scales"
                                                                ? "dynamic Resize shape subgraphs folded to fixed scales with explicit non-empty ROI"
                                                                : arguments.model_variant == "quantized-floor-removed"
                                                          ? "Conv-only QDQ INT8 calibration followed by constant FLOAT Floor removal"
                                                          : "none")
           << "}";
    output << "input" << "{" << "path" << arguments.image.string()
           << "sha256" << edgeai::backends::armnn_sha256_file(arguments.image)
           << "expected_sha256" << kExpectedInputSha256 << "shape_bgr"
           << "[" << preprocess.metadata.original_size.height << preprocess.metadata.original_size.width
           << 3 << "]" << "}";
    output << "configuration" << "{" << "path" << arguments.config.string()
           << "sha256" << edgeai::backends::armnn_sha256_file(arguments.config)
           << "expected_sha256" << kExpectedConfigSha256 << "input_size"
           << "[" << config.input_size.height << config.input_size.width << "]"
           << "confidence_threshold" << config.confidence_threshold << "iou_threshold"
           << config.iou_threshold << "class_aware_nms" << config.class_aware_nms << "}";
    output << "tensor_contract" << "{" << "input";
    write_descriptor(output, runtime.input);
    output << "output";
    write_descriptor(output, runtime.output);
    output << "}";
    output << "preprocess" << "{" << "scale" << preprocess.metadata.scale << "padding" << "{"
           << "left" << preprocess.metadata.padding.left << "top" << preprocess.metadata.padding.top
           << "right" << preprocess.metadata.padding.right << "bottom"
           << preprocess.metadata.padding.bottom << "}" << "transforms" << "[";
    for (const auto& transform : preprocess.metadata.transforms) {
        output << transform;
    }
    output << "]" << "}";

    const bool all_finite = std::all_of(decoded.values.begin(), decoded.values.end(), [](float value) {
        return std::isfinite(value);
    });
    const auto minmax = std::minmax_element(decoded.values.begin(), decoded.values.end());
    const double mean = decoded.values.empty()
                            ? 0.0
                            : std::accumulate(decoded.values.begin(), decoded.values.end(), 0.0) /
                                  static_cast<double>(decoded.values.size());
    double variance = 0.0;
    if (decoded.values.size() > 1U) {
        for (const float value : decoded.values) {
            const double delta = static_cast<double>(value) - mean;
            variance += delta * delta;
        }
        variance /= static_cast<double>(decoded.values.size() - 1U);
    }
    output << "raw_head_outputs" << "[";
    for (const auto& tensor : raw.tensors) {
        write_raw_tensor_stats(output, tensor);
    }
    output << "]" << "raw_head_files" << "[";
    for (const auto& path : raw_head_files) {
        output << "{" << "path" << path.string() << "sha256"
               << edgeai::backends::armnn_sha256_file(path) << "}";
    }
    output << "]" << "decoded_from_multihead" << (raw.tensors.size() > 1U);
    output << "raw_output_stats" << "{" << "shape";
    write_shape(output, decoded.shape);
    output << "dtype" << runtime.output.dtype << "element_count"
           << static_cast<double>(decoded.values.size()) << "finite" << all_finite
           << "min" << (decoded.values.empty() ? 0.0 : static_cast<double>(*minmax.first))
           << "max" << (decoded.values.empty() ? 0.0 : static_cast<double>(*minmax.second))
           << "mean" << mean << "sample_sd" << std::sqrt(variance) << "first_values" << "[";
    for (std::size_t index = 0; index < std::min<std::size_t>(8U, decoded.values.size()); ++index) {
        output << decoded.values[index];
    }
    output << "]" << "}";
    output << "candidate_counts" << "{" << "raw_candidate_count"
           << static_cast<int>(postprocess.raw_candidate_count) << "threshold_candidate_count"
           << static_cast<int>(postprocess.threshold_candidate_count) << "nms_candidate_count"
           << static_cast<int>(postprocess.nms_candidate_count) << "invalid_box_count"
           << static_cast<int>(postprocess.invalid_box_count) << "}";
    output << "detections";
    write_detections(output, postprocess);
    output << "correctness" << "{" << "status" << "NOT_COMPARED_BY_RUNNER"
           << "comparison_tool" << "scripts/vendor/validate_task028_armnn.py" << "}";
    output << "timings" << "{" << "model_load_ms" << model_load_ms
           << "warmup_iterations" << arguments.warmup << "measured_iterations"
           << static_cast<int>(samples.size()) << "samples" << "[";
    for (const auto& sample : samples) {
        output << "{" << "preprocess_ms" << sample.preprocess << "inference_ms"
               << sample.inference << "postprocess_ms" << sample.postprocess << "end_to_end_ms"
               << sample.end_to_end << "process_cpu_ms" << sample.process_cpu << "}";
    }
    output << "]" << "summary_ms" << "{";
    const auto write_summary = [&output, &samples](const char* name, auto selector) {
        std::vector<double> values;
        values.reserve(samples.size());
        for (const auto& sample : samples) {
            values.push_back(selector(sample));
        }
        const Summary summary = summarize(values);
        output << name << "{" << "mean" << summary.mean << "p50" << summary.p50
               << "p95" << summary.p95 << "min" << summary.min << "max" << summary.max
               << "sample_sd" << summary.sample_sd << "}";
    };
    write_summary("preprocess", [](const TimingSample& value) { return value.preprocess; });
    write_summary("inference", [](const TimingSample& value) { return value.inference; });
    write_summary("postprocess", [](const TimingSample& value) { return value.postprocess; });
    write_summary("end_to_end", [](const TimingSample& value) { return value.end_to_end; });
    output << "}" << "fps" << (1000.0 / summarize([&samples]() {
        std::vector<double> values;
        for (const auto& sample : samples) {
            values.push_back(sample.end_to_end);
        }
        return values;
    }()).mean)
           << "boundaries" << "preprocess+inference+postprocess; image read excluded"
           << "}";
    output << "observed_process_threads" << observed_process_threads()
           << "runtime_state" << "CMA/NPU state is collected by the board-side evidence script"
           << "}";
    output.release();
    if (!edgeai::filesystem::is_regular_file(arguments.output_json) ||
        edgeai::filesystem::file_size(arguments.output_json) == 0U) {
        throw std::runtime_error("result JSON was not created");
    }
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        const Arguments arguments = parse_args(argc, argv);
        if (arguments.mode == "correctness" && arguments.repeats != 1) {
            throw std::runtime_error("correctness mode requires --repeats 1");
        }
        const edgeai::common::InferenceConfig config =
            edgeai::common::load_config(arguments.config);
        const std::string model_sha = edgeai::backends::armnn_sha256_file(arguments.model);
        const std::string input_sha = edgeai::backends::armnn_sha256_file(arguments.image);
        const std::string config_sha = edgeai::backends::armnn_sha256_file(arguments.config);
        if (model_sha != expected_model_sha256(arguments) || input_sha != kExpectedInputSha256 ||
            config_sha != kExpectedConfigSha256) {
            throw std::runtime_error("frozen Task 028 model/input/config SHA256 mismatch");
        }
        std::cerr << "ArmNN backend request: Alnpu only; CpuAcc/CpuRef fallback disabled\n";
        const cv::Mat image = edgeai::common::load_bgr_image(arguments.image);
        const auto model_load_start = Clock::now();
        edgeai::backends::ArmnnDetector detector(arguments.model);
        const double model_load_ms = elapsed_ms(model_load_start, Clock::now());
        const auto& runtime = detector.runtime_info();
        if (!runtime.requested_backend_registered || runtime.load_status != "Success") {
            throw std::runtime_error("Alnpu backend was not successfully loaded");
        }

        if (arguments.parse_only) {
            std::cerr << "armnn_parser_probe=PASS_ALNPU_LOAD\n"
                      << "armnn_parser_model_sha256=" << detector.model_sha256() << "\n"
                      << "armnn_parser_input_shape=";
            for (const auto dimension : runtime.input.shape) {
                std::cerr << dimension << "x";
            }
            std::cerr << "\narmnn_parser_output_shape=";
            for (const auto dimension : runtime.output.shape) {
                std::cerr << dimension << "x";
            }
            std::cerr << "\n";
            return 0;
        }

        for (int index = 0; index < arguments.warmup; ++index) {
            const auto preprocessed = edgeai::common::preprocess_image(image, config);
            const auto raw = detector.infer(preprocessed.tensor);
            const auto decoded = raw.tensors.size() > 1U ? decode_al_onnx_heads(raw) : raw;
            static_cast<void>(edgeai::common::decode_yolov5_output(
                decoded.values, decoded.shape, config.class_names, preprocessed.metadata, config));
        }

        std::vector<TimingSample> samples;
        samples.reserve(static_cast<std::size_t>(arguments.repeats));
        edgeai::common::PreprocessResult last_preprocess;
        edgeai::backends::ArmnnRawInferenceResult last_raw;
        edgeai::backends::ArmnnRawInferenceResult last_decoded;
        edgeai::common::PostprocessResult last_postprocess;
        for (int index = 0; index < arguments.repeats; ++index) {
            const double cpu_start = cpu_ms();
            const auto end_to_end_start = Clock::now();
            const auto preprocess_start = Clock::now();
            auto preprocess = edgeai::common::preprocess_image(image, config);
            const double preprocess_ms = elapsed_ms(preprocess_start, Clock::now());
            const auto inference_start = Clock::now();
            auto raw = detector.infer(preprocess.tensor);
            const double inference_ms = elapsed_ms(inference_start, Clock::now());
            auto decoded = raw.tensors.size() > 1U ? decode_al_onnx_heads(raw) : raw;
            const auto postprocess_start = Clock::now();
            auto postprocess = edgeai::common::decode_yolov5_output(
                decoded.values, decoded.shape, config.class_names, preprocess.metadata, config);
            const double postprocess_ms = elapsed_ms(postprocess_start, Clock::now());
            const double end_to_end_ms = elapsed_ms(end_to_end_start, Clock::now());
            const double cpu_end = cpu_ms();
            samples.push_back({
                preprocess_ms, inference_ms, postprocess_ms, end_to_end_ms,
                (cpu_start >= 0.0 && cpu_end >= cpu_start) ? cpu_end - cpu_start : -1.0,
            });
            last_preprocess = std::move(preprocess);
            last_raw = std::move(raw);
            last_decoded = std::move(decoded);
            last_postprocess = std::move(postprocess);
        }
        const auto raw_head_files = write_raw_tensor_files(arguments, last_raw);
        write_json(
            arguments, config, detector, last_preprocess, last_postprocess, last_raw,
            last_decoded, raw_head_files, samples, model_load_ms, "PASS_ALNPU_BACKEND_LOAD"
        );
        std::cerr << "ArmNN Alnpu runner completed; output=" << arguments.output_json << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "edgeai_armnn_image: " << error.what() << '\n';
        return 1;
    }
}
