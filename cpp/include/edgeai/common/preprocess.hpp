#pragma once

#include "edgeai/common/config.hpp"
#include "edgeai/common/detection.hpp"

#include <filesystem>
#include <optional>

#include <opencv2/core/mat.hpp>

namespace edgeai::common {

struct PreprocessResult {
    cv::Mat letterboxed_bgr;
    InputTensor tensor;
    LetterboxMetadata metadata;
};

cv::Mat load_bgr_image(const std::filesystem::path& path);
PreprocessResult preprocess_image(const cv::Mat& image, const InferenceConfig& config);
std::optional<Box> restore_and_clip_box(
    const Box& input_box,
    const LetterboxMetadata& metadata
);

}  // namespace edgeai::common
