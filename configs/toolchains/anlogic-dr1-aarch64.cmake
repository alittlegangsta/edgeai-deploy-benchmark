# Cross-compilation contract for the MLK-F3P-CZ02-DR1M90 Buildroot target.
#
# This file is consumed inside the Anlogic Ubuntu VM. The absolute paths are
# frozen VM-side toolchain inputs, not paths intended for a generic host.

set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

set(ANLOGIC_AARCH64_TOOLCHAIN_ROOT
    "/home/uisrc/vendor/anlogic/toolchains/linaro-aarch64-linux-gnu-7.5.0"
    CACHE PATH "Validated Linaro AArch64 Linux toolchain root")
set(ANLOGIC_AARCH64_SYSROOT
    "${ANLOGIC_AARCH64_TOOLCHAIN_ROOT}/aarch64-linux-gnu/libc"
    CACHE PATH "Validated glibc 2.25 target sysroot")

set(CMAKE_C_COMPILER
    "${ANLOGIC_AARCH64_TOOLCHAIN_ROOT}/bin/aarch64-linux-gnu-gcc"
    CACHE FILEPATH "AArch64 C compiler")
set(CMAKE_CXX_COMPILER
    "${ANLOGIC_AARCH64_TOOLCHAIN_ROOT}/bin/aarch64-linux-gnu-g++"
    CACHE FILEPATH "AArch64 C++ compiler")
set(CMAKE_AR
    "${ANLOGIC_AARCH64_TOOLCHAIN_ROOT}/bin/aarch64-linux-gnu-ar"
    CACHE FILEPATH "AArch64 archiver")
set(CMAKE_RANLIB
    "${ANLOGIC_AARCH64_TOOLCHAIN_ROOT}/bin/aarch64-linux-gnu-ranlib"
    CACHE FILEPATH "AArch64 archive indexer")
set(CMAKE_STRIP
    "${ANLOGIC_AARCH64_TOOLCHAIN_ROOT}/bin/aarch64-linux-gnu-strip"
    CACHE FILEPATH "AArch64 strip tool")

set(CMAKE_SYSROOT "${ANLOGIC_AARCH64_SYSROOT}")
set(CMAKE_FIND_ROOT_PATH "${ANLOGIC_AARCH64_SYSROOT}")

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
