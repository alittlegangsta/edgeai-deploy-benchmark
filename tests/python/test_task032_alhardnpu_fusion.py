import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/vendor/audit_task032_alhardnpu_fusion.py"
EVIDENCE = ROOT / "results/evidence/032"


class Task032AlhardnpuFusionTests(unittest.TestCase):
    def test_validator_passes(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--validate"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_conclusion_is_conservative(self):
        verdict = json.loads((EVIDENCE / "fusion_eligibility_verdict.json").read_text(encoding="utf-8"))
        self.assertEqual(verdict["conclusion"], "FUSION_PREDICATE_NOT_RECOVERABLE")
        self.assertEqual(verdict["task028_status_unchanged"], "BLOCKED_EXTERNAL_VENDOR_DEPENDENCY")
        self.assertFalse(verdict["safety"]["board_accessed"])

    def test_dispatch_and_face_assignment_boundaries(self):
        symbols = json.loads((EVIDENCE / "fusion_symbol_audit.json").read_text(encoding="utf-8"))
        face = json.loads((EVIDENCE / "face_fusion_regions.json").read_text(encoding="utf-8"))
        self.assertIn("IsALHardNPUSupported", symbols["alnpu_layer_support"]["overrides"])
        self.assertIn("IsConvolution2dSupported", symbols["alnpu_layer_support"]["generic_layer_support_base_symbols"])
        self.assertEqual(face["observed_fused_assignment_count"], 3)
        self.assertEqual(face["fusion_interpretation"]["exact_region_mapping"], "NOT_RECOVERABLE")

    def test_al_onnx_pass_does_not_claim_native_fusion(self):
        audit = json.loads((EVIDENCE / "al_onnx_pass_pattern_audit.json").read_text(encoding="utf-8"))
        self.assertFalse(audit["native_or_alhardnpu_transformation"]["native_compiler_invoked"])
        self.assertFalse(audit["native_or_alhardnpu_transformation"]["alhardnpu_custom_onnx_node_created"])


if __name__ == "__main__":
    unittest.main()
