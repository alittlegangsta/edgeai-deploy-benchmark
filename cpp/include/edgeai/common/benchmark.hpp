#pragma once

#include "edgeai/common/detection.hpp"

#include <cstdint>
#include <vector>

namespace edgeai::common {

struct BenchmarkSampleNs {
    std::int64_t preprocess{0};
    std::int64_t inference{0};
    std::int64_t postprocess{0};
    std::int64_t pipeline_total{0};
};

struct DetectionComparison {
    std::size_t detection_count{0};
    double minimum_class_matched_iou{1.0};
    double maximum_absolute_confidence_difference{0.0};
};

BenchmarkSampleNs make_benchmark_sample(
    std::int64_t preprocess_ns,
    std::int64_t inference_ns,
    std::int64_t postprocess_ns
);

double process_cpu_percent_one_core_basis(
    double process_cpu_seconds_delta,
    double wall_clock_seconds_delta
);

DetectionComparison compare_benchmark_detections(
    const std::vector<Detection>& reference,
    const std::vector<Detection>& candidate,
    double minimum_iou,
    double maximum_confidence_difference
);

}  // namespace edgeai::common
