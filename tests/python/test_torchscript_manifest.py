from __future__ import annotations

import json
import math
from pathlib import Path
import unittest

from scripts.validate_torchscript_conversion import (
    EXPECTED_INPUT_SHAPE,
    EXPECTED_ONNX_SHA256,
    EXPECTED_WEIGHTS_SHA256,
    MAXIMUM_CONFIDENCE_DELTA,
    MINIMUM_CLASS_MATCHED_IOU,
    ValidationError,
    detection_matches,
)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "models/yolov5n-v7.0/torchscript_manifest.json"
EVIDENCE_PATH = ROOT / "results/evidence/010/torchscript_validation.json"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class TorchScriptManifestTest(unittest.TestCase):
    def test_real_manifest_preserves_lineage_and_contract(self) -> None:
        manifest = load_json(MANIFEST_PATH)
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["status"], "PASS")
        self.assertEqual(
            manifest["lineage"]["weights"]["sha256"], EXPECTED_WEIGHTS_SHA256
        )
        self.assertEqual(
            manifest["lineage"]["frozen_onnx"]["sha256"], EXPECTED_ONNX_SHA256
        )
        self.assertEqual(manifest["torchscript"]["input"]["shape"], EXPECTED_INPUT_SHAPE)
        self.assertEqual(manifest["torchscript"]["input"]["dtype"], "float32")
        self.assertEqual(manifest["torchscript"]["input"]["device"], "cpu")
        self.assertEqual(manifest["export"]["precision"], "FP32")
        for forbidden in (
            "half",
            "int8",
            "optimize",
            "dynamic",
            "quantization",
            "vulkan",
            "model_surgery",
            "detect_head_replacement",
        ):
            self.assertFalse(manifest["export"][forbidden])

    def test_real_evidence_has_finite_output_and_frozen_comparison(self) -> None:
        evidence = load_json(EVIDENCE_PATH)
        output = evidence["torchscript"]["outputs"][0]
        self.assertEqual(output["shape"], [1, 25200, 85])
        self.assertEqual(output["dtype"], "float32")
        self.assertTrue(output["all_finite"])
        self.assertEqual(output["finite_count"], output["element_count"])
        for key in ("min", "max", "mean", "std"):
            self.assertTrue(math.isfinite(output[key]))
        comparison = evidence["semantic_comparison"]
        self.assertEqual(comparison["status"], "PASS")
        self.assertEqual(comparison["onnx_detection_count"], 5)
        self.assertEqual(comparison["torchscript_detection_count"], 5)
        self.assertGreaterEqual(
            comparison["minimum_observed_iou"], MINIMUM_CLASS_MATCHED_IOU
        )
        self.assertLessEqual(
            comparison["maximum_observed_confidence_difference"],
            MAXIMUM_CONFIDENCE_DELTA,
        )

    def test_matching_rejects_a_class_difference(self) -> None:
        reference = [
            {
                "rank": 1,
                "class_id": 1,
                "class_name": "one",
                "confidence": 0.8,
                "box_xyxy_source": [0.0, 0.0, 10.0, 10.0],
            }
        ]
        candidate = [dict(reference[0], class_id=2, class_name="two")]
        with self.assertRaisesRegex(ValidationError, "no class match"):
            detection_matches(reference, candidate)

    def test_matching_rejects_confidence_outside_frozen_tolerance(self) -> None:
        reference = [
            {
                "rank": 1,
                "class_id": 1,
                "class_name": "one",
                "confidence": 0.8,
                "box_xyxy_source": [0.0, 0.0, 10.0, 10.0],
            }
        ]
        candidate = [dict(reference[0], confidence=0.8 + 2 * MAXIMUM_CONFIDENCE_DELTA)]
        with self.assertRaisesRegex(ValidationError, "confidence delta"):
            detection_matches(reference, candidate)


if __name__ == "__main__":
    unittest.main()
