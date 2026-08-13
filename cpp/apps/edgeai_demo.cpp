#include "edgeai/common/benchmark.hpp"
#include "edgeai/common/config.hpp"
#include "edgeai/common/postprocess.hpp"
#include "edgeai/common/preprocess.hpp"
#include "edgeai/common/video_pipeline.hpp"
#include "edgeai/common/visualize.hpp"
#include "edgeai/inference_backend.hpp"

#include <opencv2/core/persistence.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/videoio.hpp>

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;

struct Arguments {
    std::string backend;
    std::filesystem::path model;
    std::filesystem::path manifest;
    std::filesystem::path model_param;
    std::filesystem::path model_bin;
    std::filesystem::path source;
    std::string camera;
    bool camera_mode{false};
    std::filesystem::path config{"configs/yolov5n_v7_inference.json"};
    std::filesystem::path output_image{"edgeai_demo.png"};
    std::filesystem::path output_json{"edgeai_demo.json"};
    std::filesystem::path output_video;
    std::string output_codec{"MJPG"};
    std::filesystem::path golden;
    std::string precision{"fp32"};
    bool benchmark{false};
    int warmup{0};
    int repeat{1};
    int threads{2};
    bool packing{true};
    std::size_t max_frames{0U};
    double max_duration_seconds{0.0};
};

struct Stats {
    double mean{0.0};
    double p50{0.0};
    double p95{0.0};
};

struct Sample {
    double preprocess{0.0};
    double inference{0.0};
    double postprocess{0.0};
    double pipeline{0.0};
};

struct GoldenDetection {
    int class_id{-1};
    float confidence{0.0F};
    edgeai::common::Box box;
    std::string class_name;
};

struct GoldenCheck {
    std::string status{"NOT_REQUESTED"};
    std::size_t expected_count{0};
    std::size_t observed_count{0};
    double minimum_iou{1.0};
    double maximum_confidence_delta{0.0};
};

double elapsed_ms(const Clock::time_point start, const Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

int parse_positive_int(const std::string& value, const char* option) {
    std::size_t consumed = 0U;
    int result = 0;
    try {
        result = std::stoi(value, &consumed);
    } catch (const std::exception&) {
        throw std::runtime_error(std::string(option) + " must be a positive integer");
    }
    if (consumed != value.size() || result <= 0) {
        throw std::runtime_error(std::string(option) + " must be a positive integer");
    }
    return result;
}

std::size_t parse_nonnegative_size(const std::string& value, const char* option) {
    std::size_t consumed = 0U;
    unsigned long long result = 0U;
    try {
        result = std::stoull(value, &consumed);
    } catch (const std::exception&) {
        throw std::runtime_error(std::string(option) + " must be a nonnegative integer");
    }
    if (consumed != value.size()) {
        throw std::runtime_error(std::string(option) + " must be a nonnegative integer");
    }
    return static_cast<std::size_t>(result);
}

double parse_positive_double(const std::string& value, const char* option) {
    std::size_t consumed = 0U;
    double result = 0.0;
    try {
        result = std::stod(value, &consumed);
    } catch (const std::exception&) {
        throw std::runtime_error(std::string(option) + " must be a positive number");
    }
    if (consumed != value.size() || !std::isfinite(result) || result <= 0.0) {
        throw std::runtime_error(std::string(option) + " must be a positive number");
    }
    return result;
}

Arguments parse_args(const int argc, char* argv[]) {
    Arguments args;
    std::map<std::string, std::string> values;
    const std::vector<std::string> valued{
        "--backend", "--model", "--manifest", "--model-param", "--model-bin", "--source",
        "--camera", "--output-video", "--output-codec", "--max-frames", "--max-duration-seconds",
        "--config", "--output-image", "--output-json", "--golden", "--precision", "--warmup",
        "--repeat", "--threads", "--packing",
    };
    for (int index = 1; index < argc; ++index) {
        const std::string option = argv[index];
        if (option == "--benchmark") {
            if (args.benchmark) {
                throw std::runtime_error("duplicate argument: --benchmark");
            }
            args.benchmark = true;
            continue;
        }
        if (std::find(valued.begin(), valued.end(), option) == valued.end()) {
            throw std::runtime_error("unknown argument: " + option);
        }
        if (index + 1 >= argc || argv[index + 1][0] == '-') {
            throw std::runtime_error("missing value for " + option);
        }
        if (!values.emplace(option, argv[++index]).second) {
            throw std::runtime_error("duplicate argument: " + option);
        }
    }
    for (const char* required : {"--backend", "--model"}) {
        if (values.count(required) == 0U) {
            throw std::runtime_error(
                "usage: edgeai_demo --backend ort|tensorrt|ncnn --model PATH "
                "(--source IMAGE_OR_VIDEO|--camera DEVICE) [--output-video PATH] "
                "[--manifest PATH] [--precision fp32|fp16|int8] [--benchmark] "
                "[--warmup N --repeat N]"
            );
        }
    }
    const bool has_source = values.count("--source") != 0U;
    const bool has_camera = values.count("--camera") != 0U;
    if (has_source == has_camera) {
        throw std::runtime_error("exactly one of --source or --camera is required");
    }
    args.backend = values.at("--backend");
    args.model = values.at("--model");
    if (has_source) {
        args.source = values.at("--source");
    } else {
        args.camera_mode = true;
        args.camera = values.at("--camera");
    }
    if (values.count("--manifest") != 0U) args.manifest = values.at("--manifest");
    if (values.count("--model-param") != 0U) args.model_param = values.at("--model-param");
    if (values.count("--model-bin") != 0U) args.model_bin = values.at("--model-bin");
    if (values.count("--config") != 0U) args.config = values.at("--config");
    if (values.count("--output-image") != 0U) args.output_image = values.at("--output-image");
    if (values.count("--output-json") != 0U) args.output_json = values.at("--output-json");
    if (values.count("--output-video") != 0U) args.output_video = values.at("--output-video");
    if (values.count("--output-codec") != 0U) args.output_codec = values.at("--output-codec");
    if (args.output_codec.size() != 4U) {
        throw std::runtime_error("--output-codec must contain exactly four characters");
    }
    if (values.count("--golden") != 0U) args.golden = values.at("--golden");
    if (values.count("--precision") != 0U) args.precision = values.at("--precision");
    if (values.count("--warmup") != 0U) args.warmup = parse_positive_int(values.at("--warmup"), "--warmup");
    if (values.count("--repeat") != 0U) args.repeat = parse_positive_int(values.at("--repeat"), "--repeat");
    if (values.count("--threads") != 0U) args.threads = parse_positive_int(values.at("--threads"), "--threads");
    if (values.count("--packing") != 0U) {
        if (values.at("--packing") != "0" && values.at("--packing") != "1") {
            throw std::runtime_error("--packing must be 0 or 1");
        }
        args.packing = values.at("--packing") == "1";
    }
    if (values.count("--max-frames") != 0U) {
        args.max_frames = parse_nonnegative_size(values.at("--max-frames"), "--max-frames");
    }
    if (values.count("--max-duration-seconds") != 0U) {
        args.max_duration_seconds = parse_positive_double(
            values.at("--max-duration-seconds"), "--max-duration-seconds"
        );
    }
    if (args.precision != "fp32" && args.precision != "fp16" && args.precision != "int8") {
        throw std::runtime_error("--precision must be fp32, fp16 or int8");
    }
    if (args.backend == "ort" && args.precision != "fp32") {
        throw std::runtime_error("ORT supports only --precision fp32; no fallback is attempted");
    }
    if (args.backend == "tensorrt" && args.precision == "int8") {
        throw std::runtime_error("TensorRT INT8 is outside the frozen Task 037 contract");
    }
    if (args.backend == "ncnn" && args.manifest.empty()) args.manifest = args.model;
    if (args.backend == "ort" && args.manifest.empty()) {
        throw std::runtime_error("ORT requires --manifest matching the frozen ONNX contract");
    }
    if ((args.model_param.empty()) != (args.model_bin.empty())) {
        throw std::runtime_error("--model-param and --model-bin must be supplied together");
    }
    if (args.benchmark) {
        if (args.warmup == 0) args.warmup = 10;
        if (args.repeat == 1) args.repeat = 100;
    }
    if (args.camera_mode && args.max_frames == 0U && args.max_duration_seconds == 0.0) {
        throw std::runtime_error(
            "camera input requires --max-frames or --max-duration-seconds to remain bounded"
        );
    }
    return args;
}

Stats stats(std::vector<double> values) {
    if (values.empty()) throw std::runtime_error("cannot summarize an empty benchmark");
    std::sort(values.begin(), values.end());
    const double total = std::accumulate(values.begin(), values.end(), 0.0);
    const auto percentile = [&values](double fraction) {
        const std::size_t index = static_cast<std::size_t>(
            std::ceil(fraction * static_cast<double>(values.size()))
        ) - 1U;
        return values[std::min(index, values.size() - 1U)];
    };
    return {total / static_cast<double>(values.size()), percentile(0.50), percentile(0.95)};
}

void write_shape(cv::FileStorage& output, const std::vector<std::int64_t>& shape) {
    output << "[";
    for (const auto value : shape) output << static_cast<int>(value);
    output << "]";
}

void write_box(cv::FileStorage& output, const edgeai::common::Box& box) {
    output << "[" << box.x1 << box.y1 << box.x2 << box.y2 << "]";
}

void write_detections(
    cv::FileStorage& output,
    const std::vector<edgeai::common::Detection>& detections
) {
    output << "[";
    for (const auto& detection : detections) {
        output << "{" << "rank" << static_cast<int>(detection.rank)
               << "candidate_index" << static_cast<int>(detection.candidate_index)
               << "class_id" << detection.class_id << "class_name" << detection.class_name
               << "objectness" << detection.objectness << "class_score" << detection.class_score
               << "confidence" << detection.confidence << "box_xyxy_source";
        write_box(output, detection.box_xyxy_source);
        output << "}";
    }
    output << "]";
}

std::vector<GoldenDetection> read_golden(const std::filesystem::path& path) {
    cv::FileStorage storage(path.string(), cv::FileStorage::READ | cv::FileStorage::FORMAT_JSON);
    if (!storage.isOpened()) throw std::runtime_error("failed to open Golden JSON: " + path.string());
    const cv::FileNode detections = storage["detections"];
    if (!detections.isSeq()) throw std::runtime_error("Golden JSON detections is not an array");
    std::vector<GoldenDetection> result;
    for (const auto& node : detections) {
        const cv::FileNode box = node["box_xyxy_source"];
        if (!box.isSeq() || box.size() != 4U) throw std::runtime_error("Golden box is invalid");
        result.push_back({
            static_cast<int>(node["class_id"]), static_cast<float>(node["confidence"]),
            {static_cast<float>(box[0]), static_cast<float>(box[1]), static_cast<float>(box[2]),
             static_cast<float>(box[3])},
            static_cast<std::string>(node["class_name"]),
        });
    }
    return result;
}

GoldenCheck check_golden(
    const std::filesystem::path& path,
    const std::vector<edgeai::common::Detection>& detections
) {
    const auto expected = read_golden(path);
    GoldenCheck result{"PASS", expected.size(), detections.size(), 1.0, 0.0};
    if (expected.size() != detections.size()) {
        result.status = "FAIL";
        return result;
    }
    std::vector<bool> matched(detections.size(), false);
    for (const auto& reference : expected) {
        std::size_t best = detections.size();
        double best_iou = -1.0;
        for (std::size_t index = 0; index < detections.size(); ++index) {
            if (matched[index] || detections[index].class_id != reference.class_id ||
                detections[index].class_name != reference.class_name) continue;
            const double iou = edgeai::common::box_iou(reference.box, detections[index].box_xyxy_source);
            if (iou > best_iou) { best = index; best_iou = iou; }
        }
        if (best == detections.size()) { result.status = "FAIL"; return result; }
        const double confidence_delta = std::abs(
            static_cast<double>(reference.confidence) - detections[best].confidence
        );
        result.minimum_iou = std::min(result.minimum_iou, best_iou);
        result.maximum_confidence_delta = std::max(result.maximum_confidence_delta, confidence_delta);
        matched[best] = true;
        // The existing single-image Golden contract is strict: IoU >= 0.99
        // and confidence delta <= 0.001.  Task037's broader FP16 COCO gate
        // remains a separate diagnostic and is not silently substituted here.
        if (best_iou < 0.99 || confidence_delta > 0.001) result.status = "FAIL";
    }
    return result;
}

long max_rss_kib() {
    struct rusage usage {};
    if (getrusage(RUSAGE_SELF, &usage) != 0) return -1;
    return usage.ru_maxrss;
}

void write_timing_stats(cv::FileStorage& output, const std::vector<Sample>& samples) {
    std::vector<double> preprocess, inference, postprocess, pipeline;
    for (const auto& sample : samples) {
        preprocess.push_back(sample.preprocess);
        inference.push_back(sample.inference);
        postprocess.push_back(sample.postprocess);
        pipeline.push_back(sample.pipeline);
    }
    const auto write_stats = [&output](const Stats& value) {
        output << "{" << "mean_ms" << value.mean << "p50_ms" << value.p50 << "p95_ms" << value.p95
               << "}";
    };
    output << "timings_ms" << "{" << "preprocess"; write_stats(stats(preprocess));
    output << "inference"; write_stats(stats(inference));
    output << "postprocess"; write_stats(stats(postprocess));
    output << "pipeline"; write_stats(stats(pipeline));
    output << "fps" << 1000.0 / stats(pipeline).mean
           << "measurement" << "steady_clock; image already decoded; no fallback" << "}";
}

void write_output(
    const Arguments& args,
    const edgeai::common::InferenceConfig& config,
    const edgeai::unified::InferenceBackend& backend,
    const edgeai::common::PostprocessResult& postprocess,
    const std::vector<std::int64_t>& raw_shape,
    const cv::Mat& source,
    const cv::Mat& rendered,
    const std::vector<Sample>& samples,
    const GoldenCheck& golden,
    const std::filesystem::path& output_path
) {
    if (!output_path.parent_path().empty()) std::filesystem::create_directories(output_path.parent_path());
    cv::FileStorage output(output_path.string(), cv::FileStorage::WRITE | cv::FileStorage::FORMAT_JSON);
    if (!output.isOpened()) throw std::runtime_error("failed to open output JSON: " + output_path.string());
    const auto& info = backend.info();
    output << "schema_version" << 1 << "application" << "edgeai_demo"
           << "backend" << "{" << "name" << info.backend << "runtime" << info.runtime
           << "model_identity" << info.model_identity << "precision" << info.precision
           << "input_dtype" << info.input_dtype << "output_dtype" << info.output_dtype
           << "input_shape"; write_shape(output, info.input_shape);
    output << "output_shape"; write_shape(output, info.output_shape);
    output << "fallback" << "none" << "}";
    output << "model" << "{" << "path" << args.model.string() << "manifest" << args.manifest.string()
           << "}" << "source" << "{" << "path" << args.source.string() << "shape_bgr"
           << "[" << source.rows << source.cols << source.channels() << "]" << "}";
    output << "configuration" << "{" << "path" << args.config.string() << "input_size"
           << "[" << config.input_size.height << config.input_size.width << "]"
           << "confidence_threshold" << config.confidence_threshold << "iou_threshold"
           << config.iou_threshold << "class_aware_nms" << config.class_aware_nms
           << "max_detections" << config.max_detections << "precision" << args.precision
           << "threads" << args.threads << "packing" << args.packing << "}";
    output << "raw_output" << "{" << "shape"; write_shape(output, raw_shape); output << "dtype" << "float32" << "}";
    output << "candidate_counts" << "{" << "raw" << static_cast<int>(postprocess.raw_candidate_count)
           << "threshold" << static_cast<int>(postprocess.threshold_candidate_count)
           << "nms" << static_cast<int>(postprocess.nms_candidate_count)
           << "invalid_boxes" << static_cast<int>(postprocess.invalid_box_count) << "}";
    output << "detections"; write_detections(output, postprocess.detections);
    output << "correctness" << "{" << "golden_path" << args.golden.string() << "status" << golden.status
           << "expected_count" << static_cast<int>(golden.expected_count)
           << "observed_count" << static_cast<int>(golden.observed_count)
           << "minimum_iou" << golden.minimum_iou
           << "maximum_confidence_delta" << golden.maximum_confidence_delta << "}";
    output << "output_image" << "{" << "path" << args.output_image.string() << "rows" << rendered.rows
           << "cols" << rendered.cols << "channels" << rendered.channels() << "decode" << "PASS" << "}";
    write_timing_stats(output, samples);
    output << "resources" << "{" << "peak_rss_kib" << static_cast<int>(max_rss_kib()) << "}";
    output.release();
}

struct VideoFrameRecord {
    std::size_t frame_index{0U};
    edgeai::common::VideoFrameTimingsMs timings;
    edgeai::common::PostprocessResult postprocess;
    std::vector<std::int64_t> raw_shape;
};

struct VideoRunCounts {
    std::size_t captured{0U};
    std::size_t processed{0U};
    std::size_t failed{0U};
    std::size_t written{0U};
};

std::unique_ptr<edgeai::unified::InferenceBackend> make_backend(const Arguments& args) {
    edgeai::unified::BackendOptions options;
    options.backend = args.backend;
    options.precision = args.precision;
    options.model = args.backend == "ncnn" ? args.manifest : args.model;
    options.manifest = args.manifest;
    options.model_param = args.model_param;
    options.model_bin = args.model_bin;
    options.threads = args.threads;
    options.packing = args.packing;
    return edgeai::unified::make_inference_backend(options);
}

cv::VideoCapture open_camera(const std::string& specification) {
    bool numeric = !specification.empty();
    for (const char character : specification) {
        if (!std::isdigit(static_cast<unsigned char>(character))) {
            numeric = false;
            break;
        }
    }
    cv::VideoCapture capture;
    if (numeric) {
        capture.open(std::stoi(specification), cv::CAP_ANY);
    } else {
        capture.open(specification, cv::CAP_ANY);
    }
    if (!capture.isOpened()) {
        throw std::runtime_error("failed to open camera: " + specification);
    }
    return capture;
}

int fourcc_from_string(const std::string& value) {
    return cv::VideoWriter::fourcc(value[0], value[1], value[2], value[3]);
}

cv::Mat draw_video_overlay(
    const cv::Mat& frame,
    const std::vector<edgeai::common::Detection>& detections,
    const edgeai::unified::BackendInfo& backend,
    double inference_ms,
    double pipeline_fps
) {
    cv::Mat rendered = edgeai::common::draw_detections(frame, detections);
    std::ostringstream text;
    text << backend.backend << " " << backend.precision << "  inference "
         << std::fixed << std::setprecision(2) << inference_ms << " ms  pipeline FPS "
         << pipeline_fps << "  detections " << detections.size();
    const std::string label = text.str();
    int baseline = 0;
    const cv::Size size = cv::getTextSize(label, cv::FONT_HERSHEY_SIMPLEX, 0.55, 1, &baseline);
    cv::rectangle(
        rendered,
        {0, 0},
        {std::min(rendered.cols - 1, size.width + 8), std::min(rendered.rows - 1, size.height + baseline + 8)},
        {0, 0, 0},
        cv::FILLED
    );
    cv::putText(
        rendered,
        label,
        {4, size.height + 2},
        cv::FONT_HERSHEY_SIMPLEX,
        0.55,
        {255, 255, 255},
        1,
        cv::LINE_AA
    );
    return rendered;
}

void write_video_metadata(
    cv::FileStorage& output,
    const edgeai::common::VideoMetadata& metadata
) {
    output << "{" << "width" << metadata.width << "height" << metadata.height << "fps"
           << metadata.fps << "reported_frame_count"
           << static_cast<int>(metadata.reported_frame_count) << "fourcc" << metadata.fourcc
           << "backend" << metadata.backend << "}";
}

void write_video_frame_record(cv::FileStorage& output, const VideoFrameRecord& record) {
    output << "{" << "frame_index" << static_cast<int>(record.frame_index)
           << "timings_ms" << "{" << "capture_read" << record.timings.video_read
           << "preprocess" << record.timings.preprocess << "inference"
           << record.timings.inference << "postprocess" << record.timings.postprocess
           << "visualization" << record.timings.visualization << "video_write"
           << record.timings.video_write << "pipeline_total" << record.timings.pipeline_total << "}"
           << "raw_shape";
    write_shape(output, record.raw_shape);
    output << "detections";
    write_detections(output, record.postprocess.detections);
    output << "}";
}

void write_video_output(
    const Arguments& args,
    const edgeai::common::InferenceConfig& config,
    const edgeai::unified::InferenceBackend& backend,
    const edgeai::common::VideoMetadata& input_metadata,
    const edgeai::common::VideoMetadata& output_metadata,
    const std::string& source_kind,
    const std::string& writer_backend,
    const VideoRunCounts& counts,
    const std::vector<VideoFrameRecord>& records,
    double elapsed_loop_ms,
    const GoldenCheck& first_frame_golden
) {
    if (!args.output_json.parent_path().empty()) {
        std::filesystem::create_directories(args.output_json.parent_path());
    }
    cv::FileStorage output(
        args.output_json.string(), cv::FileStorage::WRITE | cv::FileStorage::FORMAT_JSON
    );
    if (!output.isOpened()) {
        throw std::runtime_error("failed to open video output JSON: " + args.output_json.string());
    }
    const auto& info = backend.info();
    std::vector<double> read, preprocess, inference, postprocess, visualization, write, pipeline;
    for (const auto& record : records) {
        read.push_back(record.timings.video_read);
        preprocess.push_back(record.timings.preprocess);
        inference.push_back(record.timings.inference);
        postprocess.push_back(record.timings.postprocess);
        visualization.push_back(record.timings.visualization);
        write.push_back(record.timings.video_write);
        pipeline.push_back(record.timings.pipeline_total);
    }
    const auto write_stats = [&output](const std::vector<double>& values) {
        const Stats summary = stats(values);
        output << "{" << "mean_ms" << summary.mean << "p50_ms" << summary.p50
               << "p95_ms" << summary.p95 << "}";
    };
    const double effective_fps = elapsed_loop_ms > 0.0
        ? 1000.0 * static_cast<double>(counts.processed) / elapsed_loop_ms
        : 0.0;
    output << "schema_version" << 2 << "application" << "edgeai_demo"
           << "mode" << source_kind << "backend" << "{" << "name" << info.backend
           << "runtime" << info.runtime << "model_identity" << info.model_identity
           << "precision" << info.precision << "input_dtype" << info.input_dtype
           << "output_dtype" << info.output_dtype << "input_shape";
    write_shape(output, info.input_shape);
    output << "output_shape";
    write_shape(output, info.output_shape);
    output << "fallback" << "none" << "}";
    output << "model" << "{" << "path" << args.model.string() << "manifest"
           << args.manifest.string() << "}";
    output << "source" << "{" << "kind" << source_kind << "path"
           << (args.camera_mode ? args.camera : args.source.string()) << "metadata";
    write_video_metadata(output, input_metadata);
    output << "}";
    output << "configuration" << "{" << "path" << args.config.string() << "input_size"
           << "[" << config.input_size.height << config.input_size.width << "]"
           << "confidence_threshold" << config.confidence_threshold << "iou_threshold"
           << config.iou_threshold << "max_detections" << config.max_detections
           << "threads" << args.threads << "packing" << args.packing << "warmup"
           << args.warmup << "repeat" << args.repeat << "}";
    output << "counts" << "{" << "captured_frames" << static_cast<int>(counts.captured)
           << "processed_frames" << static_cast<int>(counts.processed)
           << "dropped_frames" << 0 << "failed_frames" << static_cast<int>(counts.failed)
           << "written_frames" << static_cast<int>(counts.written) << "}";
    output << "queue" << "{" << "mode" << "synchronous" << "capacity" << 0
           << "drop_policy" << "none; capture and inference are serialized" << "}";
    output << "input_video_metadata";
    write_video_metadata(output, input_metadata);
    output << "output_video" << "{" << "path" << args.output_video.string()
           << "requested_codec" << args.output_codec << "writer_backend" << writer_backend
           << "metadata";
    write_video_metadata(output, output_metadata);
    output << "}";
    output << "timings_ms" << "{" << "capture_read";
    write_stats(read);
    output << "preprocess";
    write_stats(preprocess);
    output << "inference";
    write_stats(inference);
    output << "postprocess";
    write_stats(postprocess);
    output << "visualization";
    write_stats(visualization);
    output << "video_write";
    write_stats(write);
    output << "pipeline_end_to_end";
    write_stats(pipeline);
    output << "effective_processing_fps" << effective_fps << "source_fps" << input_metadata.fps
           << "measurement" << "synchronous; image decode and video encode are reported separately"
           << "}";
    output << "first_frame_golden" << "{" << "status" << first_frame_golden.status
           << "expected_count" << static_cast<int>(first_frame_golden.expected_count)
           << "observed_count" << static_cast<int>(first_frame_golden.observed_count)
           << "minimum_iou" << first_frame_golden.minimum_iou
           << "maximum_confidence_delta" << first_frame_golden.maximum_confidence_delta << "}";
    output << "frames" << "[";
    for (const auto& record : records) write_video_frame_record(output, record);
    output << "]";
    output.release();
}

int run_dynamic(
    const Arguments& args,
    const edgeai::common::InferenceConfig& config
) {
    if (args.output_video.empty()) {
        throw std::runtime_error("video and camera sources require --output-video PATH");
    }
    const auto backend = make_backend(args);
    cv::VideoCapture capture = args.camera_mode
        ? open_camera(args.camera)
        : cv::VideoCapture(args.source.string());
    if (!capture.isOpened()) {
        throw std::runtime_error(
            args.camera_mode ? "failed to open camera source" : "failed to open video source: " + args.source.string()
        );
    }
    const int width = static_cast<int>(std::llround(capture.get(cv::CAP_PROP_FRAME_WIDTH)));
    const int height = static_cast<int>(std::llround(capture.get(cv::CAP_PROP_FRAME_HEIGHT)));
    const double source_fps = capture.get(cv::CAP_PROP_FPS);
    const auto reported_frames = static_cast<std::int64_t>(std::llround(
        capture.get(cv::CAP_PROP_FRAME_COUNT)
    ));
    const int source_fourcc = static_cast<int>(std::llround(capture.get(cv::CAP_PROP_FOURCC)));
    if (width <= 0 || height <= 0) throw std::runtime_error("source dimensions are invalid");
    const double output_fps = std::isfinite(source_fps) && source_fps > 0.0 ? source_fps : 30.0;
    edgeai::common::VideoMetadata input_metadata{
        width, height, source_fps, reported_frames, edgeai::common::fourcc_to_string(source_fourcc),
        capture.getBackendName(),
    };
    if (input_metadata.fourcc.size() != 4U) input_metadata.fourcc = "????";
    const int codec = fourcc_from_string(args.output_codec);
    if (!args.output_video.parent_path().empty()) {
        std::filesystem::create_directories(args.output_video.parent_path());
    }
    cv::VideoWriter writer(
        args.output_video.string(), codec, output_fps, cv::Size(width, height), true
    );
    if (!writer.isOpened()) {
        throw std::runtime_error(
            "VideoWriter failed for " + args.output_video.string() + " codec=" + args.output_codec
        );
    }

    auto run_frame = [&](const cv::Mat& frame, VideoFrameRecord* record) {
        const auto loop_start = Clock::now();
        const auto preprocess_start = Clock::now();
        const auto preprocessed = edgeai::common::preprocess_image(frame, config);
        const auto preprocess_end = Clock::now();
        const auto inference_start = Clock::now();
        const auto raw = backend->infer(preprocessed.tensor);
        const auto inference_end = Clock::now();
        const auto postprocess_start = Clock::now();
        const auto postprocessed = edgeai::common::decode_yolov5_output(
            raw.values, raw.shape, config.class_names, preprocessed.metadata, config
        );
        const auto postprocess_end = Clock::now();
        if (record != nullptr) {
            record->timings.preprocess = elapsed_ms(preprocess_start, preprocess_end);
            record->timings.inference = elapsed_ms(inference_start, inference_end);
            record->timings.postprocess = elapsed_ms(postprocess_start, postprocess_end);
            record->timings.pipeline_total = elapsed_ms(loop_start, postprocess_end);
            record->postprocess = postprocessed;
            record->raw_shape = raw.shape;
        }
        return postprocessed;
    };

    VideoRunCounts counts;
    std::vector<VideoFrameRecord> records;
    const auto wall_start = Clock::now();
    const auto deadline = args.max_duration_seconds > 0.0
        ? wall_start + std::chrono::duration_cast<Clock::duration>(
              std::chrono::duration<double>(args.max_duration_seconds)
          )
        : Clock::time_point::max();
    GoldenCheck first_golden;
    cv::Mat frame;
    while ((args.max_frames == 0U || counts.captured < args.max_frames) &&
           Clock::now() < deadline) {
        const auto frame_loop_start = Clock::now();
        const auto read_start = Clock::now();
        if (!capture.read(frame)) break;
        const auto read_end = Clock::now();
        ++counts.captured;
        if (frame.empty() || frame.type() != CV_8UC3 || frame.cols != width || frame.rows != height) {
            ++counts.failed;
            continue;
        }
        for (int warmup = 0; warmup < args.warmup; ++warmup) run_frame(frame, nullptr);
        VideoFrameRecord record;
        record.frame_index = counts.captured - 1U;
        record.timings.video_read = elapsed_ms(read_start, read_end);
        cv::Mat rendered;
        run_frame(frame, &record);
        const auto visualization_start = Clock::now();
        const double elapsed_loop = elapsed_ms(wall_start, visualization_start);
        rendered = draw_video_overlay(
            frame,
            record.postprocess.detections,
            backend->info(),
            record.timings.inference,
            counts.processed > 0U ? 1000.0 * static_cast<double>(counts.processed) / elapsed_loop : 0.0
        );
        const auto visualization_end = Clock::now();
        writer.write(rendered);
        const auto write_end = Clock::now();
        record.timings.visualization = elapsed_ms(visualization_start, visualization_end);
        record.timings.video_write = elapsed_ms(visualization_end, write_end);
        record.timings.pipeline_total = elapsed_ms(frame_loop_start, write_end);
        if (args.golden.empty() && counts.processed == 0U) {
            first_golden.status = "NOT_REQUESTED";
        } else if (!args.golden.empty() && counts.processed == 0U) {
            first_golden = check_golden(args.golden, record.postprocess.detections);
        }
        records.push_back(std::move(record));
        ++counts.processed;
        ++counts.written;
    }
    capture.release();
    const std::string writer_backend = writer.getBackendName();
    writer.release();
    if (counts.processed == 0U) throw std::runtime_error("dynamic source produced no valid frames");
    cv::VideoCapture verify_capture(args.output_video.string());
    if (!verify_capture.isOpened()) throw std::runtime_error("output video cannot be reopened");
    const int output_width = static_cast<int>(std::llround(verify_capture.get(cv::CAP_PROP_FRAME_WIDTH)));
    const int output_height = static_cast<int>(std::llround(verify_capture.get(cv::CAP_PROP_FRAME_HEIGHT)));
    const double output_reported_fps = verify_capture.get(cv::CAP_PROP_FPS);
    const auto output_reported_count = static_cast<std::int64_t>(std::llround(
        verify_capture.get(cv::CAP_PROP_FRAME_COUNT)
    ));
    std::size_t decoded = 0U;
    cv::Mat verify_frame;
    while (verify_capture.read(verify_frame)) {
        if (verify_frame.empty() || verify_frame.cols != width || verify_frame.rows != height ||
            verify_frame.type() != CV_8UC3) {
            throw std::runtime_error("output video frame validation failed");
        }
        ++decoded;
    }
    verify_capture.release();
    if (output_width != width || output_height != height || decoded != counts.written ||
        output_reported_count != static_cast<std::int64_t>(counts.written)) {
        throw std::runtime_error("output video frame/geometry validation failed");
    }
    edgeai::common::VideoMetadata output_metadata{
        output_width,
        output_height,
        output_reported_fps,
        output_reported_count,
        args.output_codec,
        "OpenCV VideoWriter",
    };
    write_video_output(
        args,
        config,
        *backend,
        input_metadata,
        output_metadata,
        args.camera_mode ? "camera" : "video",
        writer_backend,
        counts,
        records,
        elapsed_ms(wall_start, Clock::now()),
        first_golden
    );
    std::cout << "mode=" << (args.camera_mode ? "camera" : "video")
              << " backend=" << backend->info().backend << " precision=" << backend->info().precision
              << " captured=" << counts.captured << " processed=" << counts.processed
              << " dropped=0 output_video=" << args.output_video << '\n';
    return first_golden.status == "FAIL" ? 2 : 0;
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        const Arguments args = parse_args(argc, argv);
        const auto config = edgeai::common::load_config(args.config);
        const cv::Mat input_probe = args.camera_mode
            ? cv::Mat{}
            : cv::imread(args.source.string(), cv::IMREAD_COLOR);
        if (args.camera_mode || input_probe.empty()) {
            return run_dynamic(args, config);
        }
        if (!args.output_video.empty()) {
            throw std::runtime_error("--output-video is only valid for video or camera sources");
        }
        const cv::Mat source = edgeai::common::load_bgr_image(args.source);
        const auto backend = make_backend(args);

        const auto run_once = [&](Sample* sample, edgeai::common::PostprocessResult* result,
                                  std::vector<std::int64_t>* raw_shape) {
            const auto pipeline_start = Clock::now();
            const auto preprocess_start = Clock::now();
            const auto preprocessed = edgeai::common::preprocess_image(source, config);
            const auto preprocess_end = Clock::now();
            const auto inference_start = Clock::now();
            const auto raw = backend->infer(preprocessed.tensor);
            const auto inference_end = Clock::now();
            const auto postprocess_start = Clock::now();
            const auto postprocessed = edgeai::common::decode_yolov5_output(
                raw.values, raw.shape, config.class_names, preprocessed.metadata, config
            );
            const auto postprocess_end = Clock::now();
            if (sample != nullptr) {
                sample->preprocess = elapsed_ms(preprocess_start, preprocess_end);
                sample->inference = elapsed_ms(inference_start, inference_end);
                sample->postprocess = elapsed_ms(postprocess_start, postprocess_end);
                sample->pipeline = elapsed_ms(pipeline_start, postprocess_end);
            }
            if (result != nullptr) *result = postprocessed;
            if (raw_shape != nullptr) *raw_shape = raw.shape;
        };
        for (int index = 0; index < args.warmup; ++index) run_once(nullptr, nullptr, nullptr);
        std::vector<Sample> samples;
        samples.reserve(static_cast<std::size_t>(args.repeat));
        edgeai::common::PostprocessResult final_result;
        std::vector<std::int64_t> final_shape;
        for (int index = 0; index < args.repeat; ++index) {
            Sample sample;
            run_once(&sample, &final_result, &final_shape);
            samples.push_back(sample);
        }
        const cv::Mat rendered = edgeai::common::draw_detections(source, final_result.detections);
        edgeai::common::save_image(args.output_image, rendered);
        const cv::Mat read_back = cv::imread(args.output_image.string(), cv::IMREAD_COLOR);
        if (read_back.empty() || read_back.size() != source.size() || read_back.type() != CV_8UC3) {
            throw std::runtime_error("annotated image read-back validation failed");
        }
        const GoldenCheck golden = args.golden.empty()
            ? GoldenCheck{}
            : check_golden(args.golden, final_result.detections);
        write_output(args, config, *backend, final_result, final_shape, source, read_back, samples, golden, args.output_json);
        std::cout << "backend=" << backend->info().backend << " precision=" << backend->info().precision
                  << " detections=" << final_result.detections.size() << " golden=" << golden.status
                  << " output_json=" << args.output_json << " output_image=" << args.output_image << '\n';
        if (golden.status == "FAIL") return 2;
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "edgeai_demo error: " << error.what() << '\n';
        return 1;
    }
}
