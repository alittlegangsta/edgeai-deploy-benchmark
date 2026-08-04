#!/usr/bin/env python3
"""Bounded, read-only inventory for the Anlogic NPU_info package.

The tool reports metadata only. It never extracts archives, executes files,
loads modules, or follows paths outside the two explicitly supplied roots.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any, Dict, Iterable, List


# Keep the default portable and free of a host-specific Windows username.  The
# caller must pass the approved local material root with --npu-info when the
# package is outside the repository.
PATTERNS = (
    "*.ko",
    "*.hpf",
    "*.bit",
    "*.bin",
    "rt.bin",
    "weight.bin",
    "convert_tool",
    "al_ai_flow",
    "libnpu*",
    "*runtime*",
    "*NPU*",
    "*npu*",
)


def sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        try:
            if path.is_file() and not path.is_symlink():
                yield path
        except OSError:
            continue


def pattern_matches(path: Path) -> bool:
    return any(path.match(pattern) for pattern in PATTERNS)


def audit(npu_info: Path, knowledge: Path, hash_selected: bool) -> Dict[str, Any]:
    if not npu_info.is_dir():
        raise FileNotFoundError(f"NPU_info root is not a directory: {npu_info}")
    npu_files = list(files(npu_info))
    selected: List[Dict[str, Any]] = []
    for path in npu_files:
        if pattern_matches(path):
            record: Dict[str, Any] = {
                "relative_path": path.relative_to(npu_info).as_posix(),
                "size_bytes": path.stat().st_size,
                "file_type": stat.filemode(path.stat().st_mode),
            }
            if hash_selected:
                record["sha256"] = sha256(path)
            selected.append(record)

    result: Dict[str, Any] = {
        "schema_version": "task023-package-audit-tool-v1",
        "read_only": True,
        "npu_info_root": str(npu_info),
        "knowledge_root": str(knowledge),
        "knowledge_versions_yaml_present": (
            knowledge / ".knowledge/manifests/versions.yaml"
        ).is_file(),
        "regular_file_count": len(npu_files),
        "regular_bytes": sum(path.stat().st_size for path in npu_files),
        "selected_pattern_count": len(selected),
        "selected_pattern_files": sorted(selected, key=lambda item: item["relative_path"]),
        "archive_extraction": "not performed",
        "execution": {
            "vendor_binaries_executed": False,
            "modules_loaded": False,
            "board_modified": False,
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--npu-info", type=Path, required=True)
    parser.add_argument("--knowledge-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--hash-selected",
        action="store_true",
        help="hash matched files; may take time for large bitstreams/images",
    )
    args = parser.parse_args()
    result = audit(args.npu_info.resolve(), args.knowledge_root.resolve(), args.hash_selected)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
