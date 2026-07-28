"""Synthetic, non-measured tests for the Task 018 threading validator."""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/vendor/validate_anlogic_arm_threading_experiment.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_anlogic_arm_threading_experiment", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def detections() -> list[dict]:
    values = []
    for rank, (class_id, class_name) in enumerate(
        ((66, "keyboard"), (62, "tv"), (41, "cup"), (64, "mouse"), (64, "mouse"))
    ):
        left = 100.0 + rank * 20.0
        top = 120.0 + rank * 15.0
        values.append(
            {
                "rank": rank,
                "class_id": class_id,
                "class_name": class_name,
                "confidence": 0.9 - rank * 0.1,
                "box_xyxy_source": [left, top, left + 50.0, top + 40.0],
            }
        )
    return values


def correctness() -> dict:
    return {
        "status": "PASS_TARGET",
        "detection_count": 5,
        "minimum_class_matched_iou": 0.9999,
        "maximum_absolute_confidence_difference": 0.00001,
        "detections": detections(),
    }


def raw_payload(
    config_sha: str,
    configured_threads: int,
    *,
    inference_ns: int,
    unstable: bool = False,
) -> dict:
    rounds = []
    for pair in range(1, 6):
        execution_order = VALIDATOR.expected_order(pair, configured_threads)
        samples = []
        round_inference = inference_ns * 2 if unstable and pair == 5 else inference_ns
        for iteration in range(1, 21):
            preprocess = 42_000_000 + pair * 1000 + iteration
            inference = round_inference + pair * 1000 + iteration
            postprocess = 54_000_000 + pair * 1000 + iteration
            pipeline = preprocess + inference + postprocess
            samples.append(
                {
                    "round": pair,
                    "pair_index": pair,
                    "execution_order": execution_order,
                    "configured_threads": configured_threads,
                    "iteration": iteration,
                    "aggregate_sample_index": (pair - 1) * 20 + iteration,
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
                "round": pair,
                "pair_index": pair,
                "execution_order": execution_order,
                "thread_condition": configured_threads,
                "process_id": configured_threads * 1000 + pair,
                "process_started_unix_ns": configured_threads * 10_000_000 + pair,
                "model_load_ms": 630.0 + pair,
                "executable_sha256": "a" * 64,
                "ncnn_manifest_sha256": VALIDATOR.TASK017.EXPECTED_MANIFEST,
                "ncnn_param_sha256": VALIDATOR.TASK017.EXPECTED_PARAM,
                "ncnn_bin_sha256": VALIDATOR.TASK017.EXPECTED_BIN,
                "image_sha256": VALIDATOR.TASK017.EXPECTED_INPUT,
                "inference_config_sha256": VALIDATOR.TASK017.EXPECTED_CONFIG,
                "golden_result_sha256": VALIDATOR.TASK017.EXPECTED_GOLDEN,
                "runtime": {
                    "ncnn_version": "1.0.20240410",
                    "threads": configured_threads,
                    "configured_threads": configured_threads,
                    "vulkan": False,
                    "fp16": False,
                    "bf16": False,
                    "int8": False,
                },
                "environment": {"architecture": "aarch64"},
                "warmup_iterations": 10,
                "formal_iterations": 20,
                "resource_measurement": {
                    "peak_rss_kib": 142_000 + configured_threads * 100 + pair,
                    "peak_rss_bytes": (
                        142_000 + configured_threads * 100 + pair
                    )
                    * 1024,
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
        "schema_version": 3,
        "evidence_type": "task018_anlogic_arm_threading_raw_benchmark",
        "backend": "cpp_ncnn",
        "benchmark_config_sha256": config_sha,
        "rounds": rounds,
    }


def process_environment() -> dict:
    events = []
    for pair, executions in VALIDATOR.EXPECTED_SCHEDULE:
        for execution_order, configured_threads in executions:
            for phase in ("before", "after"):
                events.append(
                    {
                        "pair_index": pair,
                        "execution_order": execution_order,
                        "configured_threads": configured_threads,
                        "phase": phase,
                        "board_model": "MLK-F3P-CZ02-DR1M90",
                        "architecture": "aarch64",
                        "load_average": [0.0, 0.01, 0.02],
                        "cpu_frequency_khz": None,
                        "temperature_millicelsius": None,
                    }
                )
    return {
        "schema_version": 1,
        "evidence_type": "task018_process_environment",
        "system_modification": False,
        "new_runtime_dependencies": False,
        "events": events,
    }


class AnlogicArmThreadingExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config_path = ROOT / "configs/benchmark_anlogic_arm_threading.json"
        cls.contract_path = ROOT / "results/evidence/018/experiment_contract.json"
        cls.order_path = ROOT / "results/evidence/018/execution_order.json"
        cls.config = json.loads(cls.config_path.read_text(encoding="utf-8"))
        cls.contract = json.loads(cls.contract_path.read_text(encoding="utf-8"))
        cls.order = json.loads(cls.order_path.read_text(encoding="utf-8"))
        cls.config_sha = VALIDATOR.sha256_file(cls.config_path)

    def summarize(
        self,
        threads1: dict,
        threads2: dict,
        environment: dict | None = None,
    ) -> tuple[dict, dict, dict, dict]:
        return VALIDATOR.validate_and_summarize(
            threads1_raw=threads1,
            threads2_raw=threads2,
            process_environment=environment or process_environment(),
            config=self.config,
            config_sha=self.config_sha,
        )

    def test_frozen_contract_and_order(self) -> None:
        VALIDATOR.validate_contract(
            self.config,
            self.contract,
            self.order,
            self.config_sha,
            VALIDATOR.sha256_file(self.order_path),
        )
        self.assertFalse(self.contract["formal_data_collected"])

    def test_beneficial_fixture(self) -> None:
        _, _, comparison, validation = self.summarize(
            raw_payload(self.config_sha, 1, inference_ns=3_418_000_000),
            raw_payload(self.config_sha, 2, inference_ns=2_600_000_000),
        )
        self.assertEqual(comparison["classification"], "BENEFICIAL")
        self.assertGreaterEqual(comparison["pipeline_speedup"], 1.05)
        self.assertEqual(validation["status"], "PASS_CANDIDATE_REQUIRES_HUMAN_REVIEW")

    def test_neutral_fixture(self) -> None:
        _, _, comparison, _ = self.summarize(
            raw_payload(self.config_sha, 1, inference_ns=3_418_000_000),
            raw_payload(self.config_sha, 2, inference_ns=3_450_000_000),
        )
        self.assertEqual(comparison["classification"], "NEUTRAL")

    def test_regression_fixture(self) -> None:
        _, _, comparison, _ = self.summarize(
            raw_payload(self.config_sha, 1, inference_ns=3_418_000_000),
            raw_payload(self.config_sha, 2, inference_ns=3_700_000_000),
        )
        self.assertEqual(comparison["classification"], "REGRESSION")

    def test_correctness_failure_is_rejected(self) -> None:
        threads2 = raw_payload(self.config_sha, 2, inference_ns=2_600_000_000)
        threads2["rounds"][2]["correctness"]["after_measurement"]["detection_count"] = 4
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "detection count"):
            self.summarize(
                raw_payload(self.config_sha, 1, inference_ns=3_418_000_000),
                threads2,
            )

    def test_stability_failure_classifies_regression(self) -> None:
        threads2_summary = self.summarize(
            raw_payload(self.config_sha, 1, inference_ns=3_418_000_000),
            raw_payload(
                self.config_sha,
                2,
                inference_ns=2_600_000_000,
                unstable=True,
            ),
        )
        self.assertEqual(threads2_summary[1]["stability_status"], "FAIL")
        self.assertEqual(threads2_summary[2]["classification"], "REGRESSION")

    def test_insufficient_sample_count_is_rejected(self) -> None:
        threads1 = raw_payload(self.config_sha, 1, inference_ns=3_418_000_000)
        threads1["rounds"][0]["samples"].pop()
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "20 samples"):
            self.summarize(
                threads1,
                raw_payload(self.config_sha, 2, inference_ns=2_600_000_000),
            )

    def test_wrong_thread_condition_is_rejected(self) -> None:
        threads2 = raw_payload(self.config_sha, 2, inference_ns=2_600_000_000)
        threads2["rounds"][0]["runtime"]["configured_threads"] = 1
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "configured threads"):
            self.summarize(
                raw_payload(self.config_sha, 1, inference_ns=3_418_000_000),
                threads2,
            )

    def test_wrong_execution_order_is_rejected(self) -> None:
        threads1 = raw_payload(self.config_sha, 1, inference_ns=3_418_000_000)
        threads1["rounds"][1]["execution_order"] = 1
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "execution order"):
            self.summarize(
                threads1,
                raw_payload(self.config_sha, 2, inference_ns=2_600_000_000),
            )

    def test_task017_history_drift_is_warning_only(self) -> None:
        _, _, comparison, validation = self.summarize(
            raw_payload(self.config_sha, 1, inference_ns=5_000_000_000),
            raw_payload(self.config_sha, 2, inference_ns=4_000_000_000),
        )
        self.assertEqual(
            comparison["task017_historical_consistency"]["status"],
            "WARNING_ENVIRONMENT_DRIFT",
        )
        self.assertEqual(validation["status"], "PASS_CANDIDATE_REQUIRES_HUMAN_REVIEW")

    def test_json_null_environment_fields_are_preserved(self) -> None:
        env = process_environment()
        self.assertTrue(
            all(
                event["cpu_frequency_khz"] is None
                and event["temperature_millicelsius"] is None
                for event in env["events"]
            )
        )
        _, _, comparison, _ = self.summarize(
            raw_payload(self.config_sha, 1, inference_ns=3_418_000_000),
            raw_payload(self.config_sha, 2, inference_ns=2_600_000_000),
            env,
        )
        self.assertEqual(comparison["cross_condition_correctness"]["status"], "PASS_TARGET")

    def test_classification_flags_correctness_and_resource_regression(self) -> None:
        self.assertEqual(
            VALIDATOR.classify_result(
                pipeline_speedup=1.2,
                threads1_p90_ms=10.0,
                threads2_p90_ms=9.0,
                threads2_correctness=False,
            ),
            "REGRESSION",
        )
        self.assertEqual(
            VALIDATOR.classify_result(
                pipeline_speedup=1.2,
                threads1_p90_ms=10.0,
                threads2_p90_ms=9.0,
                runtime_resource_issue=True,
            ),
            "REGRESSION",
        )


if __name__ == "__main__":
    unittest.main()
