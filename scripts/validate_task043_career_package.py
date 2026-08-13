#!/usr/bin/env python3
"""Validate the documentation-only Task043 career package.

The validator reads the frozen Task040 manifest and checks that the career
documents preserve its numbers and NPU boundaries.  It never runs an inference
binary or generates new evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "results/final/authoritative_results.json"
CAREER = ROOT / "docs/career"

DOCS = {
    "resume": CAREER / "RESUME_PROJECT.md",
    "pitch": CAREER / "PROJECT_PITCH.md",
    "qa": CAREER / "INTERVIEW_QA.md",
    "stories": CAREER / "PROJECT_STORIES.md",
    "facts": CAREER / "FINAL_PROJECT_FACTS.md",
}

ALLOWED = {
    "TASKS.md",
    "tasks/043_resume_interview_package.md",
    "docs/career/RESUME_PROJECT.md",
    "docs/career/PROJECT_PITCH.md",
    "docs/career/INTERVIEW_QA.md",
    "docs/career/PROJECT_STORIES.md",
    "docs/career/FINAL_PROJECT_FACTS.md",
    "scripts/validate_task043_career_package.py",
    "tests/python/test_task043_career_package.py",
    "scripts/validate_task041_presentation.py",
    "scripts/validate_task042_demo_release.py",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise AssertionError(message)


def read_authoritative() -> dict[str, Any]:
    with AUTH.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        fail("authoritative results must be a JSON object")
    if value.get("status") != "FINAL_BENCHMARK_RESULTS_FROZEN":
        fail("Task040 results are not frozen")
    return value


def local_links(path: Path, text: str) -> int:
    count = 0
    for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        if link.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = (path.parent / link.split("#", 1)[0]).resolve()
        if not target.exists():
            fail(f"broken Markdown link: {path.relative_to(ROOT)} -> {link}")
        count += 1
    return count


def expected_formal_values(authoritative: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    rows = authoritative["authoritative_results"]["cross_platform_yolov5n_performance"]
    for row in rows:
        metrics = row["metrics"]
        for key in ("backend_inference_ms", "pipeline_ms", "fps"):
            values.add(f"{float(metrics[key]['mean'] if key != 'fps' else metrics[key]):.6f}")
        rss = metrics["peak_rss_kib"].get("mean")
        if rss is not None:
            values.add(f"{float(rss):.0f}")
    for trade in authoritative["authoritative_results"]["accuracy_performance_tradeoff"]:
        accuracy = trade["accuracy"]
        for side in ("reference", "candidate", "delta_candidate_minus_reference"):
            for key in ("mAP50", "mAP50_95"):
                values.add(f"{float(accuracy[side][key]):.6f}")
    return values


def validate() -> dict[str, Any]:
    authoritative = read_authoritative()
    for name, path in DOCS.items():
        if not path.is_file():
            fail(f"missing career document: {name}")
    texts = {name: path.read_text(encoding="utf-8") for name, path in DOCS.items()}

    required_sections = {
        "resume": ("推荐项目名称", "中文简历 bullets", "English version", "技术栈关键词"),
        "pitch": ("30 秒介绍", "1 分钟介绍", "3 分钟介绍"),
        "qa": ("模型与 ONNX", "C++ 工程", "TensorRT / CUDA", "ARM / ncnn", "INT8 量化", "Linux / 交叉编译", "V4L2 / camera", "性能 profiling", "NPU / Arm NN / Alnpu", "系统设计"),
        "stories": ("ARM 性能优化", "INT8 量化", "TensorRT", "DR1 camera", "DR1 NPU", "Situation", "Task", "Action", "Result"),
        "facts": ("项目契约", "正式 YOLOv5n benchmark", "NPU facts and exact boundaries", "可以说", "不能说", "Backend capability matrix"),
    }
    for name, sections in required_sections.items():
        missing = [section for section in sections if section not in texts[name]]
        if missing:
            fail(f"{name} missing sections/markers: {missing}")

    keywords = ("C++", "ONNX", "ONNX Runtime", "TensorRT", "CUDA", "OpenCV", "ncnn", "INT8", "FP16", "ARM Linux", "V4L2", "NPU", "profiling", "benchmark")
    combined = "\n".join(texts.values())
    missing_keywords = [keyword for keyword in keywords if keyword.lower() not in combined.lower()]
    if missing_keywords:
        fail(f"career package missing technical keywords: {missing_keywords}")

    values = expected_formal_values(authoritative)
    facts = texts["facts"]
    missing_values = [value for value in sorted(values) if value not in facts]
    if missing_values:
        fail(f"FINAL_PROJECT_FACTS is missing authoritative values: {missing_values}")

    for marker in ("WAITING_FOR_VENDOR_INPUT", "FUNCTIONAL_CONTROL_ONLY", "Alnpu | ALHardNPU", "no CPU fallback", "custom YOLOv5n"):
        if marker.lower() not in combined.lower():
            fail(f"missing NPU boundary marker: {marker}")
    if "not benchmarked" not in facts.lower():
        fail("FINAL_PROJECT_FACTS must mark custom NPU as not benchmarked")
    if "runtime/driver bring-up" not in facts.lower():
        fail("FINAL_PROJECT_FACTS must preserve the allowed NPU bring-up wording")

    # Strong overclaims are forbidden in outward-facing documents.  The facts
    # file contains the phrase in its explicit "不能说" section, so check the
    # public narrative files separately.
    overclaim_patterns = (
        r"custom\s+YOLOv5n[^\n]{0,80}(?:已经|已|成功)运行[^\n]{0,40}NPU",
        r"vendor\s+face[^\n]{0,80}(?:x|倍|speedup)[^\n]{0,30}YOLOv5n",
        r"Alnpu[^\n]{0,80}YOLOv5n[^\n]{0,30}(?:FPS|speedup|加速)",
    )
    for name in ("resume", "pitch", "qa", "stories"):
        for pattern in overclaim_patterns:
            if re.search(pattern, texts[name], re.I):
                fail(f"possible NPU overclaim in {name}: {pattern}")

    links = sum(local_links(path, texts[name]) for name, path in DOCS.items())
    sensitive = re.compile(r"/mnt/c/Users/|/home/[^/< >]+/|[A-Z]:[\\/]Users[\\/]|-----BEGIN .*PRIVATE KEY-----", re.I)
    for name, text in texts.items():
        if sensitive.search(text):
            fail(f"sensitive absolute path/private-key marker in {name}")

    status = subprocess.check_output(["git", "status", "--short", "--untracked-files=all"], cwd=ROOT, text=True)
    changed = []
    for line in status.splitlines():
        path = line[3:]
        changed.append(path)
        if path not in ALLOWED:
            fail(f"changed path outside Task043 allowed set: {path}")
    tracked = set(
        subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    )
    missing_documents = [
        str(path.relative_to(ROOT))
        for path in DOCS.values()
        if str(path.relative_to(ROOT)) not in changed
        and str(path.relative_to(ROOT)) not in tracked
    ]
    if missing_documents:
        fail(f"career documents are neither changed nor tracked: {missing_documents}")

    return {
        "status": "PASS",
        "task": "043",
        "checks": {
            "five_career_documents": True,
            "authoritative_values": True,
            "npu_boundaries": True,
            "source_links": True,
            "sensitive_material_scan": True,
            "allowed_file_hygiene": True,
        },
        "authoritative_sha256": sha256(AUTH),
        "local_markdown_links_checked": links,
        "changed_paths_checked": len(changed),
        "experiments_run": False,
    }


def main() -> int:
    report = validate()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
