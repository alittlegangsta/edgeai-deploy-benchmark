# Repository Instructions for Coding Agents

- Work on one task at a time and read the active task file completely before editing.
- Follow the task's allowed-file list and forbidden-change list exactly.
- Keep changes narrow; do not perform broad refactors outside the active task.
- Never fabricate build output, runtime results, logs, benchmark data, or screenshots.
- Do not download dependencies silently or add dependency-fetching mechanisms.
- Use C++17 for C++ code and prefer target-based CMake configuration.
- Keep inference-independent modules separate from inference-backend adapters.
- Do not commit or push unless the user explicitly requests it.
- Report commands actually run separately from commands not run.
- If an environmental dependency is missing, stop the affected operation and report
  the exact error without installing, downloading, or substituting the dependency.
