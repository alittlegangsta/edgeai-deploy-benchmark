#!/usr/bin/env python3
"""Safely copy explicitly approved P0 documents into the private workspace.

The default operation is a dry-run.  A manifest record must explicitly set
``approved_for_copy: true`` before ``--execute`` can copy it.  This utility
never deletes or moves source files and never changes approval state.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LOCAL_PATHS_FILE = REPOSITORY_ROOT / ".knowledge" / "local_paths.yaml"
MANIFEST_FILE = REPOSITORY_ROOT / ".knowledge" / "manifests" / "p0_documents.yaml"


class CopyConfigurationError(RuntimeError):
    """Raised when configuration or a manifest record is unsafe to use."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run (default) or copy P0 records whose manifest explicitly "
            "sets approved_for_copy: true."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="perform approved copies; without this flag only print a dry-run",
    )
    return parser.parse_args()


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CopyConfigurationError(f"configuration file does not exist: {path}")
    try:
        import yaml  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise CopyConfigurationError(
            "PyYAML is required to read repository YAML files; install it in "
            "an explicitly approved environment before using this tool"
        ) from exc
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise CopyConfigurationError(f"cannot parse YAML {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CopyConfigurationError(f"YAML root must be a mapping: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise CopyConfigurationError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def resolve_under(path: Path, root: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise CopyConfigurationError(
            f"{label} is outside the configured root or does not exist: {path}"
        ) from exc
    return resolved


def approved_records(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records = manifest.get("documents")
    if not isinstance(records, list):
        raise CopyConfigurationError("manifest field 'documents' must be a list")
    result: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise CopyConfigurationError(f"manifest documents[{index}] must be a mapping")
        if record.get("approved_for_copy") is True:
            result.append(record)
    return result


def simplified_relative_path(relative_source: Path) -> Path:
    """Keep a short, recognizable source hierarchy in the private workspace."""
    parts = relative_source.parts
    aliases = {
        ("02_hardware", "hardware_MLK_F3P_CZ02_DR1_20250526"): "hardware",
        ("01_start", "02_start_Linux"): "linux",
        ("03_demo", "3-4_ex_soc_linux"): "linux_ebook",
        ("03_demo", "3-0_book_all"): "sdk",
        ("01_start", "01_start_fpga"): "fpga",
    }
    for prefix, alias in aliases.items():
        if parts[: len(prefix)] == prefix:
            return Path(alias, *parts[len(prefix) :])
    return relative_source


def copy_record(record: dict[str, Any], source_root: Path, target_root: Path, execute: bool) -> str:
    identifier = record.get("id", "<missing-id>")
    raw_source = record.get("exact_source_path")
    if not isinstance(raw_source, str) or not raw_source:
        raise CopyConfigurationError(f"record {identifier}: exact_source_path is required")
    source = resolve_under(Path(raw_source), source_root, f"record {identifier} source")
    if not source.is_file():
        raise CopyConfigurationError(f"record {identifier} source is not a file: {source}")

    expected_hash = record.get("sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise CopyConfigurationError(f"record {identifier}: sha256 must be a 64-character string")
    source_hash = sha256(source)
    if source_hash != expected_hash:
        raise CopyConfigurationError(
            f"record {identifier}: source SHA256 mismatch; manifest={expected_hash}, "
            f"actual={source_hash}"
        )

    relative_source = source.relative_to(source_root.resolve(strict=True))
    destination = target_root / simplified_relative_path(relative_source)
    # target_root is private workspace configuration, but keep the same safety
    # invariant if a malformed relative path is ever supplied by a manifest.
    try:
        destination.resolve().relative_to(target_root.resolve())
    except ValueError as exc:
        raise CopyConfigurationError(
            f"record {identifier}: destination escapes private P0 directory"
        ) from exc

    if not execute:
        return f"DRY-RUN {identifier}: {source} -> {destination} (sha256={source_hash})"

    if destination.exists():
        if not destination.is_file():
            raise CopyConfigurationError(
                f"record {identifier}: destination exists and is not a file: {destination}"
            )
        destination_hash = sha256(destination)
        if destination_hash == source_hash:
            return f"SKIP {identifier}: destination already has matching SHA256 ({destination})"
        raise CopyConfigurationError(
            f"record {identifier}: destination SHA256 differs; refusing overwrite: {destination}"
        )

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    except OSError as exc:
        raise CopyConfigurationError(f"record {identifier}: copy failed: {exc}") from exc
    destination_hash = sha256(destination)
    if destination_hash != source_hash:
        raise CopyConfigurationError(
            f"record {identifier}: post-copy SHA256 mismatch; source={source_hash}, "
            f"destination={destination_hash}"
        )
    return f"COPY {identifier}: {source} -> {destination} (sha256={source_hash})"


def main() -> int:
    args = parse_args()
    try:
        local_paths = load_yaml(LOCAL_PATHS_FILE)
        manifest = load_yaml(MANIFEST_FILE)
        raw_source_root = local_paths.get("milianke_source_root")
        raw_private_root = local_paths.get("private_workspace_root")
        if not isinstance(raw_source_root, str) or not raw_source_root:
            raise CopyConfigurationError("local_paths.yaml is missing milianke_source_root")
        if not isinstance(raw_private_root, str) or not raw_private_root:
            raise CopyConfigurationError("local_paths.yaml is missing private_workspace_root")
        source_root = Path(raw_source_root).expanduser()
        if not source_root.is_dir():
            raise CopyConfigurationError(f"milianke source root does not exist: {source_root}")
        target_root = Path(raw_private_root).expanduser() / "milianke" / "p0"
        records = approved_records(manifest)
        mode = "EXECUTE" if args.execute else "DRY-RUN"
        print(f"mode: {mode}")
        print(f"source_root: {source_root.resolve()}")
        print(f"target_root: {target_root}")
        print(f"approved_records: {len(records)}")
        if not records:
            print("No records have approved_for_copy: true; no files copied.")
            return 0
        for record in records:
            print(copy_record(record, source_root, target_root, args.execute))
    except CopyConfigurationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
