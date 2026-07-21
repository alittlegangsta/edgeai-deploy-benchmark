#pragma once

#include "edgeai/common/detection.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

#include <opencv2/core/mat.hpp>
#include <opencv2/videoio.hpp>

namespace edgeai::common {

struct VideoMetadata {
    int width{0};
    int height{0};
    double fps{0.0};
    std::int64_t reported_frame_count{0};
    std::string fourcc;
    std::string backend;
};

struct VideoFrameTimingsMs {
    std::size_t frame_index{0};
    double video_read{0.0};
    double preprocess{0.0};
    double inference{0.0};
    double postprocess{0.0};
    double visualization{0.0};
    double video_write{0.0};
    double pipeline_total{0.0};
};

struct VideoTimingTotalsMs {
    double video_read{0.0};
    double preprocess{0.0};
    double inference{0.0};
    double postprocess{0.0};
    double visualization{0.0};
    double video_write{0.0};
    double pipeline_total{0.0};
};

struct VideoVerificationSample {
    std::size_t frame_index{0};
    std::array<double, 3> mean_bgr{{0.0, 0.0, 0.0}};
};

struct VideoVerificationResult {
    VideoMetadata metadata;
    std::size_t decoded_frame_count{0};
    std::vector<VideoVerificationSample> samples;
};

std::string fourcc_to_string(int fourcc);
VideoMetadata read_video_metadata(const cv::VideoCapture& capture);
void validate_video_metadata(const VideoMetadata& metadata);
void validate_video_frame(
    const cv::Mat& frame,
    int expected_width,
    int expected_height,
    std::size_t frame_index
);
void validate_frame_detections(
    const std::vector<Detection>& detections,
    int frame_width,
    int frame_height,
    std::size_t frame_index
);
VideoTimingTotalsMs sum_video_timings(const std::vector<VideoFrameTimingsMs>& timings);
VideoVerificationResult verify_video_file(
    const std::filesystem::path& path,
    int expected_width,
    int expected_height,
    double expected_fps,
    std::size_t expected_frame_count
);

}  // namespace edgeai::common
