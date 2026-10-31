"""
Image Converter & Symbolic Generator for system tray icons.
Handles background removal, silhouette extraction, accent color preservation,
and generation of symbolic SVGs or transparent monochrome PNGs.
"""

import os
import shutil
import math
from typing import Optional, Tuple, List, Union
from PIL import Image, ImageOps, ImageFilter
import numpy as np


class IconConverter:
    """Utilities to convert, clean, and adapt icons into flat/monochrome tray icons."""

    @staticmethod
    def remove_background(
        img: Image.Image,
        tolerance: int = 30,
        corner_samples: int = 4
    ) -> Image.Image:
        """
        Detects if the image has a solid opaque background (e.g., black or white box)
        and converts the background color into transparent pixels.
        """
        rgba = img.convert("RGBA")
        arr = np.array(rgba)
        h, w, _ = arr.shape

        # Sample 4 corners
        corners = [
            arr[0, 0, :3],
            arr[0, w - 1, :3],
            arr[h - 1, 0, :3],
            arr[h - 1, w - 1, :3]
        ]
        
        # Check if corners are relatively uniform
        mean_corner = np.mean(corners, axis=0)
        corner_dists = [np.linalg.norm(c - mean_corner) for c in corners]
        if max(corner_dists) > tolerance * 1.5:
            # Not a simple uniform background, return original
            return rgba

        bg_color = mean_corner

        # Calculate distance to background color for all pixels
        diff = np.linalg.norm(arr[:, :, :3] - bg_color, axis=2)
        
        # Create alpha mask: if close to background, alpha -> 0
        mask = diff > tolerance
        
        # Smooth the alpha transition
        new_alpha = np.where(mask, arr[:, :, 3], 0)
        arr[:, :, 3] = new_alpha
        return Image.fromarray(arr, mode="RGBA")

    @classmethod
    def to_monochrome(
        cls,
        img: Image.Image,
        foreground_color: Tuple[int, int, int] = (223, 223, 223),
        preserve_accents: bool = True,
        accent_saturation_threshold: float = 0.45,
        contrast_boost: bool = True
    ) -> Image.Image:
        """
        Converts the foreground glyph into flat monochrome with smooth transparency,
        optionally preserving bright accent dots (e.g. notification dots or brand badges).
        """
        rgba = img.convert("RGBA")
        arr = np.array(rgba).astype(float)
        h, w, _ = arr.shape

        r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]

        # Calculate saturation and luminance
        cmax = np.maximum(np.maximum(r, g), b)
        cmin = np.minimum(np.minimum(r, g), b)
        delta = cmax - cmin

        # Saturation: delta / cmax where cmax > 0
        sat = np.zeros_like(cmax)
        nonzero = cmax > 0
        sat[nonzero] = delta[nonzero] / cmax[nonzero]

        # Luminance
        lum = 0.299 * r + 0.587 * g + 0.114 * b

        out = np.zeros((h, w, 4), dtype=np.uint8)
        fg_r, fg_g, fg_b = foreground_color

        transparent = a <= 5
        if preserve_accents:
            is_accent = (~transparent) & (sat >= accent_saturation_threshold) & (lum > 30)
        else:
            is_accent = np.zeros((h, w), dtype=bool)

        is_mono = (~transparent) & (~is_accent)

        out[is_accent, 0] = r[is_accent].astype(np.uint8)
        out[is_accent, 1] = g[is_accent].astype(np.uint8)
        out[is_accent, 2] = b[is_accent].astype(np.uint8)
        out[is_accent, 3] = a[is_accent].astype(np.uint8)

        if contrast_boost:
            factor = np.minimum(1.0, (lum / 255.0) * 1.2)
            factor_mono = factor[is_mono]
        else:
            factor_mono = 1.0

        out[is_mono, 0] = (fg_r * factor_mono).astype(np.uint8)
        out[is_mono, 1] = (fg_g * factor_mono).astype(np.uint8)
        out[is_mono, 2] = (fg_b * factor_mono).astype(np.uint8)
        out[is_mono, 3] = a[is_mono].astype(np.uint8)

        return Image.fromarray(out, mode="RGBA")

    @classmethod
    def fit_tray(
        cls,
        img: Image.Image,
        size: int = 22,
        padding: int = 2
    ) -> Image.Image:
        """
        Autocrops the content to its bounding box, resizes it with high quality Lanczos,
        and centers it in a `size`x`size` canvas with the specified padding.
        """
        rgba = img.convert("RGBA")
        bbox = rgba.getbbox()
        if bbox:
            cropped = rgba.crop(bbox)
        else:
            cropped = rgba

        target_inner_size = size - (padding * 2)
        if target_inner_size <= 0:
            target_inner_size = size

        w, h = cropped.size
        scale = min(target_inner_size / w, target_inner_size / h)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))

        resized = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)

        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        offset_x = (size - new_w) // 2
        offset_y = (size - new_h) // 2
        canvas.paste(resized, (offset_x, offset_y), resized)
        return canvas

    @classmethod
    def convert_file(
        cls,
        input_path: str,
        output_path: str,
        size: int = 22,
        padding: int = 2,
        strip_bg: bool = True,
        preserve_accents: bool = True,
        foreground_hex: str = "#dfdfdf"
    ) -> bool:
        """Processes an input image file and saves the converted tray icon."""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input image not found: {input_path}")

        # Parse hex color
        hex_clean = foreground_hex.lstrip("#")
        fg_color = tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))

        # If input is SVG, render with magick/convert first
        if input_path.lower().endswith(".svg"):
            import subprocess
            import tempfile
            temp_png = tempfile.mktemp(suffix=".png")
            renderer = shutil.which("magick") or shutil.which("convert")
            if renderer:
                cmd = [renderer, "-density", "300", "-background", "none", input_path, temp_png]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                img = Image.open(temp_png)
                try:
                    os.remove(temp_png)
                except OSError:
                    pass
            else:
                raise RuntimeError("ImageMagick (magick/convert) is required to process SVG inputs")
        else:
            img = Image.open(input_path)

        if strip_bg:
            img = cls.remove_background(img)

        mono = cls.to_monochrome(
            img,
            foreground_color=fg_color,
            preserve_accents=preserve_accents
        )

        fitted = cls.fit_tray(mono, size=size, padding=padding)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        fitted.save(output_path, format="PNG")
        return True

    @staticmethod
    def generate_symbolic_svg_wrapper(
        svg_content: str,
        class_name: str = "ColorScheme-Text"
    ) -> str:
        """
        Injects FreeDesktop/KDE Plasma ColorScheme stylesheet into SVG if missing,
        ensuring proper adaptation to dark/light panels.
        """
        if "ColorScheme-Text" in svg_content:
            return svg_content

        style_block = (
            "  <defs>\n"
            '    <style id="current-color-scheme" type="text/css">\n'
            "      .ColorScheme-Text { color:#dfdfdf; }\n"
            "      .ColorScheme-Highlight { color:#3daee9; }\n"
            "      .ColorScheme-NeutralText { color:#f67400; }\n"
            "      .ColorScheme-PositiveText { color:#27ae60; }\n"
            "      .ColorScheme-NegativeText { color:#da4453; }\n"
            "    </style>\n"
            "  </defs>\n"
        )
        
        insert_idx = svg_content.find(">")
        if insert_idx != -1:
            return svg_content[:insert_idx + 1] + "\n" + style_block + svg_content[insert_idx + 1:]
        return svg_content
