#include "edgeai/common/video_pipeline.hpp"

#include <algorithm>
#include <cmath>
#include <cctype>
#include <limits>
#include <set>
#include <stdexcept>
#include <string>

#include <opencv2/core.hpp>

namespace edgeai::common {
namespace {

void require_finite_nonnegative(double value, const char* field) {
    if (!std::isfinite(value) || value < 0.0) {
        throw std::runtime_error(std::string("invalid video timing field: ") + field);
    }
}

}  // namespace

std::string fourcc_to_string(int fourcc) {
    std::string value(4U, '?');
    for (std::size_t index = 0; index < value.size(); ++index) {
        const auto character = static_cast<unsigned char>((fourcc >> (8U * index)) & 0xFF);
        value[index] = std::isprint(character) != 0 ? static_cast<char>(character) : '?';
    }
    return value;
}

VideoMetadata read_video_metadata(const cv::VideoCapture& capture) {
    if (!capture.isOpened()) {
        throw std::runtime_error("video capture is not open");
    }
    const auto width = static_cast<int>(std::llround(capture.get(cv::CAP_PROP_FRAME_WIDTH)));
    const auto height = static_cast<int>(std::llround(capture.get(cv::CAP_PROP_FRAME_HEIGHT)));
    const double fps = capture.get(cv::CAP_PROP_FPS);
    const auto frame_count =
        static_cast<std::int64_t>(std::llround(capture.get(cv::CAP_PROP_FRAME_COUNT)));
    const auto fourcc = static_cast<int>(std::llround(capture.get(cv::CAP_PROP_FOURCC)));
    VideoMetadata metadata{
        width,
        height,
        fps,
        frame_count,
        fourcc_to_string(fourcc),
        capture.getBackendName(),
    };
    validate_video_metadata(metadata);
    return metadata;
}

void validate_video_metadata(const VideoMetadata& metadata) {
    if (metadata.width <= 0 || metadata.height <= 0) {
        throw std::runtime_error("video dimensions must be positive");
    }
    if (!std::isfinite(metadata.fps) || metadata.fps <= 0.0) {
        throw std::runtime_error("video FPS must be finite and positive");
    }
    if (metadata.reported_frame_count <= 0) {
        throw std::runtime_error("video reported frame count must be positive");
    }
    if (metadata.fourcc.size() != 4U || metadata.backend.empty()) {
        throw std::runtime_error("video codec/backend metadata is incomplete");
    }
}

void validate_video_frame(
    const cv::Mat& frame,
    int expected_width,
    int expected_height,
    std::size_t frame_index
) {
    if (frame.empty()) {
        throw std::runtime_error("decoded frame is empty at index " + std::to_string(frame_index));
    }
    if (frame.cols != expected_width || frame.rows != expected_height || frame.type() != CV_8UC3) {
        throw std::runtime_error(
            "decoded frame geometry/type differs at index " + std::to_string(frame_index)
        );
    }
}

void validate_frame_detections(
    const std::vector<Detection>& detections,
    int frame_width,
    int frame_height,
    std::size_t frame_index
) {
    for (std::size_t index = 0; index < detections.size(); ++index) {
        const Detection& detection = detections[index];
        const Box& box = detection.box_xyxy_source;
        const bool finite_box = std::isfinite(box.x1) && std::isfinite(box.y1) &&
                                std::isfinite(box.x2) && std::isfinite(box.y2);
        if (detection.rank != index + 1U || detection.class_id < 0 ||
            detection.class_name.empty() || !std::isfinite(detection.confidence) ||
            detection.confidence < 0.0F || detection.confidence > 1.0F || !finite_box ||
            box.x1 < 0.0F || box.y1 < 0.0F || box.x2 > static_cast<float>(frame_width) ||
            box.y2 > static_cast<float>(frame_height) || box.x2 <= box.x1 || box.y2 <= box.y1) {
            throw std::runtime_error(
                "invalid detection at frame " + std::to_string(frame_index) + ", rank " +
                std::to_string(index + 1U)
            );
        }
    }
}

VideoTimingTotalsMs sum_video_timings(const std::vector<VideoFrameTimingsMs>& timings) {
    VideoTimingTotalsMs totals;
    for (const VideoFrameTimingsMs& timing : timings) {
        require_finite_nonnegative(timing.video_read, "video_read");
        require_finite_nonnegative(timing.preprocess, "preprocess");
        require_finite_nonnegative(timing.inference, "inference");
        require_finite_nonnegative(timing.postprocess, "postprocess");
        require_finite_nonnegative(timing.visualization, "visualization");
        require_finite_nonnegative(timing.video_write, "video_write");
        require_finite_nonnegative(timing.pipeline_total, "pipeline_total");
        totals.video_read += timing.video_read;
        totals.preprocess += timing.preprocess;
        totals.inference += timing.inference;
        totals.postprocess += timing.postprocess;
        totals.visualization += timing.visualization;
        totals.video_write += timing.video_write;
        totals.pipeline_total += timing.pipeline_total;
    }
    return totals;
}

VideoVerificationResult verify_video_file(
    const std::filesystem::path& path,
    int expected_width,
    int expected_height,
    double expected_fps,
    std::size_t expected_frame_count
) {
    if (!std::filesystem::is_regular_file(path) || std::filesystem::file_size(path) == 0U) {
        throw std::runtime_error("output video is missing or empty: " + path.string());
    }
    if (expected_width <= 0 || expected_height <= 0 || !std::isfinite(expected_fps) ||
        expected_fps <= 0.0 || expected_frame_count == 0U) {
        throw std::runtime_error("expected output video metadata is invalid");
    }
    cv::VideoCapture capture(path.string());
    if (!capture.isOpened()) {
        throw std::runtime_error("failed to reopen output video: " + path.string());
    }
    VideoVerificationResult result;
    result.metadata = read_video_metadata(capture);
    if (result.metadata.width != expected_width || result.metadata.height != expected_height) {
        throw std::runtime_error("reopened output video dimensions differ from expected values");
    }
    if (std::abs(result.metadata.fps - expected_fps) > 0.01) {
        throw std::runtime_error("reopened output video FPS differs from expected value");
    }
    if (result.metadata.reported_frame_count != static_cast<std::int64_t>(expected_frame_count)) {
        throw std::runtime_error("reopened output reported frame count differs from expected value");
    }

    const std::set<std::size_t> sample_indices{
        0U,
        expected_frame_count / 2U,
        expected_frame_count - 1U,
    };
    cv::Mat frame;
    while (capture.read(frame)) {
        validate_video_frame(frame, expected_width, expected_height, result.decoded_frame_count);
        if (sample_indices.count(result.decoded_frame_count) != 0U) {
            const cv::Scalar mean = cv::mean(frame);
            result.samples.push_back({
                result.decoded_frame_count,
                {{mean[0], mean[1], mean[2]}},
            });
        }
        ++result.decoded_frame_count;
    }
    capture.release();
    if (result.decoded_frame_count != expected_frame_count) {
        throw std::runtime_error("decoded output frame count differs from expected value");
    }
    if (result.samples.size() != sample_indices.size()) {
        throw std::runtime_error("failed to decode first/middle/last output verification frames");
    }
    return result;
}

}  // namespace edgeai::common
