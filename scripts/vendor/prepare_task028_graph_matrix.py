#!/usr/bin/env python3
"""Build the Task 028 graph-dialect report, export matrix, and parser probes.

The exporter uses the repository's frozen TorchScript artifact.  ``do_constant_folding``
is recorded explicitly; it is not silently called onnx-simplifier because that
third-party package is not part of the frozen offline environment.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper
import onnxruntime as ort
import torch


REPO = Path(__file__).resolve().parents[2]
PYTHON_ROOT = REPO / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))
from edgeai_benchmark.preprocess import load_and_prepare_image  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dtype_name(value: int) -> str:
    return TensorProto.DataType.Name(value)


def dim_summary(value: onnx.ValueInfoProto) -> list[Any]:
    result: list[Any] = []
    tensor = value.type.tensor_type
    for dimension in tensor.shape.dim:
        if dimension.HasField("dim_value"):
            result.append(int(dimension.dim_value))
        elif dimension.HasField("dim_param"):
            result.append(dimension.dim_param)
        else:
            result.append(None)
    return result


def io_summary(values: list[onnx.ValueInfoProto]) -> list[dict[str, Any]]:
    return [
        {
            "name": value.name,
            "dtype": dtype_name(value.type.tensor_type.elem_type),
            "shape": dim_summary(value),
            "dynamic_dimensions": sum(
                not dimension.HasField("dim_value")
                for dimension in value.type.tensor_type.shape.dim
            ),
        }
        for value in values
    ]


def attrs(node: onnx.NodeProto) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for attribute in node.attribute:
        if attribute.type == onnx.AttributeProto.STRING:
            output[attribute.name] = attribute.s.decode("utf-8")
        elif attribute.type == onnx.AttributeProto.INT:
            output[attribute.name] = int(attribute.i)
        elif attribute.type == onnx.AttributeProto.FLOAT:
            output[attribute.name] = float(attribute.f)
        elif attribute.type == onnx.AttributeProto.INTS:
            output[attribute.name] = [int(item) for item in attribute.ints]
        elif attribute.type == onnx.AttributeProto.FLOATS:
            output[attribute.name] = [float(item) for item in attribute.floats]
        else:
            output[attribute.name] = f"type_{attribute.type}"
    return output


def graph_summary(path: Path) -> dict[str, Any]:
    model = onnx.load(str(path))
    nodes = list(model.graph.node)
    counts = collections.Counter(node.op_type for node in nodes)
    selected = []
    for index, node in enumerate(nodes):
        if node.op_type in {
            "Resize", "Shape", "Gather", "Floor", "QuantizeLinear",
            "DequantizeLinear", "QLinearConv", "Constant", "Cast",
        }:
            selected.append(
                {
                    "index": index,
                    "op_type": node.op_type,
                    "name": node.name,
                    "inputs": list(node.input),
                    "outputs": list(node.output),
                    "attributes": attrs(node),
                }
            )
    initializers = list(model.graph.initializer)
    initializer_bytes = sum(len(item.raw_data) for item in initializers)
    initializer_dtypes = collections.Counter(dtype_name(item.data_type) for item in initializers)
    dynamic = sum(
        not dimension.HasField("dim_value")
        for value in list(model.graph.input) + list(model.graph.output)
        for dimension in value.type.tensor_type.shape.dim
    )
    return {
        "path_name": path.name,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "ir_version": int(model.ir_version),
        "producer": {"name": model.producer_name, "version": model.producer_version},
        "domain": model.domain,
        "model_version": int(model.model_version),
        "opsets": [{"domain": item.domain, "version": int(item.version)} for item in model.opset_import],
        "inputs": io_summary(list(model.graph.input)),
        "outputs": io_summary(list(model.graph.output)),
        "node_count": len(nodes),
        "operator_counts": dict(sorted(counts.items())),
        "initializer_count": len(initializers),
        "initializer_bytes": initializer_bytes,
        "initializer_dtypes": dict(sorted(initializer_dtypes.items())),
        "value_info_count": len(model.graph.value_info),
        "dynamic_io_dimension_count": dynamic,
        "selected_nodes": selected,
        "metadata": {item.key: item.value for item in model.metadata_props},
    }


def raw_output(path: Path, tensor: np.ndarray) -> np.ndarray:
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: tensor})
    if len(outputs) != 1:
        raise RuntimeError(f"expected one output for YOLOv5n candidate, got {len(outputs)}")
    return np.asarray(outputs[0])


def make_probe_models(output_dir: Path) -> list[dict[str, Any]]:
    input_info = helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 640, 640])
    output_info = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3, 640, 640])
    models: dict[str, onnx.ModelProto] = {}
    models["identity"] = helper.make_model(
        helper.make_graph(
            [helper.make_node("Identity", ["images"], ["output"], name="identity")],
            "identity", [input_info], [output_info]
        ), opset_imports=[helper.make_opsetid("", 12)], ir_version=7
    )
    models["floor"] = helper.make_model(
        helper.make_graph(
            [helper.make_node("Floor", ["images"], ["output"], name="floor")],
            "floor", [input_info], [output_info]
        ), opset_imports=[helper.make_opsetid("", 12)], ir_version=7
    )
    shape_output = helper.make_tensor_value_info("output", TensorProto.INT64, [1])
    models["shape-gather"] = helper.make_model(
        helper.make_graph(
            [
                helper.make_node("Shape", ["images"], ["shape"], name="shape"),
                helper.make_node("Gather", ["shape", "index"], ["output"], name="gather", axis=0),
            ], "shape_gather", [input_info], [shape_output],
            initializer=[numpy_helper.from_array(np.asarray(0, dtype=np.int64), "index")],
        ), opset_imports=[helper.make_opsetid("", 12)], ir_version=7
    )
    scales = numpy_helper.from_array(np.asarray([1.0, 1.0, 2.0, 2.0], dtype=np.float32), "scales")
    resize_output = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3, 1280, 1280])
    models["resize-scales"] = helper.make_model(
        helper.make_graph(
            [helper.make_node("Resize", ["images", "roi", "scales"], ["output"], name="resize", mode="nearest")],
            "resize_scales", [input_info], [resize_output],
            initializer=[scales, numpy_helper.from_array(np.asarray([], dtype=np.float32), "roi")],
        ), opset_imports=[helper.make_opsetid("", 12)], ir_version=7
    )
    sizes = numpy_helper.from_array(np.asarray([1, 3, 320, 320], dtype=np.int64), "sizes")
    resize_small = helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 3, 320, 320])
    models["resize-sizes"] = helper.make_model(
        helper.make_graph(
            [helper.make_node("Resize", ["images", "roi", "scales", "sizes"], ["output"], name="resize", mode="nearest")],
            "resize_sizes", [input_info], [resize_small],
            initializer=[sizes, numpy_helper.from_array(np.asarray([], dtype=np.float32), "roi"),
                         numpy_helper.from_array(np.asarray([], dtype=np.float32), "scales")],
        ), opset_imports=[helper.make_opsetid("", 12)], ir_version=7
    )
    weight = numpy_helper.from_array(np.ones((1, 3, 1, 1), dtype=np.float32), "weight")
    bias = numpy_helper.from_array(np.zeros((1,), dtype=np.float32), "bias")
    models["conv-relu"] = helper.make_model(
        helper.make_graph(
            [
                helper.make_node("Conv", ["images", "weight", "bias"], ["conv"], name="conv"),
                helper.make_node("Relu", ["conv"], ["output"], name="relu"),
            ], "conv_relu", [input_info], [output_info], initializer=[weight, bias]
        ), opset_imports=[helper.make_opsetid("", 12)], ir_version=7
    )
    scale = numpy_helper.from_array(np.asarray(1.0, dtype=np.float32), "scale")
    zero = numpy_helper.from_array(np.asarray(0, dtype=np.uint8), "zero")
    models["qdq"] = helper.make_model(
        helper.make_graph(
            [
                helper.make_node("QuantizeLinear", ["images", "scale", "zero"], ["quant"], name="quant"),
                helper.make_node("DequantizeLinear", ["quant", "scale", "zero"], ["output"], name="dequant"),
            ], "qdq", [input_info], [output_info], initializer=[scale, zero]
        ), opset_imports=[helper.make_opsetid("", 12)], ir_version=7
    )
    result: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, model in models.items():
        path = output_dir / f"parser_probe_{name}.onnx"
        onnx.checker.check_model(model)
        onnx.save(model, str(path))
        result.append({"name": name, "path_name": path.name, "sha256": sha256(path), "summary": graph_summary(path)})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--torchscript", type=Path, required=True)
    parser.add_argument("--positive-control", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument("--graph-report", type=Path, required=True)
    parser.add_argument("--matrix-report", type=Path, required=True)
    parser.add_argument("--parser-report", type=Path, required=True)
    parser.add_argument(
        "--opsets",
        nargs="+",
        type=int,
        default=[10, 11, 12],
        help="ONNX opsets to export; the default preserves the original matrix",
    )
    args = parser.parse_args()

    tensor, metadata = load_and_prepare_image(args.input)
    frozen_summary = graph_summary(args.frozen)
    positive_summary = graph_summary(args.positive_control)
    args.graph_report.parent.mkdir(parents=True, exist_ok=True)
    args.graph_report.write_text(json.dumps({
        "schema_version": 1,
        "purpose": "official ArmNN/Alnpu positive-control versus frozen YOLOv5n graph dialect",
        "positive_control": positive_summary,
        "frozen_yolov5n": frozen_summary,
        "comparison": {
            "opset_difference": [positive_summary["opsets"], frozen_summary["opsets"]],
            "input_contract_difference": [positive_summary["inputs"], frozen_summary["inputs"]],
            "output_contract_difference": [positive_summary["outputs"], frozen_summary["outputs"]],
            "positive_control_quantization": {
                "quantize_linear": positive_summary["operator_counts"].get("QuantizeLinear", 0),
                "dequantize_linear": positive_summary["operator_counts"].get("DequantizeLinear", 0),
                "qlinearconv": positive_summary["operator_counts"].get("QLinearConv", 0),
            },
            "frozen_shape_ops": {
                key: frozen_summary["operator_counts"].get(key, 0)
                for key in ["Shape", "Gather", "Floor", "Resize", "Cast", "Slice", "Unsqueeze"]
            },
            "positive_control_shape_ops": {
                key: positive_summary["operator_counts"].get(key, 0)
                for key in ["Shape", "Gather", "Floor", "Resize", "Cast", "Slice", "Unsqueeze"]
            },
            "positive_control_backend_evidence": {
                "source": "results/evidence/026/official_demo_validation.json",
                "requested_backends": ["Alnpu"],
                "assigned_backend": "Alnpu",
                "assigned_layer_type": "ALHardNPU",
                "cpu_fallback_allowed": False,
            },
        },
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    args.models_dir.mkdir(parents=True, exist_ok=True)
    torch_model = torch.jit.load(str(args.torchscript), map_location="cpu").eval()
    matrix: list[dict[str, Any]] = []
    for opset in args.opsets:
        for folding in (False, True):
            name = f"yolov5n_opset{opset}_static640_simplify_{'on' if folding else 'off'}"
            path = args.models_dir / f"{name}.onnx"
            record: dict[str, Any] = {
                "name": name, "opset": opset, "static_shape": True,
                "simplify_requested": "on" if folding else "off",
                "simplify_implementation": "torch.onnx.do_constant_folding",
                "export_source": "models/yolov5n-v7.0/yolov5n.torchscript",
                "export_status": "FAILED",
            }
            try:
                torch.onnx.export(
                    torch_model, torch.zeros((1, 3, 640, 640)), str(path),
                    opset_version=opset, do_constant_folding=folding,
                    input_names=["images"], output_names=["output0"], dynamic_axes=None,
                )
                model = onnx.load(str(path))
                onnx.checker.check_model(model)
                output = raw_output(path, tensor)
                baseline = raw_output(args.frozen, tensor)
                delta = np.abs(output.astype(np.float64) - baseline.astype(np.float64))
                record.update({
                    "export_status": "PASS",
                    "path_name": path.name,
                    "sha256": sha256(path),
                    "size_bytes": path.stat().st_size,
                    "onnx_checker": "PASS",
                    "ort_raw_output": {
                        "status": "PASS",
                        "shape": list(output.shape),
                        "dtype": str(output.dtype),
                        "max_abs_delta_vs_frozen": float(delta.max()),
                        "mean_abs_delta_vs_frozen": float(delta.mean()),
                        "exact_equal": bool(np.array_equal(output, baseline)),
                        "golden_input": metadata,
                    },
                    "summary": graph_summary(path),
                })
            except Exception as error:  # preserve each real exporter/checker/ORT failure
                record["error"] = f"{type(error).__name__}: {error}"
            matrix.append(record)
    args.matrix_report.write_text(json.dumps({
        "schema_version": 1,
        "source_torchscript_sha256": sha256(args.torchscript),
        "source_frozen_onnx_sha256": sha256(args.frozen),
        "onnx_version": onnx.__version__,
        "onnxruntime_version": ort.__version__,
        "matrix": matrix,
        "interpretation": "Only export_status=PASS entries are candidates for the board parser; failed entries remain evidence and are not silently substituted.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    probes = make_probe_models(args.models_dir)
    args.parser_report.write_text(json.dumps({
        "schema_version": 1,
        "purpose": "minimal ONNX subgraphs for bounded ArmNN parser bisection",
        "models": probes,
        "board_protocol": "edgeai_armnn_image --parse-only 1 --model-variant matrix --expected-model-sha256 <hash>; Alnpu only; no inference or CPU fallback",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "graph_report": str(args.graph_report),
        "matrix_report": str(args.matrix_report),
        "parser_report": str(args.parser_report),
        "matrix_passes": sum(item["export_status"] == "PASS" for item in matrix),
        "matrix_failures": sum(item["export_status"] != "PASS" for item in matrix),
        "parser_probe_count": len(probes),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
