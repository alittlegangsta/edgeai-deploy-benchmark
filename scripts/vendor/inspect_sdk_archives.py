#!/usr/bin/env python3
"""Inspect ZIP central directories without extracting archive members.

The script hashes and integrity-tests the selected archives, records every
member name and metadata in an external private directory, and emits a bounded
JSON summary. It never opens a member for extraction or execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PROJECT_ROOT / ".knowledge/manifests/local_sdk_inventory.yaml"
DEFAULT_PATHS = PROJECT_ROOT / ".knowledge/local_paths.yaml"

ARCHIVE_ALIASES = {
    "demo.zip": "secondary_demo_archive",
    "01_ex_linux_base_F3P_DR1M90G.zip": "linux_base_archive",
    "02_ex_linux_drive_F3P_DR1M90G.zip": "linux_driver_archive",
}

PATTERNS: dict[str, list[tuple[str, str]]] = {
    "sdk_markers": [
        ("SDK_*", r"(?:^|/)(?:SDK_[^/]*|sdk_[^/]*)"),
        ("VERSION", r"(?:^|/)(?:VERSION|version(?:\.[^/]*)?|version\.ini)$"),
        ("release_or_manifest", r"(?:^|/)(?:release(?:_notes)?|manifest)(?:\.[^/]*)?$"),
        ("README", r"(?:^|/)README(?:\.[^/]*)?$"),
    ],
    "buildroot_markers": [
        ("buildroot", r"buildroot"),
        ("output/host", r"(?:^|/)output/host(?:/|$)"),
        ("output/staging", r"(?:^|/)output/staging(?:/|$)"),
        ("output/target", r"(?:^|/)output/target(?:/|$)"),
        ("host/bin", r"(?:^|/)host/bin(?:/|$)"),
        ("staging", r"staging"),
        ("sysroot", r"sysroot"),
        ("rootfs", r"rootfs"),
        ("envsetup_or_setenv", r"(?:^|/)(?:envsetup|setenv)(?:\.sh)?$"),
        ("build.sh", r"(?:^|/)build\.sh$"),
    ],
    "toolchain_markers": [
        ("aarch64-linux-gnu-gcc", r"aarch64-linux-gnu-gcc"),
        ("aarch64-none-linux-gnu-gcc", r"aarch64-none-linux-gnu-gcc"),
        ("aarch64-buildroot-linux-gnu-gcc", r"aarch64-buildroot-linux-gnu-gcc"),
        ("aarch64-* -gcc", r"aarch64-[^/]*-gcc"),
        ("toolchain", r"toolchain"),
        ("toolchain.cmake", r"(?:^|/)toolchain\.cmake$"),
    ],
    "sysroot_markers": [
        ("sysroot", r"sysroot"),
        ("libc.so", r"(?:^|/)libc\.so(?:\.|$)"),
        ("ld-linux-aarch64", r"ld-linux-aarch64"),
        ("glibc", r"glibc"),
        ("musl", r"musl"),
    ],
    "kernel_markers": [
        ("linux/", r"(?:^|/)linux(?:/|$)"),
        ("kernel", r"kernel"),
        ("Image/uImage", r"(?:^|/)(?:Image|uImage)$"),
        ("modules", r"modules"),
        (".ko", r"\.ko$"),
    ],
    "npu_markers": [
        ("armnn", r"arm[_-]?nn"),
        ("opencv", r"opencv4?"),
        ("libnpu_runtime", r"libnpu_runtime"),
        ("npu_runtime", r"npu_runtime"),
        ("hard_npu.ko", r"hard_npu\.ko$"),
        ("soft_npu.ko", r"soft_npu\.ko$"),
        ("cma_mem.ko", r"cma_mem\.ko$"),
        (".hpf", r"\.hpf$"),
        ("*.bit", r"\.bit$"),
        ("bitstream", r"bitstream"),
        ("rt.bin/weight.bin", r"(?:^|/)(?:rt|weight)\.bin$"),
    ],
}


def load_yaml(path: Path) -> Any:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "PyYAML is required to read the repository YAML manifests; "
            "installing dependencies is outside this script"
        ) from exc
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except OSError as exc:
        raise RuntimeError(f"cannot read YAML file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise RuntimeError(f"invalid YAML in {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive_entries(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for item in manifest.get("archives", []):
        if not isinstance(item, dict) or not item.get("path"):
            raise RuntimeError("local_sdk_inventory.yaml contains an invalid archive record")
        path = Path(str(item["path"]))
        archive_id = str(item.get("id") or ARCHIVE_ALIASES.get(path.name, ""))
        if not archive_id:
            raise RuntimeError(f"archive has no stable id: {path}")
        if archive_id in records:
            raise RuntimeError(f"duplicate archive id: {archive_id}")
        records[archive_id] = {**item, "id": archive_id, "path": str(path)}
    expected = {"secondary_demo_archive", "linux_base_archive", "linux_driver_archive"}
    missing = sorted(expected - records.keys())
    if missing:
        raise RuntimeError(f"manifest is missing required archive ids: {', '.join(missing)}")
    return records


def choose_records(records: dict[str, dict[str, Any]], selected: list[str] | None) -> list[dict[str, Any]]:
    if not selected:
        return [records[key] for key in sorted(records)]
    unknown = sorted(set(selected) - records.keys())
    if unknown:
        raise RuntimeError(f"unknown --archive-id: {', '.join(unknown)}")
    return [records[key] for key in selected]


def private_output_default(paths_data: dict[str, Any]) -> Path:
    private_root = paths_data.get("private_workspace_root")
    if not private_root:
        raise RuntimeError(".knowledge/local_paths.yaml lacks private_workspace_root")
    return Path(str(private_root)) / "logs" / "archive_inventory"


def top_level(name: str) -> str:
    normalized = name.replace("\\", "/").lstrip("/")
    return normalized.split("/", 1)[0] if normalized else "<empty>"


def marker_summary(names: Iterable[str], patterns: list[tuple[str, str]]) -> list[dict[str, Any]]:
    names_list = list(names)
    result: list[dict[str, Any]] = []
    for label, expression in patterns:
        regex = re.compile(expression, re.IGNORECASE)
        matches = sorted({name for name in names_list if regex.search(name)})
        if matches:
            result.append({"pattern": label, "count": len(matches), "members": matches[:50]})
    return result


def encoding_summary(infos: list[zipfile.ZipInfo]) -> list[dict[str, Any]]:
    replacement = [info.filename for info in infos if "\ufffd" in info.filename]
    legacy_non_ascii = [
        info.filename
        for info in infos
        if not (info.flag_bits & 0x800) and any(ord(char) > 127 for char in info.filename)
    ]
    issues: list[dict[str, Any]] = []
    if replacement:
        issues.append({"kind": "unicode_replacement_character", "count": len(replacement), "members": replacement[:20]})
    if legacy_non_ascii:
        issues.append({"kind": "legacy_non_utf8_filename_flag", "count": len(legacy_non_ascii), "members": legacy_non_ascii[:20]})
    return issues


def sibling_split_markers(path: Path) -> list[str]:
    candidates: list[Path] = []
    for suffix in (".z01", ".z02", ".z03", ".001", ".002"):
        candidates.append(path.with_suffix(suffix))
    candidates.append(path.with_name(path.name + ".001"))
    return [str(candidate) for candidate in candidates if candidate.exists()]


def inspect_record(record: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    archive_id = record["id"]
    path = Path(record["path"])
    if not path.is_file():
        raise RuntimeError(f"archive not found: {path}")
    archive_size = path.stat().st_size
    actual_sha256 = sha256_file(path)
    expected_sha256 = str(record.get("sha256", "unknown"))
    sha_matches = expected_sha256 == "unknown" or actual_sha256 == expected_sha256
    split_markers = sibling_split_markers(path)
    member_list_path = output_dir / f"{archive_id}.members.txt"
    member_list_path.parent.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "id": archive_id,
        "archive_path": str(path),
        "sha256": actual_sha256,
        "manifest_sha256": expected_sha256,
        "sha256_matches_manifest": sha_matches,
        "archive_size": archive_size,
        "integrity_status": "unknown",
        "member_count": 0,
        "uncompressed_size": 0,
        "compressed_size_from_members": 0,
        "top_level_entries": [],
        "largest_members": [],
        "large_member_threshold_bytes": 100 * 1024 * 1024,
        "large_members": [],
        "sdk_markers": [],
        "buildroot_markers": [],
        "toolchain_markers": [],
        "sysroot_markers": [],
        "kernel_markers": [],
        "npu_markers": [],
        "encoding_issues": [],
        "split_markers": split_markers,
        "member_list_path": str(member_list_path),
        "zip_test_bad_member": None,
        "notes": [],
    }
    if not sha_matches:
        summary["integrity_status"] = "hash_mismatch"
        summary["notes"].append("archive SHA256 differs from local_sdk_inventory.yaml")

    try:
        with zipfile.ZipFile(path, "r", allowZip64=True) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            summary["member_count"] = len(infos)
            summary["uncompressed_size"] = sum(info.file_size for info in infos)
            summary["compressed_size_from_members"] = sum(info.compress_size for info in infos)
            summary["top_level_entries"] = sorted({top_level(name) for name in names})
            summary["encoding_issues"] = encoding_summary(infos)
            summary["largest_members"] = [
                {
                    "name": info.filename,
                    "uncompressed_size": info.file_size,
                    "compressed_size": info.compress_size,
                    "compression": info.compress_type,
                }
                for info in sorted(infos, key=lambda item: (item.file_size, item.filename), reverse=True)[:20]
            ]
            summary["large_members"] = [
                {
                    "name": info.filename,
                    "uncompressed_size": info.file_size,
                    "compressed_size": info.compress_size,
                }
                for info in infos
                if info.file_size >= summary["large_member_threshold_bytes"]
            ]
            if summary["large_members"]:
                summary["notes"].append(
                    f"{len(summary['large_members'])} member(s) meet the 100 MiB large-member threshold"
                )
            else:
                summary["notes"].append("no member meets the 100 MiB large-member threshold")
            for field, patterns in PATTERNS.items():
                summary[field] = marker_summary(names, patterns)

            with member_list_path.open("w", encoding="utf-8") as listing:
                listing.write(f"# archive_id: {archive_id}\n")
                listing.write(f"# archive_path: {path}\n")
                listing.write(f"# sha256: {actual_sha256}\n")
                listing.write("# central-directory metadata only; no member extracted\n")
                listing.write("name\tuncompressed_size\tcompressed_size\tcrc32\tflag_bits\tdate_time\n")
                for info in infos:
                    listing.write(
                        f"{info.filename}\t{info.file_size}\t{info.compress_size}\t"
                        f"{info.CRC:08x}\t{info.flag_bits}\t{info.date_time}\n"
                    )

            # testzip reads compressed member data to verify CRC/structure but does not extract files.
            bad_member = archive.testzip()
            summary["zip_test_bad_member"] = bad_member
            if bad_member is None and sha_matches:
                summary["integrity_status"] = "valid"
            elif bad_member is not None:
                summary["integrity_status"] = "damaged"
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        summary["integrity_status"] = "damaged"
        summary["notes"].append(f"ZIP inspection failed: {exc}")
        return summary

    if split_markers:
        summary["notes"].append("sibling split-archive markers exist")
    if summary["encoding_issues"]:
        summary["notes"].append("one or more member names may require encoding review")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect ZIP central directories without extraction")
    parser.add_argument("--archive-id", action="append", help="inspect one archive id; repeatable")
    parser.add_argument("--output-dir", type=Path, help="external directory for complete member listings")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="local SDK inventory YAML")
    parser.add_argument("--summary-json", type=Path, help="write bounded JSON summary to this path")
    args = parser.parse_args()

    manifest = load_yaml(args.manifest)
    paths_data = load_yaml(DEFAULT_PATHS)
    if not isinstance(manifest, dict) or not isinstance(paths_data, dict):
        raise RuntimeError("manifest and local paths YAML must contain mappings")
    records = archive_entries(manifest)
    selected = choose_records(records, args.archive_id)
    output_dir = args.output_dir or private_output_default(paths_data)
    output_dir.mkdir(parents=True, exist_ok=True)

    summaries = [inspect_record(record, output_dir) for record in selected]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(args.manifest),
        "output_dir": str(output_dir),
        "extraction_performed": False,
        "execution_performed": False,
        "archives": summaries,
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if all(item["integrity_status"] == "valid" for item in summaries) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
