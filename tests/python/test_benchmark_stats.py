"""Unit tests for the unified Task 009 statistics and correctness helpers."""

from __future__ import annotations

import unittest

from edgeai_benchmark.benchmark import (
    BenchmarkError,
    compare_detections,
    maximum_relative_difference,
    nearest_rank,
    sample_from_boundaries,
    summarize_ns,
)


class BenchmarkStatisticsTests(unittest.TestCase):
    def test_nearest_rank_even_count(self) -> None:
        values = [40.0, 10.0, 30.0, 20.0]
        self.assertEqual(nearest_rank(values, 0.50), 20.0)
        self.assertEqual(nearest_rank(values, 0.90), 40.0)

    def test_nearest_rank_rejects_empty_and_invalid_values(self) -> None:
        with self.assertRaises(BenchmarkError):
            nearest_rank([], 0.5)
        with self.assertRaises(BenchmarkError):
            nearest_rank([1.0, float("nan")], 0.5)

    def test_summary_converts_nanoseconds_once(self) -> None:
        summary = summarize_ns([1_000_000, 2_000_000, 3_000_000, 4_000_000])
        self.assertEqual(summary["count"], 4)
        self.assertEqual(summary["mean_ms"], 2.5)
        self.assertEqual(summary["p50_ms"], 2.0)
        self.assertEqual(summary["p90_ms"], 4.0)
        self.assertEqual(summary["min_ms"], 1.0)
        self.assertEqual(summary["max_ms"], 4.0)

    def test_pipeline_total_is_exact_unrounded_sum(self) -> None:
        sample = sample_from_boundaries(11, 22, 33)
        self.assertEqual(sample["pipeline_total_ns"], 66)
        with self.assertRaises(BenchmarkError):
            sample_from_boundaries(-1, 2, 3)

    def test_maximum_relative_difference(self) -> None:
        self.assertAlmostEqual(maximum_relative_difference([10.0, 11.0, 10.5]), 10.0)
        with self.assertRaises(BenchmarkError):
            maximum_relative_difference([0.0, 1.0])

    def test_detection_matching_handles_duplicate_classes(self) -> None:
        reference = [
            {
                "class_id": 64,
                "class_name": "mouse",
                "confidence": 0.8,
                "box_xyxy_source": [0.0, 0.0, 10.0, 10.0],
            },
            {
                "class_id": 64,
                "class_name": "mouse",
                "confidence": 0.6,
                "box_xyxy_source": [20.0, 20.0, 30.0, 30.0],
            },
        ]
        candidate = [
            {
                "class_id": 64,
                "class_name": "mouse",
                "confidence": 0.6005,
                "box_xyxy_source": [20.0, 20.0, 30.0, 30.0],
            },
            {
                "class_id": 64,
                "class_name": "mouse",
                "confidence": 0.8005,
                "box_xyxy_source": [0.0, 0.0, 10.0, 10.0],
            },
        ]
        result = compare_detections(reference, candidate, 0.99, 0.001)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["detection_count"], 2)
        self.assertEqual(result["minimum_class_matched_iou"], 1.0)

    def test_detection_mismatch_fails(self) -> None:
        with self.assertRaises(BenchmarkError):
            compare_detections([], [{"class_id": 1}], 0.99, 0.001)


if __name__ == "__main__":
    unittest.main()
