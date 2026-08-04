import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
EVIDENCE = ROOT / "results" / "evidence" / "024"
VALIDATOR = ROOT / "scripts" / "vendor" / "validate_task024_npu_mapping.py"


class Task024NpuMappingTests(unittest.TestCase):
    def read(self, name):
        with (EVIDENCE / name).open(encoding="utf-8") as handle:
            return json.load(handle)

    def test_mapping_is_blocked_without_promoting_candidates(self):
        boot = self.read("board_boot_chain.json")
        matrix = self.read("board_mapping_matrix.json")
        self.assertEqual(boot["verdict"]["primary"], "BLOCKED_ACTIVE_BITSTREAM_IDENTITY")
        self.assertTrue(boot["access"]["current_board"]["reachable"])
        self.assertTrue(boot["access"]["current_board"]["current_observation_valid"])
        self.assertEqual(boot["active_boot_chain"]["status"], "CURRENT_READ_CONFIRMED")
        self.assertIn("BLOCKED_ACTIVE_BITSTREAM_IDENTITY", boot["verdict"]["primary"])
        self.assertTrue(all(row["controlled_deployment"] is False for row in matrix["rows"]))

    def test_current_dt_and_kernel_boundaries_remain_unresolved(self):
        dt = self.read("board_device_tree.json")
        kernel = self.read("board_kernel_provenance.json")
        self.assertTrue(dt["comparison"]["active_current_read_available"])
        self.assertFalse(dt["current_observation"]["hard_npu"]["driver_bound"])
        self.assertEqual(dt["current_observation"]["cma"]["size_bytes"], 134217728)
        self.assertEqual(
            kernel["vm_provenance"]["defconfig_symbols"]["CONFIG_MODVERSIONS"],
            "not set in candidate defconfig; active board value unknown",
        )
        self.assertEqual(
            kernel["driver_static_compatibility"]["modules"][0]["loadability"],
            "NOT_PROVEN",
        )

    def test_plan_is_read_only_and_sd_first(self):
        plan = self.read("controlled_deployment_plan.json")
        self.assertFalse(plan["executed"])
        self.assertEqual(plan["approval"], "NOT_GRANTED")
        self.assertIn("isolated SD card first", plan["recommended_media"])
        self.assertFalse(plan["safety"]["module_load_performed"])

    def test_validator_rejects_candidate_as_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "evidence"
            shutil.copytree(EVIDENCE, target)
            boot_path = target / "board_boot_chain.json"
            boot = json.loads(boot_path.read_text(encoding="utf-8"))
            boot["active_boot_chain"]["status"] = "VERIFIED_ACTIVE"
            boot_path.write_text(json.dumps(boot), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--evidence-dir", str(target)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("active boot chain", result.stdout)


if __name__ == "__main__":
    unittest.main()
