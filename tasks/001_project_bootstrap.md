# Task 001: Project Bootstrap and OpenCV/CMake Smoke Test

## Status

Completed

## Branch

```text
feature/001-project-bootstrap
```

## Goal

Initialize the repository with the minimum useful project documentation and implement a small C++17/OpenCV program that can be configured and built with CMake.

This task validates only the local C++ toolchain, CMake integration, OpenCV discovery, executable generation, filesystem access, image processing, and image writing.

This task must not introduce model inference, ONNX Runtime, ncnn, Python inference code, benchmark data, cross-compilation, or board-specific code.

## Why This Task Exists

Before integrating inference frameworks, the project needs a verified native build baseline.

A successful result proves that:

1. The compiler supports C++17.

2. CMake can discover OpenCV.

3. The repository has a minimal and understandable build structure.

4. A native executable can create and save an image.

5. Later build failures can be separated from basic compiler or OpenCV problems.

## Knowledge Covered

The task introduces:

- Basic Git repository organization

- CMake configure and build phases

- CMake targets

- `find_package`

- Imported or discovered dependencies

- C++17 standard configuration

- OpenCV matrix creation

- Basic drawing and image encoding

- `std::filesystem`

- Exit codes and error handling

- Build and run evidence collection

## Scope

Create only the files required for the first working C++ baseline.

Expected files:

```text
AGENTS.md
README.md
ROADMAP.md
TASKS.md
CHANGELOG.md
.gitattributes
.gitignore
tasks/001_project_bootstrap.md
cpp/CMakeLists.txt
cpp/apps/opencv_smoke.cpp
```

Directories such as `models/`, `configs/`, `python/`, `benchmarks/`, `deploy/`, and unused C++ module directories must not be created during this task.

Runtime directories under `results/` may be created by commands or by the smoke-test application when needed. Empty runtime directories must not be committed.

Placeholder `.gitkeep` files left over from before this task may be deleted from the project directories, together with any empty directories produced by that cleanup. New `.gitkeep` files must not be created.

## Allowed Files

Codex may create or modify only:

```text
AGENTS.md
README.md
ROADMAP.md
TASKS.md
CHANGELOG.md
.gitattributes
.gitignore
tasks/001_project_bootstrap.md
cpp/CMakeLists.txt
cpp/apps/opencv_smoke.cpp
```

Codex may also delete pre-existing placeholder `.gitkeep` files under `benchmarks/`, `configs/`, `data/`, `deploy/`, `docs/`, `models/`, `python/`, `results/`, `scripts/`, and `cpp/`, and remove the resulting empty directories. The `tasks/` and `cpp/apps/` directories must be preserved.

## Forbidden Files and Changes

Codex must not:

- Create model files

- Download model weights

- Add ONNX Runtime

- Add ncnn

- Add Python inference code

- Create `pyproject.toml`

- Add FetchContent

- Add Git submodules

- Vendor OpenCV or another dependency

- Add Docker configuration

- Add CI workflows

- Add board-specific code

- Add benchmark results

- Add fabricated logs or screenshots

- Create placeholder directory trees

- Create `.gitkeep` files

- Modify files outside the allowed list

- Run `git commit`

- Run `git push`

- Install operating-system packages

- Use `sudo`

## Implementation Requirements

### 1. CMake Project

Create `cpp/CMakeLists.txt` with the following properties:

- `cmake_minimum_required(VERSION 3.16)`

- Project language is CXX

- Require C++17

- Disable compiler-specific C++ extensions

- Default to a sensible build type when using a single-config generator

- Find OpenCV 4

- Request only these OpenCV components:

```text
core
imgproc
imgcodecs
```

- Create one executable:

```text
edgeai_opencv_smoke
```

- Source file:

```text
apps/opencv_smoke.cpp
```

- Enable warnings for GCC and Clang:

```text
-Wall
-Wextra
-Wpedantic
```

- Do not treat warnings as errors

- Do not use global include directories or global compiler flags when target-level settings are sufficient

- Do not download any dependencies from CMake

### 2. OpenCV Smoke-Test Program

Create `cpp/apps/opencv_smoke.cpp`.

The executable must:

1. Print a clear application name.

2. Print the C++ standard value from `__cplusplus`.

3. Print the OpenCV version.

4. Accept zero or one positional argument.

5. Use this default output path when no argument is supplied:

```text
results/images/opencv_smoke.png
```

6. Reject more than one positional argument with a usage message and nonzero exit code.

7. Create the output parent directory with `std::filesystem`.

8. Create a BGR image with dimensions:

```text
width: 640
height: 360
```

9. Draw at least:

```text
one filled background
one rectangle
one line of text
```

10. Save the image with `cv::imwrite`.

11. Read the image back with `cv::imread`.

12. Verify that the read-back image:

```text
is not empty
has width 640
has height 360
```

13. Print the final output path and verified image dimensions.

14. Return zero only when every operation succeeds.

15. Catch standard exceptions and print a useful error message to standard error.

16. Avoid unnecessary classes, abstractions, argument-parsing libraries, or helper modules.

### 3. README

The initial `README.md` must contain:

- Project name

- Project purpose

- Current status

- Stage-one and stage-two scope

- Explicit non-goals

- Required packages for Task 001

- Configure command

- Build command

- Run command

- Expected smoke-test behavior

- Statement that no model inference has been implemented yet

Do not claim that ONNX Runtime, ncnn, ARM deployment, or benchmark work is complete.

### 4. AGENTS.md

The initial `AGENTS.md` must instruct coding agents to:

- Work on one task at a time

- Read the active task file before editing

- Respect allowed and forbidden file lists

- Avoid fabricated runtime results

- Avoid silent dependency downloads

- Avoid broad refactors

- Use C++17

- Prefer target-based CMake

- Keep inference-independent modules separate from backend adapters

- Never commit or push unless explicitly requested

- Report commands actually run and commands not run

- Stop and report the exact error when an environmental dependency is missing

### 5. ROADMAP.md

Create a concise roadmap containing only:

```text
Stage 1: PC deployment baseline
Stage 2: Anlogic DR1 ARM CPU baseline
Future work: explicitly out of scope
```

Do not create detailed speculative designs.

### 6. TASKS.md

List Tasks 001 through 015 with one-line descriptions and statuses.

Only Task 001 may be marked as in progress. All other tasks must be marked as planned.

### 7. CHANGELOG.md

Use a simple changelog format.

Add an `Unreleased` section containing the repository bootstrap and OpenCV smoke-test entry.

Do not invent release versions.

### 8. .gitignore

Ignore at least:

```text
build/
cmake-build-*/
.cache/
.vscode/
.idea/
.venv/
__pycache__/
*.pyc
*.pyo
*.swp
*.tmp
*.log
compile_commands.json
third_party/
models/**/*.pt
models/**/*.onnx
models/**/*.bin
results/videos/*
data/samples/videos/*
```

Do not ignore all of `results/images/`, because selected small result images may later be committed as project evidence.

## Environment Preparation

The user performs system package installation manually.

Recommended commands on WSL2 Ubuntu 24.04:

```bash
sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    ninja-build \
    pkg-config \
    libopencv-dev
```

Record the environment:

```bash
uname -a
g++ --version
cmake --version
ninja --version
pkg-config --modversion opencv4
```

## Build Commands

Run from the repository root:

```bash
cmake \
  -S cpp \
  -B build/pc-release \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release

cmake --build build/pc-release --parallel
```

## Run Commands

```bash
mkdir -p results/logs

./build/pc-release/edgeai_opencv_smoke \
  results/images/opencv_smoke.png \
  2>&1 | tee results/logs/001_opencv_smoke.log
```

Run the default-path case separately:

```bash
rm -f results/images/opencv_smoke.png

./build/pc-release/edgeai_opencv_smoke
```

Verify the generated file:

```bash
test -s results/images/opencv_smoke.png
file results/images/opencv_smoke.png
```

Verify invalid argument handling:

```bash
set +e
./build/pc-release/edgeai_opencv_smoke one.png extra_argument
status=$?
set -e

test "$status" -ne 0
```

## Review Commands

```bash
git status --short
git diff --stat
git diff
git diff --check
```

## Acceptance Criteria

Task 001 is complete only when all of the following are true:

- CMake configuration succeeds.

- C++ compilation succeeds without errors.

- The target is compiled as C++17.

- OpenCV is found through CMake.

- The executable returns zero for a valid invocation.

- The executable generates a nonempty PNG file.

- The executable reads the generated PNG back successfully.

- The verified image dimensions are 640 by 360.

- The executable returns nonzero when too many arguments are provided.

- The log contains the C++ standard value.

- The log contains the OpenCV version.

- The log contains the output path.

- `git diff --check` reports no whitespace errors.

- `.gitattributes` enforces LF line endings for text, CRLF for Windows command scripts, and binary handling for the listed binary artifacts.

- No meaningless `.gitkeep` files remain.

- No model or inference framework has been added.

- No empty project directory tree has been created.

- No runtime result has been fabricated.

- README accurately states that model inference is not yet implemented.

## Evidence to Preserve

Preserve the real output of:

```text
uname -a
g++ --version
cmake --version
ninja --version
pkg-config --modversion opencv4
CMake configure
CMake build
smoke-test execution
file results/images/opencv_smoke.png
git status --short
git diff --stat
git diff --check
```

The generated smoke-test image may be retained as Task 001 evidence.

The build directory must not be committed.

## Codex Responsibilities

Codex may:

- Inspect the repository

- Create the allowed files

- Implement the CMake target

- Implement the OpenCV smoke program

- Run non-privileged configure, build, and test commands

- Report exact errors

- Summarize changed files

Codex must not:

- Install dependencies

- Hide build failures

- replace real output with expected output

- Mark the task complete without running the acceptance commands

- Commit or push changes

## User Responsibilities

The user must personally:

- Review every changed file

- Understand how `find_package(OpenCV)` works

- Understand the difference between CMake configure and build

- Confirm that C++17 is actually enabled

- Run the build and executable

- Inspect the generated image

- Review `git diff`

- Decide whether to commit

- Preserve real logs

## Known Risks

1. `libopencv-dev` may not be installed.

2. OpenCV may be installed in a nonstandard path.

3. CMake may find a different OpenCV installation than `pkg-config`.

4. The repository may already contain files outside the expected bootstrap scope.

5. WSL filesystem performance may be poor when the repository is stored under `/mnt/c`.

When OpenCV is not found, report the exact CMake error and the relevant environment output. Do not modify the project to download OpenCV automatically.
