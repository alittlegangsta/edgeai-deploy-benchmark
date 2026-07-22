from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import onnx
from onnx import TensorProto, helper

from scripts.inspect_onnx_contract import (
    ContractError,
    find_nms_nodes,
    inspect_model,
    inspect_weight_reference,
    sha256_file,
    validate_export_command,
    validate_inspection,
)


def make_model(path: Path, input_shape: list[object] | None = None) -> None:
    shape = input_shape or [1, 3, 640, 640]
    model_input = helper.make_tensor_value_info("actual_input", TensorProto.FLOAT, shape)
    model_output = helper.make_tensor_value_info("actual_output", TensorProto.FLOAT, [1, 1, 85])
    value = helper.make_tensor("value", TensorProto.FLOAT, [1, 1, 85], [0.0] * 85)
    node = helper.make_node("Constant", [], ["actual_output"], value=value)
    graph = helper.make_graph([node], "contract-test", [model_input], [model_output])
    model = helper.make_model(
        graph,
        producer_name="task-002-test",
        opset_imports=[helper.make_operatorsetid("", 12)],
    )
    metadata = model.metadata_props.add()
    metadata.key = "names"
    metadata.value = repr({index: f"class-{index}" for index in range(80)})
    onnx.save(model, path)


class ModelContractTest(unittest.TestCase):
    def test_inspects_names_shapes_dtypes_and_opset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.onnx"
            make_model(path)
            inspection = inspect_model(path)
        self.assertEqual(inspection["inputs"][0]["name"], "actual_input")
        self.assertEqual(inspection["inputs"][0]["shape"], [1, 3, 640, 640])
        self.assertEqual(inspection["inputs"][0]["dtype"], "FLOAT")
        self.assertEqual(inspection["outputs"][0]["name"], "actual_output")
        self.assertEqual(inspection["outputs"][0]["shape"], [1, 1, 85])
        self.assertEqual(inspection["class_count"], 80)
        self.assertFalse(inspection["contains_graph_nms"])

    def test_rejects_dynamic_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dynamic.onnx"
            make_model(path, ["batch", 3, 640, 640])
            with self.assertRaisesRegex(ContractError, "static NCHW"):
                inspect_model(path)

    def test_rejects_graph_nms(self) -> None:
        inspection = {
            "opset_imports": [{"domain": "", "version": 12}],
            "inputs": [{"name": "input", "shape": [1, 3, 640, 640], "dtype": "FLOAT"}],
            "outputs": [{"name": "output", "shape": [1, 1, 85], "dtype": "FLOAT"}],
            "contains_graph_nms": True,
            "nms_nodes": [{"op_type": "NonMaxSuppression"}],
            "class_count": 80,
        }
        with self.assertRaisesRegex(ContractError, "contains NMS"):
            validate_inspection(inspection)

    def test_finds_non_max_suppression_node(self) -> None:
        graph = helper.make_graph(
            [helper.make_node("NonMaxSuppression", ["boxes", "scores"], ["selected"])],
            "nms-test",
            [],
            [],
        )
        model = helper.make_model(graph)
        matches = find_nms_nodes(model)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["op_type"], "NonMaxSuppression")

    def test_sha256_reads_real_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "value.bin"
            path.write_bytes(b"abc")
            self.assertEqual(
                sha256_file(path),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            )

    def test_export_command_rejects_contract_changes(self) -> None:
        source = Path("/tmp/yolov5-v7.0")
        weights = Path("models/yolov5n-v7.0/yolov5n.pt")
        base = (
            f"python {source.resolve() / 'export.py'} --weights {weights} "
            "--imgsz 640 640 --batch-size 1 --device cpu --include onnx --opset 12"
        )
        self.assertTrue(validate_export_command(base, weights, source))
        with self.assertRaisesRegex(ContractError, "forbidden"):
            validate_export_command(base + " --simplify", weights, source)

    def test_weight_reference_must_come_from_verified_source_readme(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "README.md").write_text(
                "https://github.com/ultralytics/yolov5/releases/download/v6.2/yolov5n.pt\n",
                encoding="utf-8",
            )
            reference = inspect_weight_reference(source)
            self.assertEqual(
                reference["url"],
                "https://github.com/ultralytics/yolov5/releases/download/v6.2/yolov5n.pt",
            )

    def test_missing_weight_reference_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "README.md").write_text("no model link\n", encoding="utf-8")
            with self.assertRaisesRegex(ContractError, "weight reference"):
                inspect_weight_reference(source)


if __name__ == "__main__":
    unittest.main()
