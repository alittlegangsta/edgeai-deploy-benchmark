"""Focused tests for the Task 012 campaign and acceptance generator."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "generate_pc_acceptance", ROOT / "scripts/generate_pc_acceptance.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PcAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment_before = {
            name: os.environ.get(name)
            for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                         "NUMEXPR_NUM_THREADS")
        }
        for name in self.environment_before:
            os.environ[name] = "1"
        self.config_path = ROOT / "configs/benchmark_pc_three_backend.json"
        self.base_path = ROOT / "configs/benchmark_pc.json"
        self.config, _ = MODULE.load_and_validate_config(self.config_path, self.base_path)

    def tearDown(self) -> None:
        for name, value in self.environment_before.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def process_fragment(self, backend: str) -> dict:
        source_names = {
            "python_ort": "pc_python_ort.json",
            "cpp_ort": "pc_cpp_ort.json",
            "cpp_ncnn": "pc_cpp_ncnn.json",
        }
        source = json.loads(
            (ROOT / "results/benchmarks" / source_names[backend]).read_text(encoding="utf-8")
        )
        source["rounds"] = [source["rounds"][0]]
        return source

    def campaign_payload(self, backend: str) -> dict:
        entries = []
        for campaign_round, order in enumerate(MODULE.EXPECTED_ORDER, 1):
            position = order.index(backend) + 1
            payload = copy.deepcopy(self.process_fragment(backend))
            process_round = payload["rounds"][0]
            process_round["process_id"] = 10_000 + campaign_round
            process_round["process_started_unix_ns"] = 1_000_000_000 + campaign_round
            entries.append({
                "campaign_round": campaign_round,
                "position": position,
                "sequence_index": (campaign_round - 1) * 3 + position,
                "source_process_round_argument": 1,
                "source_fragment_sha256": "0" * 64,
                "source_payload_canonical_sha256": MODULE.sha256_json(payload),
                "process_id": process_round["process_id"],
                "process_started_unix_ns": process_round["process_started_unix_ns"],
                "process_payload": payload,
            })
        return {
            "schema_version": 1,
            "evidence_type": "task012_three_backend_raw_campaign",
            "methodology_id": self.config["methodology_id"],
            "backend": backend,
            "campaign_config_sha256": MODULE.sha256_file(self.config_path),
            "base_process_config_sha256": MODULE.sha256_file(self.base_path),
            "raw_process_payloads_unmodified": True,
            "rounds": entries,
        }

    def test_config_and_position_balance(self) -> None:
        self.assertEqual(self.config["rounds"]["count"], 6)
        for backend in MODULE.BACKENDS:
            positions = [row.index(backend) + 1 for row in MODULE.EXPECTED_ORDER]
            self.assertEqual(sorted(positions), [1, 1, 2, 2, 3, 3])
        self.assertEqual(MODULE.validate_environment(self.config), {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        })

    def test_existing_process_fragments_satisfy_frozen_contract(self) -> None:
        base_sha = MODULE.sha256_file(self.base_path)
        for backend in MODULE.BACKENDS:
            process_round = MODULE.validate_process_payload(
                self.process_fragment(backend), backend, base_sha, self.config
            )
            self.assertEqual(len(process_round["samples"]), 100)

    def test_six_round_summary_has_600_samples_and_position_groups(self) -> None:
        for backend in MODULE.BACKENDS:
            summary = MODULE.summarize_backend(
                self.campaign_payload(backend), backend, self.config,
                MODULE.sha256_file(self.config_path), MODULE.sha256_file(self.base_path)
            )
            self.assertEqual(summary["sample_count"], 600)
            self.assertEqual(len(summary["rounds"]), 6)
            self.assertEqual([item["stages"]["pipeline_total"]["count"]
                              for item in summary["positions"]], [200, 200, 200])
            self.assertEqual(summary["aggregate"][
                "six_round_pipeline_mean_max_relative_difference_percent"], 0.0)
            self.assertEqual(summary["aggregate"]["position_pipeline_mean_spread_percent"], 0.0)

    def test_stage_sum_drift_is_rejected(self) -> None:
        payload = self.process_fragment("python_ort")
        payload["rounds"][0]["samples"][0]["pipeline_total_ns"] += 1
        with self.assertRaisesRegex(MODULE.AcceptanceError, "exact stage sum"):
            MODULE.validate_process_payload(
                payload, "python_ort", MODULE.sha256_file(self.base_path), self.config
            )

    def test_csv_uses_lf_and_contains_round_position_and_aggregate(self) -> None:
        summaries = [
            MODULE.summarize_backend(
                self.campaign_payload(backend), backend, self.config,
                MODULE.sha256_file(self.config_path), MODULE.sha256_file(self.base_path)
            )
            for backend in MODULE.BACKENDS
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.csv"
            MODULE.write_summary_csv(path, summaries)
            raw = path.read_bytes()
            self.assertNotIn(b"\r\n", raw)
            text = raw.decode("utf-8")
            self.assertIn("python_ort,round,1,1,pipeline_total", text)
            self.assertIn("cpp_ort,position,,2,pipeline_total", text)
            self.assertIn("cpp_ncnn,aggregate,,,pipeline_total", text)

    def test_generated_markdown_records_pc_completion_without_arm_claim(self) -> None:
        summary = {
            "model_relationship": self.config["workload"]["model_relationship"],
            "summaries": [
                MODULE.summarize_backend(
                    self.campaign_payload(backend), backend, self.config,
                    MODULE.sha256_file(self.config_path), MODULE.sha256_file(self.base_path)
                )
                for backend in MODULE.BACKENDS
            ],
        }
        readme = MODULE.render_readme(summary)
        self.assertIn("Tasks 001–012 are completed", readme)
        self.assertIn("Checkpoint C is human-approved", readme)
        self.assertIn("Stage 2", readme)
        self.assertIn("has not been implemented", readme)
        self.assertIn("Not implemented / Planned", readme)
        self.assertNotIn("blocked only", readme)
        self.assertNotIn("ARM performance result exists", readme)
        self.assertNotIn("/home/dministrator", readme)
        self.assertIn("Final PC performance", readme)
        self.assertIn("Running-position effect", readme)
        self.assertIn("Peak RSS", readme)
        self.assertIn("separately frozen TorchScript-to-pnnx", readme)
        self.assertIn("build/reproduction/", readme)
        self.assertNotIn("--output-json results/evidence/004/", readme)
        self.assertNotIn("--output-json results/evidence/007/", readme)
        self.assertNotIn("--output-json results/evidence/008/", readme)
        self.assertNotIn("--output-json results/evidence/011/", readme)


if __name__ == "__main__":
    unittest.main()
