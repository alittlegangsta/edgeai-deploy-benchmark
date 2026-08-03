#include "edgeai/backends/ncnn_detector.hpp"
#include "edgeai/common/camera_pipeline.hpp"
#include "edgeai/common/config.hpp"
#include "edgeai/common/filesystem.hpp"
#include "edgeai/common/postprocess.hpp"
#include "edgeai/common/preprocess.hpp"
#include "edgeai/common/visualize.hpp"

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <cmath>
#include <cstring>
#include <fcntl.h>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <linux/videodev2.h>
#include <map>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/ioctl.h>
#include <thread>
#include <unistd.h>
#include <utility>
#include <vector>

#include <opencv2/core/persistence.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/videoio.hpp>

namespace {

using Clock = std::chrono::steady_clock;

struct Arguments {
    edgeai::filesystem::path manifest;
    edgeai::filesystem::path config;
    edgeai::filesystem::path model_param;
    edgeai::filesystem::path model_bin;
    edgeai::filesystem::path output_json;
    edgeai::filesystem::path capabilities_json;
    edgeai::filesystem::path output_frames_dir;
    std::string camera_device;
    std::string runtime_profile{"recommended-dual-thread"};
    std::string camera_format;
    int capture_width{0};
    int capture_height{0};
    double capture_fps{0.0};
    std::size_t max_processed_frames{0U};
    double max_duration_seconds{0.0};
    bool no_display{true};
    bool audit_only{false};
};

struct CameraFormatCapability {
    std::string pixel_format;
    std::string description;
    std::vector<std::string> frame_sizes;
    std::vector<std::string> frame_intervals;
};

struct CameraCapabilities {
    std::string device;
    std::string driver;
    std::string card;
    std::string bus_info;
    std::uint32_t capabilities{0U};
    std::vector<CameraFormatCapability> formats;
};

struct CaptureStats {
    std::size_t captured{0U};
    std::size_t invalid{0U};
    std::size_t published{0U};
};

struct ProcessedFrame {
    std::size_t processed_index{0U};
    edgeai::common::CameraFrame source;
    edgeai::common::PostprocessResult postprocess;
    double inference_start_ms{0.0};
    double result_ms{0.0};
    double frame_age_at_inference_start_ms{0.0};
    double end_to_end_age_ms{0.0};
    double preprocess_ms{0.0};
    double inference_ms{0.0};
    double postprocess_ms{0.0};
    double pipeline_ms{0.0};
    int observed_threads{-1};
    std::string raw_path;
    std::string annotated_path;
};

double elapsed_ms(Clock::time_point start, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - start).count();
}

double monotonic_ms() {
    return std::chrono::duration<double, std::milli>(Clock::now().time_since_epoch()).count();
}

std::string fourcc_string(std::uint32_t value) {
    std::string result(4, ' ');
    for (int index = 0; index < 4; ++index) {
        const unsigned char character = static_cast<unsigned char>((value >> (8 * index)) & 0xffU);
        result[static_cast<std::size_t>(index)] =
            (character >= 32U && character <= 126U) ? static_cast<char>(character) : '?';
    }
    return result;
}

int fourcc_value(const std::string& value) {
    if (value.size() != 4U) {
        throw std::runtime_error("--camera-format must contain exactly four characters");
    }
    return cv::VideoWriter::fourcc(value[0], value[1], value[2], value[3]);
}

std::size_t parse_size(const std::string& value, const char* option) {
    std::size_t consumed = 0U;
    unsigned long long result = 0U;
    try {
        result = std::stoull(value, &consumed);
    } catch (const std::exception&) {
        throw std::runtime_error(std::string(option) + " must be a nonnegative integer");
    }
    if (consumed != value.size() || result == 0U) {
        throw std::runtime_error(std::string(option) + " must be a positive integer");
    }
    return static_cast<std::size_t>(result);
}

int parse_int(const std::string& value, const char* option) {
    std::size_t consumed = 0U;
    int result = 0;
    try {
        result = std::stoi(value, &consumed);
    } catch (const std::exception&) {
        throw std::runtime_error(std::string(option) + " must be an integer");
    }
    if (consumed != value.size() || result <= 0) {
        throw std::runtime_error(std::string(option) + " must be a positive integer");
    }
    return result;
}

double parse_double(const std::string& value, const char* option) {
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

Arguments parse_args(int argc, char* argv[]) {
    if (argc < 3 || argc % 2 == 0) {
        throw std::runtime_error(
            "usage: edgeai_ncnn_camera --camera-device PATH --output-json PATH "
            "[--audit-only 1] [--manifest PATH --config PATH --model-param PATH "
            "--model-bin PATH --runtime-profile recommended-dual-thread "
            "--max-processed-frames N --max-duration-seconds N "
            "--output-frames-dir PATH --capabilities-json PATH "
            "--capture-width N --capture-height N --capture-fps N --camera-format FOURCC]"
        );
    }
    const std::vector<std::string> allowed{
        "--manifest", "--config", "--model-param", "--model-bin", "--output-json",
        "--capabilities-json", "--output-frames-dir", "--camera-device",
        "--runtime-profile", "--max-processed-frames", "--max-duration-seconds",
        "--capture-width", "--capture-height", "--capture-fps", "--camera-format",
        "--no-display", "--audit-only",
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
    for (const char* required : {"--camera-device", "--output-json"}) {
        if (values.count(required) == 0U) {
            throw std::runtime_error(std::string("missing required argument: ") + required);
        }
    }
    Arguments result;
    result.camera_device = values.at("--camera-device");
    result.output_json = values.at("--output-json");
    result.audit_only = values.count("--audit-only") != 0U;
    if (result.audit_only) {
        return result;
    }
    for (const char* required : {"--manifest", "--config", "--model-param", "--model-bin",
                                 "--output-frames-dir", "--max-processed-frames"}) {
        if (values.count(required) == 0U) {
            throw std::runtime_error(std::string("missing required argument: ") + required);
        }
    }
    result.manifest = values.at("--manifest");
    result.config = values.at("--config");
    result.model_param = values.at("--model-param");
    result.model_bin = values.at("--model-bin");
    result.output_frames_dir = values.at("--output-frames-dir");
    if (values.count("--capabilities-json") != 0U) {
        result.capabilities_json = edgeai::filesystem::path(values.at("--capabilities-json"));
    } else {
        result.capabilities_json =
            result.output_json.parent_path() / "camera_capabilities.json";
    }
    result.runtime_profile = values.count("--runtime-profile") != 0U
                                 ? values.at("--runtime-profile")
                                 : "recommended-dual-thread";
    result.max_processed_frames = parse_size(values.at("--max-processed-frames"),
                                             "--max-processed-frames");
    if (values.count("--max-duration-seconds") != 0U) {
        result.max_duration_seconds = parse_double(
            values.at("--max-duration-seconds"), "--max-duration-seconds"
        );
    }
    if (values.count("--capture-width") != 0U) {
        result.capture_width = parse_int(values.at("--capture-width"), "--capture-width");
    }
    if (values.count("--capture-height") != 0U) {
        result.capture_height = parse_int(values.at("--capture-height"), "--capture-height");
    }
    if (values.count("--capture-fps") != 0U) {
        result.capture_fps = parse_double(values.at("--capture-fps"), "--capture-fps");
    }
    if (values.count("--camera-format") != 0U) {
        result.camera_format = values.at("--camera-format");
        fourcc_value(result.camera_format);
    }
    return result;
}

int safe_ioctl(int fd, unsigned long request, void* argument) {
    int result = 0;
    do {
        result = ioctl(fd, request, argument);
    } while (result < 0 && errno == EINTR);
    return result;
}

std::string frame_size_string(const v4l2_frmsizeenum& size) {
    if (size.type == V4L2_FRMSIZE_TYPE_DISCRETE) {
        return std::to_string(size.discrete.width) + "x" + std::to_string(size.discrete.height);
    }
    return "stepwise:" + std::to_string(size.stepwise.min_width) + "x" +
           std::to_string(size.stepwise.min_height) + "-" +
           std::to_string(size.stepwise.max_width) + "x" +
           std::to_string(size.stepwise.max_height);
}

std::string frame_interval_string(const v4l2_frmivalenum& interval) {
    if (interval.type == V4L2_FRMIVAL_TYPE_DISCRETE) {
        if (interval.discrete.numerator == 0U) {
            return "0";
        }
        const double fps = static_cast<double>(interval.discrete.denominator) /
                           static_cast<double>(interval.discrete.numerator);
        std::ostringstream stream;
        stream << std::fixed << std::setprecision(6) << fps << "fps";
        return stream.str();
    }
    return "stepwise";
}

CameraCapabilities enumerate_capabilities(const std::string& device) {
    const int fd = open(device.c_str(), O_RDONLY | O_NONBLOCK);
    if (fd < 0) {
        throw std::runtime_error("failed to open camera device: " + device + ": " +
                                 std::strerror(errno));
    }
    v4l2_capability capability{};
    if (safe_ioctl(fd, VIDIOC_QUERYCAP, &capability) < 0) {
        const std::string message = std::string("VIDIOC_QUERYCAP failed: ") + std::strerror(errno);
        close(fd);
        throw std::runtime_error(message);
    }
    CameraCapabilities result{
        device,
        reinterpret_cast<const char*>(capability.driver),
        reinterpret_cast<const char*>(capability.card),
        reinterpret_cast<const char*>(capability.bus_info),
        capability.capabilities,
        {},
    };
    for (std::uint32_t format_index = 0U;; ++format_index) {
        v4l2_fmtdesc format{};
        format.type = V4L2_BUF_TYPE_VIDEO_CAPTURE;
        format.index = format_index;
        if (safe_ioctl(fd, VIDIOC_ENUM_FMT, &format) < 0) {
            break;
        }
        CameraFormatCapability current{
            fourcc_string(format.pixelformat),
            reinterpret_cast<const char*>(format.description),
            {},
            {},
        };
        for (std::uint32_t size_index = 0U;; ++size_index) {
            v4l2_frmsizeenum size{};
            size.pixel_format = format.pixelformat;
            size.index = size_index;
            if (safe_ioctl(fd, VIDIOC_ENUM_FRAMESIZES, &size) < 0) {
                break;
            }
            current.frame_sizes.push_back(frame_size_string(size));
            if (size.type == V4L2_FRMSIZE_TYPE_DISCRETE) {
                for (std::uint32_t interval_index = 0U;; ++interval_index) {
                    v4l2_frmivalenum interval{};
                    interval.pixel_format = format.pixelformat;
                    interval.index = interval_index;
                    interval.width = size.discrete.width;
                    interval.height = size.discrete.height;
                    if (safe_ioctl(fd, VIDIOC_ENUM_FRAMEINTERVALS, &interval) < 0) {
                        break;
                    }
                    current.frame_intervals.push_back(
                        current.frame_sizes.back() + "@" + frame_interval_string(interval)
                    );
                }
            }
        }
        result.formats.push_back(std::move(current));
    }
    close(fd);
    return result;
}

void write_capabilities(
    const edgeai::filesystem::path& path,
    const CameraCapabilities& capabilities,
    const std::string& source
) {
    if (!path.parent_path().empty()) {
        edgeai::filesystem::create_directories(path.parent_path());
    }
    cv::FileStorage output(path.string(), cv::FileStorage::WRITE | cv::FileStorage::FORMAT_JSON);
    if (!output.isOpened()) {
        throw std::runtime_error("failed to open camera capabilities JSON: " + path.string());
    }
    output << "schema_version" << 1 << "capture_method" << source << "device"
           << capabilities.device << "driver" << capabilities.driver << "card"
           << capabilities.card << "bus_info" << capabilities.bus_info << "capabilities"
           << static_cast<int>(capabilities.capabilities) << "formats" << "[";
    for (const auto& format : capabilities.formats) {
        output << "{" << "pixel_format" << format.pixel_format << "description"
               << format.description << "frame_sizes" << "[";
        for (const auto& size : format.frame_sizes) {
            output << size;
        }
        output << "]" << "frame_intervals" << "[";
        for (const auto& interval : format.frame_intervals) {
            output << interval;
        }
        output << "]" << "}";
    }
    output << "]" << "status" << "PASS";
    output.release();
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
        output << "{" << "rank" << static_cast<int>(detection.rank) << "class_id"
               << detection.class_id << "class_name" << detection.class_name << "objectness"
               << detection.objectness << "class_score" << detection.class_score << "confidence"
               << detection.confidence << "box_xyxy_source";
        write_box(output, detection.box_xyxy_source);
        output << "}";
    }
    output << "]";
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

void write_run_json(
    const Arguments& arguments,
    const edgeai::common::InferenceConfig& config,
    const edgeai::backends::NcnnDetector& detector,
    const CameraCapabilities& capabilities,
    const cv::VideoCapture& capture,
    const CaptureStats& capture_stats,
    const edgeai::common::LatestFrameSlot& slot,
    const std::vector<ProcessedFrame>& frames,
    std::size_t invalid_capture_count,
    int maximum_observed_threads,
    double run_start_ms,
    double run_end_ms
) {
    if (!arguments.output_json.parent_path().empty()) {
        edgeai::filesystem::create_directories(arguments.output_json.parent_path());
    }
    cv::FileStorage output(
        arguments.output_json.string(), cv::FileStorage::WRITE | cv::FileStorage::FORMAT_JSON
    );
    if (!output.isOpened()) {
        throw std::runtime_error("failed to open camera run JSON: " + arguments.output_json.string());
    }
    const auto& runtime = detector.runtime_info();
    output << "schema_version" << 1 << "task" << "021"
           << "application" << "edgeai_ncnn_camera"
           << "automated_validation" << "PENDING_OFFLINE_REPLAY"
           << "human_camera_review" << "PENDING";
    output << "runtime" << "{" << "profile" << arguments.runtime_profile << "version"
           << runtime.version << "configured_threads" << runtime.threads
           << "ncnn_openmp_compiled" << runtime.openmp_compiled
           << "ncnn_threads_compiled" << runtime.threads_compiled
           << "ncnn_simpleomp_compiled" << runtime.simpleomp_compiled
           << "compiler_openmp" << runtime.compiler_openmp << "effective_parallel_backend"
           << runtime.effective_parallel_backend << "ncnn_library_sha256" << runtime.library_sha256
           << "private_libgomp_sha256" << runtime.private_libgomp_sha256 << "observed_process_threads"
           << maximum_observed_threads << "cpu_only" << true << "precision" << "FP32"
           << "batch" << 1 << "input_tensor" << "[" << 1 << 3 << 640 << 640 << "]"
           << "vulkan" << false
           << "fp16" << false << "bf16" << false << "int8" << false << "param_sha256"
           << detector.param_sha256() << "bin_sha256" << detector.bin_sha256() << "}";
    output << "camera" << "{" << "device" << arguments.camera_device << "backend"
           << capture.getBackendName() << "requested_width" << arguments.capture_width
           << "requested_height" << arguments.capture_height << "requested_fps"
           << arguments.capture_fps << "requested_fourcc" << arguments.camera_format
           << "negotiated_width" << static_cast<int>(capture.get(cv::CAP_PROP_FRAME_WIDTH))
           << "negotiated_height" << static_cast<int>(capture.get(cv::CAP_PROP_FRAME_HEIGHT))
           << "negotiated_fps" << capture.get(cv::CAP_PROP_FPS) << "negotiated_fourcc"
           << fourcc_string(static_cast<std::uint32_t>(capture.get(cv::CAP_PROP_FOURCC)))
           << "capabilities_json" << arguments.capabilities_json.string() << "}";
    output << "capture_capabilities" << "{" << "device" << capabilities.device << "driver"
           << capabilities.driver << "card" << capabilities.card << "bus_info"
           << capabilities.bus_info << "format_count" << static_cast<int>(capabilities.formats.size())
           << "}";
    output << "configuration" << "{" << "path" << arguments.config.string()
           << "input_width" << config.input_size.width << "input_height" << config.input_size.height
           << "confidence_threshold" << config.confidence_threshold << "nms_iou_threshold"
           << config.iou_threshold << "}";
    output << "counts" << "{" << "captured_frames" << static_cast<int>(capture_stats.captured)
           << "published_frames" << static_cast<int>(capture_stats.published)
           << "processed_frames" << static_cast<int>(frames.size()) << "overwritten_frames"
           << static_cast<int>(slot.overwritten_count()) << "dropped_frames"
           << static_cast<int>(slot.overwritten_count()) << "invalid_capture_frames"
           << static_cast<int>(invalid_capture_count) << "pending_frame_at_stop"
           << (slot.has_pending() ? 1 : 0) << "latest_frame_capacity" << 1 << "}";
    output << "run_clock" << "{" << "monotonic_start_ms" << run_start_ms << "monotonic_end_ms"
           << run_end_ms << "board_wall_clock_synchronization" << "not required; board clock may be unsynchronized"
           << "}";
    output << "frames" << "[";
    for (const auto& frame : frames) {
        output << "{" << "processed_index" << static_cast<int>(frame.processed_index)
               << "source_sequence" << static_cast<double>(frame.source.sequence)
               << "capture_monotonic_ms" << frame.source.capture_monotonic_ms
               << "inference_start_monotonic_ms" << frame.inference_start_ms
               << "result_monotonic_ms" << frame.result_ms << "frame_age_at_inference_start_ms"
               << frame.frame_age_at_inference_start_ms << "end_to_end_age_ms"
               << frame.end_to_end_age_ms << "paths" << "{" << "raw" << frame.raw_path
               << "annotated" << frame.annotated_path << "}" << "timings_ms" << "{"
               << "preprocess" << frame.preprocess_ms << "inference" << frame.inference_ms
               << "postprocess" << frame.postprocess_ms << "pipeline" << frame.pipeline_ms
               << "}" << "observed_process_threads" << frame.observed_threads
               << "detections";
        write_detections(output, frame.postprocess.detections);
        output << "}";
    }
    output << "]" << "exit_code" << 0 << "status" << "CAPTURE_AND_INFERENCE_PASS";
    output.release();
}

int run(int argc, char* argv[]) {
    const Arguments arguments = parse_args(argc, argv);
    const CameraCapabilities capabilities = enumerate_capabilities(arguments.camera_device);
    if (arguments.audit_only) {
        write_capabilities(arguments.output_json, capabilities, "V4L2 ioctl enumeration");
        std::cout << "camera_audit=PASS\n"
                  << "device=" << capabilities.device << "\n"
                  << "driver=" << capabilities.driver << "\n"
                  << "card=" << capabilities.card << "\n"
                  << "format_count=" << capabilities.formats.size() << "\n";
        return 0;
    }
    const auto config = edgeai::common::load_config(arguments.config);
    edgeai::backends::NcnnDetector detector(
        arguments.manifest, 2, arguments.model_param, arguments.model_bin
    );
    if (arguments.runtime_profile != "recommended-dual-thread") {
        throw std::runtime_error("Task 021 requires recommended-dual-thread profile");
    }

    cv::VideoCapture capture;
    if (!capture.open(arguments.camera_device, cv::CAP_V4L2)) {
        throw std::runtime_error("failed to open camera with V4L2 backend: " + arguments.camera_device);
    }
    if (arguments.capture_width > 0) {
        capture.set(cv::CAP_PROP_FRAME_WIDTH, arguments.capture_width);
    }
    if (arguments.capture_height > 0) {
        capture.set(cv::CAP_PROP_FRAME_HEIGHT, arguments.capture_height);
    }
    if (arguments.capture_fps > 0.0) {
        capture.set(cv::CAP_PROP_FPS, arguments.capture_fps);
    }
    if (!arguments.camera_format.empty()) {
        capture.set(cv::CAP_PROP_FOURCC, fourcc_value(arguments.camera_format));
    }
    if (!capture.isOpened()) {
        throw std::runtime_error("camera closed after format negotiation");
    }
    write_capabilities(arguments.capabilities_json, capabilities, "V4L2 ioctl enumeration");

    const double run_start_ms = monotonic_ms();
    edgeai::common::LatestFrameSlot slot;
    std::atomic<bool> stop_requested{false};
    CaptureStats capture_stats;
    std::size_t invalid_capture_count = 0U;
    std::vector<ProcessedFrame> processed;
    processed.reserve(arguments.max_processed_frames);
    std::exception_ptr worker_error;
    std::mutex worker_error_mutex;

    std::thread capture_thread([&] {
        std::uint64_t sequence = 0U;
        try {
            while (!stop_requested.load()) {
                if (arguments.max_duration_seconds > 0.0 &&
                    monotonic_ms() - run_start_ms >= arguments.max_duration_seconds * 1000.0) {
                    break;
                }
                cv::Mat frame;
                if (!capture.read(frame) || frame.empty() || frame.type() != CV_8UC3) {
                    ++invalid_capture_count;
                    continue;
                }
                ++capture_stats.captured;
                const auto capture_time = monotonic_ms();
                const bool accepted = slot.publish({frame.clone(), sequence++, capture_time});
                if (accepted || !slot.closed()) {
                    ++capture_stats.published;
                }
            }
        } catch (...) {
            std::lock_guard<std::mutex> lock(worker_error_mutex);
            worker_error = std::current_exception();
            stop_requested.store(true);
        }
        slot.close();
    });

    std::thread inference_thread([&] {
        try {
            while (!stop_requested.load()) {
                edgeai::common::CameraFrame frame;
                if (!slot.wait_pop(frame)) {
                    break;
                }
                const double inference_start = monotonic_ms();
                const double age_at_start = inference_start - frame.capture_monotonic_ms;
                const auto preprocess_start = Clock::now();
                const auto preprocessed = edgeai::common::preprocess_image(frame.bgr, config);
                const double preprocess_ms = elapsed_ms(preprocess_start, Clock::now());
                const auto inference_clock = Clock::now();
                const auto raw = detector.infer(preprocessed.tensor);
                const double inference_ms = elapsed_ms(inference_clock, Clock::now());
                const int observed_threads = observed_process_threads();
                const auto postprocess_start = Clock::now();
                const auto postprocessed = edgeai::common::decode_yolov5_output(
                    raw.values, raw.shape, config.class_names, preprocessed.metadata, config
                );
                const double postprocess_ms = elapsed_ms(postprocess_start, Clock::now());
                edgeai::common::validate_frame_detections(
                    postprocessed.detections, frame.bgr.cols, frame.bgr.rows, processed.size()
                );
                const cv::Mat annotated =
                    edgeai::common::draw_detections(frame.bgr, postprocessed.detections);
                const std::size_t processed_index = processed.size();
                const auto raw_path = arguments.output_frames_dir /
                                      ("processed_" + std::to_string(processed_index) + "_raw.png");
                const auto annotated_path = arguments.output_frames_dir /
                                            ("processed_" + std::to_string(processed_index) + "_annotated.png");
                edgeai::common::save_image(raw_path, frame.bgr);
                edgeai::common::save_image(annotated_path, annotated);
                const double result_ms = monotonic_ms();
                processed.push_back({
                    processed_index,
                    std::move(frame),
                    postprocessed,
                    inference_start,
                    result_ms,
                    age_at_start,
                    result_ms - frame.capture_monotonic_ms,
                    preprocess_ms,
                    inference_ms,
                    postprocess_ms,
                    preprocess_ms + inference_ms + postprocess_ms,
                    observed_threads,
                    raw_path.string(),
                    annotated_path.string(),
                });
                if (processed.size() >= arguments.max_processed_frames) {
                    stop_requested.store(true);
                    slot.close();
                    break;
                }
            }
        } catch (...) {
            std::lock_guard<std::mutex> lock(worker_error_mutex);
            worker_error = std::current_exception();
            stop_requested.store(true);
            slot.close();
        }
    });

    inference_thread.join();
    stop_requested.store(true);
    capture_thread.join();
    if (worker_error) {
        std::rethrow_exception(worker_error);
    }
    if (processed.size() != arguments.max_processed_frames) {
        throw std::runtime_error(
            "camera ended before max-processed-frames: processed=" +
            std::to_string(processed.size())
        );
    }
    int maximum_threads = -1;
    for (const auto& frame : processed) {
        maximum_threads = std::max(maximum_threads, frame.observed_threads);
    }
    if (maximum_threads < 2) {
        throw std::runtime_error("recommended-dual-thread did not observe two process threads");
    }
    const double run_end_ms = monotonic_ms();
    write_run_json(
        arguments, config, detector, capabilities, capture, capture_stats, slot, processed,
        invalid_capture_count, maximum_threads, run_start_ms, run_end_ms
    );
    capture.release();
    std::cout << "Application: edgeai_ncnn_camera\n"
              << "Task: 021 bounded latest-frame-wins UVC camera validation\n"
              << "Runtime profile: " << arguments.runtime_profile << '\n'
              << "Camera device: " << arguments.camera_device << '\n'
              << "Camera backend: V4L2/OpenCV\n"
              << "Configured ncnn threads: 2\n"
              << "ncnn_openmp_compiled: " << (detector.runtime_info().openmp_compiled ? "true" : "false") << '\n'
              << "effective_parallel_backend: " << detector.runtime_info().effective_parallel_backend << '\n'
              << "Observed process threads (whole process): " << maximum_threads << '\n'
              << "Captured frames: " << capture_stats.captured << '\n'
              << "Published frames: " << capture_stats.published << '\n'
              << "Processed frames: " << processed.size() << '\n'
              << "Overwritten/dropped frames: " << slot.overwritten_count() << '\n'
              << "Invalid capture frames: " << invalid_capture_count << '\n'
              << "Latest-frame capacity: 1\n"
              << "Output JSON: " << arguments.output_json.string() << '\n'
              << "Output frames: " << arguments.output_frames_dir.string() << '\n'
              << "Diagnostic timing only; not a realtime benchmark\n"
              << "Exit code: 0\n";
    return 0;
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        return run(argc, argv);
    } catch (const std::exception& error) {
        std::cerr << "edgeai_ncnn_camera error: " << error.what() << '\n';
        return 1;
    }
}
