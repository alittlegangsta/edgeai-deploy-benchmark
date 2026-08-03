"""Offline checks for Task 021 camera evidence and bounded-latency semantics."""

from __future__ import annotations

import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "results" / "evidence" / "021"


class Task021CameraEvidenceTests(unittest.TestCase):
    def load(self, name: str):
        return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))

    def test_contract_freezes_recommended_profile(self):
        contract = self.load("camera_contract.json")
        identity = contract["build_identity"]
        self.assertEqual(contract["status"], "Completed")
        self.assertEqual(contract["automated_validation"], "PASS")
        self.assertEqual(contract["human_camera_review"], "PASS")
        self.assertEqual(contract["human_review_source"], "user")
        self.assertTrue(contract["candidate_approved"])
        self.assertEqual(identity["runtime_profile"], "recommended-dual-thread")
        self.assertTrue(identity["NCNN_OPENMP"])
        self.assertTrue(identity["NCNN_THREADS"])
        self.assertFalse(identity["NCNN_SIMPLEOMP"])
        self.assertEqual(identity["effective_parallel_backend"], "openmp")
        self.assertEqual(identity["configured_threads"], 2)

    def test_latest_frame_accounting(self):
        run = self.load("camera_run.json")
        counts = run["counts"]
        self.assertEqual(counts["latest_frame_capacity"], 1)
        self.assertEqual(
            counts["published_frames"],
            counts["processed_frames"]
            + counts["overwritten_frames"]
            + counts["pending_frame_at_stop"],
        )
        self.assertEqual(counts["overwritten_frames"], counts["dropped_frames"])
        self.assertEqual(
            counts["captured_frames"],
            counts["published_frames"] + counts["unpublished_at_shutdown"],
        )
        self.assertGreaterEqual(counts["processed_frames"], 10)

    def test_replay_and_validation_pass_without_camera_access(self):
        replay = self.load("camera_replay_validation.json")
        validation = self.load("camera_validation.json")
        self.assertEqual(replay["status"], "PASS_TARGET")
        self.assertEqual(replay["verified_frames"], 10)
        self.assertEqual(replay["failed_frames"], 0)
        self.assertEqual(validation["status"], "PASS")
        self.assertTrue(all(validation["checks"].values()))

    def test_representative_pngs_exist(self):
        image_dir = ROOT / "results" / "images" / "021"
        for stem in (
            "first_raw",
            "first_annotated",
            "middle_raw",
            "middle_annotated",
            "last_raw",
            "last_annotated",
        ):
            path = image_dir / f"{stem}.png"
            self.assertTrue(path.is_file(), path)
            self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
