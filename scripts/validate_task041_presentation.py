#!/usr/bin/env python3
"""Validate the concise Task 041 README and presentation pack.

This validator reads the immutable Task040 authoritative manifest.  It checks
that the homepage contains the required engineering story, does not turn
integration or NPU-control evidence into a YOLO benchmark, and that all local
Markdown links resolve without requiring external access.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
PRESENTATION = ROOT / "docs" / "PROJECT_PRESENTATION.md"
MANIFEST = ROOT / "results" / "final" / "authoritative_results.json"
TASK = ROOT / "tasks" / "041_final_readme_project_presentation.md"

TASK040_ALLOWED = {
    "README.md",
    "TASKS.md",
    "docs/FINAL_BENCHMARK_RESULTS.md",
    "results/final/README_READY_TABLES.md",
    "results/final/authoritative_results.json",
    "results/final/validation.json",
    "scripts/validate_task040_final_results.py",
    "tasks/040_final_cross_platform_benchmark_results.md",
    "tests/python/test_task040_final_results.py",
}
TASK041_ALLOWED = TASK040_ALLOWED | {
    "docs/PROJECT_PRESENTATION.md",
    "scripts/validate_task041_presentation.py",
    "tasks/041_final_readme_project_presentation.md",
    "tests/python/test_task041_presentation.py",
    # Later release-validation tasks add evidence-only presentation assets;
    # accepting these paths keeps this historical hygiene check composable
    # without relaxing its README/evidence assertions.
    "docs/FINAL_DEMO_GUIDE.md",
    "release/demo/manifest.json",
    "scripts/validate_task042_demo_release.py",
    "tasks/042_final_demo_capture_release_validation.md",
    "tests/python/test_task042_demo_release.py",
    "docs/career/RESUME_PROJECT.md",
    "docs/career/PROJECT_PITCH.md",
    "docs/career/INTERVIEW_QA.md",
    "docs/career/PROJECT_STORIES.md",
    "docs/career/FINAL_PROJECT_FACTS.md",
    "scripts/validate_task043_career_package.py",
    "tasks/043_resume_interview_package.md",
    "tests/python/test_task043_career_package.py",
}


def fail(message: str) -> None:
    raise AssertionError(message)


def local_links(path: Path, text: str) -> list[str]:
    links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
    for link in links:
        if link.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = (path.parent / link.split("#", 1)[0]).resolve()
        if not target.exists():
            fail(f"broken local Markdown link: {path.relative_to(ROOT)} -> {link}")
    return links


def fmt6(value: float) -> str:
    return f"{float(value):.6f}"


def validate() -> dict[str, object]:
    for path in (README, PRESENTATION, MANIFEST, TASK):
        if not path.is_file():
            fail(f"missing presentation file: {path.relative_to(ROOT)}")
    readme = README.read_text(encoding="utf-8")
    presentation = PRESENTATION.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    required_sections = (
        "Project Highlights", "Architecture", "Deployment Pipeline",
        "Backend Matrix", "Final Benchmark", "Accuracy / Performance Trade-off",
        "ARM Optimization", "TensorRT Optimization", "DR1 Camera Demo",
        "DR1 NPU Enablement", "Quick Start", "Repository Structure",
        "Reproducibility / Evidence", "Known Limitations",
    )
    missing = [section for section in required_sections if f"## {section}" not in readme]
    if missing:
        fail(f"README missing sections: {missing}")
    keywords = (
        "ONNX", "ONNX Runtime", "TensorRT", "CUDA", "C++", "OpenCV", "ncnn",
        "INT8", "FP16", "ARM Linux", "V4L2", "NPU", "profiling", "benchmark",
    )
    missing_keywords = [word for word in keywords if word not in readme]
    if missing_keywords:
        fail(f"README missing technical keywords: {missing_keywords}")
    if readme.count("```mermaid") < 2 or "flowchart LR" not in readme or "flowchart TD" not in readme:
        fail("README does not contain both Mermaid architecture and deployment diagrams")
    if "WAITING_FOR_VENDOR_INPUT" not in readme or "FUNCTIONAL_CONTROL_ONLY" not in readme:
        fail("README NPU status boundary is incomplete")
    if "camera integration evidence" not in readme.lower() or "not a realtime" not in readme.lower():
        fail("README camera scope boundary is incomplete")
    if "Task038" not in readme or "Task039" not in readme or "integration evidence" not in readme:
        fail("README does not distinguish integration evidence")
    if "no cpu fallback" not in readme.lower():
        fail("README does not state the no-fallback policy")
    # The formal homepage must not accidentally publish the Task038 integration
    # timing values as final rows.
    if "4.255539" in readme or "7.397064" in readme:
        fail("README copied Task038 integration timing into the presentation table")

    required_presentation_sections = (
        "README-ready architecture", "README-ready deployment flow",
        "One-to-two-minute demo script", "Demo recording shot list",
        "Screenshots and results usage", "Presenter facts to keep exact",
    )
    missing = [section for section in required_presentation_sections if f"## {section}" not in presentation]
    if missing:
        fail(f"presentation document missing sections: {missing}")
    if presentation.count("```mermaid") < 2:
        fail("presentation document is missing one of the two Mermaid diagrams")
    if "WAITING_FOR_VENDOR_INPUT" not in presentation or "Alnpu | ALHardNPU" not in presentation:
        fail("presentation NPU boundary is incomplete")

    if manifest.get("status") != "FINAL_BENCHMARK_RESULTS_FROZEN":
        fail("Task040 manifest is not frozen")
    if manifest.get("provenance_policy", {}).get("cross_platform_speedup_claimed") is not False:
        fail("cross-platform speedup policy changed")
    rows = {row["id"]: row for row in manifest["authoritative_results"]["cross_platform_yolov5n_performance"]}
    expected_ids = {
        "pc_ort_fp32", "rtx4060ti_tensorrt_fp32", "rtx4060ti_tensorrt_fp16",
        "dr1_ncnn_fp32", "dr1_ncnn_eq",
    }
    if set(rows) != expected_ids:
        fail(f"authoritative row IDs differ: {sorted(rows)}")
    # Check the displayed formal pipeline values against the authoritative file,
    # rather than maintaining a second hand-edited result source.
    for row_id in expected_ids:
        for metric_name in ("backend_inference_ms", "pipeline_ms"):
            value = fmt6(rows[row_id]["metrics"][metric_name]["mean"])
            if value not in readme:
                fail(f"README is missing authoritative {metric_name} value {row_id}: {value}")
        fps = fmt6(rows[row_id]["metrics"]["fps"])
        if fps not in readme:
            fail(f"README is missing authoritative FPS value {row_id}: {fps}")
    trt = rows["rtx4060ti_tensorrt_fp16"]["metrics"]
    if fmt6(trt["gpu_execution_ms"]["mean"]) not in readme:
        fail("README is missing the authoritative TensorRT GPU execution value")
    tradeoffs = manifest["authoritative_results"]["accuracy_performance_tradeoff"]
    if not all(item["accuracy"]["gate"]["status"] == "PASS" for item in tradeoffs):
        fail("README source contains a failed accuracy gate")
    for item in tradeoffs:
        for side in ("reference", "candidate"):
            for key in ("mAP50", "mAP50_95"):
                value = fmt6(item["accuracy"][side][key])
                if value not in readme:
                    fail(f"README is missing authoritative accuracy value {item['id']} {side} {key}: {value}")
        for key in ("mAP50", "mAP50_95"):
            value = fmt6(item["accuracy"]["delta_candidate_minus_reference"][key])
            if value not in readme:
                fail(f"README is missing authoritative accuracy delta {item['id']} {key}: {value}")
    matrix = {item["backend"]: item["status"] for item in manifest["authoritative_results"]["deployment_capability_matrix"]}
    if matrix.get("Alnpu | ALHardNPU") != "FUNCTIONAL_CONTROL_ONLY" or matrix.get("Alnpu") != "WAITING_FOR_VENDOR_INPUT":
        fail("authoritative NPU matrix changed")

    links = local_links(README, readme) + local_links(PRESENTATION, presentation)
    sensitive = re.compile(r"/mnt/c/Users/|/home/[^/]+/|[A-Z]:\\Users\\|-----BEGIN .*PRIVATE KEY-----", re.I)
    if sensitive.search(readme) or sensitive.search(presentation):
        fail("presentation contains a sensitive absolute path or private-key marker")
    status = subprocess.check_output(["git", "status", "--short", "--untracked-files=all"], cwd=ROOT, text=True)
    changed = []
    for line in status.splitlines():
        path = line[3:]
        changed.append(path)
        if path not in TASK041_ALLOWED:
            fail(f"changed path outside Task040/041 allowed set: {path}")
    if not changed:
        fail("Task041 has no visible presentation changes")
    return {
        "status": "PASS",
        "task": "041",
        "checks": {
            "readme_sections_and_keywords": True,
            "mermaid_diagrams": True,
            "authoritative_manifest_values": True,
            "npu_scope_boundary": True,
            "demo_script_and_shot_list": True,
            "markdown_links": True,
            "sensitive_material_scan": True,
            "allowed_file_hygiene": True,
        },
        "local_markdown_links_checked": len(links),
        "changed_paths_checked": len(changed),
    }


def main() -> int:
    report = validate()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
