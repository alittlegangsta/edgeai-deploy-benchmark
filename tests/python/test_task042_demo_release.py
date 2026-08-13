import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_task042_demo_release.py"
MANIFEST = ROOT / "release/demo/manifest.json"


class Task042DemoReleaseTests(unittest.TestCase):
    def test_release_validator_passes(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"status": "PASS"', result.stdout)

    def test_exactly_four_prepared_segments(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        segments = manifest["segments"]
        self.assertEqual(
            {segment["id"] for segment in segments},
            {
                "readme_architecture",
                "pc_tensorrt_fp16_video",
                "dr1_camera_ncnn_int8",
                "dr1_face_alnpu_control",
            },
        )
        self.assertEqual(len(segments), 4)
        self.assertTrue(all(segment["command_status"] == "PREPARED_NOT_RUN" for segment in segments))

    def test_scope_boundaries_are_explicit(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        face = next(segment for segment in manifest["segments"] if segment["id"] == "dr1_face_alnpu_control")
        camera = next(segment for segment in manifest["segments"] if segment["id"] == "dr1_camera_ncnn_int8")
        self.assertEqual(face["backend_gate"]["required_assignment"], "Alnpu | ALHardNPU")
        self.assertFalse(face["backend_gate"]["fallback_allowed"])
        self.assertEqual(face["scope"], "functional_control_only")
        self.assertEqual(camera["scope"], "camera_integration_evidence_only")
        self.assertEqual(manifest["source_authority"]["path"], "results/final/authoritative_results.json")


if __name__ == "__main__":
    unittest.main()
