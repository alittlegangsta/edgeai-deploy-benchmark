#pragma once

#include "edgeai/common/config.hpp"
#include "edgeai/common/detection.hpp"

#include <cstdint>
#include <vector>

namespace edgeai::common {

struct PostprocessResult {
    std::size_t raw_candidate_count{0};
    std::size_t threshold_candidate_count{0};
    std::size_t nms_candidate_count{0};
    std::size_t invalid_box_count{0};
    std::int64_t decode_ns{0};
    std::int64_t nms_ns{0};
    std::vector<Detection> detections;
};

Box xywh_to_xyxy(const Box& box);
float box_iou(const Box& left, const Box& right);
void validate_frame_detections(
    const std::vector<Detection>& detections,
    int frame_width,
    int frame_height,
    std::size_t frame_index
);
PostprocessResult decode_yolov5_output(
    const std::vector<float>& raw_output,
    const std::vector<std::int64_t>& output_shape,
    const std::vector<std::string>& class_names,
    const LetterboxMetadata& metadata,
    const InferenceConfig& config
);

}  // namespace edgeai::common
