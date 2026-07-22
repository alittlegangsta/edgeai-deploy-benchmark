#include "edgeai/backends/ncnn_detector.hpp"
#include "edgeai/common/config.hpp"
#include "edgeai/common/postprocess.hpp"
#include "edgeai/common/preprocess.hpp"
#include "edgeai/common/video_pipeline.hpp"
#include "edgeai/common/visualize.hpp"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
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

std::map<std::string, std::filesystem::path> parse_args(int argc, char* argv[]) {
    if (argc != 11) {
        throw std::runtime_error(
            "usage: edgeai_ncnn_image --manifest PATH --config PATH --image PATH "
            "--output-image PATH --output-json PATH"
        );
    }
    const std::vector<std::string> allowed{
        "--manifest", "--config", "--image", "--output-image", "--output-json",
    };
    std::map<std::string, std::filesystem::path> values;
    for (int index = 1; index < argc; index += 2) {
        const std::string option = argv[index];
        if (std::find(allowed.begin(), allowed.end(), option) == allowed.end()) {
            throw std::runtime_error("unknown argument: " + option);
        }
        if (!values.emplace(option, argv[index + 1]).second) {
            throw std::runtime_error("duplicate argument: " + option);
        }
    }
    if (values.size() != allowed.size()) {
        throw std::runtime_error("all five named arguments are required");
    }
    return values;
}

double elapsed_ms(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
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
    const std::filesystem::path& path,
    const std::map<std::string, std::filesystem::path>& arguments,
    const edgeai::common::InferenceConfig& config,
    const edgeai::common::PreprocessResult& preprocess,
    const edgeai::backends::NcnnDetector& detector,
    const edgeai::common::PostprocessResult& postprocess,
    const edgeai::common::StageTimingsMs& timings,
    const cv::Mat& source,
    const cv::Mat& rendered
) {
    std::filesystem::create_directories(path.parent_path());
    cv::FileStorage output(path.string(), cv::FileStorage::WRITE | cv::FileStorage::FORMAT_JSON);
    if (!output.isOpened()) {
        throw std::runtime_error("failed to open ncnn result JSON: " + path.string());
    }
    const auto& runtime = detector.runtime_info();
    output << "schema_version" << 1 << "application" << "edgeai_cpp_ncnn_image";
    output << "model" << "{"
           << "manifest_path" << arguments.at("--manifest").string()
           << "manifest_sha256"
           << edgeai::backends::ncnn_sha256_file(arguments.at("--manifest"))
           << "param_path" << detector.param_path().string() << "param_sha256"
           << detector.param_sha256() << "bin_path" << detector.bin_path().string()
           << "bin_sha256" << detector.bin_sha256() << "runtime_version" << runtime.version
           << "execution_provider" << runtime.execution_provider << "threads" << runtime.threads
           << "vulkan" << runtime.vulkan << "fp16" << runtime.fp16 << "bf16" << runtime.bf16
           << "int8" << runtime.int8 << "runtime_inputs";
    write_descriptors(output, runtime.inputs);
    output << "runtime_outputs";
    write_descriptors(output, runtime.outputs);
    output << "}";
    output << "configuration_file" << "{" << "path" << arguments.at("--config").string()
           << "sha256" << edgeai::backends::ncnn_sha256_file(arguments.at("--config")) << "}";
    output << "configuration" << "{" << "schema_version" << config.schema_version
           << "input_size" << "[" << config.input_size.height << config.input_size.width << "]"
           << "confidence_threshold" << config.confidence_threshold << "iou_threshold"
           << config.iou_threshold << "class_aware_nms" << config.class_aware_nms
           << "max_detections" << config.max_detections << "}";
    output << "source_image" << "{" << "path" << arguments.at("--image").string()
           << "sha256" << edgeai::backends::ncnn_sha256_file(arguments.at("--image"))
           << "size_bytes"
           << static_cast<double>(std::filesystem::file_size(arguments.at("--image")))
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
    output << "output_image" << "{" << "path" << arguments.at("--output-image").string()
           << "sha256" << edgeai::backends::ncnn_sha256_file(arguments.at("--output-image"))
           << "size_bytes"
           << static_cast<double>(std::filesystem::file_size(arguments.at("--output-image")))
           << "shape_bgr" << "[" << rendered.rows << rendered.cols << rendered.channels() << "]"
           << "decode_validation" << "PASS" << "visual_review" << "PENDING_HUMAN_REVIEW" << "}";
    output << "timings_ms" << "{" << "measurement_type"
           << "single-run diagnostic, not a benchmark" << "input_read" << timings.input_read
           << "preprocess" << timings.preprocess << "inference" << timings.inference
           << "postprocess" << timings.postprocess << "visualization" << timings.visualization
           << "output_write" << timings.output_write << "boundaries" << "{"
           << "inference" << "NcnnDetector::infer input bind, Extractor::extract, validation and copy"
           << "postprocess" << "shared YOLOv5 decode, threshold, NMS, inverse map and clipping"
           << "}" << "}";
    output.release();
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        const auto arguments = parse_args(argc, argv);
        const auto config = edgeai::common::load_config(arguments.at("--config"));
        edgeai::common::StageTimingsMs timings;
        const auto read_start = Clock::now();
        const cv::Mat source = edgeai::common::load_bgr_image(arguments.at("--image"));
        timings.input_read = elapsed_ms(read_start, Clock::now());
        const auto preprocess_start = Clock::now();
        const auto preprocessed = edgeai::common::preprocess_image(source, config);
        timings.preprocess = elapsed_ms(preprocess_start, Clock::now());
        edgeai::backends::NcnnDetector detector(arguments.at("--manifest"), 1);
        const auto inference_start = Clock::now();
        const auto raw = detector.infer(preprocessed.tensor);
        timings.inference = elapsed_ms(inference_start, Clock::now());
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
        edgeai::common::save_image(arguments.at("--output-image"), rendered);
        const cv::Mat read_back = cv::imread(arguments.at("--output-image").string());
        if (read_back.empty() || read_back.size() != source.size() || read_back.type() != CV_8UC3) {
            throw std::runtime_error("ncnn output image read-back validation failed");
        }
        timings.output_write = elapsed_ms(write_start, Clock::now());
        write_result(
            arguments.at("--output-json"), arguments, config, preprocessed, detector,
            postprocessed, timings, source, read_back
        );
        std::cout << "Application: edgeai_cpp_ncnn_image\n"
                  << "ncnn version: " << detector.runtime_info().version << '\n'
                  << "Execution provider: ncnn CPU\nThreads: 1\n"
                  << "Input: in0 [1,3,640,640] float32\n"
                  << "Output: out0 [1,25200,85] float32\n";
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
                  << " ms\nVisual review: PENDING_HUMAN_REVIEW\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "edgeai_ncnn_image error: " << error.what() << '\n';
        return 1;
    }
}
