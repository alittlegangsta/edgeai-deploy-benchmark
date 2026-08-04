import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


EVIDENCE = Path(__file__).parents[2] / "results" / "evidence" / "022"


class Task022NpuAuditTests(unittest.TestCase):
    def read(self, name):
        with (EVIDENCE / name).open(encoding="utf-8") as handle:
            return json.load(handle)

    def test_blocked_verdict_is_consistent(self):
        verdict = self.read("npu_feasibility_verdict.json")
        self.assertEqual(verdict["verdict"], "BLOCKED_DRIVER_OR_DEVICE")
        self.assertTrue(verdict["candidate_approved"])
        self.assertEqual(verdict["audit_review"]["status"], "PASS")
        self.assertEqual(verdict["official_one_shot"]["status"], "NOT_EXECUTED")
        self.assertFalse(verdict["official_one_shot"]["executed"])
        self.assertFalse(verdict["project_yolov5n_conversion_ready"])

    def test_board_audit_has_no_active_npu_nodes(self):
        board = self.read("npu_board_audit.json")
        self.assertFalse(board["modules"]["npu_or_cma_modules_loaded"])
        self.assertEqual(board["devices"]["npu_nodes"], [])
        self.assertEqual(board["devices"]["cma_nodes"], [])
        self.assertTrue(board["device_tree_and_sysfs"]["hard_npu_platform_node_present"])

    def test_dependency_matrix_covers_required_gaps(self):
        matrix = self.read("npu_dependency_matrix.json")
        requirements = {item["requirement"] for item in matrix["items"]}
        for required in ("hard_npu.ko", "soft_npu.ko", "cma_mem.ko", "npu_runtime library and C API headers", "convert_tool", "al_ai_flow"):
            self.assertIn(required, requirements)

    def test_inventory_hashes_are_sha256_or_explicitly_unavailable(self):
        inventory = self.read("npu_asset_inventory.json")
        pattern = re.compile(r"^[0-9a-f]{64}$")
        seen = 0
        for root in inventory["roots"]:
            for candidate in root.get("candidates", []):
                if candidate.get("sha256") is not None:
                    self.assertRegex(candidate["sha256"], pattern)
                    seen += 1
        self.assertGreater(seen, 0)

    def run_validator_with(self, mutate):
        script = Path(__file__).parents[2] / "scripts" / "vendor" / "validate_task022_npu_audit.py"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "evidence"
            shutil.copytree(EVIDENCE, target)
            mutate(target)
            return subprocess.run(
                [sys.executable, str(script), "--evidence-dir", str(target)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                check=False,
            )

    def test_validator_rejects_pass_without_device_nodes(self):
        def mutate(target):
            verdict = json.loads((target / "npu_feasibility_verdict.json").read_text())
            verdict["verdict"] = "PASS_VENDOR_ONE_SHOT"
            verdict["official_one_shot"] = {
                "executed": True,
                "status": "executed_successfully",
                "exit_code": 0,
            }
            (target / "npu_feasibility_verdict.json").write_text(json.dumps(verdict))

        result = self.run_validator_with(mutate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("device nodes", result.stdout)

    def test_validator_rejects_executed_without_run_evidence(self):
        def mutate(target):
            verdict = json.loads((target / "npu_feasibility_verdict.json").read_text())
            verdict["official_one_shot"] = {
                "executed": True,
                "status": "executed_successfully",
                "exit_code": 0,
            }
            (target / "npu_feasibility_verdict.json").write_text(json.dumps(verdict))

        result = self.run_validator_with(mutate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("run evidence is absent", result.stdout)

    def test_validator_rejects_armnn_candidate_as_runtime(self):
        def mutate(target):
            verdict = json.loads((target / "npu_feasibility_verdict.json").read_text())
            verdict["verdict"] = "PASS_VENDOR_ONE_SHOT"
            verdict["official_one_shot"] = {
                "executed": True,
                "status": "executed_successfully",
                "exit_code": 0,
            }
            (target / "npu_feasibility_verdict.json").write_text(json.dumps(verdict))
            matrix = json.loads((target / "npu_dependency_matrix.json").read_text())
            for item in matrix["items"]:
                if item["requirement"] == "npu_runtime library and C API headers":
                    item["status"] = "CANDIDATE_NOT_RUNTIME_PROOF"
            (target / "npu_dependency_matrix.json").write_text(json.dumps(matrix))

        result = self.run_validator_with(mutate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("READY standalone npu_runtime", result.stdout)


if __name__ == "__main__":
    unittest.main()
