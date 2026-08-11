#!/usr/bin/env python3
"""Create an explicit Task 028 constant-Floor model repair.

The frozen YOLOv5n graph contains four constant FLOAT Floor nodes whose values
are exactly 40.0 or 80.0.  Alnpu rejects Floor and Identity during optimization.
Replacing only those constant operations with equivalent Constant nodes
preserves the graph numerically; the source model, transformation and derived
hash are all checked here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper, shape_inference

SOURCE_SHA256 = "78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121"
DERIVED_SHA256 = "755fb5adc596eee7a7255bc29c48b86f1895df1e8fa1577d785cb431d233bcf2"
CONSTANT_DERIVED_SHA256 = "e6066c047c2fc6bd37bd3ffa5322fa85a62873c5c9751e57ac8a569faf6201b7"
REMOVED_DERIVED_SHA256 = "e0720ffe896ed1919dba35699e703025b0bfad906bdcf97e4f2ab81e66df92e0"
ADD_ZERO_DERIVED_SHA256 = "9f330839f3130f0af0fb7c5ab4c3f761ff6fd7f625c46298ef17a99caab40811"
FIXED_RESIZE_DERIVED_SHA256 = "a8cd7290ee2d592ffd994d79dfceee3bf9dfd0eebe6a58b77624e2b6019a9de8"
FIXED_RESIZE_INFERRED_DERIVED_SHA256 = "f29c4b85f4d2ebc16095ac9849319bc1e0ff3863001b1d38f4f28db508e86ead"
FIXED_RESIZE_SCALES_DERIVED_SHA256 = "acfad8dbd631d61f47458a6a5639ed6804c3f1c53f6a177e2af08c7078b034da"
ONNX_VERSION = "1.16.2"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--replacement", choices=("identity", "constant", "remove", "add-zero", "fixed-resize", "fixed-resize-inferred", "fixed-resize-scales"), default="constant"
    )
    args = parser.parse_args()
    if onnx.__version__ != ONNX_VERSION:
        raise SystemExit(f"requires onnx=={ONNX_VERSION}, observed {onnx.__version__}")
    observed_source = sha256(args.input)
    if observed_source != SOURCE_SHA256:
        raise SystemExit(f"source SHA256 mismatch: {observed_source}")

    model = onnx.load(str(args.input))
    if args.replacement in ("fixed-resize", "fixed-resize-inferred", "fixed-resize-scales"):
        # The four Floor nodes are only used to form fixed Resize sizes for the
        # frozen [1,3,640,640] input.  Fold those shape subgraphs to constants;
        # the resulting graph is checked against the source with ORT by the
        # focused evidence command.
        import copy

        reduced = []
        for node in model.graph.node:
            if node.name.startswith("/model.11/") or node.name.startswith("/model.15/"):
                if node.op_type != "Resize":
                    continue
                resized = copy.deepcopy(node)
                prefix = "/model.11" if node.name.startswith("/model.11/") else "/model.15"
                target = [1, 128, 40, 40] if prefix == "/model.11" else [1, 64, 80, 80]
                resized.input[1] = node.name + "/Roi"
                resized.input[2] = node.name + "/Scales"
                resized.input[3] = "" if args.replacement == "fixed-resize-scales" else node.name + "/FixedSizes"
                reduced.append((prefix, resized, target))
            else:
                reduced.append((None, node, None))
        final_nodes = []
        for prefix, node, target in reduced:
            if node.op_type == "Resize" and prefix:
                constants = (
                    (("Roi", np.zeros(8, dtype=np.float32)), ("Scales", np.asarray([1, 1, 2, 2], dtype=np.float32)))
                    if args.replacement == "fixed-resize-scales"
                    else (("Roi", np.asarray([], dtype=np.float32)), ("Scales", np.asarray([], dtype=np.float32)), ("FixedSizes", np.asarray(target, dtype=np.int64)))
                )
                for suffix, array in constants:
                    final_nodes.append(
                        helper.make_node(
                            "Constant", [], [node.name + "/" + suffix],
                            name=node.name + "/" + suffix,
                            value=numpy_helper.from_array(array),
                        )
                    )
            final_nodes.append(node)
        model.graph.ClearField("node")
        model.graph.node.extend(final_nodes)
        replacements = [
            {"node": "/model.11/Resize", "target": [1, 128, 40, 40]},
            {"node": "/model.15/Resize", "target": [1, 64, 80, 80]},
        ]
    else:
        replacements = []
    remove_names: set[str] = set()
    for node in list(model.graph.node) if args.replacement not in ("fixed-resize", "fixed-resize-inferred", "fixed-resize-scales") else []:
        if node.op_type != "Floor":
            continue
        producers = [
            candidate
            for candidate in model.graph.node
            if node.input[0] in candidate.output and candidate.op_type == "Constant"
        ]
        if len(producers) != 1:
            raise SystemExit(f"Floor input is not one Constant producer: {node.name}")
        value = numpy_helper.to_array(producers[0].attribute[0].t)
        if value.size != 1 or value.dtype != np.float32 or not float(value.item()).is_integer():
            raise SystemExit(f"Floor constant is not an exact integer FLOAT: {node.name}")
        if args.replacement == "identity":
            node.op_type = "Identity"
            del node.attribute[:]
        elif args.replacement == "constant":
            tensor = helper.make_tensor(
                node.name + "_value", TensorProto.FLOAT, [], [float(value.item())]
            )
            node.op_type = "Constant"
            node.ClearField("input")
            node.ClearField("attribute")
            node.attribute.extend([helper.make_attribute("value", tensor)])
        elif args.replacement == "remove":
            old_output = node.output[0]
            old_input = node.input[0]
            for consumer in model.graph.node:
                for index, input_name in enumerate(consumer.input):
                    if input_name == old_output:
                        consumer.input[index] = old_input
            for graph_output in model.graph.output:
                if graph_output.name == old_output:
                    graph_output.name = old_input
            remove_names.add(node.name)
        else:
            zero_name = node.name + "_zero"
            zero_output = zero_name + "_output"
            zero = helper.make_node(
                "Constant",
                [],
                [zero_output],
                name=zero_name,
                value=helper.make_tensor(zero_name + "_value", TensorProto.FLOAT, [], [0.0]),
            )
            index = list(model.graph.node).index(node)
            model.graph.node.insert(index, zero)
            node.op_type = "Add"
            node.ClearField("attribute")
            node.input.append(zero_output)
        replacements.append(
            {"node": node.name, "constant_value": float(value.item()), "replacement": args.replacement}
        )
    if args.replacement == "remove":
        keep = [node for node in model.graph.node if node.name not in remove_names]
        del model.graph.node[:]
        model.graph.node.extend(keep)
    expected_replacements = 2 if args.replacement in ("fixed-resize", "fixed-resize-inferred", "fixed-resize-scales") else 4
    if len(replacements) != expected_replacements:
        raise SystemExit(
            f"expected {expected_replacements} repair records, observed {len(replacements)}"
        )
    if args.replacement == "fixed-resize-inferred":
        model = shape_inference.infer_shapes(model)
    onnx.checker.check_model(model, full_check=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    onnx.save(model, str(args.output))
    observed_derived = sha256(args.output)
    expected_derived = {
        "identity": DERIVED_SHA256,
        "constant": CONSTANT_DERIVED_SHA256,
        "remove": REMOVED_DERIVED_SHA256,
        "add-zero": ADD_ZERO_DERIVED_SHA256,
        "fixed-resize": FIXED_RESIZE_DERIVED_SHA256,
        "fixed-resize-inferred": FIXED_RESIZE_INFERRED_DERIVED_SHA256,
        "fixed-resize-scales": FIXED_RESIZE_SCALES_DERIVED_SHA256,
    }[args.replacement]
    if observed_derived != expected_derived:
        raise SystemExit(f"derived SHA256 mismatch: {observed_derived}")
    print(
        json.dumps(
            {
                "status": "PASS",
                "onnx_version": onnx.__version__,
                "source_sha256": observed_source,
                "derived_sha256": observed_derived,
                "replacement": args.replacement,
                "replacements": replacements,
                "semantic_claim": (
                    "dynamic resize shape subgraphs containing exact-integer constant Floor nodes "
                    "were folded to fixed [1,C,H,W] sizes"
                    if args.replacement in ("fixed-resize", "fixed-resize-inferred", "fixed-resize-scales")
                    else "only exact-integer constant Floor nodes were replaced by " + args.replacement
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
