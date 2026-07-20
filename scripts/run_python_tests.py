#!/usr/bin/env python3
"""Run Python unittest discovery and save an authentic machine summary."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import platform
import sys
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class RecordingResult(unittest.TextTestResult):
    """Text result that preserves the IDs of tests actually started."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.test_ids: list[str] = []

    def startTest(self, test: unittest.case.TestCase) -> None:
        self.test_ids.append(test.id())
        super().startTest(test)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run unittest discovery with JSON output.")
    parser.add_argument("--start-directory", required=True)
    parser.add_argument("--pattern", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suite = unittest.defaultTestLoader.discover(
        start_dir=args.start_directory,
        pattern=args.pattern,
    )
    start_ns = time.perf_counter_ns()
    runner = unittest.TextTestRunner(verbosity=2, resultclass=RecordingResult)
    result = runner.run(suite)
    end_ns = time.perf_counter_ns()
    summary = {
        "schema_version": 1,
        "application": "edgeai_python_test_runner",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "discovery": {
            "start_directory": args.start_directory,
            "pattern": args.pattern,
        },
        "result": {
            "success": result.wasSuccessful(),
            "tests_run": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "expected_failures": len(result.expectedFailures),
            "unexpected_successes": len(result.unexpectedSuccesses),
            "duration_ms": round((end_ns - start_ns) / 1_000_000.0, 6),
            "test_ids": result.test_ids,
            "failure_test_ids": [test.id() for test, _ in result.failures],
            "error_test_ids": [test.id() for test, _ in result.errors],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Test summary: {args.output}")
    print(f"Test success: {result.wasSuccessful()}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
