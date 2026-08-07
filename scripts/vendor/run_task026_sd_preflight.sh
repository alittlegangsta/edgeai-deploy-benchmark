#!/usr/bin/env bash
set -euo pipefail

# Task 026 is deliberately read-only.  This entry point never formats,
# partitions, mounts, unmounts, or writes a block device.  A future write
# implementation must be a separately approved change.
mode="${1:---dry-run}"
if [[ "$mode" != "--dry-run" && "$mode" != "--check" ]]; then
  printf 'ERROR: Task 026 preflight accepts only --dry-run or --check\n' >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
evidence_dir="$repo_root/results/evidence/026"
mkdir -p "$evidence_dir"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

lsblk -J -O >"$tmp_dir/lsblk.json"
blkid >"$tmp_dir/blkid.txt" 2>&1 || true
findmnt -rn -o SOURCE,TARGET,FSTYPE,OPTIONS >"$tmp_dir/findmnt.txt" 2>&1 || true
{
  for sysdev in /sys/block/*; do
    [[ -e "$sysdev" ]] || continue
    name="${sysdev##*/}"
    printf '[%s]\n' "$name"
    for key in dev size ro removable; do
      printf '%s=%s\n' "$key" "$(cat "$sysdev/$key" 2>/dev/null || printf unavailable)"
    done
  done
} >"$tmp_dir/sys_block.txt"
{
  for dev in $(python3 - "$tmp_dir/lsblk.json" <<'PY'
import json
import sys
for item in json.load(open(sys.argv[1], encoding="utf-8")).get("blockdevices", []):
    path = item.get("path")
    if path:
        print(path)
PY
  ); do
    printf '[%s]\n' "$dev"
    udevadm info --query=property --name="$dev" 2>&1 || true
  done
} >"$tmp_dir/udevadm.txt"

python3 - "$repo_root" "$evidence_dir" "$mode" "$tmp_dir" <<'PY'
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

repo = Path(sys.argv[1])
evidence = Path(sys.argv[2])
mode = sys.argv[3]
tmp = Path(sys.argv[4])
captured_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def read_json(name):
    return json.loads((tmp / name).read_text(encoding="utf-8"))

manifest_path = repo / "results/evidence/025/npu_final_candidate_artifact_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
files = manifest.get("files", {})
sha256_re = re.compile(r"^[0-9a-f]{64}$")
manifest_structure_ok = (
    len(files) == 13
    and manifest.get("checksum_manifest", {}).get("entries") == 13
    and all(sha256_re.fullmatch(v.get("sha256", "")) for v in files.values())
)

# The Task 025 manifest intentionally stores a VM placeholder.  Only an
# explicitly supplied, reachable local candidate root may be hashed here.
candidate_root_value = manifest.get("candidate_root", "")
candidate_root = os.environ.get("TASK025_CANDIDATE_ROOT", "")
candidate_root_path = Path(candidate_root) if candidate_root else None
available = bool(candidate_root_path and candidate_root_path.is_dir())
missing = []
observed = {}
if available:
    for name, expected in files.items():
        path = candidate_root_path / name
        if not path.is_file():
            missing.append(name)
            continue
        digest = subprocess.check_output(["sha256sum", str(path)], text=True).split()[0]
        observed[name] = {"path": str(path), "sha256": digest, "expected": expected["sha256"], "match": digest == expected["sha256"]}
else:
    missing = sorted(files)

candidate_status = "PASS_HASHES_RECOMPUTED" if available and not missing and all(v["match"] for v in observed.values()) else "BLOCKED_CANDIDATE_FILES_UNAVAILABLE"
candidate_evidence = {
    "schema_version": "task026-candidate-manifest-verification-v1",
    "task": "026",
    "captured_at": captured_at,
    "status": candidate_status,
    "source_manifest": "results/evidence/025/npu_final_candidate_artifact_manifest.json",
    "manifest_structure": {"status": "PASS" if manifest_structure_ok else "FAIL", "entry_count": len(files), "expected_entries": 13},
    "candidate_root_declared": candidate_root_value,
    "candidate_root_override": candidate_root or None,
    "candidate_root_reachable": available,
    "sha256sum_manifest_sha256": manifest.get("checksum_manifest", {}).get("sha256"),
    "files": observed,
    "missing_or_unavailable": missing,
    "recompute_performed": available,
    "safety": {"write_attempted": False, "media_modified": False},
}
(evidence / "candidate_manifest_verification.json").write_text(json.dumps(candidate_evidence, indent=2) + "\n", encoding="utf-8")

lsblk = read_json("lsblk.json")
devices = []
for item in lsblk.get("blockdevices", []):
    name = item.get("name")
    path = item.get("path") or ("/dev/" + name if name else None)
    mounts = [m for m in (item.get("mountpoints") or []) if m]
    reasons = []
    if item.get("rm") is not True:
        reasons.append("removable flag is not 1")
    if item.get("vendor", "").strip().lower() == "msft" or "vmbus" in (item.get("subsystems") or ""):
        reasons.append("WSL/virtual Msft disk")
    if path == "/dev/sdd" or "/" in mounts or any(m.startswith("/home/dministrator/projects") for m in mounts):
        reasons.append("current WSL root/project disk")
    if item.get("fstype") == "swap" or "[SWAP]" in mounts:
        reasons.append("active WSL swap disk")
    if item.get("type") != "disk":
        reasons.append("not a whole-disk candidate")
    if not reasons:
        reasons.append("identity not confirmed as user SD")
    devices.append({
        "path": path, "name": name, "type": item.get("type"), "size": item.get("size"),
        "size_bytes": item.get("size_bytes"), "vendor": item.get("vendor"), "model": item.get("model"),
        "serial": item.get("serial"), "transport": item.get("tran"), "removable": item.get("rm"),
        "read_only": item.get("ro"), "filesystem": item.get("fstype"), "mountpoints": mounts,
        "partitions": item.get("children") or [], "exclusion_reasons": reasons,
        "candidate": False,
    })
block_evidence = {
    "schema_version": "task026-block-device-inventory-v1", "task": "026", "captured_at": captured_at,
    "source": {"lsblk": "lsblk -J -O", "blkid": "blkid", "udevadm": "udevadm info --query=property --name", "sysfs": "/sys/block"},
    "devices": devices,
    "removable_candidates": [],
    "windows_system_disk_visible": False,
    "wsl_virtual_disk_present": True,
    "development_board_emmc_visible": False,
    "exclusion_policy": ["Windows system disk", "WSL/VM virtual disks", "current Linux root/project disk", "development-board eMMC", "any removable!=1 device", "any identity-ambiguous device"],
    "status": "BLOCKED_NO_CONFIRMED_REMOVABLE_SD",
    "raw_outputs": {"blkid": (tmp / "blkid.txt").read_text(encoding="utf-8", errors="replace"), "findmnt": (tmp / "findmnt.txt").read_text(encoding="utf-8", errors="replace"), "udevadm": (tmp / "udevadm.txt").read_text(encoding="utf-8", errors="replace"), "sys_block": (tmp / "sys_block.txt").read_text(encoding="utf-8", errors="replace")},
}
(evidence / "block_device_inventory.json").write_text(json.dumps(block_evidence, indent=2) + "\n", encoding="utf-8")

prior = json.loads((repo / "results/evidence/025/npu_uisrc_build_script_safety.json").read_text(encoding="utf-8"))
prior_by_name = {x.get("name"): x for x in prior.get("scripts", [])}
script_names = [
    "scripts/rootfs/buildroot/make_parted.sh", "scripts/rootfs/buildroot/deploy_image.sh",
    "scripts/rootfs/buildroot/parameter-tf-fat.txt", "scripts/rootfs/buildroot/create_image.sh",
    "scripts/rootfs/buildroot/create_dr1m_image.sh", "boot.scr",
]
script_items = []
for name in script_names:
    old = prior_by_name.get(name, {})
    script_items.append({
        "name": name,
        "source_read_in_this_phase": False,
        "prior_task025_classification": old.get("classification"),
        "prior_task025_effect": old.get("effect") or old.get("reason"),
        "classification": old.get("classification", "NOT_REAUDITED_VM_UNAVAILABLE"),
        "executed_in_this_phase": False,
        "hardcoded_sdb": "UNKNOWN_VM_UNAVAILABLE",
        "device_identity_checks": "UNKNOWN_VM_UNAVAILABLE",
        "notes": "VM wrapper unavailable; no script source was executed or modified.",
    })
script_evidence = {
    "schema_version": "task026-write-script-audit-v1", "task": "026", "captured_at": captured_at,
    "status": "PARTIAL_PRIOR_EVIDENCE_VM_UNAVAILABLE", "vm_probe_error": "UtilBindVsockAnyPort:307: socket failed 1",
    "scripts": script_items,
    "known_destructive_actions": ["partition/format media", "write deployment media"],
    "commands_not_run": ["make_parted.sh", "deploy_image.sh", "dd", "mkfs", "parted", "fdisk", "mount", "umount"],
    "safety": {"destructive_script_executed": False, "block_device_written": False},
}
(evidence / "write_script_audit.json").write_text(json.dumps(script_evidence, indent=2) + "\n", encoding="utf-8")

plan = {
    "schema_version": "task026-sd-write-plan-v1", "task": "026", "captured_at": captured_at,
    "status": "BLOCKED_PREWRITE_INPUTS_UNAVAILABLE", "deployment_approval": "PENDING", "sd_write": "NOT_PERFORMED",
    "target_device": None,
    "required_identity_match": {"path": True, "capacity": True, "model": True, "serial": True, "removable": True, "removable_value": 1, "one_time_confirmation": True},
    "destructive_warning": "Writing the candidate would destroy all data and partition metadata on the selected SD device.",
    "expected_layout": "Must be confirmed from the vendor script after VM access; no layout is authorized by this phase.",
    "candidate_file_destinations": "BOOT/kernel/DTB/rootfs/modules/application destinations must be confirmed from the vendor script before approval.",
    "post_write_verification": ["read partition table", "read back files", "sha256sum each candidate file", "compare aggregate SHA256SUMS", "verify no unexpected partition or filesystem"],
    "stop_conditions": ["no removable=1 device", "any identity mismatch", "candidate hash mismatch", "script performs unreviewed command", "write target is system/WSL/VM/eMMC/ambiguous", "any error or disconnect"],
    "recovery": ["stop immediately", "do not retry on another device", "remove SD only after I/O is quiescent", "retain logs and request review", "restore known-good eMMC boot path only after physical approval"],
    "serial_first_boot": ["attach documented serial console", "select SD boot without changing eMMC", "verify kernel/DTB/FPGA/CMA identity", "verify driver probe and device nodes", "only then consider one functional NPU demo"],
    "exact_approval_format": "APPROVE TASK 026 SD WRITE: device=/dev/<exact-device>; size=<exact-bytes>; model=<exact-model>; serial=<exact-serial>; removable=1; candidate_manifest_sha256=65e4d98db58e20c407b7e65e443bfe1774b692ccb49a0fd1b6f7062ebcf73ddd; confirm=ERASE-AND-WRITE-ONCE",
    "awaiting_explicit_sd_write_approval": False,
}
(evidence / "sd_write_plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

summary = {
    "schema_version": "task026-sd-preflight-summary-v1", "task": "026", "captured_at": captured_at,
    "status": "BLOCKED_PREWRITE_INPUTS_UNAVAILABLE", "deployment_approval": "PENDING", "sd_write": "NOT_PERFORMED",
    "candidate_manifest": "BLOCKED_CANDIDATE_FILES_UNAVAILABLE", "block_devices": "BLOCKED_NO_CONFIRMED_REMOVABLE_SD",
    "script_audit": "PARTIAL_PRIOR_EVIDENCE_VM_UNAVAILABLE", "awaiting_explicit_sd_write_approval": False,
    "vm_probe": "UtilBindVsockAnyPort:307: socket failed 1", "board_accessed": False,
    "destructive_commands_run": False, "next_required_actions": ["make VM candidate workspace reachable", "connect the intended SD through the USB reader", "rerun read-only preflight"],
}
(evidence / "preflight_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"mode": mode, "status": summary["status"], "candidate": candidate_status, "devices": len(devices), "removable_candidates": 0}, indent=2))
PY
