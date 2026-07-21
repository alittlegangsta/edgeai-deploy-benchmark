#include "edgeai/backends/ort_detector.hpp"
#include "edgeai/common/benchmark.hpp"
#include "edgeai/common/config.hpp"
#include "edgeai/common/postprocess.hpp"
#include "edgeai/common/preprocess.hpp"

#include <chrono>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include <opencv2/core.hpp>
#include <opencv2/core/persistence.hpp>
#include <opencv2/imgcodecs.hpp>
#include <sys/resource.h>
#include <sys/utsname.h>
#include <unistd.h>

namespace {

using Clock = std::chrono::steady_clock;

constexpr const char* kBackend = "cpp_ort";

struct Arguments {
    std::filesystem::path benchmark_config;
    int round{0};
    std::filesystem::path output;
};

struct BenchmarkConfig {
    int round_count{0};
    int warmup{0};
    int repeat{0};
    int intra_op_threads{0};
    int inter_op_threads{0};
    int opencv_threads{0};
    std::filesystem::path model;
    std::filesystem::path manifest;
    std::filesystem::path image;
    std::filesystem::path inference_config;
    std::filesystem::path golden_result;
    std::string model_sha256;
    std::string manifest_sha256;
    std::string image_sha256;
    std::string inference_config_sha256;
    std::string golden_result_sha256;
    std::map<std::string, std::string> required_environment;
    double minimum_iou{0.0};
    double maximum_confidence_difference{0.0};
};

struct PipelineResult {
    edgeai::common::BenchmarkSampleNs sample;
    std::vector<edgeai::common::Detection> detections;
};

struct ResourceMeasurement {
    double cpu_percent{0.0};
    double process_cpu_seconds_delta{0.0};
    double wall_clock_seconds_delta{0.0};
    std::uint64_t peak_rss_bytes{0};
};

Arguments parse_args(int argc, char* argv[]) {
    if (argc != 7) {
        throw std::runtime_error(
            "usage: edgeai_benchmark_ort --benchmark-config PATH --round N --output PATH"
        );
    }
    std::map<std::string, std::string> values;
    for (int index = 1; index < argc; index += 2) {
        const std::string option = argv[index];
        if (option != "--benchmark-config" && option != "--round" && option != "--output") {
            throw std::runtime_error("unknown argument: " + option);
        }
        if (!values.emplace(option, argv[index + 1]).second) {
            throw std::runtime_error("duplicate argument: " + option);
        }
    }
    if (values.size() != 3U) {
        throw std::runtime_error("all benchmark arguments are required");
    }
    std::size_t parsed = 0U;
    const int round = std::stoi(values.at("--round"), &parsed);
    if (parsed != values.at("--round").size()) {
        throw std::runtime_error("round is not an integer");
    }
    return {values.at("--benchmark-config"), round, values.at("--output")};
}

std::string required_string(const cv::FileNode& parent, const char* key) {
    const cv::FileNode node = parent[key];
    if (!node.isString()) {
        throw std::runtime_error(std::string("benchmark config string is missing: ") + key);
    }
    return static_cast<std::string>(node);
}

int required_int(const cv::FileNode& parent, const char* key) {
    const cv::FileNode node = parent[key];
    if (!node.isInt()) {
        throw std::runtime_error(std::string("benchmark config integer is missing: ") + key);
    }
    return static_cast<int>(node);
}

double required_real(const cv::FileNode& parent, const char* key) {
    const cv::FileNode node = parent[key];
    if (!node.isReal() && !node.isInt()) {
        throw std::runtime_error(std::string("benchmark config number is missing: ") + key);
    }
    return static_cast<double>(node);
}

void require_equal(const std::string& actual, const std::string& expected, const char* name) {
    if (actual != expected) {
        throw std::runtime_error(
            std::string("benchmark config ") + name + " differs: " + actual
        );
    }
}

BenchmarkConfig load_benchmark_config(const std::filesystem::path& path) {
    cv::FileStorage storage(path.string(), cv::FileStorage::READ | cv::FileStorage::FORMAT_JSON);
    if (!storage.isOpened()) {
        throw std::runtime_error("failed to open benchmark configuration: " + path.string());
    }
    if (required_int(storage.root(), "schema_version") != 1) {
        throw std::runtime_error("benchmark schema must be 1");
    }
    require_equal(
        required_string(storage.root(), "methodology_id"),
        "task009-pc-ort-v1",
        "methodology"
    );
    const cv::FileNode environment = storage["environment"];
    require_equal(required_string(environment, "platform"), "WSL2", "platform");
    require_equal(
        required_string(environment, "cpu_affinity"),
        "scheduler managed",
        "CPU affinity"
    );
    require_equal(required_string(environment, "cpu_pinning"), "disabled", "CPU pinning");
    const cv::FileNode environment_variables = environment["required_environment_variables"];
    BenchmarkConfig result;
    for (const std::string name : {
             "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
         }) {
        const std::string value = required_string(environment_variables, name.c_str());
        require_equal(value, "1", "thread environment value");
        result.required_environment.emplace(name, value);
    }

    const cv::FileNode workload = storage["workload"];
    if (required_int(workload, "batch") != 1 || required_string(workload, "precision") != "FP32") {
        throw std::runtime_error("benchmark batch or precision differs from frozen values");
    }
    const cv::FileNode input_size = workload["input_size"];
    if (!input_size.isSeq() || input_size.size() != 2U ||
        static_cast<int>(input_size[0]) != 640 || static_cast<int>(input_size[1]) != 640) {
        throw std::runtime_error("benchmark input size must be 640x640");
    }
    const auto read_artifact = [&](const char* key, std::filesystem::path& artifact_path,
                                   std::string& sha256) {
        const cv::FileNode artifact = workload[key];
        artifact_path = required_string(artifact, "path");
        sha256 = required_string(artifact, "sha256");
    };
    read_artifact("model", result.model, result.model_sha256);
    read_artifact("manifest", result.manifest, result.manifest_sha256);
    read_artifact("image", result.image, result.image_sha256);
    read_artifact("inference_config", result.inference_config, result.inference_config_sha256);
    read_artifact("golden_result", result.golden_result, result.golden_result_sha256);

    const cv::FileNode runtime = storage["runtime"];
    require_equal(required_string(runtime, "onnxruntime_version"), "1.18.1", "ORT version");
    require_equal(
        required_string(runtime, "execution_provider"),
        "CPUExecutionProvider",
        "provider"
    );
    require_equal(
        required_string(runtime, "execution_mode"), "ORT_SEQUENTIAL", "execution mode"
    );
    require_equal(
        required_string(runtime, "graph_optimization"),
        "ORT_ENABLE_ALL",
        "graph optimization"
    );
    result.intra_op_threads = required_int(runtime, "intra_op_threads");
    result.inter_op_threads = required_int(runtime, "inter_op_threads");
    result.opencv_threads = required_int(runtime, "opencv_threads");
    if (result.intra_op_threads != 1 || result.inter_op_threads != 1 ||
        result.opencv_threads != 1) {
        throw std::runtime_error("benchmark thread counts must all be 1");
    }

    const cv::FileNode rounds = storage["rounds"];
    result.round_count = required_int(rounds, "count");
    result.warmup = required_int(rounds, "warmup");
    result.repeat = required_int(rounds, "repeat");
    if (result.round_count != 5 || result.warmup != 10 || result.repeat != 100) {
        throw std::runtime_error("benchmark rounds/warmup/repeat differ from 5/10/100");
    }
    const cv::FileNode order = rounds["order"];
    const std::vector<std::vector<std::string>> expected_order{
        {"python_ort", "cpp_ort"},
        {"cpp_ort", "python_ort"},
        {"python_ort", "cpp_ort"},
        {"cpp_ort", "python_ort"},
        {"python_ort", "cpp_ort"},
    };
    if (!order.isSeq() || order.size() != expected_order.size()) {
        throw std::runtime_error("benchmark round order is incomplete");
    }
    for (std::size_t index = 0; index < expected_order.size(); ++index) {
        const cv::FileNode pair = order[static_cast<int>(index)];
        if (!pair.isSeq() || pair.size() != 2U ||
            static_cast<std::string>(pair[0]) != expected_order[index][0] ||
            static_cast<std::string>(pair[1]) != expected_order[index][1]) {
            throw std::runtime_error("benchmark round order differs from approved order");
        }
    }
    const cv::FileNode timing = storage["timing"];
    require_equal(
        required_string(timing, "pipeline_total_formula"),
        "preprocess_ns + inference_ns + postprocess_ns",
        "pipeline formula"
    );
    const cv::FileNode statistics = storage["statistics"];
    require_equal(required_string(statistics, "percentile_method"), "nearest-rank", "percentile");
    if (std::abs(required_real(
                     statistics, "maximum_round_mean_relative_difference_percent"
                 ) - 10.0) > 1e-12) {
        throw std::runtime_error("benchmark stability limit must be 10 percent");
    }
    const cv::FileNode correctness = storage["correctness"];
    result.minimum_iou = required_real(correctness, "minimum_class_matched_iou");
    result.maximum_confidence_difference =
        required_real(correctness, "maximum_absolute_confidence_difference");
    if (std::abs(result.minimum_iou - 0.99) > 1e-12 ||
        std::abs(result.maximum_confidence_difference - 0.001) > 1e-12) {
        throw std::runtime_error("benchmark correctness tolerances differ from frozen values");
    }
    return result;
}

void require_artifact_hash(
    const std::filesystem::path& path,
    const std::string& expected,
    const char* description
) {
    const std::string actual = edgeai::backends::sha256_file(path);
    if (actual != expected) {
        throw std::runtime_error(
            std::string(description) + " SHA256 differs: expected " + expected +
            ", observed " + actual
        );
    }
}

std::vector<edgeai::common::Detection> load_golden(const std::filesystem::path& path) {
    cv::FileStorage storage(path.string(), cv::FileStorage::READ | cv::FileStorage::FORMAT_JSON);
    if (!storage.isOpened()) {
        throw std::runtime_error("failed to open golden result: " + path.string());
    }
    const cv::FileNode detections = storage["detections"];
    if (!detections.isSeq()) {
        throw std::runtime_error("golden detections must be an array");
    }
    std::vector<edgeai::common::Detection> result;
    result.reserve(detections.size());
    for (const auto& node : detections) {
        const cv::FileNode box = node["box_xyxy_source"];
        if (!box.isSeq() || box.size() != 4U) {
            throw std::runtime_error("golden detection box is invalid");
        }
        edgeai::common::Detection detection;
        detection.rank = static_cast<std::size_t>(static_cast<int>(node["rank"]));
        detection.class_id = static_cast<int>(node["class_id"]);
        detection.class_name = static_cast<std::string>(node["class_name"]);
        detection.confidence = static_cast<float>(node["confidence"]);
        detection.box_xyxy_source = {
            static_cast<float>(box[0]),
            static_cast<float>(box[1]),
            static_cast<float>(box[2]),
            static_cast<float>(box[3]),
        };
        result.push_back(std::move(detection));
    }
    return result;
}

PipelineResult run_pipeline(
    const cv::Mat& image,
    edgeai::backends::OrtDetector& detector,
    const edgeai::common::InferenceConfig& config
) {
    const auto start = Clock::now();
    const auto preprocessed = edgeai::common::preprocess_image(image, config);
    const auto after_preprocess = Clock::now();
    const auto raw = detector.infer(preprocessed.tensor);
    const auto after_inference = Clock::now();
    auto postprocessed = edgeai::common::decode_yolov5_output(
        raw.values,
        raw.shape,
        config.class_names,
        preprocessed.metadata,
        config
    );
    const auto after_postprocess = Clock::now();
    const auto to_ns = [](Clock::duration duration) {
        return std::chrono::duration_cast<std::chrono::nanoseconds>(duration).count();
    };
    return {
        edgeai::common::make_benchmark_sample(
            to_ns(after_preprocess - start),
            to_ns(after_inference - after_preprocess),
            to_ns(after_postprocess - after_inference)
        ),
        std::move(postprocessed.detections),
    };
}

double timeval_seconds(const timeval& value) {
    return static_cast<double>(value.tv_sec) + static_cast<double>(value.tv_usec) / 1'000'000.0;
}

std::string json_string(const std::string& value) {
    std::ostringstream output;
    output << '"';
    for (const unsigned char character : value) {
        switch (character) {
            case '"': output << "\\\""; break;
            case '\\': output << "\\\\"; break;
            case '\b': output << "\\b"; break;
            case '\f': output << "\\f"; break;
            case '\n': output << "\\n"; break;
            case '\r': output << "\\r"; break;
            case '\t': output << "\\t"; break;
            default:
                if (character < 0x20U) {
                    output << "\\u" << std::hex << std::setw(4) << std::setfill('0')
                           << static_cast<int>(character) << std::dec;
                } else {
                    output << static_cast<char>(character);
                }
        }
    }
    output << '"';
    return output.str();
}

std::string cpu_model() {
    std::ifstream input("/proc/cpuinfo");
    std::string line;
    while (std::getline(input, line)) {
        const std::string prefix = "model name";
        if (line.rfind(prefix, 0U) == 0U) {
            const std::size_t separator = line.find(':');
            if (separator != std::string::npos) {
                return line.substr(separator + 2U);
            }
        }
    }
    throw std::runtime_error("failed to read CPU model from /proc/cpuinfo");
}

utsname system_identity() {
    utsname value{};
    if (uname(&value) != 0) {
        throw std::runtime_error("uname failed");
    }
    if (std::string(value.release).find("microsoft") == std::string::npos &&
        std::string(value.release).find("Microsoft") == std::string::npos) {
        throw std::runtime_error("benchmark requires the approved WSL2 environment");
    }
    return value;
}

void write_comparison(
    std::ostringstream& output,
    const edgeai::common::DetectionComparison& comparison
) {
    output << "{\"status\":\"PASS\",\"detection_count\":"
           << comparison.detection_count << ",\"minimum_class_matched_iou\":"
           << comparison.minimum_class_matched_iou
           << ",\"maximum_absolute_confidence_difference\":"
           << comparison.maximum_absolute_confidence_difference << "}";
}

void write_descriptors(
    std::ostringstream& output,
    const std::vector<edgeai::backends::TensorDescriptor>& descriptors
) {
    output << '[';
    for (std::size_t index = 0; index < descriptors.size(); ++index) {
        if (index != 0U) {
            output << ',';
        }
        output << "{\"name\":" << json_string(descriptors[index].name)
               << ",\"dtype\":" << json_string(descriptors[index].dtype)
               << ",\"shape\":[";
        for (std::size_t shape_index = 0; shape_index < descriptors[index].shape.size();
             ++shape_index) {
            if (shape_index != 0U) {
                output << ',';
            }
            output << descriptors[index].shape[shape_index];
        }
        output << "]}";
    }
    output << ']';
}

std::string make_round_json(
    int round,
    std::int64_t process_started_unix_ns,
    const BenchmarkConfig& config,
    const edgeai::backends::OrtDetector& detector,
    double model_load_ms,
    const std::vector<edgeai::common::BenchmarkSampleNs>& samples,
    const ResourceMeasurement& resources,
    const edgeai::common::DetectionComparison& before,
    const edgeai::common::DetectionComparison& after
) {
    const utsname system = system_identity();
    std::ostringstream output;
    output << std::setprecision(17);
    output << "{\"round\":" << round << ",\"process_id\":" << getpid()
           << ",\"process_started_unix_ns\":" << process_started_unix_ns
           << ",\"model_load_ms\":" << model_load_ms
           << ",\"model_sha256\":" << json_string(config.model_sha256)
           << ",\"image_sha256\":" << json_string(config.image_sha256)
           << ",\"manifest_sha256\":" << json_string(config.manifest_sha256)
           << ",\"inference_config_sha256\":"
           << json_string(config.inference_config_sha256)
           << ",\"golden_result_sha256\":" << json_string(config.golden_result_sha256);

    const auto& runtime = detector.runtime_info();
    output << ",\"runtime\":{\"onnxruntime_version\":" << json_string(runtime.version)
           << ",\"execution_provider\":" << json_string(runtime.execution_provider)
           << ",\"selected_providers\":[\"CPUExecutionProvider\"]"
           << ",\"intra_op_threads\":" << runtime.intra_op_threads
           << ",\"inter_op_threads\":" << runtime.inter_op_threads
           << ",\"execution_mode\":\"ORT_SEQUENTIAL\""
           << ",\"graph_optimization\":\"ORT_ENABLE_ALL\""
           << ",\"opencv_threads\":" << cv::getNumThreads()
           << ",\"runtime_inputs\":";
    write_descriptors(output, runtime.inputs);
    output << ",\"runtime_outputs\":";
    write_descriptors(output, runtime.outputs);
    output << '}';

    output << ",\"environment\":{\"platform\":\"WSL2\",\"os\":"
           << json_string(system.sysname) << ",\"kernel\":" << json_string(system.release)
           << ",\"architecture\":" << json_string(system.machine)
           << ",\"cpu_model\":" << json_string(cpu_model())
           << ",\"logical_cpu_count\":" << std::thread::hardware_concurrency()
           << ",\"cpu_affinity\":\"scheduler managed\",\"cpu_pinning\":\"disabled\""
           << ",\"environment_variables\":{";
    std::size_t environment_index = 0U;
    for (const auto& [name, expected] : config.required_environment) {
        const char* observed_value = std::getenv(name.c_str());
        if (observed_value == nullptr || observed_value != expected) {
            throw std::runtime_error("thread environment differs for " + name);
        }
        if (environment_index++ != 0U) {
            output << ',';
        }
        output << json_string(name) << ':' << json_string(observed_value);
    }
    output << "},\"compiler_version\":" << json_string(__VERSION__)
           << ",\"opencv_version\":" << json_string(CV_VERSION)
           << ",\"build_type\":" << json_string(EDGEAI_BUILD_TYPE) << '}';

    output << ",\"warmup_iterations\":" << config.warmup
           << ",\"formal_iterations\":" << config.repeat
           << ",\"resource_measurement\":{"
           << "\"process_cpu_percent_one_core_basis\":" << resources.cpu_percent
           << ",\"process_cpu_time_delta_seconds\":" << resources.process_cpu_seconds_delta
           << ",\"wall_clock_time_delta_seconds\":" << resources.wall_clock_seconds_delta
           << ",\"peak_rss_bytes\":" << resources.peak_rss_bytes
           << ",\"peak_rss_scope\":\"process startup through formal measurement completion\""
           << ",\"peak_rss_is_process_level_not_model_only\":true"
           << ",\"language_scope_note\":\"includes executable and dynamic libraries\"}";
    output << ",\"correctness\":{\"before_warmup\":";
    write_comparison(output, before);
    output << ",\"after_measurement\":";
    write_comparison(output, after);
    output << "},\"samples\":[";
    for (std::size_t index = 0; index < samples.size(); ++index) {
        if (index != 0U) {
            output << ',';
        }
        const auto& sample = samples[index];
        output << "{\"round\":" << round << ",\"iteration\":" << index + 1U
               << ",\"aggregate_sample_index\":"
               << (static_cast<std::size_t>(round - 1) * samples.size() + index + 1U)
               << ",\"preprocess_ns\":" << sample.preprocess
               << ",\"inference_ns\":" << sample.inference
               << ",\"postprocess_ns\":" << sample.postprocess
               << ",\"pipeline_total_ns\":" << sample.pipeline_total << '}';
    }
    output << "]}";
    return output.str();
}

void append_round(
    const std::filesystem::path& path,
    const std::string& benchmark_config_sha256,
    int round,
    const std::string& round_json
) {
    if (!path.parent_path().empty()) {
        std::filesystem::create_directories(path.parent_path());
    }
    std::string payload;
    if (std::filesystem::exists(path)) {
        cv::FileStorage storage(path.string(), cv::FileStorage::READ | cv::FileStorage::FORMAT_JSON);
        if (!storage.isOpened() || static_cast<std::string>(storage["backend"]) != kBackend ||
            static_cast<std::string>(storage["benchmark_config_sha256"]) !=
                benchmark_config_sha256) {
            throw std::runtime_error("existing benchmark output identity differs");
        }
        const cv::FileNode rounds = storage["rounds"];
        if (!rounds.isSeq() || static_cast<int>(rounds.size()) + 1 != round) {
            throw std::runtime_error("benchmark rounds must be appended sequentially");
        }
        storage.release();
        std::ifstream input(path);
        payload.assign(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
        while (!payload.empty() && std::isspace(static_cast<unsigned char>(payload.back())) != 0) {
            payload.pop_back();
        }
        if (payload.size() < 2U || payload.substr(payload.size() - 2U) != "]}") {
            throw std::runtime_error("existing benchmark JSON has an unexpected suffix");
        }
        payload.resize(payload.size() - 2U);
        payload += ',' + round_json + "]}\n";
    } else {
        if (round != 1) {
            throw std::runtime_error("first persisted benchmark round must be 1");
        }
        payload = "{\"schema_version\":1,\"evidence_type\":"
                  "\"task009_raw_benchmark\",\"backend\":\"cpp_ort\","
                  "\"benchmark_config_sha256\":" +
                  json_string(benchmark_config_sha256) + ",\"rounds\":[" + round_json + "]}\n";
    }
    std::ofstream output(path, std::ios::trunc);
    output << payload;
    output.close();
    if (!output) {
        throw std::runtime_error("failed to write benchmark output: " + path.string());
    }
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        const std::int64_t process_started_unix_ns =
            std::chrono::duration_cast<std::chrono::nanoseconds>(
                std::chrono::system_clock::now().time_since_epoch()
            ).count();
        if (std::string(EDGEAI_BUILD_TYPE) != "Release") {
            throw std::runtime_error(
                std::string("formal benchmark requires Release, observed ") + EDGEAI_BUILD_TYPE
            );
        }
        const Arguments arguments = parse_args(argc, argv);
        const BenchmarkConfig benchmark = load_benchmark_config(arguments.benchmark_config);
        if (arguments.round < 1 || arguments.round > benchmark.round_count) {
            throw std::runtime_error("round must be in [1, 5]");
        }
        for (const auto& [name, expected] : benchmark.required_environment) {
            const char* observed = std::getenv(name.c_str());
            if (observed == nullptr || observed != expected) {
                throw std::runtime_error("thread environment differs for " + name);
            }
        }
        cv::setNumThreads(benchmark.opencv_threads);
        if (cv::getNumThreads() != 1) {
            throw std::runtime_error("OpenCV thread count must be 1");
        }
        require_artifact_hash(benchmark.model, benchmark.model_sha256, "model");
        require_artifact_hash(benchmark.manifest, benchmark.manifest_sha256, "manifest");
        require_artifact_hash(benchmark.image, benchmark.image_sha256, "image");
        require_artifact_hash(
            benchmark.inference_config,
            benchmark.inference_config_sha256,
            "inference config"
        );
        require_artifact_hash(
            benchmark.golden_result,
            benchmark.golden_result_sha256,
            "golden result"
        );
        const std::string benchmark_config_sha256 =
            edgeai::backends::sha256_file(arguments.benchmark_config);
        const edgeai::common::InferenceConfig inference_config =
            edgeai::common::load_config(benchmark.inference_config);
        const cv::Mat image = edgeai::common::load_bgr_image(benchmark.image);
        if (image.cols != 1280 || image.rows != 960 || image.channels() != 3) {
            throw std::runtime_error("reference image dimensions differ from 1280x960 BGR");
        }
        const auto golden = load_golden(benchmark.golden_result);

        const auto model_load_start = Clock::now();
        edgeai::backends::OrtDetector detector(
            benchmark.model,
            benchmark.manifest,
            benchmark.intra_op_threads,
            benchmark.inter_op_threads
        );
        const auto model_load_end = Clock::now();
        const double model_load_ms =
            std::chrono::duration<double, std::milli>(model_load_end - model_load_start).count();

        const auto before_pipeline = run_pipeline(image, detector, inference_config);
        const auto correctness_before = edgeai::common::compare_benchmark_detections(
            golden,
            before_pipeline.detections,
            benchmark.minimum_iou,
            benchmark.maximum_confidence_difference
        );
        for (int iteration = 0; iteration < benchmark.warmup; ++iteration) {
            static_cast<void>(run_pipeline(image, detector, inference_config));
        }

        rusage usage_before{};
        rusage usage_after{};
        if (getrusage(RUSAGE_SELF, &usage_before) != 0) {
            throw std::runtime_error("getrusage failed before formal measurement");
        }
        const auto wall_start = Clock::now();
        std::vector<edgeai::common::BenchmarkSampleNs> samples;
        samples.reserve(static_cast<std::size_t>(benchmark.repeat));
        for (int iteration = 0; iteration < benchmark.repeat; ++iteration) {
            samples.push_back(run_pipeline(image, detector, inference_config).sample);
        }
        const auto wall_end = Clock::now();
        if (getrusage(RUSAGE_SELF, &usage_after) != 0) {
            throw std::runtime_error("getrusage failed after formal measurement");
        }
        const double cpu_seconds =
            timeval_seconds(usage_after.ru_utime) + timeval_seconds(usage_after.ru_stime) -
            timeval_seconds(usage_before.ru_utime) - timeval_seconds(usage_before.ru_stime);
        const double wall_seconds =
            std::chrono::duration<double>(wall_end - wall_start).count();
        const ResourceMeasurement resources{
            edgeai::common::process_cpu_percent_one_core_basis(cpu_seconds, wall_seconds),
            cpu_seconds,
            wall_seconds,
            static_cast<std::uint64_t>(usage_after.ru_maxrss) * 1024U,
        };

        const auto after_pipeline = run_pipeline(image, detector, inference_config);
        const auto correctness_after = edgeai::common::compare_benchmark_detections(
            golden,
            after_pipeline.detections,
            benchmark.minimum_iou,
            benchmark.maximum_confidence_difference
        );
        const std::string round_json = make_round_json(
            arguments.round,
            process_started_unix_ns,
            benchmark,
            detector,
            model_load_ms,
            samples,
            resources,
            correctness_before,
            correctness_after
        );
        append_round(
            arguments.output,
            benchmark_config_sha256,
            arguments.round,
            round_json
        );
        std::cout << std::fixed << std::setprecision(6)
                  << "backend=" << kBackend << '\n'
                  << "round=" << arguments.round << '\n'
                  << "process_id=" << getpid() << '\n'
                  << "build_type=" << EDGEAI_BUILD_TYPE << '\n'
                  << "model_load_ms=" << model_load_ms << '\n'
                  << "formal_samples=" << samples.size() << '\n'
                  << "process_cpu_percent_one_core_basis=" << resources.cpu_percent << '\n'
                  << "peak_rss_bytes=" << resources.peak_rss_bytes << '\n'
                  << "correctness_before=PASS\ncorrectness_after=PASS\n"
                  << "output=" << arguments.output.string() << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "benchmark error: " << error.what() << '\n';
        return 1;
    }
}
