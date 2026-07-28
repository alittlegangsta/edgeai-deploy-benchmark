# VM AArch64 toolchain setup

This record covers the authorized SDK_2025_07 Linux AArch64 toolchain
extraction, compiler/sysroot validation, and a host-side cross-compilation
smoke test. It does not claim that an Anlogic board can execute the resulting
ELF files.

## Scope and constraints

- VM access used `/home/dministrator/bin/anlogic-vm-ssh`.
- SDK root: `/home/uisrc/vendor/anlogic/sdk/sdk`.
- The outer SDK archive and nested toolchain archive were preserved.
- Only the Linux AArch64 Linaro GCC archive was extracted.
- The `aarch64-none-elf` bare-metal archive was not extracted.
- No SDK build script, Buildroot, Linux, U-Boot, FSBL, NPU demo, driver, or
  board command was run.
- No CMake, QEMU, or package was installed.
- The AArch64 ELF smoke outputs were not executed in the x86_64 VM.

## Archive identity

| Item | Observed value |
| --- | --- |
| Outer archive | `/home/uisrc/vendor/anlogic/packages/sdk.2025.7.tar.gz` |
| Outer archive size | `1,368,135,226` bytes |
| Outer archive SHA256 | `c5a6d9f1e6c5e3182bedafb0adb049bb99b6c0d4cc4ff79a3edc85746bcaa5d0` |
| Linux toolchain archive | `/home/uisrc/vendor/anlogic/sdk/sdk/toolchains/dr1m_arm-gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu.tar` |
| Detected nested format | XZ-compressed data containing a tar stream |
| Nested archive size | `117,896,452` bytes |
| Nested archive SHA256 | `3b6465fb91564b54bbdf9578b4cc3aa198dd363f7a43820eab06ea2932c8e0bf` |
| Nested top-level directory | `gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu` |
| Nested member count | `7,575` |
| Path-traversal members | `0` |

The nested archive contains the `aarch64-linux-gnu-` compiler family. Its
member inventory contained no `aarch64-none-elf-gcc`; the bare-metal toolchain
was therefore not confused with the Linux toolchain.

## Extraction

The archive was unpacked into a temporary directory under
`/home/uisrc/vendor/anlogic/toolchains`, checked for its expected top-level
directory and compiler, and then renamed to:

```text
/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0
```

The extracted tree contains 7,152 regular files, 330 directories, 93 symbolic
links, no other file types, and 784,793,189 bytes. The source archives remain
unchanged. No bare-metal extraction target exists.

## Compiler and sysroot

The validated compiler prefix is:

```text
/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/bin/aarch64-linux-gnu-
```

The compiler reports:

```text
version:       7.5.0 (Linaro GCC 7.5-2019.12)
target:        aarch64-linux-gnu
dumpversion:   7.5.0
thread model:  posix
sysroot:       .../aarch64-linux-gnu/libc
```

The canonical sysroot path used in this record is:

```text
/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0/aarch64-linux-gnu/libc
```

The compiler-reported `libc.so` is a linker script and `libstdc++.so` is a
symbolic link, so neither is incorrectly treated as an ELF object. The
compiler-reported paths and their runtime targets were checked. The sysroot
contains `usr/include/stdio.h`, `usr/include/stdlib.h`, the C++ include tree,
`crt1.o`, `crti.o`, `crtn.o`, `libgcc_s.so.1`, `libc.so.6`,
`libstdc++.so.6`, and `ld-linux-aarch64.so.1`.

The runtime objects are ELF64 AArch64. Observed SONAME/NEEDED facts include:

- `libc.so.6`: SONAME `libc.so.6`, NEEDED `ld-linux-aarch64.so.1`;
- `libstdc++.so.6`: SONAME `libstdc++.so.6`, NEEDED `libm.so.6`, `libc.so.6`,
  and `libgcc_s.so.1`;
- `ld-linux-aarch64.so.1`: SONAME `ld-linux-aarch64.so.1`.

The libc files identify glibc 2.25, while the linked C smoke binary requires
`GLIBC_2.17`. This is toolchain evidence, not proof of compatibility with the
uninspected board image.

## Hello World cross-build

The sources were created only in the remote smoke directory:

```text
/home/uisrc/vendor/anlogic/builds/toolchain_smoke/hello_c.c
/home/uisrc/vendor/anlogic/builds/toolchain_smoke/hello_cpp.cpp
```

The exact successful commands were recorded in
`/home/uisrc/vendor/anlogic/logs/toolchain_setup/hello_build_commands.txt`.
They used the absolute cross compilers with:

```text
C:   -O2 -g -Wall -Wextra -Werror
C++: -O2 -g -Wall -Wextra -Werror -std=c++14
```

Results:

| Artifact | Result | ELF evidence |
| --- | --- | --- |
| `hello_c` | BUILT | ELF64 AArch64 dynamic executable; interpreter `/lib/ld-linux-aarch64.so.1`; NEEDED `libc.so.6` |
| `hello_cpp` | BUILT | ELF64 AArch64 dynamic executable; interpreter `/lib/ld-linux-aarch64.so.1`; NEEDED `libstdc++.so.6`, `libm.so.6`, `libgcc_s.so.1`, `libc.so.6` |
| `hello_c_static` | BUILT | ELF64 AArch64 statically linked executable; no interpreter or NEEDED entries |

No target executable was run. The VM is x86_64, so execution was deliberately
omitted.

## Decision gate

| Decision | Status | Reason |
| --- | --- | --- |
| Toolchain archive identity | **CONFIRMED** | Hash, archive members, target compiler family, and no bare-metal compiler member were checked. |
| Compiler | **VERIFIED** | GCC/G++ 7.5.0 report target `aarch64-linux-gnu`. |
| Target triple | **MATCH** | Expected `aarch64-linux-gnu` matches `-dumpmachine`. |
| Sysroot | **VERIFIED** | Headers, startup objects, runtime libraries, loader, and compiler lookup paths were checked. |
| C dynamic smoke | **BUILT** | AArch64 ELF and dynamic dependencies inspected. |
| C++ dynamic smoke | **BUILT** | AArch64 ELF, libstdc++, libgcc, libc dependencies inspected. |
| C static smoke | **BUILT** | Optional static C link succeeded. |
| Transfer for board execution | **HOLD** | Board loader, libc, filesystem, transport, and runtime were not verified. |
| Install CMake | **HOLD** | This smoke build does not require it; no new necessity was established. |
| Compile NPU demo | **HOLD** | Outside this task; package closure and board runtime remain unresolved. |

The artifacts are suitable for a separately approved deployment check, but this
record does not authorize executing them on a board.

## Evidence and reproducibility

Remote evidence is preserved under:

```text
/home/uisrc/vendor/anlogic/logs/toolchain_setup/
```

Important files are `archive_identity.txt`, `archive_members.txt`,
`extraction_summary.txt`, `compiler_versions.txt`, `sysroot_inventory.txt`,
`runtime_elf.txt`, `hello_build_commands.txt`, `hello_build_output.txt`, and
`hello_elf_inspection.txt`. The project-side reference scripts are:

- `scripts/vendor/anlogic_vm_toolchain_env.sh` — reference variables only;
- `scripts/vendor/validate_vm_aarch64_toolchain.sh` — remote read-only compiler,
  sysroot, and runtime ELF validation.

The environment script does not connect to the VM or edit shell startup files.
The validation script does not extract archives, install software, execute
target ELFs, invoke vendor scripts, or access a board.
