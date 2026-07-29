#!/usr/bin/env python3
"""Validate the two frozen Anlogic DR1 ARM runtime profiles.

The default operation is offline and never accesses the VM or board.  Optional
package validation verifies the build identity sidecar and the privately
deployed libgomp payload before a recommended-profile run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any, Callable, Dict, List


REPOSITORY = pathlib.Path(__file__).resolve().parents[2]
PROFILE_DIRECTORY = REPOSITORY / "configs" / "runtime_profiles"
PROFILE_PATHS = {
    "baseline-single-thread":
        PROFILE_DIRECTORY / "anlogic-dr1-baseline-single-thread.json",
    "recommended-dual-thread":
        PROFILE_DIRECTORY / "anlogic-dr1-recommended-dual-thread.json",
}

NCNN_COMMIT = "56775de50990ab7f16627efdcf5529b49541206f"
PARAM_SHA256 = "72fe027e14584159bd44bb79c1603e99239c0e423f869b465dd7d337dbea1ad4"
BIN_SHA256 = "658cc66df974d6c98bd4d82515b114146ba74a9bd18cdeaf68f8c3bcddde28f0"
INPUT_SHA256 = "625a64f72f19c7c674383f060c85c4c5a55068e0916ccb12e285e438d3036071"
BASELINE_NCNN_SHA256 = (
    "5c905cd8f6824bc890a076a47fb540aecf9e676d27420ff3e5d6aed6737a0b8a"
)
DUAL_NCNN_SHA256 = (
    "bd76f70f160ac34e44592d040ea68d8f2d40aea33ea7f3ce3009f13545db20f3"
)
LIBGOMP_SHA256 = (
    "87333e5498f3df629be8737e7b3c64e58668d91ce0edd8d78a7ce86065955b91"
)


class ProfileError(RuntimeError):
    """A frozen runtime profile or package violates its contract."""


def load_json(path: pathlib.Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProfileError(f"cannot load JSON {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ProfileError(f"JSON root must be an object: {path}")
    return payload


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_equal(actual: Any, expected: Any, field: str) -> None:
    if actual != expected:
        raise ProfileError(
            f"{field} mismatch: expected {expected!r}, observed {actual!r}"
        )


def validate_profile(profile: Dict[str, Any], expected_name: str) -> None:
    require_equal(profile.get("schema_version"), 1, "schema_version")
    require_equal(profile.get("profile_name"), expected_name, "profile_name")
    target = profile.get("target")
    runtime = profile.get("runtime")
    build = profile.get("build_identity")
    assets = profile.get("frozen_assets")
    evidence = profile.get("evidence")
    for field, value in (
        ("target", target),
        ("runtime", runtime),
        ("build_identity", build),
        ("frozen_assets", assets),
        ("evidence", evidence),
    ):
        if not isinstance(value, dict):
            raise ProfileError(f"{field} must be an object")

    require_equal(target.get("board"), "MLK-F3P-CZ02-DR1M90", "target.board")
    require_equal(target.get("architecture"), "AArch64", "target.architecture")
    require_equal(runtime.get("name"), "ncnn", "runtime.name")
    require_equal(runtime.get("tag"), "20240410", "runtime.tag")
    require_equal(runtime.get("commit"), NCNN_COMMIT, "runtime.commit")
    require_equal(runtime.get("cpu_only"), True, "runtime.cpu_only")
    require_equal(runtime.get("precision"), "FP32", "runtime.precision")
    require_equal(runtime.get("batch"), 1, "runtime.batch")
    require_equal(runtime.get("input_size"), [640, 640], "runtime.input_size")
    for flag in ("vulkan", "fp16", "bf16", "int8"):
        require_equal(runtime.get(flag), False, f"runtime.{flag}")
    require_equal(assets.get("param_sha256"), PARAM_SHA256, "assets.param")
    require_equal(assets.get("bin_sha256"), BIN_SHA256, "assets.bin")
    require_equal(assets.get("input_sha256"), INPUT_SHA256, "assets.input")

    require_equal(build.get("NCNN_THREADS"), True, "build.NCNN_THREADS")
    require_equal(build.get("NCNN_SIMPLEOMP"), False, "build.NCNN_SIMPLEOMP")
    if expected_name == "baseline-single-thread":
        require_equal(profile.get("recommended"), False, "recommended")
        require_equal(runtime.get("configured_threads"), 1, "runtime.threads")
        require_equal(build.get("NCNN_OPENMP"), False, "build.NCNN_OPENMP")
        require_equal(
            build.get("effective_parallel_backend"), "none", "build.backend"
        )
        require_equal(
            build.get("libncnn_a_sha256"), BASELINE_NCNN_SHA256, "build.libncnn"
        )
        require_equal(
            build.get("requires_private_libgomp"), False, "build.requires_libgomp"
        )
        require_equal(
            build.get("private_libgomp_so_1_sha256"), None, "build.libgomp"
        )
        require_equal(evidence.get("source_task"), "017", "evidence.source_task")
    elif expected_name == "recommended-dual-thread":
        require_equal(profile.get("recommended"), True, "recommended")
        require_equal(runtime.get("configured_threads"), 2, "runtime.threads")
        require_equal(build.get("NCNN_OPENMP"), True, "build.NCNN_OPENMP")
        require_equal(
            build.get("effective_parallel_backend"), "openmp", "build.backend"
        )
        require_equal(
            build.get("libncnn_a_sha256"), DUAL_NCNN_SHA256, "build.libncnn"
        )
        require_equal(
            build.get("requires_private_libgomp"), True, "build.requires_libgomp"
        )
        require_equal(
            build.get("private_libgomp_so_1_sha256"),
            LIBGOMP_SHA256,
            "build.libgomp",
        )
        require_equal(evidence.get("source_task"), "018", "evidence.source_task")
        require_equal(evidence.get("classification"), "BENEFICIAL", "classification")
        require_equal(evidence.get("correctness"), "PASS_TARGET", "correctness")
    else:
        raise ProfileError(f"unsupported profile: {expected_name}")


def validate_package(
    profile: Dict[str, Any],
    package_directory: pathlib.Path,
    hash_function: Callable[[pathlib.Path], str] = sha256_file,
) -> Dict[str, Any]:
    if not package_directory.is_dir():
        raise ProfileError(f"package directory is missing: {package_directory}")
    identity_path = package_directory / "runtime_build_identity.json"
    executable = package_directory / "edgeai_ncnn_image"
    if not executable.is_file():
        raise ProfileError(f"profile executable is missing: {executable}")
    identity = load_json(identity_path)
    build = profile["build_identity"]
    require_equal(
        identity.get("runtime_profile"), profile["profile_name"], "identity.profile"
    )
    require_equal(
        identity.get("libncnn_a_sha256"),
        build["libncnn_a_sha256"],
        "identity.libncnn",
    )
    require_equal(
        identity.get("NCNN_OPENMP"), build["NCNN_OPENMP"], "identity.NCNN_OPENMP"
    )
    require_equal(
        identity.get("NCNN_THREADS"), build["NCNN_THREADS"], "identity.NCNN_THREADS"
    )
    require_equal(
        identity.get("NCNN_SIMPLEOMP"),
        build["NCNN_SIMPLEOMP"],
        "identity.NCNN_SIMPLEOMP",
    )
    require_equal(
        identity.get("effective_parallel_backend"),
        build["effective_parallel_backend"],
        "identity.backend",
    )
    executable_sha256 = hash_function(executable)
    require_equal(
        identity.get("executable_sha256"), executable_sha256, "identity.executable"
    )

    result = {
        "runtime_profile": profile["profile_name"],
        "executable_sha256": executable_sha256,
        "private_libgomp": "not-required",
    }
    if build["requires_private_libgomp"]:
        libgomp = package_directory / "lib" / "libgomp.so.1"
        if not libgomp.is_file():
            raise ProfileError(f"private libgomp is missing: {libgomp}")
        observed = hash_function(libgomp)
        require_equal(observed, build["private_libgomp_so_1_sha256"], "libgomp.sha256")
        require_equal(
            identity.get("private_libgomp_so_1_sha256"), observed, "identity.libgomp"
        )
        result["private_libgomp"] = "PASS"
        result["private_libgomp_sha256"] = observed
    return result


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-all", action="store_true")
    group.add_argument("--profile", choices=sorted(PROFILE_PATHS))
    parser.add_argument("--package-dir", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    names: List[str] = (
        list(PROFILE_PATHS) if arguments.check_all else [arguments.profile]
    )
    results: List[Dict[str, Any]] = []
    try:
        for name in names:
            profile = load_json(PROFILE_PATHS[name])
            validate_profile(profile, name)
            entry: Dict[str, Any] = {
                "runtime_profile": name,
                "profile_path": str(PROFILE_PATHS[name].relative_to(REPOSITORY)),
                "profile_sha256": sha256_file(PROFILE_PATHS[name]),
                "status": "PASS",
            }
            if arguments.package_dir is not None:
                if len(names) != 1:
                    raise ProfileError("--package-dir requires exactly one --profile")
                entry["package"] = validate_package(profile, arguments.package_dir)
            results.append(entry)
    except ProfileError as error:
        print(f"runtime profile validation: FAIL: {error}", file=sys.stderr)
        return 1

    payload = {
        "schema_version": 1,
        "task": "019",
        "validation": "PASS",
        "profiles": results,
    }
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
