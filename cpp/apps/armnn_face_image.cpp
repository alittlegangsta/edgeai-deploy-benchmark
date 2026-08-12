#include "edgeai/backends/armnn_detector.hpp"
#include "edgeai/common/detection.hpp"
#include "edgeai/common/postprocess.hpp"
#include "edgeai/common/preprocess.hpp"
#include "edgeai/common/visualize.hpp"

#include <opencv2/core/persistence.hpp>
#include <opencv2/imgproc.hpp>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;
constexpr int kInputWidth = 416;
constexpr int kInputHeight = 416;
constexpr float kConfidenceThreshold = 0.35F;
constexpr float kIouThreshold = 0.45F;
constexpr int kMaxDetections = 100;
constexpr const char* kFaceModelSha256 =
    "5ed304f1cfd37a6c4ddc789a58a4c98e3472efe31eff62fc9e447163ea60668c";

struct Arguments {
    edgeai::filesystem::path model;
    edgeai::filesystem::path image;
    edgeai::filesystem::path output_json;
    edgeai::filesystem::path output_image;
    int warmup{1};
    int repeats{3};
};

struct FacePreprocessResult {
    cv::Mat resized_bgr;
    edgeai::common::InputTensor tensor;
    double x_scale{1.0};
    double y_scale{1.0};
};

struct TimingSample {
    double preprocess_ms{0.0};
    double inference_ms{0.0};
    double postprocess_ms{0.0};
    double end_to_end_ms{0.0};
    double cpu_ms{0.0};
};

struct Summary {
    double mean{0.0};
    double p50{0.0};
    double p95{0.0};
    double min{0.0};
    double max{0.0};
};

int positive_integer(const std::string& value, const char* option) {
    std::size_t consumed = 0U;
    int parsed = 0;
    try {
        parsed = std::stoi(value, &consumed);
    } catch (const std::exception&) {
        throw std::runtime_error(std::string(option) + " must be a positive integer");
    }
    if (consumed != value.size() || parsed <= 0) {
        throw std::runtime_error(std::string(option) + " must be a positive integer");
    }
    return parsed;
}

Arguments parse_args(int argc, char* argv[]) {
    if (argc < 9 || ((argc - 1) % 2) != 0) {
        throw std::runtime_error(
            "usage: edgeai_armnn_face_image --model PATH --image PATH "
            "--output-json PATH --output-image PATH [--warmup N] [--repeats N]"
        );
    }
    Arguments result;
    for (int index = 1; index < argc; index += 2) {
        const std::string option = argv[index];
        const std::string value = argv[index + 1];
        if (option == "--model") {
            result.model = value;
        } else if (option == "--image") {
            result.image = value;
        } else if (option == "--output-json") {
            result.output_json = value;
        } else if (option == "--output-image") {
            result.output_image = value;
        } else if (option == "--warmup") {
            result.warmup = positive_integer(value, "--warmup");
        } else if (option == "--repeats") {
            result.repeats = positive_integer(value, "--repeats");
        } else {
            throw std::runtime_error("unknown option: " + option);
        }
    }
    if (result.model.empty() || result.image.empty() || result.output_json.empty() ||
        result.output_image.empty()) {
        throw std::runtime_error("--model, --image, --output-json and --output-image are required");
    }
    return result;
}

double elapsed_ms(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

double process_cpu_ms() {
    struct rusage usage{};
    if (getrusage(RUSAGE_SELF, &usage) != 0) {
        return -1.0;
    }
    return static_cast<double>(usage.ru_utime.tv_sec + usage.ru_stime.tv_sec) * 1000.0 +
           static_cast<double>(usage.ru_utime.tv_usec + usage.ru_stime.tv_usec) / 1000.0;
}

long long peak_rss_kib() {
    struct rusage usage{};
    if (getrusage(RUSAGE_SELF, &usage) != 0) {
        return -1;
    }
    return static_cast<long long>(usage.ru_maxrss);
}

int process_threads() {
    std::ifstream status("/proc/self/status");
    std::string label;
    while (status >> label) {
        if (label == "Threads:") {
            int value = -1;
            status >> value;
            return value;
        }
        std::string ignored;
        std::getline(status, ignored);
    }
    return -1;
}

Summary summarize(std::vector<double> values) {
    if (values.empty()) {
        throw std::runtime_error("cannot summarize an empty timing list");
    }
    std::sort(values.begin(), values.end());
    const auto percentile = [&values](double q) {
        const auto rank = static_cast<std::size_t>(std::ceil(q * values.size()));
        return values[std::max<std::size_t>(1U, rank) - 1U];
    };
    const double mean = std::accumulate(values.begin(), values.end(), 0.0) /
                        static_cast<double>(values.size());
    return {mean, percentile(0.50), percentile(0.95), values.front(), values.back()};
}

double sigmoid(float value) {
    if (!std::isfinite(value)) {
        throw std::runtime_error("face output contains a non-finite value");
    }
    if (value >= 0.0F) {
        const double e = std::exp(-static_cast<double>(value));
        return 1.0 / (1.0 + e);
    }
    const double e = std::exp(static_cast<double>(value));
    return e / (1.0 + e);
}

FacePreprocessResult preprocess_face(const cv::Mat& image) {
    if (image.empty() || image.type() != CV_8UC3) {
        throw std::runtime_error("face preprocessing expects a BGR CV_8UC3 image");
    }
    cv::Mat resized;
    cv::resize(image, resized, cv::Size(kInputWidth, kInputHeight), 0.0, 0.0, cv::INTER_LINEAR);
    const std::size_t plane = static_cast<std::size_t>(kInputWidth) * kInputHeight;
    edgeai::common::InputTensor tensor;
    tensor.shape = {{1, 3, kInputHeight, kInputWidth}};
    tensor.values.resize(3U * plane);
    for (int y = 0; y < kInputHeight; ++y) {
        const auto* row = resized.ptr<cv::Vec3b>(y);
        for (int x = 0; x < kInputWidth; ++x) {
            const std::size_t offset = static_cast<std::size_t>(y) * kInputWidth + x;
            tensor.values[offset] = static_cast<float>(row[x][2]) / 255.0F;
            tensor.values[plane + offset] = static_cast<float>(row[x][1]) / 255.0F;
            tensor.values[2U * plane + offset] = static_cast<float>(row[x][0]) / 255.0F;
        }
    }
    return {std::move(resized), std::move(tensor),
            static_cast<double>(kInputWidth) / image.cols,
            static_cast<double>(kInputHeight) / image.rows};
}

struct Head {
    const edgeai::backends::ArmnnRawTensor* tensor{nullptr};
    int stride{0};
    int height{0};
    int width{0};
    std::array<float, 6> anchors{};
};

edgeai::common::PostprocessResult decode_face(
    const std::vector<edgeai::backends::ArmnnRawTensor>& tensors,
    double x_scale,
    double y_scale,
    const cv::Size& source_size
) {
    if (tensors.size() != 2U) {
        throw std::runtime_error("face model must expose two YOLO output heads");
    }
    std::vector<Head> heads;
    for (const auto& tensor : tensors) {
        if (tensor.shape.size() != 4U || tensor.shape[0] != 1 || tensor.shape[1] != 18 ||
            tensor.shape[2] != tensor.shape[3] || tensor.shape[2] <= 0 ||
            tensor.values.size() != static_cast<std::size_t>(18 * tensor.shape[2] * tensor.shape[3])) {
            throw std::runtime_error("face output head must be [1,18,H,W]");
        }
        const int height = static_cast<int>(tensor.shape[2]);
        if (kInputHeight % height != 0) {
            throw std::runtime_error("face output grid does not divide 416");
        }
        const int stride = kInputHeight / height;
        if (stride == 16) {
            heads.push_back({&tensor, stride, height, height, {4.0F, 6.0F, 8.0F, 10.0F, 13.0F, 17.0F}});
        } else if (stride == 32) {
            heads.push_back({&tensor, stride, height, height, {26.0F, 35.0F, 60.0F, 78.0F, 162.0F, 206.0F}});
        } else {
            throw std::runtime_error("face output stride must be 16 or 32");
        }
    }
    std::sort(heads.begin(), heads.end(), [](const Head& left, const Head& right) {
        return left.stride < right.stride;
    });

    struct Candidate {
        std::size_t index{0};
        float objectness{0.0F};
        float class_score{0.0F};
        float confidence{0.0F};
        edgeai::common::Box xywh{};
        edgeai::common::Box xyxy{};
    };
    std::vector<Candidate> candidates;
    std::size_t candidate_index = 0U;
    for (const auto& head : heads) {
        const auto& values = head.tensor->values;
        const int area = head.height * head.width;
        const auto value_at = [&](int anchor, int channel, int y, int x) {
            const std::size_t offset =
                (static_cast<std::size_t>(anchor * 6 + channel) * area +
                 static_cast<std::size_t>(y) * head.width + x);
            return values.at(offset);
        };
        for (int y = 0; y < head.height; ++y) {
            for (int x = 0; x < head.width; ++x) {
                for (int anchor = 0; anchor < 3; ++anchor, ++candidate_index) {
                    const float objectness = static_cast<float>(sigmoid(value_at(anchor, 4, y, x)));
                    const float class_score = static_cast<float>(sigmoid(value_at(anchor, 5, y, x)));
                    const float confidence = objectness * class_score;
                    if (confidence < kConfidenceThreshold) {
                        continue;
                    }
                    const float cx = static_cast<float>((sigmoid(value_at(anchor, 0, y, x)) * 2.0 + x) * head.stride);
                    const float cy = static_cast<float>((sigmoid(value_at(anchor, 1, y, x)) * 2.0 + y) * head.stride);
                    const float width = static_cast<float>(std::pow(sigmoid(value_at(anchor, 2, y, x)) * 2.0, 2.0) * head.anchors[anchor * 2]);
                    const float height = static_cast<float>(std::pow(sigmoid(value_at(anchor, 3, y, x)) * 2.0, 2.0) * head.anchors[anchor * 2 + 1]);
                    const edgeai::common::Box xywh{cx, cy, width, height};
                    candidates.push_back({candidate_index, objectness, class_score, confidence,
                                          xywh, edgeai::common::xywh_to_xyxy(xywh)});
                }
            }
        }
    }

    std::sort(candidates.begin(), candidates.end(), [](const Candidate& left, const Candidate& right) {
        if (left.confidence != right.confidence) {
            return left.confidence > right.confidence;
        }
        return left.index < right.index;
    });
    std::vector<std::size_t> kept;
    for (std::size_t index = 0; index < candidates.size() && kept.size() < kMaxDetections; ++index) {
        bool suppressed = false;
        for (const auto kept_index : kept) {
            if (edgeai::common::box_iou(candidates[index].xyxy, candidates[kept_index].xyxy) > kIouThreshold) {
                suppressed = true;
                break;
            }
        }
        if (!suppressed) {
            kept.push_back(index);
        }
    }

    edgeai::common::PostprocessResult result;
    result.raw_candidate_count = 3U * (26U * 26U + 13U * 13U);
    result.threshold_candidate_count = candidates.size();
    result.nms_candidate_count = kept.size();
    result.detections.reserve(kept.size());
    for (const auto kept_index : kept) {
        const auto& candidate = candidates[kept_index];
        const auto source = edgeai::common::Box{
            static_cast<float>(candidate.xyxy.x1 / x_scale),
            static_cast<float>(candidate.xyxy.y1 / y_scale),
            static_cast<float>(candidate.xyxy.x2 / x_scale),
            static_cast<float>(candidate.xyxy.y2 / y_scale),
        };
        edgeai::common::Detection detection;
        detection.rank = result.detections.size() + 1U;
        detection.candidate_index = candidate.index;
        detection.class_id = 0;
        detection.class_name = "face";
        detection.objectness = candidate.objectness;
        detection.class_score = candidate.class_score;
        detection.confidence = candidate.confidence;
        detection.box_xywh_input = candidate.xywh;
        detection.box_xyxy_input = candidate.xyxy;
        detection.box_xyxy_source = {
            std::clamp(source.x1, 0.0F, static_cast<float>(source_size.width)),
            std::clamp(source.y1, 0.0F, static_cast<float>(source_size.height)),
            std::clamp(source.x2, 0.0F, static_cast<float>(source_size.width)),
            std::clamp(source.y2, 0.0F, static_cast<float>(source_size.height)),
        };
        if (detection.box_xyxy_source.x2 <= detection.box_xyxy_source.x1 ||
            detection.box_xyxy_source.y2 <= detection.box_xyxy_source.y1) {
            ++result.invalid_box_count;
            continue;
        }
        result.detections.push_back(std::move(detection));
    }
    edgeai::common::validate_frame_detections(
        result.detections, source_size.width, source_size.height, 0);
    return result;
}

void write_shape(cv::FileStorage& output, const std::vector<std::int64_t>& shape) {
    output << "[";
    for (const auto dimension : shape) {
        output << static_cast<int>(dimension);
    }
    output << "]";
}

void write_descriptor(cv::FileStorage& output, const edgeai::backends::ArmnnTensorDescriptor& descriptor) {
    output << "{" << "name" << descriptor.name << "dtype" << descriptor.dtype << "shape";
    write_shape(output, descriptor.shape);
    output << "bytes" << static_cast<double>(descriptor.bytes)
           << "quantization_scale" << descriptor.quantization_scale
           << "quantization_offset" << static_cast<double>(descriptor.quantization_offset) << "}";
}

void write_detections(cv::FileStorage& output, const std::vector<edgeai::common::Detection>& detections) {
    output << "[";
    for (const auto& detection : detections) {
        const auto write_box = [&output](const edgeai::common::Box& box) {
            output << "[" << box.x1 << box.y1 << box.x2 << box.y2 << "]";
        };
        output << "{" << "rank" << static_cast<int>(detection.rank)
               << "class_id" << detection.class_id << "class_name" << detection.class_name
               << "objectness" << detection.objectness << "class_score" << detection.class_score
               << "confidence" << detection.confidence << "box_xyxy_input";
        write_box(detection.box_xyxy_input);
        output << "box_xyxy_source";
        write_box(detection.box_xyxy_source);
        output << "}";
    }
    output << "]";
}

void write_raw_stats(cv::FileStorage& output, const edgeai::backends::ArmnnRawTensor& tensor) {
    const auto minmax = std::minmax_element(tensor.values.begin(), tensor.values.end());
    const double mean = tensor.values.empty()
                            ? 0.0
                            : std::accumulate(tensor.values.begin(), tensor.values.end(), 0.0) /
                                  static_cast<double>(tensor.values.size());
    output << "{" << "name" << tensor.name << "shape";
    write_shape(output, tensor.shape);
    output << "dtype" << "float32_dequantized" << "element_count"
           << static_cast<double>(tensor.values.size()) << "finite"
           << std::all_of(tensor.values.begin(), tensor.values.end(), [](float value) {
                  return std::isfinite(value);
              })
           << "min" << (tensor.values.empty() ? 0.0 : static_cast<double>(*minmax.first))
           << "max" << (tensor.values.empty() ? 0.0 : static_cast<double>(*minmax.second))
           << "mean" << mean << "}";
}

void write_result(
    const Arguments& arguments,
    const edgeai::backends::ArmnnDetector& detector,
    const cv::Mat& image,
    const FacePreprocessResult& preprocess,
    const edgeai::common::PostprocessResult& postprocess,
    const edgeai::backends::ArmnnRawInferenceResult& raw,
    const std::vector<TimingSample>& samples,
    double model_load_ms,
    const std::string& status
) {
    if (!arguments.output_json.parent_path().empty()) {
        edgeai::filesystem::create_directories(arguments.output_json.parent_path());
    }
    cv::FileStorage output(arguments.output_json.string(), cv::FileStorage::WRITE | cv::FileStorage::FORMAT_JSON);
    if (!output.isOpened()) {
        throw std::runtime_error("failed to open output JSON");
    }
    const auto& runtime = detector.runtime_info();
    output << "schema_version" << 1 << "application" << "edgeai_armnn_face_image"
           << "status" << status << "model_sha256" << detector.model_sha256()
           << "model_expected_sha256" << kFaceModelSha256;
    output << "runtime" << "{" << "armnn_version" << runtime.version
           << "requested_backend" << runtime.requested_backend
           << "fallback_allowed" << false
           << "requested_backend_registered" << runtime.requested_backend_registered
           << "load_status" << runtime.load_status << "load_error" << runtime.load_error
           << "selected_backend" << "Alnpu"
           << "alhardnpu_assignment" << "must be confirmed in captured ArmNN process log"
           << "supported_backends" << "[";
    for (const auto& backend : runtime.supported_backends) {
        output << backend;
    }
    output << "]" << "optimizer_messages" << "[";
    for (const auto& message : runtime.optimizer_messages) {
        output << message;
    }
    output << "]" << "cpu_fallback" << false << "}";
    output << "model" << "{" << "path" << arguments.model.string()
           << "source" << "Anlogic dr1m90_npu face_detection yolo_face_uint8_15.onnx"
           << "input_shape" << "[" << 1 << 3 << kInputHeight << kInputWidth << "]"
           << "output_contract" << "two [1,18,H,W] heads at stride 16 and 32" << "}";
    output << "input" << "{" << "path" << arguments.image.string()
           << "sha256" << edgeai::backends::armnn_sha256_file(arguments.image)
           << "shape_bgr" << "[" << image.rows << image.cols << 3 << "]" << "}";
    output << "preprocess" << "{" << "method" << "vendor face resize (no letterbox)"
           << "resize" << "[" << kInputHeight << kInputWidth << "]"
           << "transforms" << "[" << "BGR_TO_RGB" << "HWC_TO_CHW" << "uint8_TO_float32"
           << "divide_by_255" << "]" << "x_scale" << preprocess.x_scale
           << "y_scale" << preprocess.y_scale << "}";
    output << "tensor_contract" << "{" << "input";
    write_descriptor(output, runtime.input);
    output << "outputs" << "[";
    for (const auto& descriptor : runtime.outputs) {
        write_descriptor(output, descriptor);
    }
    output << "]" << "}";
    output << "raw_outputs" << "[";
    for (const auto& tensor : raw.tensors) {
        write_raw_stats(output, tensor);
    }
    output << "]";
    output << "detections";
    write_detections(output, postprocess.detections);
    output << "counts" << "{" << "raw_candidates" << static_cast<int>(postprocess.raw_candidate_count)
           << "threshold_candidates" << static_cast<int>(postprocess.threshold_candidate_count)
           << "nms_candidates" << static_cast<int>(postprocess.nms_candidate_count)
           << "detections" << static_cast<int>(postprocess.detections.size()) << "}";
    output << "timings" << "{" << "model_load_ms" << model_load_ms
           << "warmup" << arguments.warmup << "repeats" << static_cast<int>(samples.size())
           << "samples" << "[";
    for (const auto& sample : samples) {
        output << "{" << "preprocess_ms" << sample.preprocess_ms << "inference_ms"
               << sample.inference_ms << "postprocess_ms" << sample.postprocess_ms
               << "end_to_end_ms" << sample.end_to_end_ms << "cpu_ms" << sample.cpu_ms << "}";
    }
    output << "]";
    const auto summary_field = [&output, &samples](const char* name, auto selector) {
        std::vector<double> values;
        values.reserve(samples.size());
        for (const auto& sample : samples) {
            values.push_back(selector(sample));
        }
        const Summary summary = summarize(std::move(values));
        output << name << "{" << "mean" << summary.mean << "p50" << summary.p50
               << "p95" << summary.p95 << "min" << summary.min << "max" << summary.max << "}";
    };
    output << "summary_ms" << "{";
    summary_field("preprocess", [](const TimingSample& value) { return value.preprocess_ms; });
    summary_field("inference", [](const TimingSample& value) { return value.inference_ms; });
    summary_field("postprocess", [](const TimingSample& value) { return value.postprocess_ms; });
    summary_field("end_to_end", [](const TimingSample& value) { return value.end_to_end_ms; });
    output << "}" << "fps" << (1000.0 / summarize([&samples] {
        std::vector<double> values;
        for (const auto& sample : samples) {
            values.push_back(sample.end_to_end_ms);
        }
        return values;
    }()).mean) << "peak_rss_kib" << static_cast<double>(peak_rss_kib())
           << "observed_process_threads" << process_threads()
           << "benchmark_scope" << "functional face control only; not compared to YOLOv5n"
           << "}";
    output.release();
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        const Arguments arguments = parse_args(argc, argv);
        const std::string model_sha = edgeai::backends::armnn_sha256_file(arguments.model);
        if (model_sha != kFaceModelSha256) {
            throw std::runtime_error("face control model SHA256 does not match audited vendor asset");
        }
        const cv::Mat image = edgeai::common::load_bgr_image(arguments.image);
        const auto model_load_start = Clock::now();
        edgeai::backends::ArmnnDetector detector(arguments.model);
        const double model_load_ms = elapsed_ms(model_load_start, Clock::now());
        const auto& runtime = detector.runtime_info();
        if (!runtime.requested_backend_registered || runtime.load_status != "Success" ||
            runtime.requested_backend != "Alnpu" || runtime.fallback_allowed) {
            throw std::runtime_error("strict Alnpu-only runtime contract was not established");
        }
        std::cerr << "backend_request=Alnpu fallback_allowed=false\n";
        std::vector<TimingSample> samples;
        edgeai::backends::ArmnnRawInferenceResult last_raw;
        for (int index = 0; index < arguments.warmup; ++index) {
            const auto preprocessed = preprocess_face(image);
            const auto raw = detector.infer(preprocessed.tensor);
            static_cast<void>(decode_face(raw.tensors, preprocessed.x_scale,
                                          preprocessed.y_scale, image.size()));
        }
        edgeai::common::PostprocessResult last_postprocess;
        FacePreprocessResult last_preprocess;
        for (int index = 0; index < arguments.repeats; ++index) {
            const double cpu_start = process_cpu_ms();
            const auto end_to_end_start = Clock::now();
            const auto preprocess_start = Clock::now();
            auto preprocessed = preprocess_face(image);
            const double preprocess_ms = elapsed_ms(preprocess_start, Clock::now());
            const auto inference_start = Clock::now();
            const auto raw = detector.infer(preprocessed.tensor);
            const double inference_ms = elapsed_ms(inference_start, Clock::now());
            const auto postprocess_start = Clock::now();
            auto postprocess = decode_face(raw.tensors, preprocessed.x_scale,
                                           preprocessed.y_scale, image.size());
            const double postprocess_ms = elapsed_ms(postprocess_start, Clock::now());
            const double end_to_end_ms = elapsed_ms(end_to_end_start, Clock::now());
            const double cpu_end = process_cpu_ms();
            samples.push_back({preprocess_ms, inference_ms, postprocess_ms, end_to_end_ms,
                               (cpu_start >= 0.0 && cpu_end >= cpu_start) ? cpu_end - cpu_start : -1.0});
            last_preprocess = std::move(preprocessed);
            last_raw = raw;
            last_postprocess = std::move(postprocess);
        }
        const cv::Mat annotated = edgeai::common::draw_detections(image, last_postprocess.detections);
        edgeai::common::save_image(arguments.output_image, annotated);
        write_result(arguments, detector, image, last_preprocess, last_postprocess, last_raw,
                     samples, model_load_ms, "PASS_ALNPU_ONLY");
        std::cerr << "edgeai_armnn_face_image status=PASS_ALNPU_ONLY detections="
                  << last_postprocess.detections.size() << " output=" << arguments.output_json << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "edgeai_armnn_face_image: " << error.what() << '\n';
        return 1;
    }
}
