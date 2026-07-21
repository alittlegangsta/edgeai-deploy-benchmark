#include "edgeai/backends/ort_detector.hpp"
#include "edgeai/common/config.hpp"
#include "edgeai/common/postprocess.hpp"
#include "edgeai/common/preprocess.hpp"
#include "edgeai/common/video_pipeline.hpp"
#include "edgeai/common/visualize.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
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
    double session_create{0.0};
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

struct NormalArguments {
    std::map<std::string, std::filesystem::path> values;
};

struct VerificationArguments {
    std::filesystem::path video;
    std::filesystem::path metadata;
};

double elapsed_ms(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

NormalArguments parse_normal_args(int argc, char* argv[]) {
    if (argc != 13) {
        throw std::runtime_error(
            "usage: edgeai_ort_video --model PATH --manifest PATH --config PATH "
            "--input PATH --output PATH --output-json PATH"
        );
    }
    const std::vector<std::string> allowed{
        "--model", "--manifest", "--config", "--input", "--output", "--output-json",
    };
    NormalArguments arguments;
    for (int index = 1; index < argc; index += 2) {
        const std::string option = argv[index];
        if (std::find(allowed.begin(), allowed.end(), option) == allowed.end()) {
            throw std::runtime_error("unknown argument: " + option);
        }
        if (!arguments.values.emplace(option, argv[index + 1]).second) {
            throw std::runtime_error("duplicate argument: " + option);
        }
    }
    if (arguments.values.size() != allowed.size()) {
        throw std::runtime_error("all six named arguments are required");
    }
    return arguments;
}

VerificationArguments parse_verification_args(int argc, char* argv[]) {
    if (argc != 5 || std::string(argv[1]) != "--verify-output" ||
        std::string(argv[3]) != "--expected-metadata") {
        throw std::runtime_error(
            "usage: edgeai_ort_video --verify-output PATH --expected-metadata PATH"
        );
    }
    return {argv[2], argv[4]};
}

void create_parent_directory(const std::filesystem::path& path) {
    if (!path.parent_path().empty()) {
        std::filesystem::create_directories(path.parent_path());
    }
}

void write_box(cv::FileStorage& output, const edgeai::common::Box& box) {
    output << "[" << box.x1 << box.y1 << box.x2 << box.y2 << "]";
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
    output << "{"
           << "video_read" << timings.video_read << "preprocess" << timings.preprocess
           << "inference" << timings.inference << "postprocess" << timings.postprocess
           << "visualization" << timings.visualization << "video_write"
           << timings.video_write << "pipeline_total" << timings.pipeline_total << "}";
}

void write_timing_totals(
    cv::FileStorage& output,
    const edgeai::common::VideoTimingTotalsMs& timings
) {
    output << "{"
           << "video_read" << timings.video_read << "preprocess" << timings.preprocess
           << "inference" << timings.inference << "postprocess" << timings.postprocess
           << "visualization" << timings.visualization << "video_write"
           << timings.video_write << "pipeline_total" << timings.pipeline_total << "}";
}

edgeai::common::VideoTimingTotalsMs mean_timings(
    const edgeai::common::VideoTimingTotalsMs& totals,
    std::size_t frame_count
) {
    if (frame_count == 0U) {
        throw std::runtime_error("cannot compute video timing means for zero frames");
    }
    const double divisor = static_cast<double>(frame_count);
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

void write_detection(cv::FileStorage& output, const edgeai::common::Detection& detection) {
    output << "{"
           << "rank" << static_cast<int>(detection.rank) << "candidate_index"
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

void write_result_json(
    const std::filesystem::path& path,
    const NormalArguments& arguments,
    const edgeai::common::InferenceConfig& config,
    const edgeai::backends::OrtDetector& detector,
    const edgeai::common::VideoMetadata& input_metadata,
    const std::string& writer_backend,
    const FrameCounts& counts,
    const std::vector<FrameRecord>& frame_records,
    const SetupTimingsMs& setup_timings,
    double loop_total_ms,
    const edgeai::common::VideoVerificationResult& verification
) {
    create_parent_directory(path);
    cv::FileStorage output(path.string(), cv::FileStorage::WRITE | cv::FileStorage::FORMAT_JSON);
    if (!output.isOpened()) {
        throw std::runtime_error("failed to open video result JSON: " + path.string());
    }
    const auto& values = arguments.values;
    const auto& runtime = detector.runtime_info();
    std::vector<edgeai::common::VideoFrameTimingsMs> frame_timings;
    frame_timings.reserve(frame_records.size());
    for (const FrameRecord& record : frame_records) {
        frame_timings.push_back(record.timings);
    }
    const auto timing_totals = edgeai::common::sum_video_timings(frame_timings);
    const auto timing_means = mean_timings(timing_totals, frame_records.size());

    output << "schema_version" << 1;
    output << "application" << "edgeai_cpp_ort_video";
    output << "measurement_classification" << "single-run video functional diagnostic, not a benchmark";
    output << "model" << "{"
           << "path" << values.at("--model").string() << "sha256" << detector.model_sha256()
           << "manifest_path" << values.at("--manifest").string() << "manifest_sha256"
           << edgeai::backends::sha256_file(values.at("--manifest")) << "runtime_version"
           << runtime.version << "execution_provider" << runtime.execution_provider
           << "intra_op_threads" << runtime.intra_op_threads << "inter_op_threads"
           << runtime.inter_op_threads << "execution_mode" << "ORT_SEQUENTIAL" << "}";
    output << "configuration" << "{"
           << "path" << values.at("--config").string() << "sha256"
           << edgeai::backends::sha256_file(values.at("--config")) << "input_width"
           << config.input_size.width << "input_height" << config.input_size.height
           << "confidence_threshold" << config.confidence_threshold << "iou_threshold"
           << config.iou_threshold << "class_aware_nms" << config.class_aware_nms
           << "max_detections" << config.max_detections << "}";
    output << "input_video" << "{"
           << "path" << values.at("--input").string() << "sha256"
           << edgeai::backends::sha256_file(values.at("--input")) << "size_bytes"
           << static_cast<double>(std::filesystem::file_size(values.at("--input")))
           << "metadata";
    write_video_metadata(output, input_metadata);
    output << "}";
    output << "output_video" << "{"
           << "path" << values.at("--output").string() << "sha256"
           << edgeai::backends::sha256_file(values.at("--output")) << "size_bytes"
           << static_cast<double>(std::filesystem::file_size(values.at("--output")))
           << "requested_fourcc" << "avc1" << "codec_policy"
           << "H.264 in MP4 requested through avc1; no fallback permitted"
           << "writer_backend" << writer_backend << "reopened_metadata";
    write_video_metadata(output, verification.metadata);
    output << "}";

    output << "counts" << "{"
           << "reported_input_frames" << static_cast<int>(input_metadata.reported_frame_count)
           << "decoded_frames" << static_cast<int>(counts.decoded) << "processed_frames"
           << static_cast<int>(counts.processed) << "failed_frames"
           << static_cast<int>(counts.failed) << "written_frames"
           << static_cast<int>(counts.written) << "verified_output_frames"
           << static_cast<int>(verification.decoded_frame_count) << "}";

    output << "timing_boundaries" << "{"
           << "clock" << "std::chrono::steady_clock"
           << "video_read" << "one successful cv::VideoCapture::read call"
           << "preprocess" << "letterbox and RGB NCHW FP32 construction"
           << "inference"
           << "OrtDetector::infer including tensor wrapper, Session::Run, output validation and copy"
           << "postprocess" << "YOLOv5 decode, threshold, class-aware NMS, inverse map and clipping"
           << "visualization" << "copy source frame and draw labels/boxes"
           << "video_write" << "one cv::VideoWriter::write call; writer close/flush is separate"
           << "pipeline_total"
           << "preprocess start through postprocess end; excludes read, visualization and write"
           << "loop_total"
           << "first read start through end-of-stream read; includes all frame stages and loop overhead"
           << "}";
    output << "setup_timings_ms" << "{"
           << "config_load" << setup_timings.config_load << "video_open"
           << setup_timings.video_open << "session_create" << setup_timings.session_create
           << "writer_open" << setup_timings.writer_open << "writer_close"
           << setup_timings.writer_close << "output_verification"
           << setup_timings.output_verification << "}";
    output << "aggregate_timings_ms" << "{" << "sum";
    write_timing_totals(output, timing_totals);
    output << "mean_per_frame";
    write_timing_totals(output, timing_means);
    output << "loop_total" << loop_total_ms << "}";

    output << "frames" << "[";
    for (const FrameRecord& record : frame_records) {
        output << "{" << "frame_index" << static_cast<int>(record.timings.frame_index)
               << "timings_ms";
        write_timings(output, record.timings);
        output << "candidate_counts" << "{"
               << "raw" << static_cast<int>(record.postprocess.raw_candidate_count)
               << "threshold" << static_cast<int>(record.postprocess.threshold_candidate_count)
               << "nms" << static_cast<int>(record.postprocess.nms_candidate_count)
               << "invalid_boxes" << static_cast<int>(record.postprocess.invalid_box_count) << "}"
               << "detections" << "[";
        for (const auto& detection : record.postprocess.detections) {
            write_detection(output, detection);
        }
        output << "]" << "}";
    }
    output << "]";

    output << "output_decode_verification" << "{"
           << "status" << "PASS" << "decoded_frame_count"
           << static_cast<int>(verification.decoded_frame_count) << "sampled_frames" << "[";
    for (const auto& sample : verification.samples) {
        output << "{" << "frame_index" << static_cast<int>(sample.frame_index) << "mean_bgr"
               << "[" << sample.mean_bgr[0] << sample.mean_bgr[1] << sample.mean_bgr[2] << "]"
               << "}";
    }
    output << "]" << "visual_review" << "PENDING_HUMAN_REVIEW" << "}";
    output.release();
    if (!std::filesystem::is_regular_file(path) || std::filesystem::file_size(path) == 0U) {
        throw std::runtime_error("video result JSON is missing or empty after write: " + path.string());
    }
}

int verify_output(const VerificationArguments& arguments) {
    cv::FileStorage storage(
        arguments.metadata.string(), cv::FileStorage::READ | cv::FileStorage::FORMAT_JSON
    );
    if (!storage.isOpened()) {
        throw std::runtime_error("failed to open expected video metadata JSON");
    }
    const cv::FileNode output_video = storage["output_video"];
    const cv::FileNode reopened = output_video["reopened_metadata"];
    const cv::FileNode counts = storage["counts"];
    const cv::FileNode sha256 = output_video["sha256"];
    if (!reopened["width"].isInt() || !reopened["height"].isInt() ||
        !reopened["fps"].isReal() || !counts["written_frames"].isInt() ||
        !sha256.isString()) {
        throw std::runtime_error("expected video metadata JSON is incomplete");
    }
    const int width = static_cast<int>(reopened["width"]);
    const int height = static_cast<int>(reopened["height"]);
    const double fps = static_cast<double>(reopened["fps"]);
    const auto frame_count = static_cast<std::size_t>(static_cast<int>(counts["written_frames"]));
    const auto verification = edgeai::common::verify_video_file(
        arguments.video, width, height, fps, frame_count
    );
    const std::string expected_sha = static_cast<std::string>(sha256);
    const std::string actual_sha = edgeai::backends::sha256_file(arguments.video);
    if (actual_sha != expected_sha) {
        throw std::runtime_error("output video SHA256 differs from expected metadata");
    }
    std::cout << "Output verification: PASS\n"
              << "Decoded frames: " << verification.decoded_frame_count << '\n'
              << "Dimensions: " << verification.metadata.width << 'x'
              << verification.metadata.height << '\n'
              << "FPS: " << verification.metadata.fps << '\n'
              << "FourCC: " << verification.metadata.fourcc << '\n'
              << "SHA256: " << actual_sha << '\n';
    for (const auto& sample : verification.samples) {
        std::cout << "Sample frame " << sample.frame_index << " mean BGR: ["
                  << sample.mean_bgr[0] << ", " << sample.mean_bgr[1] << ", "
                  << sample.mean_bgr[2] << "]\n";
    }
    return 0;
}

int run_video(const NormalArguments& arguments) {
    const auto& values = arguments.values;
    if (std::filesystem::absolute(values.at("--input")).lexically_normal() ==
        std::filesystem::absolute(values.at("--output")).lexically_normal()) {
        throw std::runtime_error("input and output video paths must differ");
    }
    create_parent_directory(values.at("--output"));
    create_parent_directory(values.at("--output-json"));

    SetupTimingsMs setup_timings;
    const auto config_start = Clock::now();
    const auto config = edgeai::common::load_config(values.at("--config"));
    setup_timings.config_load = elapsed_ms(config_start, Clock::now());

    const auto open_start = Clock::now();
    cv::VideoCapture capture(values.at("--input").string());
    if (!capture.isOpened()) {
        throw std::runtime_error("failed to open input video: " + values.at("--input").string());
    }
    const auto input_metadata = edgeai::common::read_video_metadata(capture);
    setup_timings.video_open = elapsed_ms(open_start, Clock::now());

    const auto session_start = Clock::now();
    edgeai::backends::OrtDetector detector(
        values.at("--model"), values.at("--manifest"), 1, 1
    );
    setup_timings.session_create = elapsed_ms(session_start, Clock::now());

    constexpr char codec[] = "avc1";
    const int fourcc = cv::VideoWriter::fourcc(codec[0], codec[1], codec[2], codec[3]);
    const auto writer_start = Clock::now();
    cv::VideoWriter writer;
    writer.open(
        values.at("--output").string(),
        cv::CAP_FFMPEG,
        fourcc,
        input_metadata.fps,
        cv::Size(input_metadata.width, input_metadata.height),
        true
    );
    if (!writer.isOpened()) {
        throw std::runtime_error("failed to open H.264/avc1 MP4 output writer; no fallback used");
    }
    const std::string writer_backend = writer.getBackendName();
    setup_timings.writer_open = elapsed_ms(writer_start, Clock::now());

    FrameCounts counts;
    std::vector<FrameRecord> frame_records;
    frame_records.reserve(static_cast<std::size_t>(input_metadata.reported_frame_count));
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
                throw std::runtime_error(
                    "input video decode stopped before the reported frame count at index " +
                    std::to_string(counts.decoded)
                );
            }
            break;
        }
        timings.video_read = elapsed_ms(read_start, read_end);
        ++counts.decoded;
        try {
            edgeai::common::validate_video_frame(
                frame, input_metadata.width, input_metadata.height, timings.frame_index
            );
            const auto pipeline_start = Clock::now();
            const auto preprocess_start = Clock::now();
            const auto preprocessed = edgeai::common::preprocess_image(frame, config);
            const auto preprocess_end = Clock::now();
            timings.preprocess = elapsed_ms(preprocess_start, preprocess_end);

            const auto inference_start = Clock::now();
            const auto raw_output = detector.infer(preprocessed.tensor);
            const auto inference_end = Clock::now();
            timings.inference = elapsed_ms(inference_start, inference_end);

            const auto postprocess_start = Clock::now();
            auto postprocessed = edgeai::common::decode_yolov5_output(
                raw_output.values,
                raw_output.shape,
                config.class_names,
                preprocessed.metadata,
                config
            );
            const auto postprocess_end = Clock::now();
            timings.postprocess = elapsed_ms(postprocess_start, postprocess_end);
            timings.pipeline_total = elapsed_ms(pipeline_start, postprocess_end);
            edgeai::common::validate_frame_detections(
                postprocessed.detections,
                input_metadata.width,
                input_metadata.height,
                timings.frame_index
            );

            const auto visualization_start = Clock::now();
            const cv::Mat rendered =
                edgeai::common::draw_detections(frame, postprocessed.detections);
            const auto visualization_end = Clock::now();
            timings.visualization = elapsed_ms(visualization_start, visualization_end);

            const auto write_start = Clock::now();
            writer.write(rendered);
            const auto write_end = Clock::now();
            timings.video_write = elapsed_ms(write_start, write_end);
            ++counts.processed;
            ++counts.written;
            frame_records.push_back({timings, std::move(postprocessed)});
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
        throw std::runtime_error("input decoded/processed/written frame counts do not agree");
    }

    const auto writer_close_start = Clock::now();
    writer.release();
    setup_timings.writer_close = elapsed_ms(writer_close_start, Clock::now());
    const auto verification_start = Clock::now();
    const auto verification = edgeai::common::verify_video_file(
        values.at("--output"),
        input_metadata.width,
        input_metadata.height,
        input_metadata.fps,
        counts.written
    );
    setup_timings.output_verification = elapsed_ms(verification_start, Clock::now());

    write_result_json(
        values.at("--output-json"),
        arguments,
        config,
        detector,
        input_metadata,
        writer_backend,
        counts,
        frame_records,
        setup_timings,
        loop_total_ms,
        verification
    );
    const auto totals = edgeai::common::sum_video_timings([&frame_records] {
        std::vector<edgeai::common::VideoFrameTimingsMs> values;
        values.reserve(frame_records.size());
        for (const FrameRecord& record : frame_records) {
            values.push_back(record.timings);
        }
        return values;
    }());
    std::cout << "Application: edgeai_cpp_ort_video\n"
              << "ONNX Runtime version: " << detector.runtime_info().version << '\n'
              << "Execution provider: " << detector.runtime_info().execution_provider << '\n'
              << "Threads: intra_op=" << detector.runtime_info().intra_op_threads
              << " inter_op=" << detector.runtime_info().inter_op_threads << '\n'
              << "Input video SHA256: " << edgeai::backends::sha256_file(values.at("--input"))
              << '\n'
              << "Input metadata: " << input_metadata.width << 'x' << input_metadata.height
              << " fps=" << input_metadata.fps << " fourcc=" << input_metadata.fourcc
              << " frames=" << input_metadata.reported_frame_count << '\n'
              << "Writer: backend=" << writer_backend << " requested_fourcc=avc1\n"
              << "Counts: decoded=" << counts.decoded << " processed=" << counts.processed
              << " failed=" << counts.failed << " written=" << counts.written
              << " verified=" << verification.decoded_frame_count << '\n'
              << std::fixed << std::setprecision(3)
              << "Diagnostic timing sums only; not a benchmark (ms): read=" << totals.video_read
              << " preprocess=" << totals.preprocess << " inference=" << totals.inference
              << " postprocess=" << totals.postprocess
              << " visualization=" << totals.visualization << " write=" << totals.video_write
              << " pipeline_total=" << totals.pipeline_total
              << " loop_total=" << loop_total_ms << '\n'
              << "Pipeline total excludes read, visualization, and write.\n"
              << "Output video: " << values.at("--output") << '\n'
              << "Output JSON: " << values.at("--output-json") << '\n'
              << "Visual review: PENDING_HUMAN_REVIEW\n";
    return 0;
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        if (argc > 1 && std::string(argv[1]) == "--verify-output") {
            return verify_output(parse_verification_args(argc, argv));
        }
        return run_video(parse_normal_args(argc, argv));
    } catch (const std::exception& error) {
        std::cerr << "edgeai_ort_video error: " << error.what() << '\n';
        return 1;
    }
}
