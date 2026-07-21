#include "edgeai/common/video_pipeline.hpp"

#include <cmath>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include <opencv2/core/mat.hpp>
#include <opencv2/videoio.hpp>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

template <typename Callable>
void require_throws(Callable&& callable, const std::string& message) {
    try {
        callable();
    } catch (const std::exception&) {
        return;
    }
    throw std::runtime_error(message);
}

void test_fourcc_and_metadata() {
    const int fourcc = cv::VideoWriter::fourcc('a', 'v', 'c', '1');
    require(edgeai::common::fourcc_to_string(fourcc) == "avc1", "fourcc conversion failed");
    edgeai::common::validate_video_metadata({1280, 720, 30.0, 240, "avc1", "FFMPEG"});
    require_throws(
        [] { edgeai::common::validate_video_metadata({0, 720, 30.0, 240, "avc1", "FFMPEG"}); },
        "zero-width video metadata was accepted"
    );
    require_throws(
        [] { edgeai::common::validate_video_metadata({1280, 720, 0.0, 240, "avc1", "FFMPEG"}); },
        "zero-FPS video metadata was accepted"
    );
    require_throws(
        [] { edgeai::common::validate_video_metadata({1280, 720, 30.0, 0, "avc1", "FFMPEG"}); },
        "zero-frame video metadata was accepted"
    );
}

void test_frames_detections_and_timings() {
    const cv::Mat frame(24, 32, CV_8UC3, cv::Scalar(1, 2, 3));
    edgeai::common::validate_video_frame(frame, 32, 24, 0U);
    require_throws(
        [&frame] { edgeai::common::validate_video_frame(frame, 31, 24, 0U); },
        "wrong frame width was accepted"
    );

    edgeai::common::Detection detection;
    detection.rank = 1U;
    detection.class_id = 2;
    detection.class_name = "car";
    detection.confidence = 0.75F;
    detection.box_xyxy_source = {1.0F, 2.0F, 20.0F, 22.0F};
    edgeai::common::validate_frame_detections({detection}, 32, 24, 0U);
    detection.box_xyxy_source.x2 = 33.0F;
    require_throws(
        [&detection] { edgeai::common::validate_frame_detections({detection}, 32, 24, 0U); },
        "out-of-bounds detection was accepted"
    );

    std::vector<edgeai::common::VideoFrameTimingsMs> timings{
        {0U, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 9.0},
        {1U, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 12.0},
    };
    const auto totals = edgeai::common::sum_video_timings(timings);
    require(std::abs(totals.video_read - 3.0) < 1.0e-12, "read timing sum failed");
    require(std::abs(totals.inference - 7.0) < 1.0e-12, "inference timing sum failed");
    require(std::abs(totals.pipeline_total - 21.0) < 1.0e-12, "pipeline sum failed");
    timings[0].video_write = -1.0;
    require_throws(
        [&timings] { static_cast<void>(edgeai::common::sum_video_timings(timings)); },
        "negative timing was accepted"
    );
}

void test_real_video_verification(const std::filesystem::path& path) {
    std::filesystem::remove(path);
    constexpr int width = 64;
    constexpr int height = 48;
    constexpr double fps = 30.0;
    constexpr std::size_t frame_count = 5U;
    const int fourcc = cv::VideoWriter::fourcc('a', 'v', 'c', '1');
    cv::VideoWriter writer(
        path.string(), cv::CAP_FFMPEG, fourcc, fps, cv::Size(width, height), true
    );
    require(writer.isOpened(), "test H.264/avc1 writer is unavailable");
    for (std::size_t index = 0; index < frame_count; ++index) {
        const cv::Mat frame(
            height,
            width,
            CV_8UC3,
            cv::Scalar(20.0 + static_cast<double>(index), 40.0, 80.0)
        );
        writer.write(frame);
    }
    writer.release();
    const auto verification =
        edgeai::common::verify_video_file(path, width, height, fps, frame_count);
    require(verification.decoded_frame_count == frame_count, "verified frame count differs");
    require(verification.samples.size() == 3U, "first/middle/last samples were not decoded");
    require(verification.metadata.width == width, "verified width differs");
    require(verification.metadata.height == height, "verified height differs");
    require_throws(
        [&path] { static_cast<void>(edgeai::common::verify_video_file(path, 63, 48, 30.0, 5U)); },
        "wrong expected video dimensions were accepted"
    );
    std::filesystem::remove(path);
    require_throws(
        [&path] { static_cast<void>(edgeai::common::verify_video_file(path, 64, 48, 30.0, 5U)); },
        "missing video was accepted"
    );
}

}  // namespace

int main() {
    const std::filesystem::path test_video = "edgeai_video_pipeline_test.mp4";
    try {
        test_fourcc_and_metadata();
        test_frames_detections_and_timings();
        test_real_video_verification(test_video);
        std::cout << "edgeai_video_pipeline_tests: PASS\n";
        return 0;
    } catch (const std::exception& error) {
        std::filesystem::remove(test_video);
        std::cerr << "edgeai_video_pipeline_tests: FAIL: " << error.what() << '\n';
        return 1;
    }
}
