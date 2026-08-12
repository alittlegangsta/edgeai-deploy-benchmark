#include "edgeai/backends/tensorrt_detector.hpp"
#include "edgeai/common/config.hpp"
#include "edgeai/common/postprocess.hpp"
#include "edgeai/common/preprocess.hpp"
#include "edgeai/common/visualize.hpp"

#include <cuda_runtime_api.h>

#include <opencv2/core/persistence.hpp>
#include <opencv2/imgcodecs.hpp>

#include <algorithm>
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
#include <vector>
#include <sys/resource.h>

namespace {

using Clock = std::chrono::steady_clock;

struct Args {
    std::filesystem::path engine;
    std::filesystem::path config;
    std::filesystem::path image;
    std::filesystem::path golden;
    std::filesystem::path output_image;
    std::filesystem::path output_json;
    std::filesystem::path raw_output;
    std::string model_sha256;
    std::string precision;
    bool golden_secondary{false};
    int warmup{10};
    int repeat{100};
};

struct GoldenDetection {
    int class_id{-1};
    float confidence{0.0F};
    edgeai::common::Box box;
};

struct Sample {
    double wall_ms{0.0};
    double preprocess_ms{0.0};
    double inference_ms{0.0};
    double postprocess_ms{0.0};
    double h2d_ms{0.0};
    double d2h_ms{0.0};
};

struct Stats {
    double mean{0.0};
    double p50{0.0};
    double p95{0.0};
};

double elapsed_ms(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

Args parse_pairs(int argc, char* argv[]) {
    if ((argc - 1) % 2 != 0) {
        throw std::runtime_error("arguments must be option/value pairs");
    }
    std::map<std::string, std::string> values;
    for (int index = 1; index < argc; index += 2) {
        const std::string option = argv[index];
        const std::vector<std::string> allowed{
            "--engine", "--config", "--image", "--golden", "--output-image",
            "--output-json", "--raw-output", "--model-sha256", "--precision",
            "--warmup", "--repeat", "--golden-secondary",
        };
        if (std::find(allowed.begin(), allowed.end(), option) == allowed.end()) {
            throw std::runtime_error("unknown argument: " + option);
        }
        if (!values.emplace(option, argv[index + 1]).second) {
            throw std::runtime_error("duplicate argument: " + option);
        }
    }
    for (const char* required : {
             "--engine", "--config", "--image", "--golden", "--output-image",
             "--output-json", "--raw-output", "--model-sha256", "--precision",
         }) {
        if (values.find(required) == values.end()) {
            throw std::runtime_error(std::string("missing required argument: ") + required);
        }
    }
    Args args{
        values.at("--engine"), values.at("--config"), values.at("--image"),
        values.at("--golden"), values.at("--output-image"), values.at("--output-json"),
        values.at("--raw-output"), values.at("--model-sha256"), values.at("--precision"),
    };
    if (values.find("--warmup") != values.end()) {
        args.warmup = std::stoi(values.at("--warmup"));
    }
    if (values.find("--repeat") != values.end()) {
        args.repeat = std::stoi(values.at("--repeat"));
    }
    if (values.find("--golden-secondary") != values.end()) {
        args.golden_secondary = values.at("--golden-secondary") == "true";
    }
    if (args.warmup < 0 || args.repeat <= 0) {
        throw std::runtime_error("warmup must be non-negative and repeat must be positive");
    }
    if (args.precision != "FP32" && args.precision != "FP16") {
        throw std::runtime_error("precision must be FP32 or FP16");
    }
    return args;
}

std::vector<GoldenDetection> load_golden(const std::filesystem::path& path) {
    cv::FileStorage storage(path.string(), cv::FileStorage::READ | cv::FileStorage::FORMAT_JSON);
    if (!storage.isOpened() || !storage["detections"].isSeq()) {
        throw std::runtime_error("golden detections are missing: " + path.string());
    }
    std::vector<GoldenDetection> result;
    for (const auto& node : storage["detections"]) {
        const cv::FileNode box = node["box_xyxy_source"];
        if (!box.isSeq() || box.size() != 4U) {
            throw std::runtime_error("golden box is malformed");
        }
        result.push_back({
            static_cast<int>(node["class_id"]),
            static_cast<float>(node["confidence"]),
            {static_cast<float>(box[0]), static_cast<float>(box[1]),
             static_cast<float>(box[2]), static_cast<float>(box[3])},
        });
    }
    return result;
}

Stats stats(std::vector<double> values) {
    if (values.empty()) {
        throw std::runtime_error("cannot summarize empty samples");
    }
    std::sort(values.begin(), values.end());
    const double total = std::accumulate(values.begin(), values.end(), 0.0);
    const auto nearest_rank = [&](double percentile) {
        const std::size_t rank = static_cast<std::size_t>(std::ceil(percentile * values.size()));
        return values[std::max<std::size_t>(1U, rank) - 1U];
    };
    return {total / static_cast<double>(values.size()), nearest_rank(0.50), nearest_rank(0.95)};
}

void write_shape(cv::FileStorage& storage, const std::vector<std::int64_t>& shape) {
    storage << "[";
    for (const auto dimension : shape) {
        storage << static_cast<int>(dimension);
    }
    storage << "]";
}

void write_box(cv::FileStorage& storage, const edgeai::common::Box& box) {
    storage << "[" << box.x1 << box.y1 << box.x2 << box.y2 << "]";
}

void write_samples(cv::FileStorage& storage, const std::vector<Sample>& samples) {
    storage << "[";
    for (const auto& sample : samples) {
        storage << "{" << "wall_ms" << sample.wall_ms << "preprocess_ms" << sample.preprocess_ms
                << "inference_ms" << sample.inference_ms << "postprocess_ms"
                << sample.postprocess_ms << "h2d_ms" << sample.h2d_ms << "d2h_ms"
                << sample.d2h_ms << "}";
    }
    storage << "]";
}

struct Correctness {
    bool pass{false};
    double minimum_iou{0.0};
    double maximum_confidence_delta{0.0};
};

Correctness compare_golden(
    const std::vector<edgeai::common::Detection>& detections,
    const std::vector<GoldenDetection>& golden
) {
    if (detections.size() != golden.size() || detections.empty()) {
        return {};
    }
    double minimum_iou = 1.0;
    double maximum_delta = 0.0;
    for (std::size_t index = 0; index < detections.size(); ++index) {
        if (detections[index].class_id != golden[index].class_id) {
            return {};
        }
        minimum_iou = std::min<double>(
            minimum_iou,
            edgeai::common::box_iou(detections[index].box_xyxy_source, golden[index].box)
        );
        maximum_delta = std::max<double>(
            maximum_delta,
            std::abs(static_cast<double>(detections[index].confidence) - golden[index].confidence)
        );
    }
    return {minimum_iou >= 0.99 && maximum_delta <= 0.001, minimum_iou, maximum_delta};
}

void write_raw(const std::filesystem::path& path, const std::vector<float>& values) {
    std::ofstream output(path, std::ios::binary);
    if (!output) {
        throw std::runtime_error("failed to open raw output: " + path.string());
    }
    output.write(reinterpret_cast<const char*>(values.data()),
                 static_cast<std::streamsize>(values.size() * sizeof(float)));
    if (!output) {
        throw std::runtime_error("failed to write raw output: " + path.string());
    }
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
    const Args args = parse_pairs(argc, argv);
        const auto config = edgeai::common::load_config(args.config);
        const auto source = edgeai::common::load_bgr_image(args.image);
        const auto golden = load_golden(args.golden);
        edgeai::backends::TensorRtDetector detector(args.engine);

        std::vector<Sample> inference_samples;
        inference_samples.reserve(static_cast<std::size_t>(args.repeat));
        for (int index = 0; index < args.warmup; ++index) {
            const auto preprocessed = edgeai::common::preprocess_image(source, config);
            static_cast<void>(detector.infer(preprocessed.tensor));
        }

        edgeai::backends::TensorRtRawResult last_raw;
        for (int index = 0; index < args.repeat; ++index) {
            const auto preprocessed = edgeai::common::preprocess_image(source, config);
            const auto start = Clock::now();
            const auto raw = detector.infer(preprocessed.tensor);
            const auto end = Clock::now();
            inference_samples.push_back({
                elapsed_ms(start, end), 0.0, raw.gpu_timings.inference, 0.0,
                raw.gpu_timings.host_to_device, raw.gpu_timings.device_to_host,
            });
            last_raw = raw;
        }

        std::vector<Sample> pipeline_samples;
        pipeline_samples.reserve(static_cast<std::size_t>(args.repeat));
        edgeai::common::PostprocessResult last_postprocessed;
        edgeai::common::PreprocessResult last_preprocessed;
        for (int index = 0; index < args.repeat; ++index) {
            const auto pipeline_start = Clock::now();
            const auto preprocess_start = Clock::now();
            const auto preprocessed = edgeai::common::preprocess_image(source, config);
            const auto preprocess_end = Clock::now();
            const auto inference_start = Clock::now();
            const auto raw = detector.infer(preprocessed.tensor);
            const auto inference_end = Clock::now();
            const auto postprocess_start = Clock::now();
            const auto postprocessed = edgeai::common::decode_yolov5_output(
                raw.values, raw.shape, config.class_names, preprocessed.metadata, config
            );
            const auto postprocess_end = Clock::now();
            pipeline_samples.push_back({
                elapsed_ms(pipeline_start, postprocess_end),
                elapsed_ms(preprocess_start, preprocess_end),
                elapsed_ms(inference_start, inference_end),
                elapsed_ms(postprocess_start, postprocess_end),
                raw.gpu_timings.host_to_device, raw.gpu_timings.device_to_host,
            });
            last_raw = raw;
            last_preprocessed = preprocessed;
            last_postprocessed = postprocessed;
        }

        const Correctness correctness = compare_golden(last_postprocessed.detections, golden);
        const auto rendered = edgeai::common::draw_detections(source, last_postprocessed.detections);
        if (!args.output_image.parent_path().empty()) {
            std::filesystem::create_directories(args.output_image.parent_path());
        }
        if (!cv::imwrite(args.output_image.string(), rendered)) {
            throw std::runtime_error("failed to write TensorRT output image");
        }
        if (!args.raw_output.parent_path().empty()) {
            std::filesystem::create_directories(args.raw_output.parent_path());
        }
        write_raw(args.raw_output, last_raw.values);

        std::size_t free_bytes = 0U;
        std::size_t total_bytes = 0U;
        const cudaError_t memory_status = cudaMemGetInfo(&free_bytes, &total_bytes);
        if (memory_status != cudaSuccess) {
            throw std::runtime_error(std::string("cudaMemGetInfo failed: ") +
                                     cudaGetErrorString(memory_status));
        }
        struct rusage usage{};
        getrusage(RUSAGE_SELF, &usage);

        const Stats inference_wall = stats([&] {
            std::vector<double> values;
            for (const auto& sample : inference_samples) values.push_back(sample.wall_ms);
            return values;
        }());
        const Stats gpu_inference = stats([&] {
            std::vector<double> values;
            for (const auto& sample : inference_samples) values.push_back(sample.inference_ms);
            return values;
        }());
        const Stats pipeline = stats([&] {
            std::vector<double> values;
            for (const auto& sample : pipeline_samples) values.push_back(sample.wall_ms);
            return values;
        }());
        const Stats preprocess = stats([&] {
            std::vector<double> values;
            for (const auto& sample : pipeline_samples) values.push_back(sample.preprocess_ms);
            return values;
        }());
        const Stats postprocess = stats([&] {
            std::vector<double> values;
            for (const auto& sample : pipeline_samples) values.push_back(sample.postprocess_ms);
            return values;
        }());

        if (!args.output_json.parent_path().empty()) {
            std::filesystem::create_directories(args.output_json.parent_path());
        }
        cv::FileStorage output(
            args.output_json.string(), cv::FileStorage::WRITE | cv::FileStorage::FORMAT_JSON
        );
        if (!output.isOpened()) {
            throw std::runtime_error("failed to open TensorRT result JSON");
        }
        const auto& info = detector.runtime_info();
        output << "schema_version" << 1 << "application" << "edgeai_tensorrt_image";
        output << "precision" << args.precision << "engine" << "{" << "path" << args.engine.string()
               << "size_bytes" << static_cast<double>(std::filesystem::file_size(args.engine))
               << "}";
        output << "model" << "{" << "sha256" << args.model_sha256 << "}";
        output << "runtime" << "{" << "device_name" << info.device_name << "compute_capability"
               << (std::to_string(info.compute_capability_major) + "." +
                   std::to_string(info.compute_capability_minor))
               << "input_name" << info.input_name << "output_name" << info.output_name
               << "input_dtype" << info.input_dtype << "output_dtype" << info.output_dtype
               << "input_shape";
        write_shape(output, info.input_shape);
        output << "output_shape";
        write_shape(output, info.output_shape);
        output << "}";
        output << "configuration" << "{" << "path" << args.config.string()
               << "confidence_threshold" << config.confidence_threshold << "iou_threshold"
               << config.iou_threshold << "input_size" << "[" << config.input_size.height
               << config.input_size.width << "]" << "}";
        output << "correctness" << "{" << "status" << (correctness.pass ? "PASS_TARGET" : "FAIL")
               << "gate_scope" << (args.golden_secondary ? "secondary_diagnostic" : "strict_single_image")
               << "detection_count" << static_cast<int>(last_postprocessed.detections.size())
               << "minimum_class_matched_iou" << correctness.minimum_iou
               << "maximum_confidence_delta" << correctness.maximum_confidence_delta << "}";
        output << "detections" << "[";
        for (const auto& detection : last_postprocessed.detections) {
            output << "{" << "rank" << static_cast<int>(detection.rank) << "candidate_index"
                   << static_cast<int>(detection.candidate_index) << "class_id" << detection.class_id
                   << "class_name" << detection.class_name << "confidence" << detection.confidence
                   << "box_xyxy_source";
            write_box(output, detection.box_xyxy_source);
            output << "}";
        }
        output << "]";
        output << "raw_output" << "{" << "path" << args.raw_output.string() << "size_bytes"
               << static_cast<double>(std::filesystem::file_size(args.raw_output)) << "shape";
        write_shape(output, last_raw.shape);
        output << "}";
        output << "benchmark" << "{" << "warmup" << args.warmup << "repeat" << args.repeat
               << "inference_wall_ms" << "{" << "mean" << inference_wall.mean << "p50"
               << inference_wall.p50 << "p95" << inference_wall.p95 << "}" << "gpu_inference_ms"
               << "{" << "mean" << gpu_inference.mean << "p50" << gpu_inference.p50 << "p95"
               << gpu_inference.p95 << "}" << "pipeline_ms" << "{" << "mean" << pipeline.mean
               << "p50" << pipeline.p50 << "p95" << pipeline.p95 << "}" << "preprocess_ms"
               << "{" << "mean" << preprocess.mean << "p50" << preprocess.p50 << "p95"
               << preprocess.p95 << "}" << "postprocess_ms" << "{" << "mean" << postprocess.mean
               << "p50" << postprocess.p50 << "p95" << postprocess.p95 << "}" << "fps"
               << (1000.0 / pipeline.mean) << "gpu_memory" << "{" << "free_bytes"
               << static_cast<double>(free_bytes) << "total_bytes" << static_cast<double>(total_bytes)
               << "}" << "peak_rss_kib" << static_cast<double>(usage.ru_maxrss) << "}";
        output << "samples" << "{" << "inference";
        write_samples(output, inference_samples);
        output << "pipeline";
        write_samples(output, pipeline_samples);
        output << "}";
        output.release();
        if (!correctness.pass && !args.golden_secondary) {
            std::cerr << "TensorRT correctness gate failed\n";
            return 2;
        }
        std::cout << "correctness=" << (correctness.pass ? "PASS_TARGET" : "SECONDARY_DIAGNOSTIC") << "\n";
        std::cout << "gpu_inference_mean_ms=" << std::fixed << std::setprecision(6)
                  << gpu_inference.mean << "\n";
        std::cout << "pipeline_mean_ms=" << pipeline.mean << "\n";
        std::cout << "fps=" << (1000.0 / pipeline.mean) << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "edgeai_tensorrt_image: " << error.what() << "\n";
        return 1;
    }
}
