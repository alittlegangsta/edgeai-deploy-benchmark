#pragma once

#include "edgeai/common/detection.hpp"

#include <filesystem>
#include <vector>

#include <opencv2/core/mat.hpp>
#include <opencv2/core/types.hpp>

namespace edgeai::common {

cv::Scalar class_color(int class_id);
cv::Mat draw_detections(const cv::Mat& image, const std::vector<Detection>& detections);
void save_image(const std::filesystem::path& path, const cv::Mat& image);

}  // namespace edgeai::common
