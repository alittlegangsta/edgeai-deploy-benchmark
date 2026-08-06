#!/usr/bin/env python3
"""Bounded, read-only archive inventory for the Task 025 03_demo audit.

The command never extracts or executes vendor material.  ZIP/TAR listings are
attempted with Python's standard library; RAR/7z entries are reported as
unavailable when no local reader is present.  Paths in the JSON are normalized
to avoid recording a host username or a Windows drive prefix.
"""

import argparse
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path


ARCHIVE_SUFFIXES = (".zip", ".rar", ".7z", ".tar", ".tar.gz", ".tgz", ".xz", ".img", ".iso")
HIGH_VALUE = (
    "05-5_npu", "npu", "linuxsdk", "boardconfig", "buildroot", "kernel",
    "u-boot", "uboot", "fsbl", "dts", "dtb", "hpf", "bitstream", "boot.bin",
    "soft_npu", "hard_npu", "cma_mem", "arm nn", "armnn", "yolo", "face",
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def priority(relative):
    text = relative.lower().replace("\\", "/")
    if "05-5_npu" in text or "/npu" in text:
        return "A"
    if "3-2_ex_fpsoc" in text or "3-4_ex_soc_linux" in text:
        return "B"
    if any(token in text for token in ("board", "linux", "sdk", "boot", "hpf", "dts")):
        return "C"
    return "D"


def listing(path):
    suffix = path.name.lower()
    if suffix.endswith(".zip"):
        try:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                return {
                    "status": "PASS",
                    "entry_count": len(names),
                    "uncompressed_bytes": sum(item.file_size for item in archive.infolist()),
                    "top_entries": names[:80],
                    "nested_archive_count": sum(
                        name.lower().endswith((".zip", ".rar", ".7z", ".tar", ".tar.gz"))
                        for name in names
                    ),
                }
        except (OSError, zipfile.BadZipFile) as exc:
            return {"status": "ERROR", "error": type(exc).__name__}
    if suffix.endswith((".tar", ".tar.gz", ".tgz")):
        try:
            with tarfile.open(path, "r:*") as archive:
                names = archive.getnames()
                return {
                    "status": "PASS",
                    "entry_count": len(names),
                    "uncompressed_bytes": sum(item.size for item in archive.getmembers()),
                    "top_entries": names[:80],
                    "nested_archive_count": sum(
                        name.lower().endswith((".zip", ".rar", ".7z", ".tar", ".tar.gz"))
                        for name in names
                    ),
                }
        except (OSError, tarfile.TarError) as exc:
            return {"status": "ERROR", "error": type(exc).__name__}
    if suffix.endswith((".rar", ".7z")):
        return {
            "status": "NOT_AVAILABLE_NO_LOCAL_READER",
            "reason": "No rar/unrar/7z reader is installed; no extraction was attempted.",
        }
    return {"status": "NOT_LISTED_FORMAT_NOT_ARCHIVE"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit("archive root is not a directory: %s" % root)
    records = []
    total = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        name = path.name.lower()
        if not name.endswith(ARCHIVE_SUFFIXES):
            continue
        relative = str(path.relative_to(root)).replace("\\", "/")
        size = path.stat().st_size
        total += size
        records.append({
            "relative_path": relative,
            "size_bytes": size,
            "sha256": digest(path),
            "format": next((suffix[1:] for suffix in ARCHIVE_SUFFIXES if name.endswith(suffix)), "unknown"),
            "priority": priority(relative),
            "listing": listing(path),
        })
    result = {
        "schema_version": "task025-03-demo-archive-inventory-v1",
        "source_root": "<vendor-root>/03_demo",
        "read_only": True,
        "extraction_performed": False,
        "archive_count": len(records),
        "archive_bytes": total,
        "local_listing_capabilities": {
            "zip": "python_zipfile",
            "tar": "python_tarfile",
            "rar": "unavailable_no_local_reader",
            "7z": "unavailable_no_local_reader",
        },
        "selection_policy": {
            "A": "direct NPU or MLK package",
            "B": "potential shared FPSoC/Linux build context",
            "C": "background or comparison payload",
            "D": "unrelated or generated/tool payload",
        },
        "artifacts": records,
        "copied_to_git": False,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "archive_count": len(records), "archive_bytes": total}, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
