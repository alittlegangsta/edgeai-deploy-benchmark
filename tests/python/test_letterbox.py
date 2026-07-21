from __future__ import annotations

import unittest

import numpy as np

from edgeai_benchmark.preprocess import letterbox


class LetterboxGeometryTest(unittest.TestCase):
    def check_case(
        self,
        source_shape: tuple[int, int, int],
        expected_scale: float,
        expected_resized: dict[str, int],
        expected_padding: dict[str, int],
    ) -> None:
        image = np.zeros(source_shape, dtype=np.uint8)
        output, metadata = letterbox(image)
        self.assertEqual(output.shape, (640, 640, 3))
        self.assertAlmostEqual(metadata["scale"], expected_scale, places=12)
        self.assertEqual(metadata["resized_size"], expected_resized)
        self.assertEqual(metadata["padding"], expected_padding)

    def test_landscape_image(self) -> None:
        self.check_case(
            (300, 600, 3),
            640.0 / 600.0,
            {"width": 640, "height": 320},
            {"left": 0, "top": 160, "right": 0, "bottom": 160},
        )

    def test_portrait_image(self) -> None:
        self.check_case(
            (600, 300, 3),
            640.0 / 600.0,
            {"width": 320, "height": 640},
            {"left": 160, "top": 0, "right": 160, "bottom": 0},
        )

    def test_exact_size_image(self) -> None:
        self.check_case(
            (640, 640, 3),
            1.0,
            {"width": 640, "height": 640},
            {"left": 0, "top": 0, "right": 0, "bottom": 0},
        )

    def test_odd_padding_is_split_deterministically(self) -> None:
        self.check_case(
            (321, 640, 3),
            1.0,
            {"width": 640, "height": 321},
            {"left": 0, "top": 159, "right": 0, "bottom": 160},
        )


if __name__ == "__main__":
    unittest.main()
