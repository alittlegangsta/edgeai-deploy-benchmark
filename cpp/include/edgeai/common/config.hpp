#pragma once

#include "edgeai/common/detection.hpp"

#include <array>
#include <filesystem>
#include <string>
#include <vector>

namespace edgeai::common {

struct LetterboxSettings {
    std::array<int, 3> pad_color_bgr{{114, 114, 114}};
    std::string interpolation{"cv2.INTER_LINEAR"};
};

struct InferenceConfig {
    int schema_version{1};
    Size2D input_size{640, 640};
    double confidence_threshold{0.25};
    double iou_threshold{0.45};
    bool class_aware_nms{true};
    int max_detections{1000};
    std::vector<std::string> class_names;
    LetterboxSettings letterbox;
};

const std::vector<std::string>& frozen_coco80_class_names();
void validate_config(const InferenceConfig& config);
InferenceConfig load_config(const std::filesystem::path& path);

}  // namespace edgeai::common
