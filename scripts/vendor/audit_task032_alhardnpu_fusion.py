#!/usr/bin/env python3
"""Generate and validate the bounded Task 032 ALHardNPU fusion audit.

The only external binary inspected by ``--write`` is the already audited
AArch64 ArmNN shared object in a temporary directory.  No vendor executable,
model, board, VM or network resource is executed or modified.  The graph and
runtime observations are read from immutable Task 028/031 evidence and are
kept separate from binary-level inference.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/evidence/032"
TASK028 = ROOT / "results/evidence/028"
TASK031 = ROOT / "results/evidence/031"
DEFAULT_LIB = Path("/tmp/task032-armnn/armnn_lib/lib/libarmnn.so.32.1")
DEFAULT_ARCHIVE: Path | None = None

VERDICTS = {
    "FUSION_REQUIREMENTS_IDENTIFIED_AND_MODEL_COMPATIBLE",
    "FUSION_REQUIREMENTS_IDENTIFIED_MODEL_INCOMPATIBLE",
    "FUSION_PREDICATE_NOT_RECOVERABLE",
}
ALNPU_OVERRIDES = (
    "IsALHardNPUSupported",
    "IsConcatSupported",
    "IsConstantSupported",
    "IsInputSupported",
    "IsLayerSupported",
    "IsMemCopySupported",
    "IsOutputSupported",
    "IsPooling2dSupported",
    "IsPreluSupported",
    "IsResizeSupported",
)
GENERIC_METHODS = (
    "IsConvolution2dSupported",
    "IsActivationSupported",
    "IsSplitterSupported",
    "IsAdditionSupported",
    "IsMultiplicationSupported",
    "IsElementwiseUnarySupported",
)
DIRECT_PREFIX = "armnn::optimizations::ConvertConv2dIntoALHardNPUImpl::"
DIRECT_NAMES = (
    "RunOptimization",
    "findLastLayer",
    "Run(armnn::Graph&",
    "RunFC(armnn::Graph&",
    "checkConv",
    "checkAct",
    "checkPool",
    "TransposeWeightLayer",
    "TransposeFcWeightLayer",
)


def load(name: str, root: Path = TASK028) -> dict[str, Any]:
    return json.loads((root / name).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command(argv: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(argv, text=True, capture_output=True, check=False)
    return proc.returncode, proc.stdout, proc.stderr


def portable(value: str) -> str:
    value = value.replace("\\", "/")
    for marker in ("/edgeai-deploy-benchmark", "/NPU_info", "/dr1m90_npu"):
        if marker in value:
            if marker == "/edgeai-deploy-benchmark":
                return "<repo>" + value.split(marker, 1)[1]
            if "/dr1m90_npu" in value:
                return "<vendor-root>" + value[value.index("/dr1m90_npu") :]
            return "<vendor-root>" + value[value.index("/NPU_info") :]
    return value


def parse_symbol_lines(text: str, needles: tuple[str, ...]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for line in text.splitlines():
        match = re.match(r"^([0-9a-fA-F]+)\s+([A-Za-z?])\s+(.+)$", line)
        if not match:
            continue
        name = match.group(3)
        if any(needle in name for needle in needles):
            records.append(
                {"address": "0x" + match.group(1).lower(), "type": match.group(2), "name": name}
            )
    return records


def find_names(records: list[dict[str, str]], fragment: str) -> list[str]:
    return sorted({r["name"] for r in records if fragment in r["name"]})


def static_binary_audit(lib: Path, archive: Path) -> dict[str, Any]:
    if not lib.is_file():
        raise RuntimeError(f"temporary audited library is missing: {lib}")
    if not archive.is_file():
        raise RuntimeError(f"audited source archive is missing: {archive}")

    file_rc, file_out, file_err = command(["file", str(lib)])
    header_rc, header_out, header_err = command(["readelf", "-h", str(lib)])
    dyn_rc, dyn_out, dyn_err = command(["readelf", "-d", str(lib)])
    nm_rc, nm_out, nm_err = command(["nm", "-D", "-C", "--defined-only", str(lib)])
    strings_rc, strings_out, strings_err = command(["strings", "-tx", str(lib)])
    objdump_rc, objdump_out, objdump_err = command(["objdump", "-f", str(lib)])
    if any(rc != 0 for rc in (file_rc, header_rc, dyn_rc, nm_rc, strings_rc)):
        raise RuntimeError(
            "static tool failure: "
            + repr({"file": file_err, "readelf_h": header_err, "readelf_d": dyn_err, "nm": nm_err, "strings": strings_err})
        )

    symbols = parse_symbol_lines(nm_out, ("ConvertConv2dIntoALHardNPUImpl", "ALHardNPU", "AlnpuALHardNPUWorkload", "CreateALHardNPU"))
    alnpu_symbols = parse_symbol_lines(nm_out, ("AlnpuLayerSupport::Is",))
    generic_symbols = parse_symbol_lines(nm_out, ("LayerSupportBase::Is",))
    embedded_needles = (
        "weights is not a supported type",
        "input and weights types mismatched",
        "biases is not a supported type",
        "the channel of conv input is not lesser or equal to 4095",
        "the height/width of output must be within 1..1023",
        "the pad is not equal to (kernel_size-1)/2",
        "only support add now",
        "input/output types not matching",
        "Do Not Supported",
    )
    embedded = [line.strip() for line in strings_out.splitlines() if any(n in line for n in embedded_needles)]

    direct = [r for r in symbols if any(n in r["name"] for n in DIRECT_NAMES)]
    override_map = {name: find_names(alnpu_symbols, f"AlnpuLayerSupport::{name}") for name in ALNPU_OVERRIDES}
    generic_map = {name: find_names(generic_symbols, f"LayerSupportBase::{name}") for name in GENERIC_METHODS}
    disassembler_candidates = {name: shutil.which(name) for name in ("aarch64-linux-gnu-objdump", "llvm-objdump")}
    prior_dispatch = load("trackc3_support_boundary_audit.json")["support_dispatch_static_audit"]

    return {
        "schema_version": 1,
        "task": "032",
        "status": "COMPLETE_STATIC_AUDIT",
        "source_classification": "source_code_fact_for_task_028_031_records; binary_fact_for_this_read; inference_explicitly_labeled",
        "external_identity": {
            "archive": {"path": "<vendor-root>/NPU_info/dr1m90_npu/npu_demo/libs/armnn_lib.tar.xz", "sha256": sha256_file(archive), "executed": False},
            "library": {"path": "<external-temp>/armnn_lib/lib/libarmnn.so.32.1", "sha256": sha256_file(lib), "file_output": file_out.strip(), "build_id": "9f9aaf6f26dd1cf57ac84c778b9f621c04c7d895", "soname": "libarmnn.so.32", "architecture": "AArch64", "stripped": True},
        },
        "commands": {
            "file": "file <external-temp>/armnn_lib/lib/libarmnn.so.32.1",
            "readelf_header": "readelf -h <external-temp>/armnn_lib/lib/libarmnn.so.32.1",
            "readelf_dynamic": "readelf -d <external-temp>/armnn_lib/lib/libarmnn.so.32.1",
            "symbols": "nm -D -C --defined-only <external-temp>/armnn_lib/lib/libarmnn.so.32.1",
            "strings": "strings -tx <external-temp>/armnn_lib/lib/libarmnn.so.32.1",
            "host_objdump": "objdump -f <external-temp>/armnn_lib/lib/libarmnn.so.32.1",
        },
        "direct_fusion_symbols": {
            "required_fragments": list(DIRECT_NAMES),
            "observed": direct,
            "required_presence": {fragment: any(fragment in r["name"] for r in direct) for fragment in DIRECT_NAMES},
            "compiled_workload_symbols": [
                name for name in ("ALHardNPURun", "ALHardNPUFCRun", "ALHardNPULayer", "AlnpuALHardNPUWorkload", "CreateALHardNPU") if any(name in r["name"] for r in symbols)
            ],
            "template_type_families_observed": {
                "float": any("ALHardNPURun<float" in r["name"] for r in symbols),
                "uint8": any("ALHardNPURun<unsigned char" in r["name"] for r in symbols),
                "int8": any("ALHardNPURun<signed char" in r["name"] for r in symbols),
            },
            "call_chain": {
                "symbol_family": ["RunOptimization", "Run", "RunFC", "checkConv", "checkAct", "checkPool", "ALHardNPULayer", "CreateALHardNPU"],
                "instruction_level_edges": "NOT_RECOVERABLE",
                "interpretation": "The names identify the bounded fusion implementation family; no call edge is asserted without AArch64 disassembly or source.",
            },
        },
        "alnpu_layer_support": {
            "overrides": {name: override_map[name] for name in ALNPU_OVERRIDES},
            "generic_layer_support_base_symbols": {name: generic_map[name] for name in GENERIC_METHODS},
            "vtable_dispatch_reused_from_task028": prior_dispatch["vtable_slots"],
            "override_set_exactly_matches_task031": all(override_map[name] for name in ALNPU_OVERRIDES),
            "generic_methods_are_not_alnpu_overrides": all(generic_map[name] for name in GENERIC_METHODS),
            "interpretation": "The audited binary has a finite AlnpuLayerSupport dispatch whitelist. The listed generic methods resolve to LayerSupportBase symbols; this is a proven dispatch fact, not a complete semantic predicate for every fused path.",
        },
        "predicate_evidence": {
            "string_level_indications": embedded,
            "indications": [
                {"condition": "weights/input/bias data-type checks and input-weight type matching", "evidence": "embedded strings", "status": "STRING_LEVEL_ONLY"},
                {"condition": "input channel <= 4095", "evidence": "embedded string", "status": "STRING_LEVEL_ONLY"},
                {"condition": "output height/width in 1..1023", "evidence": "embedded string", "status": "STRING_LEVEL_ONLY"},
                {"condition": "padding equals (kernel_size-1)/2", "evidence": "embedded string", "status": "STRING_LEVEL_ONLY"},
                {"condition": "kernel/stride modes including 2x2 and 1x4", "evidence": "nearby binary strings from retained Task 028 audit", "status": "STRING_LEVEL_ONLY"},
                {"condition": "elementwise Add-only and broadcast/type checks", "evidence": "embedded strings", "status": "MIXED_GENERIC_OR_BACKEND_STRING; NOT_ATTRIBUTED"},
                {"condition": "float, uint8 and int8 ALHardNPU template families", "evidence": "exported symbols", "status": "COMPILED_TEMPLATE_ONLY"},
            ],
            "not_recovered": [
                "exact predecessor and successor layer requirements",
                "exact Conv kernel/stride/padding/dilation/groups predicate and branch selection",
                "exact input/output channel limits beyond the string-level indications",
                "layout and tensor alignment requirements",
                "per-channel versus per-tensor scale/zero-point acceptance matrix",
                "activation fusion semantics and graph rewrite ordering",
                "hardware tile/alignment constraints",
            ],
        },
        "source_and_disassembly_limits": {
            "backend_source_available": False,
            "source_path_strings_only": True,
            "library_stripped": True,
            "aarch64_disassembler_available": any(disassembler_candidates.values()),
            "aarch64_disassembler_candidates": disassembler_candidates,
            "host_objdump_output": objdump_out.strip(),
            "host_objdump_error": objdump_err.strip(),
            "exact_predicate_recovery": "NOT_RECOVERABLE",
            "reason": "No ArmNN backend source was present in the audited scopes and the WSL host objdump cannot disassemble AArch64 instructions; symbol names, vtable dispatch and strings cannot establish the complete predicate.",
        },
        "safety": {"board_accessed": False, "vendor_program_executed": False, "model_modified": False, "benchmark_run": False, "runtime_modified": False},
    }


def face_regions() -> dict[str, Any]:
    audit = load("trackc3_capability_face_path_audit.json")
    face = audit["face_positive_path"]
    face_provenance = json.loads((TASK031 / "face_onnx_provenance.json").read_text(encoding="utf-8"))
    verified_face_sha = face_provenance["model"]["sha256"]
    assignments = face["strict_board_observation"]["runtime_assignments"]
    records = []
    for assignment in assignments:
        parts = [p.strip() for p in assignment.split("|")]
        records.append(
            {
                "assignment": assignment,
                "assignment_id": parts[0],
                "backend": parts[1],
                "fused_layer": parts[2],
                "exact_original_onnx_nodes": "NOT_RECOVERABLE_FROM_RETAINED_LOG",
                "region_graph_pattern": "NOT_RECOVERABLE; only graph-level Conv/Relu/MaxPool/Concat candidate inventory is retained",
                "region_shape_dtype_quantization": "NOT_RECOVERABLE_PER_REGION",
            }
        )
    return {
        "schema_version": 1,
        "task": "032",
        "status": "COMPLETE_WITH_MAPPING_LIMIT",
        "source_classification": "real_device_assignment_fact_reused_from_task_026; graph inventory fact from task_031; mapping limitation explicit",
        "model": {"name": face["model"], "sha256": verified_face_sha, "task028_recorded_model_hash": face["model_sha256"], "task028_recorded_hash_status": "MALFORMED_IN_IMMUTABLE_TASK028_RECORD", "opset": face["network_contract"]["opset"]},
        "execution_sequence": face["execution_sequence"],
        "observed_fused_assignment_count": len(assignments),
        "regions": records,
        "common_graph_inventory": {
            "input": face["network_contract"]["input"],
            "outputs": face["network_contract"]["outputs"],
            "nodes": face["network_contract"]["graph_nodes"],
            "operator_counts": {"Conv": 13, "Relu": 11, "MaxPool": 6, "Concat": 1, "Resize": 1, "QuantizeLinear": 33, "DequantizeLinear": 59, "Split": 0},
            "initializer_dtypes": {"FLOAT": 61, "INT32": 14, "INT64": 1, "UINT8": 37},
            "backend_layout": "NOT_RECOVERABLE_PER_REGION",
            "internal_activation_quantization": "QDQ present; exact per-region scales/zero-points not retained",
        },
        "fusion_interpretation": {
            "positive_fact": "The strict board run reported three Alnpu|ALHardNPU assignments, Optimize and LoadNetwork PASS, exit code 0, and CPU fallback disabled.",
            "why_this_is_not_generic_conv_proof": "The same audited AlnpuLayerSupport does not override generic IsConvolution2dSupported; the assignment is evidence of a vendor fusion/custom workload path.",
            "exact_region_mapping": "NOT_RECOVERABLE",
            "missing_trace": "The retained logs contain assignment IDs and layer type but no parser layer names, graph node IDs or per-region tensor descriptors.",
        },
        "safety": {"new_board_run": False, "board_evidence_reused": True, "model_modified": False},
    }


def yolov5n_comparison() -> dict[str, Any]:
    dialect = load("graph_dialect_diff.json")
    smoke = load("trackc_official_smoke.json")
    controls = load("trackc3_model_control_comparison.json")
    verified_face_sha = json.loads((TASK031 / "face_onnx_provenance.json").read_text(encoding="utf-8"))["model"]["sha256"]
    boundary = load("trackc3_support_boundary_audit.json")["real_graph_evidence"]
    original = dialect["frozen_yolov5n"]
    sim = smoke["graph_contract"]["sim_detect_crop"]
    quant = smoke["graph_contract"]["quant_uint8"]
    return {
        "schema_version": 1,
        "task": "032",
        "status": "COMPLETE_PATTERN_COMPARISON",
        "source_classification": "immutable_task_028_graph_and_real_optimize_evidence",
        "face_reference": {"model_sha256": verified_face_sha, "task028_recorded_model_hash": controls["models"]["vendor_face_positive"]["model_sha256"], "task028_recorded_hash_status": "MALFORMED_IN_IMMUTABLE_TASK028_RECORD", "operator_counts": controls["models"]["vendor_face_positive"]["operator_counts"], "input": controls["models"]["vendor_face_positive"]["input"], "outputs": controls["models"]["vendor_face_positive"]["outputs"], "split": 0, "custom_alhardnpu_onnx_node": False},
        "frozen_fp32": {"model_sha256": "78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121", "path_name": original["path_name"], "opset": original["opsets"], "node_count": original["node_count"], "operator_counts": original["operator_counts"], "input": original["inputs"][0], "output": original["outputs"][0], "qdq": False, "first_observed_board_gate": "FP32 parser rejected Floor at /model.11/Floor in Task 028 matrix; this is a parser gate, not a recovered fusion predicate"},
        "al_onnx_pass_detect_crop_fp32": {"node_count": sim["nodes"], "operator_counts": sim["operator_counts"], "inputs": sim["inputs"], "outputs": sim["outputs"], "shape_ops": sim["operators"], "semantic_change": "Detect output is intentionally cropped from [1,25200,85] to three raw FLOAT heads"},
        "al_onnx_pass_quantized": {"node_count": quant["nodes"], "operator_counts": quant["operator_counts"], "inputs": quant["inputs"], "outputs": quant["outputs"], "shape_ops": quant["operators"], "quantization": {"format": "ONNX QDQ", "uint8": "Q/DQ wrappers around generic graph operators", "int8": "QSymmS8 candidate with per-channel weight axis=0 in Task 028", "native_alhardnpu_node_created": False}, "first_observed_board_gates": {"uint8": boundary["project_yolov5n_uint8"]["first_real_graph_failure"], "int8": boundary["project_yolov5n_int8"]["first_real_graph_failure"]}},
        "pattern_comparison": [
            {"pattern": "Conv", "face": "13 Conv nodes inventory; exact fusion membership unavailable", "yolov5n": "60 Conv nodes", "backend_observation": "generic quantized Conv2d rejected for YOLOv5n; exact fusion eligibility unknown"},
            {"pattern": "SiLU", "face": "Relu nodes, no SiLU Sigmoid+Mul inventory", "yolov5n": "Sigmoid+Mul repeated (60/57 in original/cropped graph)", "backend_observation": "generic quantized Activation/ElementwiseBinary rejected"},
            {"pattern": "residual Add", "face": "not present in retained operator inventory", "yolov5n": "Add 10 original, 7 cropped/quantized", "backend_observation": "generic Add/Elementwise support is not an Alnpu override"},
            {"pattern": "C3 split/concat", "face": "Concat 1, Split 0", "yolov5n": "Concat 21 and Split 3 in original; cropped graph retains 13 Concat", "backend_observation": "Splitter is generic LayerSupportBase; no exact fusion predicate recovered"},
            {"pattern": "SPPF MaxPool/Concat", "face": "MaxPool 6, Concat 1", "yolov5n": "MaxPool 3, Concat 21 original", "backend_observation": "Pooling/Concat have Alnpu overrides, but individual descriptor acceptance is unknown"},
            {"pattern": "Resize/Upsample", "face": "Resize 1", "yolov5n": "Resize 2", "backend_observation": "Resize has an Alnpu override; exact mode/shape predicate unknown"},
            {"pattern": "Detect head", "face": "two FLOAT heads [1,18,26,26] and [1,18,13,13]", "yolov5n": "original [1,25200,85], AL_onnx_pass three FLOAT heads [1,255,80,80], [1,255,40,40], [1,255,20,20]", "backend_observation": "output contract differs; Detect crop is a documented tool operation, not a proof of fusion"},
            {"pattern": "QDQ", "face": "59 DQ/33 Q; UINT8 initializers present", "yolov5n": "320 DQ/200 Q; UINT8 or INT8 candidates", "backend_observation": "face passes through fused ALHardNPU path; YOLO candidates fail generic quantized layers at Optimize"},
        ],
        "first_observed_gate_vs_fusion": {
            "first_real_yolov5n_uint8": "QAsymmU8 Conv2d, Activation and ElementwiseBinary at Alnpu Optimize",
            "first_real_yolov5n_int8": "QSymmS8 Conv2d, Activation and ElementwiseBinary at Alnpu Optimize",
            "necessary_fusion_condition_identified": False,
            "reason": "The dispatch boundary explains which generic support slots reject, but no instruction-level/source trace connects a particular YOLO node to ConvertConv2dIntoALHardNPUImpl::checkConv/checkAct/checkPool.",
        },
        "model_sha256s": {"frozen_fp32": "78ac19bbec667f9a60e483c950f450e320e8efe3930a40edaa248fdce659c121", "uint8": controls["models"]["project_yolov5n_uint8"]["model_sha256"], "int8": controls["models"]["project_yolov5n_int8"]["model_sha256"]},
        "safety": {"new_board_run": False, "benchmark": False, "model_modified": False, "synthetic_probe_used_for_conclusion": False},
    }


def al_onnx_pass_audit() -> dict[str, Any]:
    audit = load("al_onnx_pass_audit.json")
    smoke = load("trackc_official_smoke.json")
    source_files: dict[str, dict[str, Any]] = {}
    for name, record in audit["source_files"].items():
        value: dict[str, Any] = {"role": record["role"]}
        if re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
            value["sha256"] = record["sha256"]
        else:
            value["recorded_hash"] = record["sha256"]
            value["sha256_status"] = "MALFORMED_IN_IMMUTABLE_TASK028_RECORD"
        source_files[name] = value
    return {
        "schema_version": 1,
        "task": "032",
        "status": "COMPLETE_STATIC_PIPELINE_AUDIT",
        "source_classification": "source_code_fact_reused_from_task_028",
        "source_identity": {"repository": audit["source_identity"]["root"], "branch": audit["source_identity"]["branch"], "commit": audit["source_identity"]["head"], "script_sha256": audit["source_files"]["AL_onnx_pass.py"]["sha256"], "requirements_sha256": audit["source_files"]["requirements.txt"]["sha256"]},
        "actual_stages": audit["pipeline"]["stages"],
        "source_files": source_files,
        "graph_effects": {"original_fp32": {"opset": 12, "nodes": 292, "floor": 4, "shape": 2, "resize": 2, "qdq": 0}, "official_detect_crop_fp32": {"nodes": smoke["graph_contract"]["sim_detect_crop"]["nodes"], "floor": 0, "shape": 0, "resize": 2, "qdq": 0, "outputs": smoke["graph_contract"]["sim_detect_crop"]["outputs"]}, "official_uint8": {"nodes": smoke["graph_contract"]["quant_uint8"]["nodes"], "floor": 0, "shape": 0, "resize": 2, "qdq": {"quantize": 200, "dequantize": 320}, "outputs": smoke["graph_contract"]["quant_uint8"]["outputs"]}},
        "native_or_alhardnpu_transformation": {"native_compiler_invoked": False, "npu_runtime_invoked": False, "rt_bin_or_weight_bin_created": False, "alhardnpu_custom_onnx_node_created": False, "extra_conversion_between_al_onnx_pass_and_armnn": "NOT_FOUND_IN_TASK028_SOURCE_AUDIT"},
        "causal_assessment": {"proven": ["AL_onnx_pass performs simplification, fixed-shape/Detect extraction, optional split, checker and ONNX Runtime static QDQ"], "not_proven": ["that QDQ alone destroys a previously eligible ALHardNPU fusion", "that Detect crop makes a graph eligible", "that any output shape or operator rewrite satisfies checkConv/checkAct/checkPool"], "interpretation": "The official pass removes the original Detect shape subgraph and adds generic QDQ wrappers; it does not create an ALHardNPU node or invoke a native compiler. The board failures therefore remain graph/backend observations, not a recovered conversion recipe."},
        "safety": {"vendor_script_executed_this_audit": False, "board_accessed": False, "model_modified": False},
    }


def verdict(symbols: dict[str, Any], face: dict[str, Any], yolo: dict[str, Any], alpass: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "task": "032",
        "status": "COMPLETE",
        "conclusion": "FUSION_PREDICATE_NOT_RECOVERABLE",
        "scope": "Only the audited AArch64 libarmnn.so.32.1 family and immutable Task 028/031 evidence; not a statement about DR1M90 hardware or future vendor backends.",
        "task028_status_unchanged": "BLOCKED_EXTERNAL_VENDOR_DEPENDENCY",
        "primary_root_cause_statement": "The face graph demonstrably reaches three ALHardNPU fused/custom workloads, while real YOLOv5n candidates reach generic quantized Conv2d/Activation/ElementwiseBinary rejection at Alnpu Optimize. Static dispatch proves the generic slots are not Alnpu overrides, but the complete ALHardNPU fusion predicate cannot be reconstructed from the stripped binary and unavailable backend source.",
        "proven_facts": [
            "ConvertConv2dIntoALHardNPUImpl::RunOptimization, findLastLayer, Run, RunFC, checkConv, checkAct and checkPool are exported symbols.",
            "ALHardNPU layer/workload creation and float/uint8/int8 template symbols are present.",
            "The audited AlnpuLayerSupport override set contains ten methods and does not override generic Conv2d, Activation, Splitter, Addition, Multiplication or ElementwiseUnary support.",
            "The face board run reported three Alnpu|ALHardNPU assignments with Optimize/LoadNetwork PASS and CPU fallback disabled.",
            "YOLOv5n UINT8/INT8 real graphs fail at generic quantized layer support before LoadNetwork; vendor YOLOv8n independently fails at QAsymmU8 Splitter.",
        ],
        "partial_predicate_indications": symbols["predicate_evidence"]["indications"],
        "not_proven": symbols["predicate_evidence"]["not_recovered"],
        "face_regions_exact_mapping": face["fusion_interpretation"]["exact_region_mapping"],
        "al_onnx_pass_effect": alpass["causal_assessment"],
        "model_compatibility_decision": "CANNOT_CLASSIFY_AS_A_OR_B_WITHOUT_EXACT_PREDICATE",
        "reopening_requirement": "BLOCKED_EXTERNAL_VENDOR_DEPENDENCY remains; a vendor backend source/build with the predicate, a supported generic-YOLO Alnpu backend, or APUG1205/native compiler evidence is required before a model conversion experiment.",
        "safety": {"board_accessed": False, "benchmark_run": False, "model_modified": False, "runtime_modified": False, "vendor_binary_executed": False},
    }


def write_json(name: str, value: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate() -> list[str]:
    required = ("fusion_symbol_audit.json", "face_fusion_regions.json", "yolov5n_pattern_comparison.json", "al_onnx_pass_pattern_audit.json", "fusion_eligibility_verdict.json")
    errors: list[str] = []
    docs: dict[str, dict[str, Any]] = {}
    for name in required:
        path = OUT / name
        if not path.is_file():
            errors.append(f"missing {name}")
            continue
        try:
            docs[name] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON {name}: {exc}")
    if errors:
        return errors
    symbol = docs["fusion_symbol_audit.json"]
    if symbol.get("task") != "032":
        errors.append("symbol task mismatch")
    if not all(symbol["direct_fusion_symbols"]["required_presence"].values()):
        errors.append("missing direct fusion symbol")
    if set(symbol["alnpu_layer_support"]["overrides"]) != set(ALNPU_OVERRIDES):
        errors.append("Alnpu override set mismatch")
    if set(symbol["alnpu_layer_support"]["generic_layer_support_base_symbols"]) != set(GENERIC_METHODS):
        errors.append("generic base method set mismatch")
    if symbol["source_and_disassembly_limits"]["exact_predicate_recovery"] != "NOT_RECOVERABLE":
        errors.append("predicate was incorrectly promoted")
    face = docs["face_fusion_regions.json"]
    if face.get("observed_fused_assignment_count") != 3 or len(face.get("regions", [])) != 3:
        errors.append("face assignment count/regions mismatch")
    if face["fusion_interpretation"]["exact_region_mapping"] != "NOT_RECOVERABLE":
        errors.append("face mapping limitation missing")
    if face["model"].get("sha256") != json.loads((TASK031 / "face_onnx_provenance.json").read_text(encoding="utf-8"))["model"]["sha256"]:
        errors.append("face model identity does not match Task 031 provenance")
    verdict_doc = docs["fusion_eligibility_verdict.json"]
    if verdict_doc.get("conclusion") not in VERDICTS:
        errors.append("invalid conclusion enum")
    if verdict_doc.get("conclusion") != "FUSION_PREDICATE_NOT_RECOVERABLE":
        errors.append("expected conservative C conclusion")
    alpass = docs["al_onnx_pass_pattern_audit.json"]
    if alpass["native_or_alhardnpu_transformation"]["alhardnpu_custom_onnx_node_created"]:
        errors.append("ALHardNPU custom ONNX node falsely asserted")
    comparison = docs["yolov5n_pattern_comparison.json"]
    if comparison["first_observed_gate_vs_fusion"]["necessary_fusion_condition_identified"]:
        errors.append("necessary fusion predicate falsely asserted")
    forbidden = ("/" + "mnt/c/Users/", "/" + "home/", "C:" + "\\Users\\", "-----" + "BEGIN ")
    for name in required:
        text = (OUT / name).read_text(encoding="utf-8")
        for marker in forbidden:
            if marker in text:
                errors.append(f"non-portable/sensitive marker {marker!r} in {name}")
    for old_root in (TASK028, TASK031):
        if not old_root.is_dir():
            errors.append(f"immutable evidence root missing: {old_root}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="collect the temporary binary and write evidence")
    parser.add_argument("--validate", action="store_true", help="validate generated evidence")
    parser.add_argument("--library", type=Path, default=Path(os.environ.get("TASK032_ARMNN_LIB", DEFAULT_LIB)))
    parser.add_argument("--archive", type=Path, default=None, help="external archive used for the read-only hash check (required by --write)")
    args = parser.parse_args()
    if not args.write and not args.validate:
        parser.error("choose --write or --validate")
    if args.write:
        if args.archive is None:
            parser.error("--archive is required with --write; the vendor path is intentionally not embedded in the script")
        symbols = static_binary_audit(args.library, args.archive)
        face = face_regions()
        yolo = yolov5n_comparison()
        alpass = al_onnx_pass_audit()
        final = verdict(symbols, face, yolo, alpass)
        write_json("fusion_symbol_audit.json", symbols)
        write_json("face_fusion_regions.json", face)
        write_json("yolov5n_pattern_comparison.json", yolo)
        write_json("al_onnx_pass_pattern_audit.json", alpass)
        write_json("fusion_eligibility_verdict.json", final)
    if args.validate or args.write:
        errors = validate()
        result = {"schema_version": 1, "task": "032", "status": "PASS" if not errors else "FAIL", "checks": ["required JSON parse", "fusion symbol presence and override sets", "face assignment count and explicit mapping limit", "conservative verdict enum", "AL_onnx_pass custom-node absence", "Task 028/031 evidence roots present", "portable text and sensitive-material scan"], "errors": errors, "commands": {"write": "python3 scripts/vendor/audit_task032_alhardnpu_fusion.py --write --archive <external-armnn-archive>", "validate": "python3 scripts/vendor/audit_task032_alhardnpu_fusion.py --validate"}}
        write_json("validation.json", result)
        print(json.dumps(result, indent=2))
        return 0 if not errors else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
