import json
import hashlib
import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "validate_task033_arm_cpu_optimization.py"
SMOKE = ROOT / "results" / "evidence" / "033" / "host_profiler_smoke.json"
MATRIX = ROOT / "results" / "evidence" / "033" / "experiment_matrix.json"
SUMMARY = ROOT / "results" / "evidence" / "033" / "optimization_summary.json"


class Task033ValidationTests(unittest.TestCase):
    def test_host_smoke_schema_is_recomputed(self):
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR), str(SMOKE)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_invalid_pipeline_rejected(self):
        payload = json.loads(SMOKE.read_text(encoding="utf-8"))
        payload["samples"][0]["pipeline_ns"] += 1
        broken = ROOT / "build" / "task033-invalid-profiler.json"
        broken.write_text(json.dumps(payload), encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, str(VALIDATOR), str(broken)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
        finally:
            broken.unlink(missing_ok=True)

    def test_arm_matrix_references_retained_results(self):
        matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        self.assertEqual(matrix["status"], "PASS_TARGET")
        self.assertEqual(matrix["board"]["logical_cpu_count"], 2)
        self.assertEqual(matrix["selection"]["best_accepted"], "threads2_default_packing_on")
        self.assertEqual(len(matrix["experiments"]), 9)
        self.assertEqual({row["id"] for row in matrix["skipped"]}, {"threads3", "threads4"})
        for row in matrix["experiments"]:
            result = ROOT / row["result"]
            self.assertTrue(result.is_file(), result)
            digest = hashlib.sha256(result.read_bytes()).hexdigest()
            self.assertEqual(digest, row["result_sha256"], row["id"])
        self.assertEqual(
            summary["best_configuration"]["id"],
            matrix["selection"]["best_accepted"],
        )


if __name__ == "__main__":
    unittest.main()
