# Existing SDK tree audit

Audit date: 2026-07-24 (Asia/Shanghai)

## Scope and safety boundary

This was a read-only provenance and completeness audit of:

- Archive: `/home/uisrc/vendor/anlogic/packages/sdk.2025.7.tar.gz`
- Expanded tree: `/home/uisrc/vendor/anlogic/sdk/sdk`
- Remote access: `/home/dministrator/bin/anlogic-vm-ssh`

The archive was listed with `tar tzf` and compared with `tar -df`. It was not
extracted again. The existing tree was not deleted, moved, renamed, changed,
compiled, or executed. No vendor script, Demo, package installation, Git write
operation, commit, or remote operation was performed.

## Can the staging script create this tree?

`CURRENT_SCRIPT_CAN_EXTRACT: NO`.

The current `scripts/vendor/stage_vm_vendor_inputs.sh`:

- creates `/home/uisrc/vendor/anlogic/sdk` as an empty parent directory;
- never invokes `tar x`, `tar -x`, `unzip`, `7z x`, or another extractor;
- never copies the SDK archive into the SDK directory;
- uses `cp -a` only for the NPU Demo destination;
- records SDK extraction as `NOT_PERFORMED`.

The script has no visible history in the repository because it is an untracked
file in the current worktree. A bounded Git history search found no earlier
matching implementation. This means the existing `sdk/sdk` tree cannot be
attributed to the current staging script execution.

## Filesystem timestamps and counts

The tree root reports:

| Field | Value |
| --- | --- |
| Birth | unavailable (`-`) |
| Change | 2026-07-24 15:16:15.788723134 +0800 |
| Modify | 2025-09-08 10:31:53 +0800 |
| Access | 2026-07-24 15:16:26.541535756 +0800 |
| Owner/group | `uisrc` / `uisrc` |
| Mode | `0755` |

Birth is unavailable, and neither mtime nor ctime proves the directory's
creation time. The mtime is evidence that the content predates this audit, but
not a complete creation-history record.

The expanded tree contains:

- 125,421 regular files;
- 12,577 directories;
- 213 symlinks;
- 0 other file types;
- approximately 3.0G disk usage.

The bounded shell-history search found no matching command. This is not proof
that no prior extraction occurred: shell history can be incomplete and an open
terminal command may not yet have been recorded.

## Archive structure and path comparison

The archive SHA256 remains:

```text
c5a6d9f1e6c5e3182bedafb0adb049bb99b6c0d4cc4ff79a3edc85746bcaa5d0
```

`tar tzf` succeeded with 138,211 members:

- directory entries: 12,577;
- non-directory entries: 125,634;
- top-level entry: `sdk/`;
- second-level entries include `app/`, `buildroot/`, `device/`, `fsbl/`,
  `linux/`, `opensbi/`, `toolchains/`, `tools/`, `u-boot/`, `xenomai/`,
  `README.md`, `build.sh`, and `envsetup.sh`.

Normalized archive and tree path sets both contain 138,211 entries. The
`only_in_archive.txt` and `only_in_tree.txt` logs each contain zero entries.
Therefore the natural extraction layout is confirmed:

```text
/home/uisrc/vendor/anlogic/sdk/sdk
```

The extra `sdk/` component comes from the archive's top-level `sdk/` directory
combined with the extraction parent `/home/uisrc/vendor/anlogic/sdk`.

Complete lists and the first 100 paths are preserved outside the repository in
the VM audit log directory:

`/home/uisrc/vendor/anlogic/logs/sdk_existing_tree_audit/`

## `tar -df` result

The exact comparison was:

```text
tar -df /home/uisrc/vendor/anlogic/packages/sdk.2025.7.tar.gz \
  -C /home/uisrc/vendor/anlogic/sdk
```

Exit code was `1`, with 137,998 difference lines. Every reported difference was
`Mode differs`. There were:

- 0 content/data differences;
- 0 size differences;
- 0 type differences;
- 0 missing or extra entries;
- 137,998 mode metadata differences.

The mode-only count equals the regular-file plus directory count; symlink paths
did not produce mode differences. This supports content equivalence while
requiring caution about executable and directory permissions. It is not a
byte-for-byte metadata match.

## Version and dependency evidence

The strongest version evidence is explicit:

- `buildroot/rel_ver:1` contains `SDK_2025_07`.
- The top-level `README.md` documents Ubuntu 18.04/20.04/22.04/23.04 and the
  expected `toolchains/aarch64-linux/bin/aarch64-linux-gnu-gcc` path.
- `app/npu/build.sh:20-31` references the AArch64 compiler and
  `ffmpeg_opencv4.7.0_aarch64`.
- `app/npu/readme.md:60` names the DR1M90 Buildroot defconfig.
- `toolchains/README.md` describes a separate toolchain setup script; the
  compiler binaries themselves are not extracted at the documented paths.

The tree contains toolchain archives, including the filename
`dr1m_arm-gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu.tar`, but this is
filename-only evidence. No compiler was executed. The documented compiler
paths are absent from the tree.

The tree does contain metadata paths for `app/npu/libs/armnn_lib` and
`app/npu/libs/ffmpeg_opencv4.7.0_aarch64`, including headers, CMake files and
libraries. Their ABI, runtime loading, and compatibility with another SDK tag
were not tested. No exact `libnpu_runtime` path was identified by the bounded
name scan.

`buildroot/.defconfig` contains an i686-oriented generic configuration. It was
not treated as the DR1M90 target configuration; this is an unresolved source
of possible confusion, not proof of the target runtime architecture.

## Final assessment

| Question | Result |
| --- | --- |
| Staging script can create the expanded tree | No |
| Archive top-level | `sdk/` |
| Archive/tree path set | Exact match |
| Content/data comparison | No differences reported |
| Metadata comparison | Mode-only differences |
| Local content modification detected | No |
| Existing-tree credibility | `MATCH_WITH_METADATA_DIFFERENCES` |
| Local SDK version | `SDK_2025_07` (explicit) |
| Compatibility with official `SDK_2026.01` | `mismatch` |
| Follow-up decision | `HOLD` |

The tree is credible as a content-equivalent expansion of the supplied
`SDK_2025_07` archive, with mode metadata differences. It must be held for the
current `dr1m90_npu` `SDK_2026.01` workflow because the explicit release marker
does not match the official repository requirement. No cleanup or re-extraction
is authorized by this audit.

## Evidence files

The full read-only evidence is in:

`/home/uisrc/vendor/anlogic/logs/sdk_existing_tree_audit/`

It includes filesystem stat, tree summary, bounded history matches, complete
archive members, normalized path sets, path differences, tar comparison,
version evidence, and the final summary. The project manifest is
`.knowledge/manifests/existing_sdk_tree_audit.yaml`.
