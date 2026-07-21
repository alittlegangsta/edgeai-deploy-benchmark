from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_ncnn_conversion import (
    EXPECTED_NCNN_REVISION,
    EXPECTED_NCNN_TAG,
    EXPECTED_ONNX_SHA256,
    EXPECTED_PNNX_SHA256,
    EXPECTED_TORCHSCRIPT_SHA256,
    EXPECTED_WEIGHTS_SHA256,
    ConversionError,
    parse_param,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "models/yolov5n-v7.0/ncnn_manifest.json"
EVIDENCE_PATH = ROOT / "results/evidence/010/ncnn_model_load.json"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class NcnnManifestTest(unittest.TestCase):
    def test_real_manifest_preserves_lineage_and_tool_identity(self) -> None:
        manifest = load_json(MANIFEST_PATH)
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["status"], "PASS")
        self.assertEqual(manifest["lineage"]["weights"]["sha256"], EXPECTED_WEIGHTS_SHA256)
        self.assertEqual(manifest["lineage"]["frozen_onnx"]["sha256"], EXPECTED_ONNX_SHA256)
        self.assertEqual(
            manifest["lineage"]["torchscript"]["sha256"], EXPECTED_TORCHSCRIPT_SHA256
        )
        self.assertEqual(manifest["toolchain"]["tag"], EXPECTED_NCNN_TAG)
        self.assertEqual(manifest["toolchain"]["revision"], EXPECTED_NCNN_REVISION)
        self.assertEqual(manifest["toolchain"]["pnnx"]["sha256"], EXPECTED_PNNX_SHA256)

    def test_real_artifact_hashes_and_decoded_contract(self) -> None:
        manifest = load_json(MANIFEST_PATH)
        for section, key in (("ncnn_model", "param"), ("ncnn_model", "bin")):
            identity = manifest[section][key]
            self.assertEqual(sha256_file(ROOT / identity["path"]), identity["sha256"])
        contract = manifest["contract"]
        self.assertEqual(contract["classification"], "single decoded YOLOv5 candidate tensor")
        self.assertEqual(contract["inputs"][0]["logical_shape"], [1, 3, 640, 640])
        self.assertEqual(contract["outputs"][0]["logical_shape"], [1, 25200, 85])
        self.assertEqual(contract["outputs"][0]["dtype"], "float32")
        self.assertEqual(manifest["ncnn_model"]["custom_layer_count"], 0)
        settings = manifest["conversion"]["settings"]
        self.assertEqual(settings["fp16"], 0)
        self.assertEqual(settings["optlevel"], 2)
        self.assertEqual(settings["device"], "cpu")
        self.assertEqual(settings["moduleop"], [])
        self.assertEqual(settings["customop"], [])

    def test_runtime_evidence_disables_reduced_precision_and_vulkan(self) -> None:
        evidence = load_json(EVIDENCE_PATH)
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["ncnn_version"], "1.0.20240410")
        self.assertEqual(evidence["input_names"], ["in0"])
        self.assertEqual(evidence["output_names"], ["out0"])
        self.assertEqual(evidence["probe"]["outputs"][0]["w"], 85)
        self.assertEqual(evidence["probe"]["outputs"][0]["h"], 25200)
        self.assertTrue(evidence["probe"]["outputs"][0]["all_finite"])
        for key, value in evidence["options"].items():
            if key != "num_threads":
                self.assertFalse(value, key)

    def test_param_parser_rejects_layer_count_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.param"
            path.write_text("7767517\n2 1\nInput in 0 1 x\n", encoding="utf-8")
            with self.assertRaisesRegex(ConversionError, "declared 2 layers"):
                parse_param(path)


if __name__ == "__main__":
    unittest.main()
