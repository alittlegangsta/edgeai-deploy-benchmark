import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/vendor/audit_task031_official_npu_assets.py"
EVIDENCE = ROOT / "results/evidence/031"


class Task031OfficialNpuAssetTests(unittest.TestCase):
    def test_checked_evidence_validates(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--validate"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_verdict_is_scoped_and_not_reopenable(self):
        verdict = json.loads((EVIDENCE / "compatibility_verdict.json").read_text(encoding="utf-8"))
        self.assertEqual(verdict["primary_verdict"], "BLOCKED_EXTERNAL_VENDOR_DEPENDENCY")
        self.assertFalse(verdict["new_assets_sufficient_to_reopen_yolov5n"])
        self.assertIn("audited AArch64 libarmnn.so.32.1", verdict["scope"])

    def test_face_has_no_serialized_alhardnpu_node(self):
        provenance = json.loads((EVIDENCE / "face_onnx_provenance.json").read_text(encoding="utf-8"))
        self.assertFalse(provenance["custom_op_audit"]["alhardnpu_domain_or_op_in_onnx"])
        self.assertEqual(provenance["custom_op_audit"]["alhardnpu_node_count"], 0)
        self.assertEqual(provenance["onnx_provenance"]["opsets"][0]["version"], 14)

    def test_capability_boundary_has_fused_and_generic_paths(self):
        inventory = json.loads((EVIDENCE / "armnn_backend_inventory.json").read_text(encoding="utf-8"))
        audit = inventory["capability_audit"]
        self.assertIn("IsALHardNPUSupported", audit["alnpu_overrides"])
        self.assertIn("IsConvolution2dSupported", audit["generic_methods_default_reject"])
        self.assertTrue(audit["alhardnpu_fusion_symbols_present"])
        self.assertFalse(audit["generic_support_build_found"])

    def test_hpf_matrix_does_not_promote_geg484_to_geg400(self):
        matrix = json.loads((EVIDENCE / "npu_yolo_hpf_matrix.json").read_text(encoding="utf-8"))
        self.assertFalse(matrix["geg400_official_yolo_hpf_or_td_found"])
        self.assertTrue(all("GEG484" in item["device"] or "MEG484" in item["device"] for item in matrix["d20_hpf"]))

    def test_evidence_is_text_only_and_portable(self):
        forbidden = ("/mnt/c/Users/", "/home/", "C:\\Users\\")
        for path in EVIDENCE.glob("*.json"):
            self.assertNotIn("-----BEGIN ", path.read_text(encoding="utf-8"))
            text = path.read_text(encoding="utf-8")
            for marker in forbidden:
                self.assertNotIn(marker, text, path.name)


if __name__ == "__main__":
    unittest.main()
