#include "edgeai/backends/ncnn_detector.hpp"
#include "edgeai/common/config.hpp"
#include "edgeai/common/postprocess.hpp"
#include "edgeai/common/preprocess.hpp"
#include "edgeai/common/visualize.hpp"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

#include <opencv2/core/persistence.hpp>
#include <opencv2/imgcodecs.hpp>

namespace {

using Clock = std::chrono::steady_clock;

struct Arguments {
    edgeai::filesystem::path manifest;
    edgeai::filesystem::path config;
    edgeai::filesystem::path model_param;
    edgeai::filesystem::path model_bin;
    edgeai::filesystem::path input;
    edgeai::filesystem::path output_image;
    edgeai::filesystem::path output_json;
    std::string runtime_profile{"generic-default"};
    int threads{1};
};

int parse_threads(const std::string& value) {
    std::size_t consumed = 0U;
    int threads = 0;
    try {
        threads = std::stoi(value, &consumed);
    } catch (const std::exception&) {
        throw std::runtime_error("--threads must be an integer");
    }
    if (consumed != value.size() || (threads != 1 && threads != 2)) {
        throw std::runtime_error("--threads must be 1 or 2");
    }
    return threads;
}

Arguments parse_args(int argc, char* argv[]) {
    if (argc < 11 || argc % 2 == 0) {
        throw std::runtime_error(
            "usage: edgeai_ncnn_image --manifest PATH --config PATH "
            "[--model-param PATH --model-bin PATH] (--input PATH|--image PATH) "
            "--output-image PATH --output-json PATH "
            "[--runtime-profile baseline-single-thread|recommended-dual-thread] "
            "[--threads 1|2]"
        );
    }
    const std::vector<std::string> allowed{
        "--manifest", "--config", "--model-param", "--model-bin", "--input", "--image",
        "--output-image", "--output-json", "--runtime-profile", "--threads",
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
    for (const std::string required :
         {"--manifest", "--config", "--output-image", "--output-json"}) {
        if (values.count(required) == 0U) {
            throw std::runtime_error("missing required argument: " + required);
        }
    }
    const bool has_input = values.count("--input") != 0U;
    const bool has_image = values.count("--image") != 0U;
    if (has_input == has_image) {
        throw std::runtime_error("exactly one of --input or --image is required");
    }
    const bool has_param = values.count("--model-param") != 0U;
    const bool has_bin = values.count("--model-bin") != 0U;
    if (has_param != has_bin) {
        throw std::runtime_error("--model-param and --model-bin must be supplied together");
    }
    const std::string profile_name =
        values.count("--runtime-profile") != 0U
            ? values.at("--runtime-profile")
            : "generic-default";
    const auto profile = edgeai::backends::ncnn_runtime_profile(profile_name);
    const int threads =
        values.count("--threads") != 0U
            ? parse_threads(values.at("--threads"))
            : profile.configured_threads;
    if (profile_name != "generic-default" && threads != profile.configured_threads) {
        throw std::runtime_error(
            "--threads differs from runtime profile " + profile_name
        );
    }
    edgeai::backends::validate_ncnn_runtime_profile(
        profile, edgeai::backends::ncnn_build_capabilities()
    );
    return {
        values.at("--manifest"),
        values.at("--config"),
        has_param ? edgeai::filesystem::path(values.at("--model-param"))
                  : edgeai::filesystem::path{},
        has_bin ? edgeai::filesystem::path(values.at("--model-bin"))
                : edgeai::filesystem::path{},
        has_input ? edgeai::filesystem::path(values.at("--input"))
                  : edgeai::filesystem::path(values.at("--image")),
        values.at("--output-image"),
        values.at("--output-json"),
        profile_name,
        threads,
    };
}

double elapsed_ms(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
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
        std::string remainder;
        std::getline(status, remainder);
    }
    return -1;
}

void write_shape(cv::FileStorage& output, const std::vector<std::int64_t>& shape) {
    output << "[";
    for (const std::int64_t dimension : shape) {
        output << static_cast<int>(dimension);
    }
    output << "]";
}

void write_box(cv::FileStorage& output, const edgeai::common::Box& box) {
    output << "[" << box.x1 << box.y1 << box.x2 << box.y2 << "]";
}

void write_descriptors(
    cv::FileStorage& output,
    const std::vector<edgeai::backends::NcnnTensorDescriptor>& descriptors
) {
    output << "[";
    for (const auto& descriptor : descriptors) {
        output << "{" << "name" << descriptor.name << "dtype" << descriptor.dtype
               << "logical_shape";
        write_shape(output, descriptor.logical_shape);
        output << "dims" << descriptor.dims << "w" << descriptor.w << "h" << descriptor.h
               << "d" << descriptor.d << "c" << descriptor.c << "elempack"
               << descriptor.elempack << "elembits" << descriptor.elembits << "}";
    }
    output << "]";
}

void write_result(
    const edgeai::filesystem::path& path,
    const Arguments& arguments,
    const edgeai::common::InferenceConfig& config,
    const edgeai::common::PreprocessResult& preprocess,
    const edgeai::backends::NcnnDetector& detector,
    const edgeai::common::PostprocessResult& postprocess,
    const edgeai::common::StageTimingsMs& timings,
    double pipeline_total,
    int process_threads,
    const cv::Mat& source,
    const cv::Mat& rendered
) {
    if (!path.parent_path().empty()) {
        edgeai::filesystem::create_directories(path.parent_path());
    }
    cv::FileStorage output(path.string(), cv::FileStorage::WRITE | cv::FileStorage::FORMAT_JSON);
    if (!output.isOpened()) {
        throw std::runtime_error("failed to open ncnn result JSON: " + path.string());
    }
    const auto& runtime = detector.runtime_info();
    output << "schema_version" << 1 << "application" << "edgeai_cpp_ncnn_image"
           << "runtime_profile" << arguments.runtime_profile;
    output << "model" << "{"
           << "manifest_path" << arguments.manifest.string()
           << "manifest_sha256"
           << edgeai::backends::ncnn_sha256_file(arguments.manifest)
           << "param_path" << detector.param_path().string() << "param_sha256"
           << detector.param_sha256() << "bin_path" << detector.bin_path().string()
           << "bin_sha256" << detector.bin_sha256() << "runtime_version" << runtime.version
           << "execution_provider" << runtime.execution_provider << "threads" << runtime.threads
           << "ncnn_openmp_compiled" << runtime.openmp_compiled
           << "ncnn_threads_compiled" << runtime.threads_compiled
           << "ncnn_simpleomp_compiled" << runtime.simpleomp_compiled
           << "compiler_openmp" << runtime.compiler_openmp
           << "effective_parallel_backend" << runtime.effective_parallel_backend
           << "ncnn_library_sha256" << runtime.library_sha256
           << "private_libgomp_sha256" << runtime.private_libgomp_sha256
           << "observed_process_threads" << process_threads
           << "vulkan" << runtime.vulkan << "fp16" << runtime.fp16 << "bf16" << runtime.bf16
           << "int8" << runtime.int8 << "runtime_inputs";
    write_descriptors(output, runtime.inputs);
    output << "runtime_outputs";
    write_descriptors(output, runtime.outputs);
    output << "}";
    output << "configuration_file" << "{" << "path" << arguments.config.string()
           << "sha256" << edgeai::backends::ncnn_sha256_file(arguments.config) << "}";
    output << "configuration" << "{" << "schema_version" << config.schema_version
           << "input_size" << "[" << config.input_size.height << config.input_size.width << "]"
           << "confidence_threshold" << config.confidence_threshold << "iou_threshold"
           << config.iou_threshold << "class_aware_nms" << config.class_aware_nms
           << "max_detections" << config.max_detections << "}";
    output << "source_image" << "{" << "path" << arguments.input.string()
           << "sha256" << edgeai::backends::ncnn_sha256_file(arguments.input)
           << "size_bytes"
           << static_cast<double>(edgeai::filesystem::file_size(arguments.input))
           << "shape_bgr" << "[" << source.rows << source.cols << source.channels() << "]" << "}";
    output << "preprocess" << "{" << "scale" << preprocess.metadata.scale << "padding" << "{"
           << "left" << preprocess.metadata.padding.left << "top" << preprocess.metadata.padding.top
           << "right" << preprocess.metadata.padding.right << "bottom"
           << preprocess.metadata.padding.bottom << "}" << "transforms" << "[";
    for (const auto& transform : preprocess.metadata.transforms) {
        output << transform;
    }
    output << "]" << "}";
    output << "candidate_counts" << "{" << "raw_candidate_count"
           << static_cast<int>(postprocess.raw_candidate_count) << "threshold_candidate_count"
           << static_cast<int>(postprocess.threshold_candidate_count) << "nms_candidate_count"
           << static_cast<int>(postprocess.nms_candidate_count) << "invalid_box_count"
           << static_cast<int>(postprocess.invalid_box_count) << "}";
    output << "detections" << "[";
    for (const auto& detection : postprocess.detections) {
        output << "{" << "rank" << static_cast<int>(detection.rank) << "candidate_index"
               << static_cast<int>(detection.candidate_index) << "class_id" << detection.class_id
               << "class_name" << detection.class_name << "objectness" << detection.objectness
               << "class_score" << detection.class_score << "confidence" << detection.confidence
               << "box_xywh_input";
        write_box(output, detection.box_xywh_input);
        output << "box_xyxy_input";
        write_box(output, detection.box_xyxy_input);
        output << "box_xyxy_source";
        write_box(output, detection.box_xyxy_source);
        output << "}";
    }
    output << "]";
    output << "output_image" << "{" << "path" << arguments.output_image.string()
           << "sha256" << edgeai::backends::ncnn_sha256_file(arguments.output_image)
           << "size_bytes"
           << static_cast<double>(edgeai::filesystem::file_size(arguments.output_image))
           << "shape_bgr" << "[" << rendered.rows << rendered.cols << rendered.channels() << "]"
           << "decode_validation" << "PASS" << "visual_review" << "PENDING_HUMAN_REVIEW" << "}";
    output << "timings_ms" << "{" << "measurement_type"
           << "single-run diagnostic, not a benchmark" << "input_read" << timings.input_read
           << "preprocess" << timings.preprocess << "inference" << timings.inference
           << "postprocess" << timings.postprocess << "visualization" << timings.visualization
           << "output_write" << timings.output_write << "pipeline_total" << pipeline_total
           << "boundaries" << "{"
           << "inference" << "NcnnDetector::infer input bind, Extractor::extract, validation and copy"
           << "postprocess" << "shared YOLOv5 decode, threshold, NMS, inverse map and clipping"
           << "}" << "}";
    output.release();
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        const auto arguments = parse_args(argc, argv);
        const auto pipeline_start = Clock::now();
        const auto config = edgeai::common::load_config(arguments.config);
        edgeai::common::StageTimingsMs timings;
        const auto read_start = Clock::now();
        const cv::Mat source = edgeai::common::load_bgr_image(arguments.input);
        timings.input_read = elapsed_ms(read_start, Clock::now());
        const auto preprocess_start = Clock::now();
        const auto preprocessed = edgeai::common::preprocess_image(source, config);
        timings.preprocess = elapsed_ms(preprocess_start, Clock::now());
        edgeai::backends::NcnnDetector detector(
            arguments.manifest,
            arguments.threads,
            arguments.model_param,
            arguments.model_bin
        );
        const auto inference_start = Clock::now();
        const auto raw = detector.infer(preprocessed.tensor);
        timings.inference = elapsed_ms(inference_start, Clock::now());
        const int process_threads = observed_process_threads();
        if (arguments.runtime_profile == "recommended-dual-thread" &&
            process_threads < 2) {
            throw std::runtime_error(
                "recommended-dual-thread did not observe at least two process threads"
            );
        }
        const auto postprocess_start = Clock::now();
        const auto postprocessed = edgeai::common::decode_yolov5_output(
            raw.values, raw.shape, config.class_names, preprocessed.metadata, config
        );
        timings.postprocess = elapsed_ms(postprocess_start, Clock::now());
        edgeai::common::validate_frame_detections(
            postprocessed.detections, source.cols, source.rows, 0U
        );
        const auto visualization_start = Clock::now();
        const cv::Mat rendered = edgeai::common::draw_detections(source, postprocessed.detections);
        timings.visualization = elapsed_ms(visualization_start, Clock::now());
        const auto write_start = Clock::now();
        edgeai::common::save_image(arguments.output_image, rendered);
        const cv::Mat read_back = cv::imread(arguments.output_image.string());
        if (read_back.empty() || read_back.size() != source.size() || read_back.type() != CV_8UC3) {
            throw std::runtime_error("ncnn output image read-back validation failed");
        }
        timings.output_write = elapsed_ms(write_start, Clock::now());
        const double pipeline_total = elapsed_ms(pipeline_start, Clock::now());
        write_result(
            arguments.output_json, arguments, config, preprocessed, detector, postprocessed,
            timings, pipeline_total, process_threads, source, read_back
        );
        std::cout << "Application: edgeai_cpp_ncnn_image\n"
                  << "Program contract: Task 019 profiled single-image CPU/FP32\n"
                  << "Runtime profile: " << arguments.runtime_profile << '\n'
                  << "ncnn version: " << detector.runtime_info().version << '\n'
                  << "Execution provider: ncnn CPU\nThreads: " << arguments.threads << '\n'
                  << "ncnn_openmp_compiled: "
                  << (detector.runtime_info().openmp_compiled ? "true" : "false") << '\n'
                  << "ncnn_threads_compiled: "
                  << (detector.runtime_info().threads_compiled ? "true" : "false") << '\n'
                  << "ncnn_simpleomp_compiled: "
                  << (detector.runtime_info().simpleomp_compiled ? "true" : "false") << '\n'
                  << "effective_parallel_backend: "
                  << detector.runtime_info().effective_parallel_backend << '\n'
                  << "observed_process_threads: " << process_threads << '\n'
                  << "Param SHA256: " << detector.param_sha256() << '\n'
                  << "Bin SHA256: " << detector.bin_sha256() << '\n'
                  << "Input SHA256: " << edgeai::backends::ncnn_sha256_file(arguments.input)
                  << '\n'
                  << "Input: in0 [1,3,640,640] float32\n"
                  << "Output: out0 [1,25200,85] float32\n"
                  << "Confidence threshold: " << config.confidence_threshold << '\n'
                  << "NMS IoU threshold: " << config.iou_threshold << '\n'
                  << "Detection count: " << postprocessed.detections.size() << '\n';
        for (const auto& detection : postprocessed.detections) {
            std::cout << "Detection " << detection.rank << ": class=" << detection.class_name
                      << " class_id=" << detection.class_id << " confidence=" << std::fixed
                      << std::setprecision(6) << detection.confidence << " box=["
                      << detection.box_xyxy_source.x1 << ", " << detection.box_xyxy_source.y1
                      << ", " << detection.box_xyxy_source.x2 << ", "
                      << detection.box_xyxy_source.y2 << "]\n";
        }
        std::cout << "Diagnostic timings only; not a benchmark: preprocess=" << timings.preprocess
                  << " inference=" << timings.inference << " postprocess=" << timings.postprocess
                  << " pipeline=" << pipeline_total << " ms\n"
                  << "Output JSON: " << arguments.output_json.string() << '\n'
                  << "Output image: " << arguments.output_image.string() << '\n'
                  << "Visual review: PENDING_HUMAN_REVIEW\n"
                  << "Exit code: 0\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "edgeai_ncnn_image error: " << error.what() << '\n';
        return 1;
    }
}
