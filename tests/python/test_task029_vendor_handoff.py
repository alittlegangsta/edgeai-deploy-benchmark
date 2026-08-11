import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/vendor_handoff/dr1m90_npu"
VALIDATOR = ROOT / "scripts/vendor/validate_task029_vendor_handoff.py"


class Task029VendorHandoffTests(unittest.TestCase):
    def run_validator(self, package: Path):
        return subprocess.run([sys.executable, str(VALIDATOR), "--package-dir", str(package)], cwd=ROOT, capture_output=True, text=True, check=False)

    def copy_fixture(self, directory: str):
        repo = Path(directory) / "repo"
        target = repo / "docs/vendor_handoff/dr1m90_npu"
        target.parent.mkdir(parents=True)
        shutil.copytree(PACKAGE, target)
        (repo / "results/evidence").mkdir(parents=True)
        shutil.copytree(ROOT / "results/evidence/028", repo / "results/evidence/028")
        return target

    def test_checked_in_handoff_passes(self):
        result = self.run_validator(PACKAGE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_validator_rejects_missing_question_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = self.copy_fixture(directory)
            (target / "questions.md").unlink()
            result = self.run_validator(target)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("questions.md", result.stdout)

    def test_validator_rejects_evidence_hash_change(self):
        with tempfile.TemporaryDirectory() as directory:
            target = self.copy_fixture(directory)
            manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
            manifest["evidence"][0]["sha256"] = "0" * 64
            (target / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            result = self.run_validator(target)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("evidence SHA256 mismatch", result.stdout)

    def test_validator_rejects_binary_material(self):
        with tempfile.TemporaryDirectory() as directory:
            target = self.copy_fixture(directory)
            (target / "forbidden.onnx").write_bytes(b"not a model")
            result = self.run_validator(target)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("vendor/binary-like material", result.stdout)


if __name__ == "__main__":
    unittest.main()
