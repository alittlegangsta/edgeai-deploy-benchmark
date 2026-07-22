#include "edgeai/backends/ncnn_detector.hpp"
#include "edgeai/common/config.hpp"
#include "edgeai/common/postprocess.hpp"
#include "edgeai/common/preprocess.hpp"
#include "edgeai/common/video_pipeline.hpp"
#include "edgeai/common/visualize.hpp"

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <opencv2/core/persistence.hpp>
#include <opencv2/videoio.hpp>

namespace {

using Clock = std::chrono::steady_clock;

struct FrameRecord {
    edgeai::common::VideoFrameTimingsMs timings;
    edgeai::common::PostprocessResult postprocess;
};

struct SetupTimingsMs {
    double config_load{0.0};
    double video_open{0.0};
    double model_load{0.0};
    double writer_open{0.0};
    double writer_close{0.0};
    double output_verification{0.0};
};

struct FrameCounts {
    std::size_t decoded{0};
    std::size_t processed{0};
    std::size_t failed{0};
    std::size_t written{0};
};

double elapsed_ms(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

std::map<std::string, std::filesystem::path> parse_args(int argc, char* argv[]) {
    if (argc != 11) {
        throw std::runtime_error(
            "usage: edgeai_ncnn_video --manifest PATH --config PATH --input PATH "
            "--output PATH --output-json PATH"
        );
    }
    const std::vector<std::string> allowed{
        "--manifest", "--config", "--input", "--output", "--output-json",
    };
    std::map<std::string, std::filesystem::path> arguments;
    for (int index = 1; index < argc; index += 2) {
        const std::string option = argv[index];
        if (std::find(allowed.begin(), allowed.end(), option) == allowed.end()) {
            throw std::runtime_error("unknown argument: " + option);
        }
        if (!arguments.emplace(option, argv[index + 1]).second) {
            throw std::runtime_error("duplicate argument: " + option);
        }
    }
    if (arguments.size() != allowed.size()) {
        throw std::runtime_error("all five named arguments are required");
    }
    return arguments;
}

void create_parent_directory(const std::filesystem::path& path) {
    if (!path.parent_path().empty()) {
        std::filesystem::create_directories(path.parent_path());
    }
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

void write_timings(
    cv::FileStorage& output,
    const edgeai::common::VideoFrameTimingsMs& timings
) {
    output << "{" << "video_read" << timings.video_read << "preprocess"
           << timings.preprocess << "inference" << timings.inference << "postprocess"
           << timings.postprocess << "visualization" << timings.visualization << "video_write"
           << timings.video_write << "pipeline_total" << timings.pipeline_total << "}";
}

void write_totals(
    cv::FileStorage& output,
    const edgeai::common::VideoTimingTotalsMs& timings
) {
    output << "{" << "video_read" << timings.video_read << "preprocess"
           << timings.preprocess << "inference" << timings.inference << "postprocess"
           << timings.postprocess << "visualization" << timings.visualization << "video_write"
           << timings.video_write << "pipeline_total" << timings.pipeline_total << "}";
}

edgeai::common::VideoTimingTotalsMs mean_timings(
    const edgeai::common::VideoTimingTotalsMs& totals,
    std::size_t count
) {
    if (count == 0U) {
        throw std::runtime_error("cannot compute video means for zero frames");
    }
    const double divisor = static_cast<double>(count);
    return {
        totals.video_read / divisor,
        totals.preprocess / divisor,
        totals.inference / divisor,
        totals.postprocess / divisor,
        totals.visualization / divisor,
        totals.video_write / divisor,
        totals.pipeline_total / divisor,
    };
}

void write_box(cv::FileStorage& output, const edgeai::common::Box& box) {
    output << "[" << box.x1 << box.y1 << box.x2 << box.y2 << "]";
}

void write_detection(cv::FileStorage& output, const edgeai::common::Detection& detection) {
    output << "{" << "rank" << static_cast<int>(detection.rank) << "candidate_index"
           << static_cast<int>(detection.candidate_index) << "class_id" << detection.class_id
           << "class_name" << detection.class_name << "objectness" << detection.objectness
           << "class_score" << detection.class_score << "confidence" << detection.confidence
           << "box_xyxy_source";
    write_box(output, detection.box_xyxy_source);
    output << "}";
}

void write_result(
    const std::filesystem::path& path,
    const std::map<std::string, std::filesystem::path>& arguments,
    const edgeai::common::InferenceConfig& config,
    const edgeai::backends::NcnnDetector& detector,
    const edgeai::common::VideoMetadata& input_metadata,
    const std::string& writer_backend,
    const FrameCounts& counts,
    const std::vector<FrameRecord>& records,
    const SetupTimingsMs& setup,
    double loop_total_ms,
    const edgeai::common::VideoVerificationResult& verification
) {
    create_parent_directory(path);
    cv::FileStorage output(path.string(), cv::FileStorage::WRITE | cv::FileStorage::FORMAT_JSON);
    if (!output.isOpened()) {
        throw std::runtime_error("failed to open ncnn video result JSON: " + path.string());
    }
    std::vector<edgeai::common::VideoFrameTimingsMs> frame_timings;
    frame_timings.reserve(records.size());
    for (const FrameRecord& record : records) {
        frame_timings.push_back(record.timings);
    }
    const auto totals = edgeai::common::sum_video_timings(frame_timings);
    const auto means = mean_timings(totals, records.size());
    const auto& runtime = detector.runtime_info();

    output << "schema_version" << 1 << "application" << "edgeai_cpp_ncnn_video";
    output << "measurement_classification"
           << "single-run video functional diagnostic, not a benchmark";
    output << "model" << "{" << "manifest_path" << arguments.at("--manifest").string()
           << "manifest_sha256"
           << edgeai::backends::ncnn_sha256_file(arguments.at("--manifest")) << "param_path"
           << detector.param_path().string() << "param_sha256" << detector.param_sha256()
           << "bin_path" << detector.bin_path().string() << "bin_sha256"
           << detector.bin_sha256() << "runtime_version" << runtime.version
           << "execution_provider" << runtime.execution_provider << "threads"
           << runtime.threads << "vulkan" << runtime.vulkan << "fp16" << runtime.fp16
           << "bf16" << runtime.bf16 << "int8" << runtime.int8 << "input_blob"
           << runtime.inputs.at(0).name << "output_blob" << runtime.outputs.at(0).name << "}";
    output << "configuration" << "{" << "path" << arguments.at("--config").string()
           << "sha256" << edgeai::backends::ncnn_sha256_file(arguments.at("--config"))
           << "input_width" << config.input_size.width << "input_height"
           << config.input_size.height << "confidence_threshold" << config.confidence_threshold
           << "iou_threshold" << config.iou_threshold << "class_aware_nms"
           << config.class_aware_nms << "max_detections" << config.max_detections << "}";
    output << "input_video" << "{" << "path" << arguments.at("--input").string()
           << "sha256" << edgeai::backends::ncnn_sha256_file(arguments.at("--input"))
           << "size_bytes"
           << static_cast<double>(std::filesystem::file_size(arguments.at("--input")))
           << "metadata";
    write_video_metadata(output, input_metadata);
    output << "}";
    output << "output_video" << "{" << "path" << arguments.at("--output").string()
           << "sha256" << edgeai::backends::ncnn_sha256_file(arguments.at("--output"))
           << "size_bytes"
           << static_cast<double>(std::filesystem::file_size(arguments.at("--output")))
           << "requested_fourcc" << "avc1" << "writer_backend" << writer_backend
           << "reopened_metadata";
    write_video_metadata(output, verification.metadata);
    output << "}";
    output << "counts" << "{" << "reported_input_frames"
           << static_cast<int>(input_metadata.reported_frame_count) << "decoded_frames"
           << static_cast<int>(counts.decoded) << "processed_frames"
           << static_cast<int>(counts.processed) << "failed_frames"
           << static_cast<int>(counts.failed) << "written_frames"
           << static_cast<int>(counts.written) << "verified_output_frames"
           << static_cast<int>(verification.decoded_frame_count) << "}";
    output << "timing_boundaries" << "{" << "video_read"
           << "one successful cv::VideoCapture::read call" << "preprocess"
           << "shared letterbox and RGB NCHW FP32 construction" << "inference"
           << "NcnnDetector::infer input bind, Extractor::extract, validation and copy"
           << "postprocess"
           << "shared YOLOv5 decode, threshold, NMS, inverse map and clipping"
           << "visualization" << "shared labels and boxes" << "video_write"
           << "one cv::VideoWriter::write call; close/flush is separate" << "pipeline_total"
           << "preprocess + inference + postprocess; excludes read, visualization and write"
           << "container_fps_note"
           << "30 FPS is output container playback metadata, not actual processing FPS" << "}";
    output << "setup_timings_ms" << "{" << "config_load" << setup.config_load
           << "video_open" << setup.video_open << "model_load" << setup.model_load
           << "writer_open" << setup.writer_open << "writer_close" << setup.writer_close
           << "output_verification" << setup.output_verification << "}";
    output << "aggregate_timings_ms" << "{" << "sum";
    write_totals(output, totals);
    output << "mean_per_frame";
    write_totals(output, means);
    output << "loop_total" << loop_total_ms << "}";
    output << "frames" << "[";
    for (const FrameRecord& record : records) {
        output << "{" << "frame_index" << static_cast<int>(record.timings.frame_index)
               << "timings_ms";
        write_timings(output, record.timings);
        output << "candidate_counts" << "{" << "raw"
               << static_cast<int>(record.postprocess.raw_candidate_count) << "threshold"
               << static_cast<int>(record.postprocess.threshold_candidate_count) << "nms"
               << static_cast<int>(record.postprocess.nms_candidate_count) << "invalid_boxes"
               << static_cast<int>(record.postprocess.invalid_box_count) << "}" << "detections"
               << "[";
        for (const auto& detection : record.postprocess.detections) {
            write_detection(output, detection);
        }
        output << "]" << "}";
    }
    output << "]";
    output << "output_decode_verification" << "{" << "status" << "PASS"
           << "decoded_frame_count" << static_cast<int>(verification.decoded_frame_count)
           << "visual_review" << "PENDING_HUMAN_REVIEW" << "}";
    output.release();
    if (!std::filesystem::is_regular_file(path) || std::filesystem::file_size(path) == 0U) {
        throw std::runtime_error("ncnn video result JSON is missing or empty");
    }
}

int run(int argc, char* argv[]) {
    const auto arguments = parse_args(argc, argv);
    if (std::filesystem::absolute(arguments.at("--input")).lexically_normal() ==
        std::filesystem::absolute(arguments.at("--output")).lexically_normal()) {
        throw std::runtime_error("input and output video paths must differ");
    }
    create_parent_directory(arguments.at("--output"));
    create_parent_directory(arguments.at("--output-json"));

    SetupTimingsMs setup;
    const auto config_start = Clock::now();
    const auto config = edgeai::common::load_config(arguments.at("--config"));
    setup.config_load = elapsed_ms(config_start, Clock::now());
    const auto open_start = Clock::now();
    cv::VideoCapture capture(arguments.at("--input").string());
    if (!capture.isOpened()) {
        throw std::runtime_error("failed to open input video");
    }
    const auto input_metadata = edgeai::common::read_video_metadata(capture);
    edgeai::common::validate_video_metadata(input_metadata);
    setup.video_open = elapsed_ms(open_start, Clock::now());

    const auto model_start = Clock::now();
    edgeai::backends::NcnnDetector detector(arguments.at("--manifest"), 1);
    setup.model_load = elapsed_ms(model_start, Clock::now());
    const auto writer_start = Clock::now();
    cv::VideoWriter writer(
        arguments.at("--output").string(),
        cv::VideoWriter::fourcc('a', 'v', 'c', '1'),
        input_metadata.fps,
        cv::Size(input_metadata.width, input_metadata.height),
        true
    );
    if (!writer.isOpened()) {
        throw std::runtime_error("failed to open avc1 output video writer");
    }
    const std::string writer_backend = writer.getBackendName();
    setup.writer_open = elapsed_ms(writer_start, Clock::now());

    FrameCounts counts;
    std::vector<FrameRecord> records;
    records.reserve(static_cast<std::size_t>(input_metadata.reported_frame_count));
    const auto loop_start = Clock::now();
    while (true) {
        edgeai::common::VideoFrameTimingsMs timings;
        timings.frame_index = counts.decoded;
        cv::Mat frame;
        const auto read_start = Clock::now();
        const bool read_ok = capture.read(frame);
        const auto read_end = Clock::now();
        if (!read_ok) {
            if (counts.decoded < static_cast<std::size_t>(input_metadata.reported_frame_count)) {
                ++counts.failed;
                throw std::runtime_error("video ended before reported frame count");
            }
            break;
        }
        timings.video_read = elapsed_ms(read_start, read_end);
        ++counts.decoded;
        try {
            edgeai::common::validate_video_frame(
                frame, input_metadata.width, input_metadata.height, timings.frame_index
            );
            const auto preprocess_start = Clock::now();
            const auto preprocessed = edgeai::common::preprocess_image(frame, config);
            const auto preprocess_end = Clock::now();
            timings.preprocess = elapsed_ms(preprocess_start, preprocess_end);
            const auto inference_start = Clock::now();
            const auto raw = detector.infer(preprocessed.tensor);
            const auto inference_end = Clock::now();
            timings.inference = elapsed_ms(inference_start, inference_end);
            const auto postprocess_start = Clock::now();
            auto postprocessed = edgeai::common::decode_yolov5_output(
                raw.values, raw.shape, config.class_names, preprocessed.metadata, config
            );
            const auto postprocess_end = Clock::now();
            timings.postprocess = elapsed_ms(postprocess_start, postprocess_end);
            timings.pipeline_total =
                timings.preprocess + timings.inference + timings.postprocess;
            edgeai::common::validate_frame_detections(
                postprocessed.detections,
                input_metadata.width,
                input_metadata.height,
                timings.frame_index
            );
            const auto visualization_start = Clock::now();
            const cv::Mat rendered =
                edgeai::common::draw_detections(frame, postprocessed.detections);
            timings.visualization = elapsed_ms(visualization_start, Clock::now());
            const auto write_start = Clock::now();
            writer.write(rendered);
            timings.video_write = elapsed_ms(write_start, Clock::now());
            ++counts.processed;
            ++counts.written;
            records.push_back({timings, std::move(postprocessed)});
        } catch (...) {
            ++counts.failed;
            throw;
        }
    }
    const double loop_total_ms = elapsed_ms(loop_start, Clock::now());
    capture.release();
    if (counts.decoded != static_cast<std::size_t>(input_metadata.reported_frame_count) ||
        counts.processed != counts.decoded || counts.written != counts.decoded ||
        counts.failed != 0U) {
        throw std::runtime_error("decoded, processed, written, and reported counts differ");
    }
    const auto close_start = Clock::now();
    writer.release();
    setup.writer_close = elapsed_ms(close_start, Clock::now());
    const auto verification_start = Clock::now();
    const auto verification = edgeai::common::verify_video_file(
        arguments.at("--output"),
        input_metadata.width,
        input_metadata.height,
        input_metadata.fps,
        counts.written
    );
    setup.output_verification = elapsed_ms(verification_start, Clock::now());
    write_result(
        arguments.at("--output-json"), arguments, config, detector, input_metadata,
        writer_backend, counts, records, setup, loop_total_ms, verification
    );
    std::vector<edgeai::common::VideoFrameTimingsMs> timings;
    timings.reserve(records.size());
    for (const auto& record : records) {
        timings.push_back(record.timings);
    }
    const auto totals = edgeai::common::sum_video_timings(timings);
    std::cout << "Application: edgeai_cpp_ncnn_video\n"
              << "ncnn version: " << detector.runtime_info().version << '\n'
              << "Execution provider: ncnn CPU\nThreads: 1\n"
              << "Counts: decoded=" << counts.decoded << " processed=" << counts.processed
              << " failed=" << counts.failed << " written=" << counts.written
              << " verified=" << verification.decoded_frame_count << '\n'
              << std::fixed << std::setprecision(3)
              << "Diagnostic timing sums only; not a benchmark (ms): read="
              << totals.video_read << " preprocess=" << totals.preprocess
              << " inference=" << totals.inference << " postprocess=" << totals.postprocess
              << " visualization=" << totals.visualization << " write="
              << totals.video_write << " pipeline_total=" << totals.pipeline_total << '\n'
              << "Pipeline total excludes read, visualization, and write.\n"
              << "30 FPS is container metadata, not actual processing FPS.\n"
              << "Visual review: PENDING_HUMAN_REVIEW\n";
    return 0;
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        return run(argc, argv);
    } catch (const std::exception& error) {
        std::cerr << "edgeai_ncnn_video error: " << error.what() << '\n';
        return 1;
    }
}
