#include "edgeai/backends/ncnn_detector.hpp"
#include "edgeai/common/config.hpp"
#include "edgeai/common/postprocess.hpp"
#include "edgeai/common/preprocess.hpp"
#include "edgeai/common/video_pipeline.hpp"
#include "edgeai/common/visualize.hpp"

#include <algorithm>
#include <chrono>
#include <fstream>
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

struct Arguments {
    edgeai::filesystem::path manifest;
    edgeai::filesystem::path config;
    edgeai::filesystem::path model_param;
    edgeai::filesystem::path model_bin;
    edgeai::filesystem::path input_video;
    edgeai::filesystem::path output_video;
    edgeai::filesystem::path output_json;
    std::string runtime_profile{"generic-default"};
    std::string output_codec{"avc1"};
    int threads{1};
    std::size_t max_frames{0U};
};

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
    std::size_t decoded{0U};
    std::size_t processed{0U};
    std::size_t failed{0U};
    std::size_t written{0U};
};

double elapsed_ms(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

int parse_threads(const std::string& value) {
    std::size_t consumed = 0U;
    int result = 0;
    try {
        result = std::stoi(value, &consumed);
    } catch (const std::exception&) {
        throw std::runtime_error("--threads must be an integer");
    }
    if (consumed != value.size() || (result != 1 && result != 2)) {
        throw std::runtime_error("--threads must be 1 or 2");
    }
    return result;
}

std::size_t parse_max_frames(const std::string& value) {
    std::size_t consumed = 0U;
    unsigned long long result = 0U;
    try {
        result = std::stoull(value, &consumed);
    } catch (const std::exception&) {
        throw std::runtime_error("--max-frames must be a nonnegative integer");
    }
    if (consumed != value.size()) {
        throw std::runtime_error("--max-frames must be a nonnegative integer");
    }
    return static_cast<std::size_t>(result);
}

Arguments parse_args(int argc, char* argv[]) {
    if (argc < 11 || argc % 2 == 0) {
        throw std::runtime_error(
            "usage: edgeai_ncnn_video --manifest PATH --config PATH "
            "[--model-param PATH --model-bin PATH] "
            "(--input PATH|--input-video PATH) (--output PATH|--output-video PATH) "
            "--output-json PATH "
            "[--runtime-profile baseline-single-thread|recommended-dual-thread] "
            "[--threads 1|2] [--output-codec FOURCC] [--max-frames COUNT]"
        );
    }
    const std::vector<std::string> allowed{
        "--manifest",       "--config",         "--model-param",
        "--model-bin",      "--input",          "--input-video",
        "--output",         "--output-video",   "--output-json",
        "--runtime-profile", "--threads",        "--output-codec",
        "--max-frames",
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
    for (const std::string required : {"--manifest", "--config", "--output-json"}) {
        if (values.count(required) == 0U) {
            throw std::runtime_error("missing required argument: " + required);
        }
    }
    const bool has_input = values.count("--input") != 0U;
    const bool has_input_video = values.count("--input-video") != 0U;
    const bool has_output = values.count("--output") != 0U;
    const bool has_output_video = values.count("--output-video") != 0U;
    if (has_input == has_input_video) {
        throw std::runtime_error("exactly one of --input or --input-video is required");
    }
    if (has_output == has_output_video) {
        throw std::runtime_error("exactly one of --output or --output-video is required");
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
        throw std::runtime_error("--threads differs from runtime profile " + profile_name);
    }
    edgeai::backends::validate_ncnn_runtime_profile(
        profile, edgeai::backends::ncnn_build_capabilities()
    );

    const std::string codec =
        values.count("--output-codec") != 0U ? values.at("--output-codec") : "avc1";
    if (codec.size() != 4U) {
        throw std::runtime_error("--output-codec must contain exactly four characters");
    }
    return {
        values.at("--manifest"),
        values.at("--config"),
        has_param ? edgeai::filesystem::path(values.at("--model-param"))
                  : edgeai::filesystem::path{},
        has_bin ? edgeai::filesystem::path(values.at("--model-bin"))
                : edgeai::filesystem::path{},
        has_input ? edgeai::filesystem::path(values.at("--input"))
                  : edgeai::filesystem::path(values.at("--input-video")),
        has_output ? edgeai::filesystem::path(values.at("--output"))
                   : edgeai::filesystem::path(values.at("--output-video")),
        values.at("--output-json"),
        profile_name,
        codec,
        threads,
        values.count("--max-frames") != 0U
            ? parse_max_frames(values.at("--max-frames"))
            : 0U,
    };
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

void create_parent_directory(const edgeai::filesystem::path& path) {
    if (!path.parent_path().empty()) {
        edgeai::filesystem::create_directories(path.parent_path());
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
    const Arguments& arguments,
    const edgeai::common::InferenceConfig& config,
    const edgeai::backends::NcnnDetector& detector,
    const edgeai::common::VideoMetadata& input_metadata,
    const std::string& writer_backend,
    const FrameCounts& counts,
    const std::vector<FrameRecord>& records,
    const SetupTimingsMs& setup,
    double loop_total_ms,
    int observed_threads,
    const edgeai::common::VideoVerificationResult& verification
) {
    create_parent_directory(arguments.output_json);
    cv::FileStorage output(
        arguments.output_json.string(),
        cv::FileStorage::WRITE | cv::FileStorage::FORMAT_JSON
    );
    if (!output.isOpened()) {
        throw std::runtime_error(
            "failed to open ncnn video result JSON: " + arguments.output_json.string()
        );
    }
    std::vector<edgeai::common::VideoFrameTimingsMs> frame_timings;
    frame_timings.reserve(records.size());
    for (const FrameRecord& record : records) {
        frame_timings.push_back(record.timings);
    }
    const auto totals = edgeai::common::sum_video_timings(frame_timings);
    const auto means = mean_timings(totals, records.size());
    const auto& runtime = detector.runtime_info();

    output << "schema_version" << 2 << "application" << "edgeai_cpp_ncnn_video"
           << "task" << "020" << "runtime_profile" << arguments.runtime_profile
           << "measurement_classification"
           << "full-video functional diagnostic, not a performance benchmark";
    output << "model" << "{" << "manifest_path" << arguments.manifest.string()
           << "manifest_sha256" << edgeai::backends::ncnn_sha256_file(arguments.manifest)
           << "param_path" << detector.param_path().string() << "param_sha256"
           << detector.param_sha256() << "bin_path" << detector.bin_path().string()
           << "bin_sha256" << detector.bin_sha256() << "runtime_version" << runtime.version
           << "execution_provider" << runtime.execution_provider << "configured_threads"
           << runtime.threads << "observed_process_threads" << observed_threads
           << "ncnn_openmp_compiled" << runtime.openmp_compiled
           << "ncnn_threads_compiled" << runtime.threads_compiled
           << "ncnn_simpleomp_compiled" << runtime.simpleomp_compiled
           << "compiler_openmp" << runtime.compiler_openmp
           << "effective_parallel_backend" << runtime.effective_parallel_backend
           << "ncnn_library_sha256" << runtime.library_sha256
           << "private_libgomp_sha256" << runtime.private_libgomp_sha256
           << "vulkan" << runtime.vulkan << "fp16" << runtime.fp16 << "bf16"
           << runtime.bf16 << "int8" << runtime.int8 << "input_blob"
           << runtime.inputs.at(0).name << "output_blob" << runtime.outputs.at(0).name << "}";
    output << "configuration" << "{" << "path" << arguments.config.string() << "sha256"
           << edgeai::backends::ncnn_sha256_file(arguments.config) << "input_width"
           << config.input_size.width << "input_height" << config.input_size.height
           << "confidence_threshold" << config.confidence_threshold << "iou_threshold"
           << config.iou_threshold << "class_aware_nms" << config.class_aware_nms
           << "max_detections" << config.max_detections << "}";
    output << "input_video" << "{" << "path" << arguments.input_video.string()
           << "sha256" << edgeai::backends::ncnn_sha256_file(arguments.input_video)
           << "size_bytes"
           << static_cast<double>(edgeai::filesystem::file_size(arguments.input_video))
           << "metadata";
    write_video_metadata(output, input_metadata);
    output << "}";
    output << "output_video" << "{" << "path" << arguments.output_video.string()
           << "sha256" << edgeai::backends::ncnn_sha256_file(arguments.output_video)
           << "size_bytes"
           << static_cast<double>(edgeai::filesystem::file_size(arguments.output_video))
           << "requested_fourcc" << arguments.output_codec << "writer_backend"
           << writer_backend << "reopened_metadata";
    write_video_metadata(output, verification.metadata);
    output << "}";
    output << "counts" << "{" << "reported_input_frames"
           << static_cast<int>(input_metadata.reported_frame_count) << "max_frames"
           << static_cast<int>(arguments.max_frames) << "decoded_frames"
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
           << "one cv::VideoWriter::write call; close/flush is separate"
           << "pipeline_total"
           << "preprocess + inference + postprocess; excludes read, visualization and write"
           << "container_fps_note"
           << "container FPS is playback metadata, not processing throughput" << "}";
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
    output << "exit_code" << 0;
    output.release();
    if (!edgeai::filesystem::is_regular_file(arguments.output_json) ||
        edgeai::filesystem::file_size(arguments.output_json) == 0U) {
        throw std::runtime_error("ncnn video result JSON is missing or empty");
    }
}

int run(int argc, char* argv[]) {
    const auto arguments = parse_args(argc, argv);
    if (edgeai::filesystem::absolute(arguments.input_video) ==
        edgeai::filesystem::absolute(arguments.output_video)) {
        throw std::runtime_error("input and output video paths must differ");
    }
    create_parent_directory(arguments.output_video);
    create_parent_directory(arguments.output_json);

    SetupTimingsMs setup;
    const auto config_start = Clock::now();
    const auto config = edgeai::common::load_config(arguments.config);
    setup.config_load = elapsed_ms(config_start, Clock::now());
    const auto open_start = Clock::now();
    cv::VideoCapture capture(arguments.input_video.string());
    if (!capture.isOpened()) {
        throw std::runtime_error("failed to open input video: " + arguments.input_video.string());
    }
    const auto input_metadata = edgeai::common::read_video_metadata(capture);
    setup.video_open = elapsed_ms(open_start, Clock::now());
    const std::size_t reported_frames =
        static_cast<std::size_t>(input_metadata.reported_frame_count);
    const std::size_t expected_frames =
        arguments.max_frames == 0U ? reported_frames
                                  : std::min(arguments.max_frames, reported_frames);

    const auto model_start = Clock::now();
    edgeai::backends::NcnnDetector detector(
        arguments.manifest,
        arguments.threads,
        arguments.model_param,
        arguments.model_bin
    );
    setup.model_load = elapsed_ms(model_start, Clock::now());
    const auto writer_start = Clock::now();
    const int fourcc = cv::VideoWriter::fourcc(
        arguments.output_codec[0],
        arguments.output_codec[1],
        arguments.output_codec[2],
        arguments.output_codec[3]
    );
    cv::VideoWriter writer(
        arguments.output_video.string(),
        fourcc,
        input_metadata.fps,
        cv::Size(input_metadata.width, input_metadata.height),
        true
    );
    if (!writer.isOpened()) {
        throw std::runtime_error(
            "failed to open output video writer for codec " + arguments.output_codec
        );
    }
    const std::string writer_backend = writer.getBackendName();
    setup.writer_open = elapsed_ms(writer_start, Clock::now());

    FrameCounts counts;
    std::vector<FrameRecord> records;
    records.reserve(expected_frames);
    int maximum_observed_threads = -1;
    const auto loop_start = Clock::now();
    while (counts.decoded < expected_frames) {
        edgeai::common::VideoFrameTimingsMs timings;
        timings.frame_index = counts.decoded;
        cv::Mat frame;
        const auto read_start = Clock::now();
        const bool read_ok = capture.read(frame);
        const auto read_end = Clock::now();
        if (!read_ok) {
            ++counts.failed;
            throw std::runtime_error("video ended before the expected frame count");
        }
        timings.video_read = elapsed_ms(read_start, read_end);
        ++counts.decoded;
        try {
            edgeai::common::validate_video_frame(
                frame, input_metadata.width, input_metadata.height, timings.frame_index
            );
            const auto preprocess_start = Clock::now();
            const auto preprocessed = edgeai::common::preprocess_image(frame, config);
            timings.preprocess = elapsed_ms(preprocess_start, Clock::now());
            const auto inference_start = Clock::now();
            const auto raw = detector.infer(preprocessed.tensor);
            timings.inference = elapsed_ms(inference_start, Clock::now());
            maximum_observed_threads =
                std::max(maximum_observed_threads, observed_process_threads());
            const auto postprocess_start = Clock::now();
            auto postprocessed = edgeai::common::decode_yolov5_output(
                raw.values, raw.shape, config.class_names, preprocessed.metadata, config
            );
            timings.postprocess = elapsed_ms(postprocess_start, Clock::now());
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
    if (counts.decoded != expected_frames || counts.processed != expected_frames ||
        counts.written != expected_frames || counts.failed != 0U) {
        throw std::runtime_error("decoded, processed, written, expected, and failed counts differ");
    }
    if (arguments.runtime_profile == "recommended-dual-thread" &&
        maximum_observed_threads < 2) {
        throw std::runtime_error(
            "recommended-dual-thread did not observe at least two process threads"
        );
    }
    const auto close_start = Clock::now();
    writer.release();
    setup.writer_close = elapsed_ms(close_start, Clock::now());
    const auto verification_start = Clock::now();
    const auto verification = edgeai::common::verify_video_file(
        arguments.output_video,
        input_metadata.width,
        input_metadata.height,
        input_metadata.fps,
        counts.written
    );
    setup.output_verification = elapsed_ms(verification_start, Clock::now());
    write_result(
        arguments, config, detector, input_metadata, writer_backend, counts, records, setup,
        loop_total_ms, maximum_observed_threads, verification
    );

    std::vector<edgeai::common::VideoFrameTimingsMs> timings;
    timings.reserve(records.size());
    for (const auto& record : records) {
        timings.push_back(record.timings);
    }
    const auto totals = edgeai::common::sum_video_timings(timings);
    std::cout << "Application: edgeai_cpp_ncnn_video\n"
              << "Program contract: Task 020 profiled video-file CPU/FP32\n"
              << "Runtime profile: " << arguments.runtime_profile << '\n'
              << "ncnn version: " << detector.runtime_info().version << '\n'
              << "Execution provider: ncnn CPU\n"
              << "Configured threads: " << arguments.threads << '\n'
              << "ncnn_openmp_compiled: "
              << (detector.runtime_info().openmp_compiled ? "true" : "false") << '\n'
              << "ncnn_threads_compiled: "
              << (detector.runtime_info().threads_compiled ? "true" : "false") << '\n'
              << "ncnn_simpleomp_compiled: "
              << (detector.runtime_info().simpleomp_compiled ? "true" : "false") << '\n'
              << "effective_parallel_backend: "
              << detector.runtime_info().effective_parallel_backend << '\n'
              << "observed_process_threads: " << maximum_observed_threads << '\n'
              << "Param SHA256: " << detector.param_sha256() << '\n'
              << "Bin SHA256: " << detector.bin_sha256() << '\n'
              << "Input video SHA256: "
              << edgeai::backends::ncnn_sha256_file(arguments.input_video) << '\n'
              << "Input video: " << input_metadata.width << 'x' << input_metadata.height
              << " fps=" << input_metadata.fps << " frames="
              << input_metadata.reported_frame_count << " fourcc=" << input_metadata.fourcc
              << '\n'
              << "Output codec: " << arguments.output_codec << '\n'
              << "Confidence threshold: " << config.confidence_threshold << '\n'
              << "NMS IoU threshold: " << config.iou_threshold << '\n'
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
              << "Output JSON: " << arguments.output_json.string() << '\n'
              << "Output video: " << arguments.output_video.string() << '\n'
              << "Visual review: PENDING_HUMAN_REVIEW\n"
              << "Exit code: 0\n";
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
