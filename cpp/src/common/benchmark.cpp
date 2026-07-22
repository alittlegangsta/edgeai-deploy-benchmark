#include "edgeai/common/benchmark.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

namespace edgeai::common {
namespace {

double benchmark_box_iou(const Box& left, const Box& right) {
    const double intersection_width = std::max(
        0.0,
        std::min(static_cast<double>(left.x2), static_cast<double>(right.x2)) -
            std::max(static_cast<double>(left.x1), static_cast<double>(right.x1))
    );
    const double intersection_height = std::max(
        0.0,
        std::min(static_cast<double>(left.y2), static_cast<double>(right.y2)) -
            std::max(static_cast<double>(left.y1), static_cast<double>(right.y1))
    );
    const double intersection = intersection_width * intersection_height;
    const double left_area =
        std::max(0.0, static_cast<double>(left.x2 - left.x1)) *
        std::max(0.0, static_cast<double>(left.y2 - left.y1));
    const double right_area =
        std::max(0.0, static_cast<double>(right.x2 - right.x1)) *
        std::max(0.0, static_cast<double>(right.y2 - right.y1));
    const double union_area = left_area + right_area - intersection;
    return union_area > 0.0 ? intersection / union_area : 0.0;
}

}  // namespace

BenchmarkSampleNs make_benchmark_sample(
    std::int64_t preprocess_ns,
    std::int64_t inference_ns,
    std::int64_t postprocess_ns
) {
    if (preprocess_ns < 0 || inference_ns < 0 || postprocess_ns < 0) {
        throw std::runtime_error("benchmark stage durations must be nonnegative");
    }
    if (preprocess_ns > std::numeric_limits<std::int64_t>::max() - inference_ns ||
        preprocess_ns + inference_ns >
            std::numeric_limits<std::int64_t>::max() - postprocess_ns) {
        throw std::runtime_error("benchmark pipeline duration overflows int64");
    }
    return {
        preprocess_ns,
        inference_ns,
        postprocess_ns,
        preprocess_ns + inference_ns + postprocess_ns,
    };
}

double process_cpu_percent_one_core_basis(
    double process_cpu_seconds_delta,
    double wall_clock_seconds_delta
) {
    if (!std::isfinite(process_cpu_seconds_delta) || process_cpu_seconds_delta < 0.0 ||
        !std::isfinite(wall_clock_seconds_delta) || wall_clock_seconds_delta <= 0.0) {
        throw std::runtime_error("CPU utilization deltas must be finite and positive");
    }
    return 100.0 * process_cpu_seconds_delta / wall_clock_seconds_delta;
}

DetectionComparison compare_benchmark_detections(
    const std::vector<Detection>& reference,
    const std::vector<Detection>& candidate,
    double minimum_iou,
    double maximum_confidence_difference
) {
    if (reference.size() != candidate.size()) {
        throw std::runtime_error("benchmark correctness detection count differs");
    }
    if (!std::isfinite(minimum_iou) || minimum_iou < 0.0 || minimum_iou > 1.0 ||
        !std::isfinite(maximum_confidence_difference) ||
        maximum_confidence_difference < 0.0) {
        throw std::runtime_error("benchmark correctness tolerance is invalid");
    }
    std::vector<bool> matched(candidate.size(), false);
    DetectionComparison result;
    result.detection_count = candidate.size();
    for (const auto& expected : reference) {
        std::size_t best_index = candidate.size();
        double best_iou = -1.0;
        for (std::size_t index = 0; index < candidate.size(); ++index) {
            if (matched[index] || candidate[index].class_id != expected.class_id ||
                candidate[index].class_name != expected.class_name) {
                continue;
            }
            const double overlap =
                benchmark_box_iou(expected.box_xyxy_source, candidate[index].box_xyxy_source);
            if (overlap > best_iou) {
                best_iou = overlap;
                best_index = index;
            }
        }
        if (best_index == candidate.size()) {
            throw std::runtime_error("benchmark correctness class match is missing");
        }
        const double confidence_difference = std::abs(
            static_cast<double>(expected.confidence) -
            static_cast<double>(candidate[best_index].confidence)
        );
        if (best_iou < minimum_iou) {
            throw std::runtime_error("benchmark correctness IoU is below tolerance");
        }
        if (confidence_difference > maximum_confidence_difference) {
            throw std::runtime_error("benchmark correctness confidence differs beyond tolerance");
        }
        matched[best_index] = true;
        result.minimum_class_matched_iou =
            std::min(result.minimum_class_matched_iou, best_iou);
        result.maximum_absolute_confidence_difference = std::max(
            result.maximum_absolute_confidence_difference,
            confidence_difference
        );
    }
    return result;
}

}  // namespace edgeai::common
