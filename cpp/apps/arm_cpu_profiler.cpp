#include "edgeai/backends/ncnn_detector.hpp"
#include "edgeai/common/benchmark.hpp"
#include "edgeai/common/config.hpp"
#include "edgeai/common/postprocess.hpp"
#include "edgeai/common/preprocess.hpp"

#include <opencv2/core/persistence.hpp>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cerrno>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <sched.h>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <sys/utsname.h>
#include <unistd.h>
#include <vector>

namespace {

using Clock = std::chrono::steady_clock;
using Path = edgeai::filesystem::path;

struct Arguments {
    Path manifest;
    Path config;
    Path input;
    Path reference;
    Path output;
    int threads{1};
    int warmup{3};
    int repeat{10};
    std::string affinity{"default"};
    bool packing{true};
    bool fp16_packed{false};
    bool fp16_storage{false};
    bool fp16_arithmetic{false};
    bool int8{false};
};

struct Usage {
    std::string name;
    std::string value;
};

struct GoldenDetection {
    edgeai::common::Detection detection;
};

struct ResourceDelta {
    double user_seconds{0.0};
    double system_seconds{0.0};
    double total_seconds{0.0};
    double wall_seconds{0.0};
    double cpu_percent{0.0};
    long peak_rss_kib{0};
    int threads_before{0};
    int threads_after{0};
};

struct Sample {
    std::int64_t preprocess_ns{0};
    std::int64_t inference_ns{0};
    std::int64_t postprocess_ns{0};
    std::int64_t decode_ns{0};
    std::int64_t nms_ns{0};
    std::int64_t pipeline_ns{0};
    std::int64_t end_to_end_ns{0};
    ResourceDelta resources;
    std::optional<std::int64_t> frequency_khz;
    std::optional<std::int64_t> temperature_millicelsius;
    edgeai::common::DetectionComparison correctness;
    std::string correctness_status{"PASS_TARGET"};
    std::string correctness_error;
};

struct RunResult {
    Sample sample;
    std::vector<edgeai::common::Detection> detections;
    std::vector<float> raw;
    std::vector<std::int64_t> shape;
};

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

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

bool parse_bool(const std::string& value, const char* name) {
    if (value == "1" || value == "true" || value == "on") return true;
    if (value == "0" || value == "false" || value == "off") return false;
    throw std::runtime_error(std::string(name) + " must be on/off or true/false");
}

int parse_int(const std::string& value, const char* name, int minimum) {
    std::size_t consumed = 0U;
    int result = 0;
    try {
        result = std::stoi(value, &consumed);
    } catch (const std::exception&) {
        throw std::runtime_error(std::string(name) + " must be an integer");
    }
    if (consumed != value.size() || result < minimum) {
        throw std::runtime_error(std::string(name) + " is outside the allowed range");
    }
    return result;
}

Arguments parse_args(int argc, char* argv[]) {
    if (argc < 11 || argc % 2 == 0) {
        throw std::runtime_error(
            "usage: edgeai_arm_cpu_profiler --manifest PATH --config PATH --input PATH "
            "--reference PATH --output PATH [--threads N] [--warmup N] [--repeat N] "
            "[--affinity default|cpu0|cpu1|both] [--packing on|off] "
            "[--fp16-packed on|off] [--fp16-storage on|off] [--fp16-arithmetic on|off] "
            "[--int8 on|off]"
        );
    }
    const std::vector<std::string> allowed{
        "--manifest", "--config", "--input", "--reference", "--output", "--threads",
        "--warmup", "--repeat", "--affinity", "--packing", "--fp16-packed",
        "--fp16-storage", "--fp16-arithmetic", "--int8",
    };
    std::map<std::string, std::string> values;
    for (int index = 1; index < argc; index += 2) {
        const std::string option = argv[index];
        if (std::find(allowed.begin(), allowed.end(), option) == allowed.end()) {
            throw std::runtime_error("unknown option: " + option);
        }
        if (!values.emplace(option, argv[index + 1]).second) {
            throw std::runtime_error("duplicate option: " + option);
        }
    }
    for (const char* required_name : {"--manifest", "--config", "--input", "--reference", "--output"}) {
        if (values.count(required_name) == 0U) {
            throw std::runtime_error(std::string("missing option: ") + required_name);
        }
    }
    Arguments result{
        values.at("--manifest"), values.at("--config"), values.at("--input"),
        values.at("--reference"), values.at("--output"), 1, 3, 10, "default", true,
        false, false, false, false,
    };
    if (values.count("--threads") != 0U) result.threads = parse_int(values.at("--threads"), "--threads", 1);
    if (values.count("--warmup") != 0U) result.warmup = parse_int(values.at("--warmup"), "--warmup", 0);
    if (values.count("--repeat") != 0U) result.repeat = parse_int(values.at("--repeat"), "--repeat", 1);
    if (values.count("--affinity") != 0U) result.affinity = values.at("--affinity");
    if (result.affinity != "default" && result.affinity != "cpu0" &&
        result.affinity != "cpu1" && result.affinity != "both") {
        throw std::runtime_error("--affinity must be default, cpu0, cpu1, or both");
    }
    if (values.count("--packing") != 0U) result.packing = parse_bool(values.at("--packing"), "--packing");
    if (values.count("--fp16-packed") != 0U) result.fp16_packed = parse_bool(values.at("--fp16-packed"), "--fp16-packed");
    if (values.count("--fp16-storage") != 0U) result.fp16_storage = parse_bool(values.at("--fp16-storage"), "--fp16-storage");
    if (values.count("--fp16-arithmetic") != 0U) result.fp16_arithmetic = parse_bool(values.at("--fp16-arithmetic"), "--fp16-arithmetic");
    if (values.count("--int8") != 0U) result.int8 = parse_bool(values.at("--int8"), "--int8");
    return result;
}

double timeval_seconds(const timeval& value) {
    return static_cast<double>(value.tv_sec) + static_cast<double>(value.tv_usec) / 1'000'000.0;
}

ResourceDelta resource_delta(const rusage& before, const rusage& after, double wall_seconds) {
    ResourceDelta result;
    result.user_seconds = timeval_seconds(after.ru_utime) - timeval_seconds(before.ru_utime);
    result.system_seconds = timeval_seconds(after.ru_stime) - timeval_seconds(before.ru_stime);
    result.total_seconds = result.user_seconds + result.system_seconds;
    result.wall_seconds = wall_seconds;
    result.cpu_percent = edgeai::common::process_cpu_percent_one_core_basis(
        result.total_seconds, wall_seconds
    );
    result.peak_rss_kib = after.ru_maxrss;
    return result;
}

int process_threads() {
    std::ifstream input("/proc/self/status");
    std::string key;
    while (input >> key) {
        if (key == "Threads:") {
            int result = 0;
            input >> result;
            return result;
        }
        std::string remainder;
        std::getline(input, remainder);
    }
    return 0;
}

std::string cpu_mask() {
    cpu_set_t mask;
    CPU_ZERO(&mask);
    if (sched_getaffinity(0, sizeof(mask), &mask) != 0) {
        return "unavailable:" + std::string(std::strerror(errno));
    }
    std::ostringstream result;
    bool first = true;
    for (int index = 0; index < CPU_SETSIZE; ++index) {
        if (CPU_ISSET(index, &mask)) {
            if (!first) result << ',';
            result << index;
            first = false;
        }
    }
    return result.str();
}

void apply_affinity(const std::string& affinity) {
    if (affinity == "default") return;
    cpu_set_t mask;
    CPU_ZERO(&mask);
    if (affinity == "cpu0" || affinity == "both") CPU_SET(0, &mask);
    if (affinity == "cpu1" || affinity == "both") CPU_SET(1, &mask);
    if (sched_setaffinity(0, sizeof(mask), &mask) != 0) {
        throw std::runtime_error("sched_setaffinity(" + affinity + ") failed: " + std::strerror(errno));
    }
}

std::optional<std::int64_t> read_integer_file(const Path& path) {
    std::ifstream input(path.string());
    std::int64_t value = 0;
    if (!(input >> value) || value < 0) return std::nullopt;
    return value;
}

std::optional<std::int64_t> maximum_indexed_value(
    const Path& root, const std::string& prefix, const Path& suffix
) {
    std::optional<std::int64_t> result;
    for (int index = 0; index < 256; ++index) {
        const auto value = read_integer_file(root / (prefix + std::to_string(index)) / suffix);
        if (value && (!result || *value > *result)) result = value;
    }
    return result;
}

std::optional<std::int64_t> frequency_khz() {
    return maximum_indexed_value("/sys/devices/system/cpu", "cpu", "cpufreq/scaling_cur_freq");
}

std::optional<std::int64_t> temperature_millicelsius() {
    return maximum_indexed_value("/sys/class/thermal", "thermal_zone", "temp");
}

std::vector<edgeai::common::Detection> load_golden(const Path& path) {
    cv::FileStorage storage(path.string(), cv::FileStorage::READ | cv::FileStorage::FORMAT_JSON);
    if (!storage.isOpened()) throw std::runtime_error("failed to open golden: " + path.string());
    const cv::FileNode nodes = storage["detections"];
    if (!nodes.isSeq()) throw std::runtime_error("golden detections are missing");
    std::vector<edgeai::common::Detection> result;
    for (const auto& node : nodes) {
        const cv::FileNode box = node["box_xyxy_source"];
        if (!box.isSeq() || box.size() != 4U) throw std::runtime_error("invalid golden box");
        edgeai::common::Detection detection;
        detection.rank = static_cast<std::size_t>(static_cast<int>(node["rank"]));
        detection.class_id = static_cast<int>(node["class_id"]);
        detection.class_name = static_cast<std::string>(node["class_name"]);
        detection.confidence = static_cast<float>(node["confidence"]);
        detection.box_xyxy_source = {
            static_cast<float>(box[0]), static_cast<float>(box[1]),
            static_cast<float>(box[2]), static_cast<float>(box[3]),
        };
        result.push_back(std::move(detection));
    }
    return result;
}

std::string cpu_model() {
    std::ifstream input("/proc/cpuinfo");
    std::string line;
    while (std::getline(input, line)) {
        if (line.rfind("model name", 0U) == 0U || line.rfind("CPU part", 0U) == 0U) return line;
    }
    return "unknown";
}

constexpr bool compiled_aarch64() {
#if defined(__aarch64__)
    return true;
#else
    return false;
#endif
}

constexpr bool compiled_neon() {
#if defined(__ARM_NEON) || defined(__aarch64__)
    return true;
#else
    return false;
#endif
}

constexpr bool compiled_arm82() {
#if defined(NCNN_ARM82) && NCNN_ARM82
    return true;
#else
    return false;
#endif
}

std::string uname_field(int field) {
    struct utsname value{};
    if (uname(&value) != 0) return "unknown";
    const char* fields[] = {value.sysname, value.nodename, value.release, value.version, value.machine};
    return fields[field];
}

double milliseconds(std::int64_t nanoseconds) {
    return static_cast<double>(nanoseconds) / 1'000'000.0;
}

std::int64_t elapsed_ns(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
}

RunResult run_once(
    const cv::Mat& image,
    edgeai::backends::NcnnDetector& detector,
    const edgeai::common::InferenceConfig& config,
    const std::vector<edgeai::common::Detection>& golden
) {
    const auto start = Clock::now();
    const int threads_before = process_threads();
    struct rusage before{};
    struct rusage after{};
    getrusage(RUSAGE_SELF, &before);
    const auto pre_start = Clock::now();
    const auto preprocessed = edgeai::common::preprocess_image(image, config);
    const auto pre_end = Clock::now();
    const auto infer_start = Clock::now();
    const auto raw = detector.infer(preprocessed.tensor);
    const auto infer_end = Clock::now();
    const auto post_start = Clock::now();
    const auto post = edgeai::common::decode_yolov5_output(
        raw.values, raw.shape, config.class_names, preprocessed.metadata, config
    );
    const auto post_end = Clock::now();
    const auto end = Clock::now();
    getrusage(RUSAGE_SELF, &after);
    edgeai::common::validate_frame_detections(post.detections, image.cols, image.rows, 0U);
    edgeai::common::DetectionComparison comparison;
    std::string correctness_status = "PASS_TARGET";
    std::string correctness_error;
    try {
        comparison = edgeai::common::compare_benchmark_detections(
            golden, post.detections, 0.99, 0.01
        );
    } catch (const std::exception& error) {
        correctness_status = "FAIL_CORRECTNESS_GATE";
        correctness_error = error.what();
        comparison.detection_count = post.detections.size();
        comparison.minimum_class_matched_iou = 0.0;
        comparison.maximum_absolute_confidence_difference = 0.0;
    }
    Sample sample;
    sample.preprocess_ns = elapsed_ns(pre_start, pre_end);
    sample.inference_ns = elapsed_ns(infer_start, infer_end);
    sample.postprocess_ns = elapsed_ns(post_start, post_end);
    sample.decode_ns = post.decode_ns;
    sample.nms_ns = post.nms_ns;
    sample.pipeline_ns = sample.preprocess_ns + sample.inference_ns + sample.postprocess_ns;
    sample.end_to_end_ns = elapsed_ns(start, end);
    sample.resources = resource_delta(
        before, after, static_cast<double>(sample.end_to_end_ns) / 1'000'000'000.0
    );
    sample.resources.threads_before = threads_before;
    sample.resources.threads_after = process_threads();
    sample.frequency_khz = frequency_khz();
    sample.temperature_millicelsius = temperature_millicelsius();
    sample.correctness = comparison;
    sample.correctness_status = correctness_status;
    sample.correctness_error = correctness_error;
    return {std::move(sample), post.detections, raw.values, raw.shape};
}

double nearest_rank(const std::vector<double>& values, double percentile) {
    require(!values.empty(), "cannot calculate percentile of an empty sample set");
    std::vector<double> sorted = values;
    std::sort(sorted.begin(), sorted.end());
    const auto rank = static_cast<std::size_t>(std::ceil(percentile * sorted.size()));
    return sorted[std::max<std::size_t>(1U, rank) - 1U];
}

double mean(const std::vector<double>& values) {
    double total = 0.0;
    for (double value : values) total += value;
    return total / static_cast<double>(values.size());
}

double sample_sd(const std::vector<double>& values) {
    if (values.size() < 2U) return 0.0;
    const double average = mean(values);
    double total = 0.0;
    for (double value : values) total += (value - average) * (value - average);
    return std::sqrt(total / static_cast<double>(values.size() - 1U));
}

void write_optional(std::ostringstream& output, const std::optional<std::int64_t>& value) {
    if (value) output << *value;
    else output << "null";
}

void write_sample(std::ostringstream& output, const Sample& sample, std::size_t index) {
    if (index != 0U) output << ',';
    output << "{\"preprocess_ns\":" << sample.preprocess_ns
           << ",\"inference_ns\":" << sample.inference_ns
           << ",\"decode_ns\":" << sample.decode_ns
           << ",\"nms_ns\":" << sample.nms_ns
           << ",\"postprocess_ns\":" << sample.postprocess_ns
           << ",\"pipeline_ns\":" << sample.pipeline_ns
           << ",\"end_to_end_ns\":" << sample.end_to_end_ns
           << ",\"pipeline_reconciliation_error_ns\":"
           << sample.end_to_end_ns - sample.pipeline_ns
           << ",\"preprocess_ms\":" << milliseconds(sample.preprocess_ns)
           << ",\"inference_ms\":" << milliseconds(sample.inference_ns)
           << ",\"decode_ms\":" << milliseconds(sample.decode_ns)
           << ",\"nms_ms\":" << milliseconds(sample.nms_ns)
           << ",\"postprocess_ms\":" << milliseconds(sample.postprocess_ns)
           << ",\"pipeline_ms\":" << milliseconds(sample.pipeline_ns)
           << ",\"end_to_end_ms\":" << milliseconds(sample.end_to_end_ns)
           << ",\"cpu_percent_one_core_basis\":" << sample.resources.cpu_percent
           << ",\"user_cpu_seconds\":" << sample.resources.user_seconds
           << ",\"system_cpu_seconds\":" << sample.resources.system_seconds
           << ",\"peak_rss_kib\":" << sample.resources.peak_rss_kib
           << ",\"threads_before\":" << sample.resources.threads_before
           << ",\"threads_after\":" << sample.resources.threads_after
           << ",\"cpu_frequency_khz\":";
    write_optional(output, sample.frequency_khz);
    output << ",\"temperature_millicelsius\":";
    write_optional(output, sample.temperature_millicelsius);
    output << ",\"correctness\":{\"status\":" << json_string(sample.correctness_status)
           << ",\"detection_count\":"
           << sample.correctness.detection_count
           << ",\"minimum_class_matched_iou\":";
    if (sample.correctness_status == "PASS_TARGET") output << sample.correctness.minimum_class_matched_iou;
    else output << "null";
    output << ",\"maximum_absolute_confidence_difference\":";
    if (sample.correctness_status == "PASS_TARGET") {
        output << sample.correctness.maximum_absolute_confidence_difference;
    } else {
        output << "null";
    }
    output
           << ",\"error\":" << json_string(sample.correctness_error) << "}}";
}

void write_summary(std::ostringstream& output, const std::vector<Sample>& samples) {
    const auto collect = [&samples](auto member) {
        std::vector<double> values;
        values.reserve(samples.size());
        for (const auto& sample : samples) values.push_back(milliseconds(member(sample)));
        return values;
    };
    const auto write_stage = [&output, &collect](const char* name, auto member) {
        const auto values = collect(member);
        output << json_string(name) << ":{\"mean_ms\":" << mean(values)
               << ",\"p50_ms\":" << nearest_rank(values, 0.50)
               << ",\"p95_ms\":" << nearest_rank(values, 0.95)
               << ",\"min_ms\":" << *std::min_element(values.begin(), values.end())
               << ",\"max_ms\":" << *std::max_element(values.begin(), values.end())
               << ",\"sample_sd_ms\":" << sample_sd(values)
               << ",\"fps\":" << (1000.0 / mean(values)) << "}";
    };
    output << "{\"sample_count\":" << samples.size() << ",\"stages\":{";
    write_stage("preprocess", [](const Sample& sample) { return sample.preprocess_ns; }); output << ',';
    write_stage("inference", [](const Sample& sample) { return sample.inference_ns; }); output << ',';
    write_stage("decode", [](const Sample& sample) { return sample.decode_ns; }); output << ',';
    write_stage("nms", [](const Sample& sample) { return sample.nms_ns; }); output << ',';
    write_stage("postprocess", [](const Sample& sample) { return sample.postprocess_ns; }); output << ',';
    write_stage("pipeline", [](const Sample& sample) { return sample.pipeline_ns; }); output << ',';
    write_stage("end_to_end", [](const Sample& sample) { return sample.end_to_end_ns; });
    output << "}}";
}

std::string raw_stats(const std::vector<float>& values) {
    require(!values.empty(), "raw output is empty");
    float minimum = values[0];
    float maximum = values[0];
    long double total = 0.0;
    for (float value : values) {
        require(std::isfinite(value), "raw output contains a non-finite value");
        minimum = std::min(minimum, value);
        maximum = std::max(maximum, value);
        total += value;
    }
    std::ostringstream output;
    output << "{\"count\":" << values.size() << ",\"min\":" << minimum
           << ",\"max\":" << maximum << ",\"mean\":"
           << static_cast<double>(total / values.size()) << "}";
    return output.str();
}

void write_output(
    const Arguments& arguments,
    const edgeai::common::InferenceConfig& config,
    const edgeai::backends::NcnnDetector& detector,
    const std::vector<Sample>& samples,
    const RunResult& first_result,
    double model_load_ms,
    const std::string& initial_mask
) {
    if (!arguments.output.parent_path().empty()) {
        edgeai::filesystem::create_directories(arguments.output.parent_path());
    }
    std::ostringstream output;
    output << std::setprecision(17);
    const auto& runtime = detector.runtime_info();
    const bool all_pass = std::all_of(
        samples.begin(), samples.end(), [](const Sample& sample) {
            return sample.correctness_status == "PASS_TARGET";
        }
    );
    output << "{\"schema_version\":1,\"task\":"
           << json_string(arguments.int8 ? "035" : "033")
           << ",\"status\":" << json_string(all_pass ? "PASS_TARGET" : "FAIL_CORRECTNESS_GATE")
           << ",\"identity\":{\"manifest_sha256\":"
           << json_string(edgeai::backends::ncnn_sha256_file(arguments.manifest))
           << ",\"param_sha256\":" << json_string(detector.param_sha256())
           << ",\"bin_sha256\":" << json_string(detector.bin_sha256())
           << ",\"input_sha256\":" << json_string(edgeai::backends::ncnn_sha256_file(arguments.input))
           << ",\"config_sha256\":" << json_string(edgeai::backends::ncnn_sha256_file(arguments.config))
           << ",\"reference_sha256\":" << json_string(edgeai::backends::ncnn_sha256_file(arguments.reference))
           << ",\"ncnn_version\":" << json_string(runtime.version)
           << ",\"ncnn_library_sha256\":" << json_string(runtime.library_sha256)
           << ",\"private_libgomp_sha256\":" << json_string(runtime.private_libgomp_sha256)
           << "},\"experiment\":{\"threads\":" << arguments.threads
           << ",\"affinity\":" << json_string(arguments.affinity)
           << ",\"affinity_mask_before\":" << json_string(initial_mask)
           << ",\"affinity_mask_after\":" << json_string(cpu_mask())
           << ",\"packing_layout\":" << (arguments.packing ? "true" : "false")
           << ",\"fp16_packed\":" << (arguments.fp16_packed ? "true" : "false")
           << ",\"fp16_storage\":" << (arguments.fp16_storage ? "true" : "false")
           << ",\"fp16_arithmetic\":" << (arguments.fp16_arithmetic ? "true" : "false")
           << ",\"int8_inference\":" << (arguments.int8 ? "true" : "false")
           << ",\"warmup\":" << arguments.warmup << ",\"repeat\":" << arguments.repeat << "}"
           << ",\"runtime\":{\"threads\":" << runtime.threads
           << ",\"openmp_compiled\":" << (runtime.openmp_compiled ? "true" : "false")
           << ",\"threads_compiled\":" << (runtime.threads_compiled ? "true" : "false")
           << ",\"simpleomp_compiled\":" << (runtime.simpleomp_compiled ? "true" : "false")
           << ",\"compiler_openmp\":" << (runtime.compiler_openmp ? "true" : "false")
           << ",\"effective_parallel_backend\":" << json_string(runtime.effective_parallel_backend)
           << ",\"packing_layout\":" << (runtime.packing_layout ? "true" : "false")
           << ",\"fp16\":" << (runtime.fp16 ? "true" : "false")
           << ",\"bf16\":" << (runtime.bf16 ? "true" : "false")
           << ",\"int8\":" << (runtime.int8 ? "true" : "false") << "}"
           << ",\"build_capabilities\":{\"compiled_aarch64\":"
           << (compiled_aarch64() ? "true" : "false")
           << ",\"compiled_neon\":" << (compiled_neon() ? "true" : "false")
           << ",\"ncnn_arm82\":" << (compiled_arm82() ? "true" : "false") << "}"
           << ",\"environment\":{\"architecture\":" << json_string(uname_field(4))
           << ",\"kernel\":" << json_string(uname_field(2))
           << ",\"cpu_model\":" << json_string(cpu_model())
           << ",\"logical_cpu_count\":" << sysconf(_SC_NPROCESSORS_ONLN)
           << ",\"cpu_affinity_after\":" << json_string(cpu_mask()) << "}"
           << ",\"workload\":{\"input_shape\":[1,3,640,640],\"output_shape\":[1,25200,85]"
           << ",\"input_dtype\":\"float32\",\"output_dtype\":\"float32\",\"confidence_threshold\":"
           << config.confidence_threshold << ",\"nms_iou_threshold\":" << config.iou_threshold << "}"
           << ",\"model_load_ms\":" << model_load_ms
           << ",\"correctness\":{\"status\":"
           << json_string(first_result.sample.correctness_status)
           << ",\"detection_count\":"
           << first_result.sample.correctness.detection_count
           << ",\"minimum_class_matched_iou\":";
    if (first_result.sample.correctness_status == "PASS_TARGET") {
        output << first_result.sample.correctness.minimum_class_matched_iou;
    } else {
        output << "null";
    }
    output << ",\"maximum_absolute_confidence_difference\":";
    if (first_result.sample.correctness_status == "PASS_TARGET") {
        output << first_result.sample.correctness.maximum_absolute_confidence_difference;
    } else {
        output << "null";
    }
    output
           << ",\"error\":" << json_string(first_result.sample.correctness_error)
           << ",\"raw_output_stats\":" << raw_stats(first_result.raw) << "}"
           << ",\"samples\":[";
    for (std::size_t index = 0; index < samples.size(); ++index) write_sample(output, samples[index], index);
    output << "],\"summary\":";
    write_summary(output, samples);
    output << "}\n";
    std::ofstream file(arguments.output.string(), std::ios::trunc);
    if (!file) throw std::runtime_error("failed to write profiler output: " + arguments.output.string());
    file << output.str();
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        const Arguments arguments = parse_args(argc, argv);
        const std::string initial_mask = cpu_mask();
        apply_affinity(arguments.affinity);
        const auto config = edgeai::common::load_config(arguments.config);
        const auto golden = load_golden(arguments.reference);
        const cv::Mat image = edgeai::common::load_bgr_image(arguments.input);
        edgeai::backends::NcnnRuntimeOptions options;
        options.threads = arguments.threads;
        options.use_packing_layout = arguments.packing;
        options.use_fp16_packed = arguments.fp16_packed;
        options.use_fp16_storage = arguments.fp16_storage;
        options.use_fp16_arithmetic = arguments.fp16_arithmetic;
        options.use_int8_inference = arguments.int8;
        options.use_int8_packed = arguments.int8;
        options.use_int8_storage = arguments.int8;
        const auto load_start = Clock::now();
        edgeai::backends::NcnnDetector detector(arguments.manifest, options);
        const double model_load_ms = std::chrono::duration<double, std::milli>(Clock::now() - load_start).count();
        require(
            detector.runtime_info().effective_parallel_backend == "openmp",
            "Task 033 requires the validated OpenMP ncnn backend"
        );
        RunResult first_result = run_once(image, detector, config, golden);
        for (int iteration = 0; iteration < arguments.warmup; ++iteration) {
            static_cast<void>(run_once(image, detector, config, golden));
        }
        std::vector<Sample> samples;
        samples.reserve(static_cast<std::size_t>(arguments.repeat));
        RunResult last_result = first_result;
        for (int iteration = 0; iteration < arguments.repeat; ++iteration) {
            last_result = run_once(image, detector, config, golden);
            samples.push_back(last_result.sample);
        }
        write_output(arguments, config, detector, samples, last_result, model_load_ms, initial_mask);
        const auto& summary = samples.front();
        const bool all_pass = std::all_of(
            samples.begin(), samples.end(), [](const Sample& sample) {
                return sample.correctness_status == "PASS_TARGET";
            }
        );
        std::cout << "Task " << (arguments.int8 ? "035" : "033") << " profiler "
                  << (all_pass ? "PASS_TARGET" : "FAIL_CORRECTNESS_GATE") << '\n'
                  << "threads=" << arguments.threads << " affinity=" << arguments.affinity
                  << " mask=" << cpu_mask() << " packing_layout=" << (arguments.packing ? "on" : "off") << '\n'
                  << "int8_inference=" << (arguments.int8 ? "on" : "off") << '\n'
                  << "ncnn=" << detector.runtime_info().version
                  << " backend=" << detector.runtime_info().effective_parallel_backend << '\n'
                  << "correctness_detection_count=" << summary.correctness.detection_count
                  << " minimum_iou=" << summary.correctness.minimum_class_matched_iou
                  << " max_confidence_delta=" << summary.correctness.maximum_absolute_confidence_difference
                  << " status=" << summary.correctness_status
                  << (summary.correctness_error.empty() ? "" : " error=" + summary.correctness_error) << '\n'
                  << "output=" << arguments.output.string() << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "edgeai_arm_cpu_profiler error: " << error.what() << '\n';
        return 1;
    }
}
