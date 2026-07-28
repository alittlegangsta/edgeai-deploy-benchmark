"""Synthetic, non-measured tests for the Task 017 ARM benchmark validator."""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/vendor/validate_anlogic_arm_benchmark.py"
SPEC = importlib.util.spec_from_file_location("validate_anlogic_arm_benchmark", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def environment(phase: str) -> dict:
    return {
        "schema_version": 1,
        "evidence_type": "task017_board_environment",
        "phase": phase,
        "board": {
            "model": "MLK-F3P-CZ02-DR1M90",
            "architecture": "aarch64",
            "os": "Buildroot 2022.02.6",
            "kernel": "6.1.111-rt42",
            "glibc": "2.25",
            "cpu_count": 2,
        },
        "memory": {"mem_total_kib": 1_012_000, "mem_available_kib": 800_000},
        "uptime_seconds": 1234.5,
        "load_average": [0.0, 0.01, 0.02],
        "governors": [{"path": "cpu0", "value": "ondemand"}],
        "available_frequencies_khz": [],
        "current_frequencies_khz": [{"path": "cpu0", "value": 1_000_000}],
        "thermal_zones": [{"path": "thermal_zone0", "temperature_millicelsius": 45_000}],
    }


def correctness() -> dict:
    return {
        "status": "PASS_TARGET",
        "detection_count": 5,
        "minimum_class_matched_iou": 0.999,
        "maximum_absolute_confidence_difference": 0.00001,
    }


def raw_payload(config_sha: str) -> dict:
    rounds = []
    aggregate_index = 0
    for round_number in range(1, 6):
        samples = []
        for iteration in range(1, 21):
            aggregate_index += 1
            preprocess = 1_000_000 + aggregate_index
            inference = 10_000_000 + aggregate_index
            postprocess = 2_000_000 + aggregate_index
            pipeline = preprocess + inference + postprocess
            samples.append(
                {
                    "round": round_number,
                    "iteration": iteration,
                    "aggregate_sample_index": aggregate_index,
                    "preprocess_ns": preprocess,
                    "inference_ns": inference,
                    "postprocess_ns": postprocess,
                    "pipeline_total_ns": pipeline,
                    "preprocess_ms": preprocess / 1_000_000.0,
                    "inference_ms": inference / 1_000_000.0,
                    "postprocess_ms": postprocess / 1_000_000.0,
                    "pipeline_ms": pipeline / 1_000_000.0,
                    "cpu_frequency_khz": None if iteration == 1 else 1_000_000,
                    "temperature_millicelsius": None if iteration == 1 else 45_000,
                    "error_status": None,
                }
            )
        rounds.append(
            {
                "round": round_number,
                "process_id": 1000 + round_number,
                "process_started_unix_ns": 10_000_000_000 + round_number,
                "model_load_ms": 25.0 + round_number,
                "executable_sha256": "a" * 64,
                "ncnn_manifest_sha256": VALIDATOR.EXPECTED_MANIFEST,
                "ncnn_param_sha256": VALIDATOR.EXPECTED_PARAM,
                "ncnn_bin_sha256": VALIDATOR.EXPECTED_BIN,
                "image_sha256": VALIDATOR.EXPECTED_INPUT,
                "inference_config_sha256": VALIDATOR.EXPECTED_CONFIG,
                "golden_result_sha256": VALIDATOR.EXPECTED_GOLDEN,
                "reference_detections_sha256": VALIDATOR.EXPECTED_GOLDEN,
                "runtime": {
                    "ncnn_version": "1.0.20240410",
                    "threads": 1,
                    "vulkan": False,
                    "fp16": False,
                    "bf16": False,
                    "int8": False,
                },
                "environment": {"architecture": "aarch64"},
                "warmup_iterations": 10,
                "formal_iterations": 20,
                "resource_measurement": {
                    "peak_rss_kib": 180_000 + round_number,
                    "peak_rss_bytes": (180_000 + round_number) * 1024,
                    "process_cpu_percent_one_core_basis": 99.0,
                },
                "correctness": {
                    "before_warmup": correctness(),
                    "after_measurement": correctness(),
                },
                "samples": samples,
            }
        )
    return {
        "schema_version": 2,
        "evidence_type": "task017_anlogic_arm_raw_benchmark",
        "backend": "cpp_ncnn",
        "benchmark_config_sha256": config_sha,
        "rounds": rounds,
    }


class AnlogicArmBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config_path = ROOT / "configs/benchmark_anlogic_arm.json"
        cls.contract_path = ROOT / "results/evidence/017/benchmark_contract.json"
        cls.config = json.loads(cls.config_path.read_text(encoding="utf-8"))
        cls.contract = json.loads(cls.contract_path.read_text(encoding="utf-8"))
        cls.config_sha = VALIDATOR.sha256_file(cls.config_path)

    def test_frozen_contract(self) -> None:
        VALIDATOR.validate_contract(self.config, self.contract, self.config_sha)
        self.assertFalse(self.contract["formal_data_collected"])
        self.assertFalse(self.contract["published_performance_values"])

    def test_valid_fixture_recomputes_all_statistics(self) -> None:
        summary = VALIDATOR.validate_and_summarize(
            raw_payload(self.config_sha),
            self.config,
            self.config_sha,
            environment("before"),
            environment("after"),
        )
        self.assertEqual(summary["sample_count"], 100)
        self.assertEqual(summary["valid_process_rounds"], 5)
        self.assertEqual(summary["statistics"]["pipeline"]["count"], 100)
        self.assertGreater(summary["statistics"]["pipeline"]["sample_standard_deviation_ms"], 0)
        self.assertGreater(summary["pipeline_fps_batch1_sequential"], 0)
        self.assertEqual(summary["correctness_before_after"], "PASS_TARGET")
        self.assertEqual(summary["benchmark_status"], "PASS_CANDIDATE_REQUIRES_HUMAN_REVIEW")
        self.assertFalse(summary["candidate_approved"])

    def test_user_approved_fixture_is_final(self) -> None:
        review = VALIDATOR.human_review_record(
            approve_candidate=True,
            source="user",
            recorded_at="2026-07-28T18:00:25+08:00",
        )
        summary = VALIDATOR.validate_and_summarize(
            raw_payload(self.config_sha),
            self.config,
            self.config_sha,
            environment("before"),
            environment("after"),
            review,
        )
        self.assertEqual(summary["benchmark_status"], "PASS")
        self.assertEqual(summary["formal_publication"], "APPROVED_BASELINE")
        self.assertEqual(summary["human_review"], "PASS")
        self.assertEqual(summary["human_review_source"], "user")
        self.assertTrue(summary["candidate_approved"])

    def test_rejects_approval_without_user_source(self) -> None:
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "review source must be user"
        ):
            VALIDATOR.human_review_record(
                approve_candidate=True,
                source=None,
                recorded_at="2026-07-28T18:00:25+08:00",
            )

    def test_rejects_incomplete_round(self) -> None:
        payload = raw_payload(self.config_sha)
        payload["rounds"][0]["samples"].pop()
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "20 samples"):
            VALIDATOR.validate_and_summarize(
                payload,
                self.config,
                self.config_sha,
                environment("before"),
                environment("after"),
            )

    def test_rejects_non_exact_stage_sum(self) -> None:
        payload = raw_payload(self.config_sha)
        payload["rounds"][0]["samples"][0]["pipeline_total_ns"] += 1
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "exact stage sum"):
            VALIDATOR.validate_and_summarize(
                payload,
                self.config,
                self.config_sha,
                environment("before"),
                environment("after"),
            )

    def test_rejects_process_reuse(self) -> None:
        payload = raw_payload(self.config_sha)
        payload["rounds"][1]["process_id"] = payload["rounds"][0]["process_id"]
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "process id was reused"):
            VALIDATOR.validate_and_summarize(
                payload,
                self.config,
                self.config_sha,
                environment("before"),
                environment("after"),
            )

    def test_rejects_failed_correctness(self) -> None:
        payload = raw_payload(self.config_sha)
        payload["rounds"][4]["correctness"]["after_measurement"]["detection_count"] = 4
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "detections differ"):
            VALIDATOR.validate_and_summarize(
                payload,
                self.config,
                self.config_sha,
                environment("before"),
                environment("after"),
            )

    def test_rejects_latency_based_filtering_contract(self) -> None:
        config = copy.deepcopy(self.config)
        config["rounds"]["latency_outlier_removal"] = True
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "outlier policy differs"):
            VALIDATOR.validate_contract(config, self.contract, self.config_sha)


if __name__ == "__main__":
    unittest.main()
