#!/usr/bin/env python3
"""Bounded, read-only inventory of explicitly approved Anlogic asset roots.

The script records identities only; it never executes a discovered file.  Paths
in the JSON output are relative to the supplied root labels so a local Windows
username is not copied into repository evidence.
"""
import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Dict, Iterable, List


TOKENS = (
    "npu", "runtime", "one shot", "one_shot", "yolo", "hard_npu", "soft_npu",
    "cma_mem", "rt.bin", "weight.bin", "model.bin", "libnpu", "libnn",
    "converter", "compiler", "quant", "softnpu", "video_npu", "apug1205",
    "ipug166",
)
TOKEN_RE = re.compile("|".join(re.escape(t) for t in TOKENS), re.IGNORECASE)


def sha256(path: Path, limit: int) -> Dict[str, Any]:
    size = path.stat().st_size
    if size > limit:
        return {"sha256": None, "sha256_status": "not_computed_above_limit", "sha256_limit_bytes": limit}
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "sha256_status": "computed"}


def safe_type(path: Path) -> str:
    mode = path.stat().st_mode
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISREG(mode):
        suffix = path.suffix.lower()
        if suffix in {".pdf", ".md", ".txt", ".rst"}:
            return "document"
        if suffix in {".hpf", ".bit", ".bin", ".img", ".dtb", ".ko"}:
            return "binary_or_hardware_asset"
        if suffix in {".so", ".a"} or ".so." in path.name:
            return "library"
        if path.name.lower().endswith(('.sh', '.py', '.c', '.cc', '.cpp', '.h', '.hpp', 'makefile')):
            return "source_or_script"
        return "file"
    return "other"


def iter_candidates(root: Path, max_files: int) -> Iterable[Path]:
    count = 0
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", "__pycache__"}]
        for filename in sorted(filenames):
            path = Path(directory) / filename
            try:
                relative = path.relative_to(root).as_posix()
            except ValueError:
                continue
            if not TOKEN_RE.search(relative):
                continue
            yield path
            count += 1
            if count >= max_files:
                return


def describe_path(path: Path, root: Path, hash_limit: int, selection: str = "token_match") -> Dict[str, Any]:
    st = path.stat()
    item: Dict[str, Any] = {
        "relative_path": path.relative_to(root).as_posix(),
        "selection": selection,
        "type": safe_type(path),
        "size_bytes": st.st_size,
        "mtime_epoch": int(st.st_mtime),
        "mode": oct(stat.S_IMODE(st.st_mode)),
    }
    item.update(sha256(path, hash_limit))
    return item


def inventory_root(label: str, root: Path, max_files: int, hash_limit: int, explicit: List[str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {"root_label": label, "root_exists": root.exists(), "candidates": []}
    if not root.exists():
        result["root_status"] = "not_found"
        return result
    result["root_status"] = "readable_directory" if root.is_dir() else "not_directory"
    if not root.is_dir():
        return result
    seen = set()
    for path in iter_candidates(root, max_files):
        try:
            item = describe_path(path, root, hash_limit)
            result["candidates"].append(item)
            seen.add(item["relative_path"])
        except (OSError, ValueError) as exc:
            result["candidates"].append({"relative_path": str(path), "status": "stat_failed", "error_type": type(exc).__name__})
    for relative in explicit:
        path = root / relative
        if relative in seen:
            continue
        try:
            result["candidates"].append(describe_path(path, root, hash_limit, "explicit"))
        except (OSError, ValueError) as exc:
            result["candidates"].append({"relative_path": relative, "selection": "explicit", "status": "stat_failed", "error_type": type(exc).__name__})
    result["candidate_count"] = len(result["candidates"])
    result["scan_status"] = "bounded_complete"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", nargs=2, metavar=("LABEL", "PATH"), required=True)
    parser.add_argument("--max-files-per-root", type=int, default=500)
    parser.add_argument("--hash-limit-bytes", type=int, default=16 * 1024 * 1024)
    parser.add_argument("--include", action="append", nargs=2, metavar=("LABEL", "RELATIVE_PATH"), default=[],
                        help="include an explicitly reviewed path even if its name has no token")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = {
        "schema_version": "task022-npu-asset-inventory-v1",
        "capture_method": "bounded_read_only_filesystem_scan",
        "executed_files": False,
        "roots": [inventory_root(label, Path(path), args.max_files_per_root, args.hash_limit_bytes,
                                   [relative for include_label, relative in args.include if include_label == label])
                  for label, path in args.root],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.output)
    print(json.dumps({"output": str(args.output), "roots": len(payload["roots"]), "executed_files": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
