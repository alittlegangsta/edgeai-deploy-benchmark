#include "edgeai/backends/ort_detector.hpp"
#include "edgeai/common/config.hpp"
#include "edgeai/common/postprocess.hpp"
#include "edgeai/common/preprocess.hpp"
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
    if (argc != 13) {
        throw std::runtime_error(
            "usage: edgeai_ort_image --model PATH --manifest PATH --config PATH "
            "--image PATH --output-image PATH --output-json PATH"
        );
    }
    const std::vector<std::string> allowed{
        "--model", "--manifest", "--config", "--image", "--output-image", "--output-json",
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
        throw std::runtime_error("all six named arguments are required");
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

void write_size(cv::FileStorage& output, const edgeai::common::Size2D& size) {
    output << "{" << "width" << size.width << "height" << size.height << "}";
}

void write_box(cv::FileStorage& output, const edgeai::common::Box& box) {
    output << "[" << box.x1 << box.y1 << box.x2 << box.y2 << "]";
}

void write_descriptors(
    cv::FileStorage& output,
    const std::vector<edgeai::backends::TensorDescriptor>& descriptors
) {
    output << "[";
    for (const auto& descriptor : descriptors) {
        output << "{" << "name" << descriptor.name << "dtype" << descriptor.dtype << "shape";
        write_shape(output, descriptor.shape);
        output << "}";
    }
    output << "]";
}

void write_result_json(
    const std::filesystem::path& path,
    const std::map<std::string, std::filesystem::path>& arguments,
    const edgeai::common::InferenceConfig& config,
    const edgeai::common::PreprocessResult& preprocess,
    const edgeai::backends::OrtDetector& detector,
    const edgeai::common::PostprocessResult& postprocess,
    const edgeai::common::StageTimingsMs& timings,
    const cv::Mat& source_image,
    const cv::Mat& output_image
) {
    if (!path.parent_path().empty()) {
        std::filesystem::create_directories(path.parent_path());
    }
    cv::FileStorage output(path.string(), cv::FileStorage::WRITE | cv::FileStorage::FORMAT_JSON);
    if (!output.isOpened()) {
        throw std::runtime_error("failed to open result JSON: " + path.string());
    }
    const auto& runtime = detector.runtime_info();
    output << "schema_version" << 1;
    output << "application" << "edgeai_cpp_ort_image";
    output << "model" << "{";
    output << "path" << arguments.at("--model").string();
    output << "sha256" << detector.model_sha256();
    output << "manifest_path" << arguments.at("--manifest").string();
    output << "manifest_sha256" << edgeai::backends::sha256_file(arguments.at("--manifest"));
    output << "runtime_version" << runtime.version;
    output << "execution_provider" << runtime.execution_provider;
    output << "threading" << "{"
           << "intra_op_threads" << runtime.intra_op_threads
           << "inter_op_threads" << runtime.inter_op_threads
           << "execution_mode" << "ORT_SEQUENTIAL"
           << "}";
    output << "runtime_inputs";
    write_descriptors(output, runtime.inputs);
    output << "runtime_outputs";
    write_descriptors(output, runtime.outputs);
    output << "}";

    output << "configuration_file" << "{"
           << "path" << arguments.at("--config").string()
           << "sha256" << edgeai::backends::sha256_file(arguments.at("--config"))
           << "}";
    output << "configuration" << "{"
           << "schema_version" << config.schema_version
           << "input_size" << "[" << config.input_size.height << config.input_size.width << "]"
           << "confidence_threshold" << config.confidence_threshold
           << "iou_threshold" << config.iou_threshold
           << "class_aware_nms" << config.class_aware_nms
           << "max_detections" << config.max_detections
           << "}";

    output << "source_image" << "{"
           << "path" << arguments.at("--image").string()
           << "sha256" << edgeai::backends::sha256_file(arguments.at("--image"))
           << "size_bytes" << static_cast<double>(std::filesystem::file_size(arguments.at("--image")))
           << "shape_bgr" << "[" << source_image.rows << source_image.cols << source_image.channels()
           << "]"
           << "}";

    const auto& metadata = preprocess.metadata;
    output << "preprocess" << "{";
    output << "original_size";
    write_size(output, metadata.original_size);
    output << "target_size";
    write_size(output, metadata.target_size);
    output << "resized_size";
    write_size(output, metadata.resized_size);
    output << "scale" << metadata.scale;
    output << "padding" << "{"
           << "left" << metadata.padding.left << "top" << metadata.padding.top
           << "right" << metadata.padding.right << "bottom" << metadata.padding.bottom << "}";
    output << "pad_color_bgr" << "[" << metadata.pad_color_bgr[0] << metadata.pad_color_bgr[1]
           << metadata.pad_color_bgr[2] << "]";
    output << "interpolation" << metadata.interpolation;
    output << "transforms" << "[";
    for (const auto& transform : metadata.transforms) {
        output << transform;
    }
    output << "]" << "}";

    output << "candidate_counts" << "{"
           << "raw_candidate_count" << static_cast<int>(postprocess.raw_candidate_count)
           << "threshold_candidate_count" << static_cast<int>(postprocess.threshold_candidate_count)
           << "nms_candidate_count" << static_cast<int>(postprocess.nms_candidate_count)
           << "invalid_box_count" << static_cast<int>(postprocess.invalid_box_count) << "}";
    output << "detections" << "[";
    for (const auto& detection : postprocess.detections) {
        output << "{"
               << "rank" << static_cast<int>(detection.rank)
               << "candidate_index" << static_cast<int>(detection.candidate_index)
               << "class_id" << detection.class_id
               << "class_name" << detection.class_name
               << "objectness" << detection.objectness
               << "class_score" << detection.class_score
               << "confidence" << detection.confidence
               << "box_xywh_input";
        write_box(output, detection.box_xywh_input);
        output << "box_xyxy_input";
        write_box(output, detection.box_xyxy_input);
        output << "box_xyxy_source";
        write_box(output, detection.box_xyxy_source);
        output << "}";
    }
    output << "]";

    output << "output_image" << "{"
           << "path" << arguments.at("--output-image").string()
           << "sha256" << edgeai::backends::sha256_file(arguments.at("--output-image"))
           << "size_bytes"
           << static_cast<double>(std::filesystem::file_size(arguments.at("--output-image")))
           << "shape_bgr" << "[" << output_image.rows << output_image.cols << output_image.channels()
           << "]"
           << "decode_validation" << "PASS"
           << "visual_review" << "PENDING_HUMAN_REVIEW"
           << "}";

    output << "timings_ms" << "{"
           << "measurement_type" << "single-run diagnostic, not a benchmark"
           << "clock" << "std::chrono::steady_clock"
           << "input_read" << timings.input_read
           << "preprocess" << timings.preprocess
           << "inference" << timings.inference
           << "postprocess" << timings.postprocess
           << "visualization" << timings.visualization
           << "output_write" << timings.output_write
           << "boundaries" << "{"
           << "input_read" << "cv::imread and input validation"
           << "preprocess" << "letterbox and RGB NCHW FP32 construction"
           << "inference" << "Ort::Session::Run only"
           << "postprocess" << "decode, threshold, class-aware NMS, inverse map, clipping"
           << "visualization" << "copy and draw labels/boxes"
           << "output_write" << "PNG encode, write, and read-back validation"
           << "}"
           << "}";
    output.release();
    if (!std::filesystem::is_regular_file(path) || std::filesystem::file_size(path) == 0U) {
        throw std::runtime_error("result JSON is missing or empty after write: " + path.string());
    }
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        const auto arguments = parse_args(argc, argv);
        std::cerr << "Stage: load configuration\n";
        const auto config = edgeai::common::load_config(arguments.at("--config"));
        edgeai::common::StageTimingsMs timings;

        std::cerr << "Stage: load image\n";
        const auto read_start = Clock::now();
        const cv::Mat source_image = edgeai::common::load_bgr_image(arguments.at("--image"));
        const auto read_end = Clock::now();
        timings.input_read = elapsed_ms(read_start, read_end);

        std::cerr << "Stage: preprocess\n";
        const auto preprocess_start = Clock::now();
        const auto preprocessed = edgeai::common::preprocess_image(source_image, config);
        const auto preprocess_end = Clock::now();
        timings.preprocess = elapsed_ms(preprocess_start, preprocess_end);

        std::cerr << "Stage: initialize ONNX Runtime session\n";
        edgeai::backends::OrtDetector detector(
            arguments.at("--model"), arguments.at("--manifest"), 1, 1
        );
        std::cerr << "Stage: inference\n";
        const auto inference_start = Clock::now();
        const auto raw_output = detector.infer(preprocessed.tensor);
        const auto inference_end = Clock::now();
        timings.inference = elapsed_ms(inference_start, inference_end);

        std::cerr << "Stage: postprocess\n";
        const auto postprocess_start = Clock::now();
        const auto postprocessed = edgeai::common::decode_yolov5_output(
            raw_output.values,
            raw_output.shape,
            config.class_names,
            preprocessed.metadata,
            config
        );
        const auto postprocess_end = Clock::now();
        timings.postprocess = elapsed_ms(postprocess_start, postprocess_end);

        std::cerr << "Stage: visualization\n";
        const auto visualization_start = Clock::now();
        const cv::Mat rendered =
            edgeai::common::draw_detections(source_image, postprocessed.detections);
        const auto visualization_end = Clock::now();
        timings.visualization = elapsed_ms(visualization_start, visualization_end);

        std::cerr << "Stage: output image write and read-back\n";
        const auto write_start = Clock::now();
        edgeai::common::save_image(arguments.at("--output-image"), rendered);
        const cv::Mat read_back =
            cv::imread(arguments.at("--output-image").string(), cv::IMREAD_COLOR);
        if (read_back.empty() || read_back.size() != source_image.size() ||
            read_back.type() != CV_8UC3) {
            throw std::runtime_error("output image read-back validation failed");
        }
        const auto write_end = Clock::now();
        timings.output_write = elapsed_ms(write_start, write_end);

        std::cerr << "Stage: result JSON write\n";
        write_result_json(
            arguments.at("--output-json"),
            arguments,
            config,
            preprocessed,
            detector,
            postprocessed,
            timings,
            source_image,
            read_back
        );

        const auto& runtime = detector.runtime_info();
        std::cout << "Application: edgeai_cpp_ort_image\n"
                  << "ONNX Runtime version: " << runtime.version << '\n'
                  << "Execution provider: " << runtime.execution_provider << '\n'
                  << "Threads: intra_op=" << runtime.intra_op_threads
                  << " inter_op=" << runtime.inter_op_threads << '\n'
                  << "Model SHA256: " << detector.model_sha256() << '\n';
        for (const auto& input : runtime.inputs) {
            std::cout << "Input: name=" << input.name << " dtype=" << input.dtype << " shape=[";
            for (std::size_t index = 0; index < input.shape.size(); ++index) {
                std::cout << (index == 0U ? "" : ", ") << input.shape[index];
            }
            std::cout << "]\n";
        }
        for (const auto& output : runtime.outputs) {
            std::cout << "Output: name=" << output.name << " dtype=" << output.dtype << " shape=[";
            for (std::size_t index = 0; index < output.shape.size(); ++index) {
                std::cout << (index == 0U ? "" : ", ") << output.shape[index];
            }
            std::cout << "]\n";
        }
        for (const auto& detection : postprocessed.detections) {
            std::cout << "Detection " << detection.rank << ": class=" << detection.class_name
                      << " class_id=" << detection.class_id << " confidence=" << std::fixed
                      << std::setprecision(6) << detection.confidence << " box=["
                      << detection.box_xyxy_source.x1 << ", " << detection.box_xyxy_source.y1
                      << ", " << detection.box_xyxy_source.x2 << ", "
                      << detection.box_xyxy_source.y2 << "]\n";
        }
        std::cout << "Diagnostic timings only; not a benchmark: input_read=" << timings.input_read
                  << " preprocess=" << timings.preprocess << " inference=" << timings.inference
                  << " postprocess=" << timings.postprocess
                  << " visualization=" << timings.visualization
                  << " output_write=" << timings.output_write << " ms\n"
                  << "Output image: " << arguments.at("--output-image") << '\n'
                  << "Output JSON: " << arguments.at("--output-json") << '\n'
                  << "Visual review: PENDING_HUMAN_REVIEW\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "edgeai_ort_image error: " << error.what() << '\n';
        return 1;
    }
}
