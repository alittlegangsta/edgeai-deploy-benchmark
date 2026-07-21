from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import cv2
import numpy as np

from edgeai_benchmark.model_contract import (
    ContractError,
    load_frozen_contract,
    summarize_tensor,
    validate_runtime_io,
)
from edgeai_benchmark.preprocess import letterbox, load_bgr_image, prepare_image_tensor


def write_manifest(path: Path, model_hash: str) -> None:
    manifest = {
        "schema_version": 1,
        "export": {
            "batch_size": 1,
            "input_size": [640, 640],
            "layout": "NCHW",
            "precision": "FP32",
        },
        "onnx": {
            "sha256": model_hash,
            "contract": {
                "inputs": [
                    {"name": "images", "shape": [1, 3, 640, 640], "dtype": "FLOAT"}
                ],
                "outputs": [
                    {"name": "output0", "shape": [1, 25200, 85], "dtype": "FLOAT"}
                ],
                "contains_graph_nms": False,
            },
        },
    }
    path.write_text(json.dumps(manifest), encoding="utf-8")


class OrtTensorBaselineTest(unittest.TestCase):
    def test_letterbox_records_deterministic_padding(self) -> None:
        image = np.zeros((320, 640, 3), dtype=np.uint8)
        output, metadata = letterbox(image)
        self.assertEqual(output.shape, (640, 640, 3))
        self.assertEqual(metadata["scale"], 1.0)
        self.assertEqual(metadata["resized_size"], {"width": 640, "height": 320})
        self.assertEqual(
            metadata["padding"],
            {"left": 0, "top": 160, "right": 0, "bottom": 160},
        )
        np.testing.assert_array_equal(output[0, 0], [114, 114, 114])

    def test_preprocess_converts_bgr_to_contiguous_rgb_nchw_fp32(self) -> None:
        image = np.array([[[0, 64, 255], [255, 128, 0]]], dtype=np.uint8)
        tensor, metadata = prepare_image_tensor(image, target_size=(1, 2))
        self.assertEqual(tensor.shape, (1, 3, 1, 2))
        self.assertEqual(tensor.dtype, np.float32)
        self.assertTrue(tensor.flags.c_contiguous)
        self.assertEqual(metadata["padding"], {"left": 0, "top": 0, "right": 0, "bottom": 0})
        np.testing.assert_allclose(tensor[0, :, 0, 0], [1.0, 64.0 / 255.0, 0.0])
        self.assertGreaterEqual(float(tensor.min()), 0.0)
        self.assertLessEqual(float(tensor.max()), 1.0)

    def test_loads_manifest_only_when_model_hash_matches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "model.onnx"
            manifest = root / "manifest.json"
            model.write_bytes(b"real model identity")
            digest = hashlib.sha256(model.read_bytes()).hexdigest()
            write_manifest(manifest, digest)
            loaded = load_frozen_contract(manifest, model)
        self.assertEqual(loaded["model_sha256"], digest)

    def test_rejects_model_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "model.onnx"
            manifest = root / "manifest.json"
            model.write_bytes(b"unexpected model")
            write_manifest(manifest, "0" * 64)
            with self.assertRaisesRegex(ContractError, "SHA256 mismatch"):
                load_frozen_contract(manifest, model)

    def test_runtime_io_must_match_frozen_contract(self) -> None:
        frozen = {
            "inputs": [{"name": "images", "shape": [1, 3, 640, 640], "dtype": "FLOAT"}],
            "outputs": [
                {"name": "output0", "shape": [1, 25200, 85], "dtype": "FLOAT"}
            ],
        }
        runtime_inputs = [dict(frozen["inputs"][0], ort_type="tensor(float)")]
        runtime_outputs = [dict(frozen["outputs"][0], ort_type="tensor(float)")]
        validate_runtime_io(runtime_inputs, runtime_outputs, frozen)
        runtime_outputs[0]["shape"] = [1, 1, 85]
        with self.assertRaisesRegex(ContractError, "output contract mismatch"):
            validate_runtime_io(runtime_inputs, runtime_outputs, frozen)

    def test_tensor_statistics_are_real_and_finite(self) -> None:
        tensor = np.array([[1.0, 2.0, 3.0]], dtype=np.float32)
        statistics = summarize_tensor("values", tensor)
        self.assertEqual(statistics["shape"], [1, 3])
        self.assertEqual(statistics["dtype"], "float32")
        self.assertEqual(statistics["min"], 1.0)
        self.assertEqual(statistics["max"], 3.0)
        self.assertEqual(statistics["mean"], 2.0)
        self.assertEqual(statistics["finite_count"], 3)
        self.assertTrue(statistics["all_finite"])

    def test_non_finite_tensor_is_rejected(self) -> None:
        tensor = np.array([1.0, np.nan], dtype=np.float32)
        with self.assertRaisesRegex(ContractError, "non-finite"):
            summarize_tensor("values", tensor)

    def test_repository_reference_image_is_decodable(self) -> None:
        path = Path("data/samples/images/pc_reference.jpg")
        image = load_bgr_image(path)
        self.assertEqual(image.dtype, np.uint8)
        self.assertEqual(image.shape, (960, 1280, 3))
        self.assertEqual(cv2.imread(str(path), cv2.IMREAD_COLOR).shape, image.shape)


if __name__ == "__main__":
    unittest.main()
