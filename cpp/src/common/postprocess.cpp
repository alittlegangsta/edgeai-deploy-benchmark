#include "edgeai/common/postprocess.hpp"

#include "edgeai/common/preprocess.hpp"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <utility>

namespace edgeai::common {
namespace {

struct Candidate {
    std::size_t candidate_index{0};
    int class_id{-1};
    float objectness{0.0F};
    float class_score{0.0F};
    float confidence{0.0F};
    Box xywh;
    Box xyxy;
};

float round_six(float value) {
    return static_cast<float>(std::round(static_cast<double>(value) * 1'000'000.0) /
                              1'000'000.0);
}

bool finite_box(const Box& box) {
    return std::isfinite(box.x1) && std::isfinite(box.y1) && std::isfinite(box.x2) &&
           std::isfinite(box.y2);
}

}  // namespace

Box xywh_to_xyxy(const Box& box) {
    if (!finite_box(box)) {
        throw std::runtime_error("xywh box contains a non-finite value");
    }
    return {
        box.x1 - box.x2 / 2.0F,
        box.y1 - box.y2 / 2.0F,
        box.x1 + box.x2 / 2.0F,
        box.y1 + box.y2 / 2.0F,
    };
}

float box_iou(const Box& left, const Box& right) {
    if (!finite_box(left) || !finite_box(right)) {
        throw std::runtime_error("IoU box contains a non-finite value");
    }
    const float intersection_width =
        std::max(0.0F, std::min(left.x2, right.x2) - std::max(left.x1, right.x1));
    const float intersection_height =
        std::max(0.0F, std::min(left.y2, right.y2) - std::max(left.y1, right.y1));
    const float intersection = intersection_width * intersection_height;
    const float left_area =
        std::max(0.0F, left.x2 - left.x1) * std::max(0.0F, left.y2 - left.y1);
    const float right_area =
        std::max(0.0F, right.x2 - right.x1) * std::max(0.0F, right.y2 - right.y1);
    const float union_area = left_area + right_area - intersection;
    return union_area > 0.0F ? intersection / union_area : 0.0F;
}

PostprocessResult decode_yolov5_output(
    const std::vector<float>& raw_output,
    const std::vector<std::int64_t>& output_shape,
    const std::vector<std::string>& class_names,
    const LetterboxMetadata& metadata,
    const InferenceConfig& config
) {
    validate_config(config);
    if (output_shape.size() != 3U || output_shape[0] != 1 || output_shape[1] < 0 ||
        output_shape[2] != static_cast<std::int64_t>(5U + class_names.size())) {
        throw std::runtime_error("YOLOv5 output shape is incompatible with batch-1 classes");
    }
    const auto candidate_count = static_cast<std::size_t>(output_shape[1]);
    const auto attribute_count = static_cast<std::size_t>(output_shape[2]);
    if (raw_output.size() != candidate_count * attribute_count) {
        throw std::runtime_error("YOLOv5 output buffer size does not match its shape");
    }
    if (class_names.empty()) {
        throw std::runtime_error("YOLOv5 class names must not be empty");
    }

    std::vector<Candidate> candidates;
    candidates.reserve(candidate_count);
    for (std::size_t candidate_index = 0; candidate_index < candidate_count; ++candidate_index) {
        const std::size_t offset = candidate_index * attribute_count;
        for (std::size_t attribute = 0; attribute < attribute_count; ++attribute) {
            if (!std::isfinite(raw_output[offset + attribute])) {
                throw std::runtime_error("YOLOv5 output contains a non-finite value");
            }
        }
        const float objectness = raw_output[offset + 4U];
        if (objectness < 0.0F || objectness > 1.0F) {
            throw std::runtime_error("YOLOv5 objectness falls outside [0, 1]");
        }
        int class_id = 0;
        float class_score = raw_output[offset + 5U];
        for (std::size_t class_index = 0; class_index < class_names.size(); ++class_index) {
            const float score = raw_output[offset + 5U + class_index];
            if (score < 0.0F || score > 1.0F) {
                throw std::runtime_error("YOLOv5 class score falls outside [0, 1]");
            }
            if (score > class_score) {
                class_score = score;
                class_id = static_cast<int>(class_index);
            }
        }
        const float confidence = objectness * class_score;
        if (static_cast<double>(confidence) < config.confidence_threshold) {
            continue;
        }
        const Box xywh{
            raw_output[offset],
            raw_output[offset + 1U],
            raw_output[offset + 2U],
            raw_output[offset + 3U],
        };
        if (xywh.x2 <= 0.0F || xywh.y2 <= 0.0F) {
            throw std::runtime_error("thresholded YOLOv5 candidate has non-positive box size");
        }
        candidates.push_back(
            {candidate_index,
             class_id,
             objectness,
             class_score,
             confidence,
             xywh,
             xywh_to_xyxy(xywh)}
        );
    }

    std::vector<std::size_t> order(candidates.size());
    std::iota(order.begin(), order.end(), 0U);
    std::sort(order.begin(), order.end(), [&](std::size_t left_index, std::size_t right_index) {
        const Candidate& left = candidates[left_index];
        const Candidate& right = candidates[right_index];
        if (left.confidence != right.confidence) {
            return left.confidence > right.confidence;
        }
        if (left.class_id != right.class_id) {
            return left.class_id < right.class_id;
        }
        return left.candidate_index < right.candidate_index;
    });

    std::vector<std::size_t> kept;
    kept.reserve(std::min(candidates.size(), static_cast<std::size_t>(config.max_detections)));
    for (const std::size_t position : order) {
        if (kept.size() >= static_cast<std::size_t>(config.max_detections)) {
            break;
        }
        bool suppressed = false;
        for (const std::size_t kept_position : kept) {
            if (candidates[kept_position].class_id == candidates[position].class_id &&
                static_cast<double>(box_iou(
                    candidates[position].xyxy,
                    candidates[kept_position].xyxy
                )) > config.iou_threshold) {
                suppressed = true;
                break;
            }
        }
        if (!suppressed) {
            kept.push_back(position);
        }
    }

    PostprocessResult result;
    result.raw_candidate_count = candidate_count;
    result.threshold_candidate_count = candidates.size();
    result.nms_candidate_count = kept.size();
    result.detections.reserve(kept.size());
    for (const std::size_t position : kept) {
        const Candidate& candidate = candidates[position];
        const auto restored = restore_and_clip_box(candidate.xyxy, metadata);
        if (!restored.has_value()) {
            ++result.invalid_box_count;
            continue;
        }
        Detection detection;
        detection.rank = result.detections.size() + 1U;
        detection.candidate_index = candidate.candidate_index;
        detection.class_id = candidate.class_id;
        detection.class_name = class_names[static_cast<std::size_t>(candidate.class_id)];
        detection.objectness = round_six(candidate.objectness);
        detection.class_score = round_six(candidate.class_score);
        detection.confidence = round_six(candidate.confidence);
        detection.box_xywh_input = {
            round_six(candidate.xywh.x1),
            round_six(candidate.xywh.y1),
            round_six(candidate.xywh.x2),
            round_six(candidate.xywh.y2),
        };
        detection.box_xyxy_input = {
            round_six(candidate.xyxy.x1),
            round_six(candidate.xyxy.y1),
            round_six(candidate.xyxy.x2),
            round_six(candidate.xyxy.y2),
        };
        detection.box_xyxy_source = {
            round_six(restored->x1),
            round_six(restored->y1),
            round_six(restored->x2),
            round_six(restored->y2),
        };
        result.detections.push_back(std::move(detection));
    }
    return result;
}

}  // namespace edgeai::common
