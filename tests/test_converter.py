import os
import unittest
from PIL import Image
import numpy as np
from tray_icons_flat.converter import IconConverter


class TestIconConverter(unittest.TestCase):

    def test_remove_background_solid_black_box(self):
        # Create an image with black background and a white circle in the center
        img = Image.new("RGBA", (50, 50), (0, 0, 0, 255))
        for y in range(15, 35):
            for x in range(15, 35):
                img.putpixel((x, y), (255, 255, 255, 255))

        cleaned = IconConverter.remove_background(img, tolerance=20)
        arr = np.array(cleaned)
        # Corners should be transparent
        self.assertEqual(arr[0, 0, 3], 0)
        self.assertEqual(arr[49, 49, 3], 0)
        # Center should remain opaque white
        self.assertEqual(arr[25, 25, 3], 255)
        self.assertEqual(arr[25, 25, 0], 255)

    def test_monochrome_with_accent_preservation(self):
        img = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
        # Blue main shape
        for x in range(5, 10):
            for y in range(5, 10):
                img.putpixel((x, y), (50, 120, 240, 255))
        # Bright red badge dot
        for x in range(15, 18):
            for y in range(2, 5):
                img.putpixel((x, y), (255, 0, 0, 255))

        mono = IconConverter.to_monochrome(
            img,
            foreground_color=(223, 223, 223),
            preserve_accents=True,
            accent_saturation_threshold=0.5
        )
        arr = np.array(mono)

        # Red dot should still be strongly red
        self.assertGreater(arr[3, 16, 0], 200)
        self.assertLess(arr[3, 16, 1], 50)

    def test_fit_tray_dimensions(self):
        img = Image.new("RGBA", (100, 50), (255, 255, 255, 255))
        fitted = IconConverter.fit_tray(img, size=22, padding=2)
        self.assertEqual(fitted.size, (22, 22))


if __name__ == "__main__":
    unittest.main()
