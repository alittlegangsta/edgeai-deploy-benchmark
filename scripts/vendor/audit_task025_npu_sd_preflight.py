#!/usr/bin/env python3
"""Bounded, read-only inventory for a Task 025 vendor-material root."""

import argparse
import hashlib
import json
from pathlib import Path


PATTERNS = (
    "BOOT.bin", "boot.scr", "system.dtb", "dtb.bin", "kernel.bin",
    "rootfs.bin", "*.hpf", "*.bit", "*.dts", "BoardConfig*",
    "*.ko", "libarmnn.so*", "libarmnnOnnxParser.so*", "rt.bin",
    "weight.bin", "convert_tool", "al_ai_flow",
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected(path):
    return any(path.match(pattern) or path.name == pattern for pattern in PATTERNS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit("inventory root is not a directory: %s" % root)
    count = 0
    total = 0
    selected_files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        count += 1
        size = path.stat().st_size
        total += size
        if selected(path):
            selected_files.append({
                "relative_path": str(path.relative_to(root)),
                "size_bytes": size,
                "sha256": sha256(path),
            })
    result = {
        "schema_version": "task025-bounded-vendor-inventory-v1",
        "root": str(root),
        "read_only": True,
        "regular_file_count": count,
        "regular_bytes": total,
        "selected_patterns": list(PATTERNS),
        "selected_files": selected_files,
        "copied_to_git": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "regular_file_count": count, "regular_bytes": total}, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
