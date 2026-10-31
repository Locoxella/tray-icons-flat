import os
import tempfile
import unittest
from unittest.mock import patch
from tray_icons_flat.theme_installer import ThemeInstaller


class TestThemeInstaller(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.user_icons_base = os.path.join(self.temp_dir.name, "icons")
        os.makedirs(self.user_icons_base, exist_ok=True)
        # Point ThemeInstaller to test dir
        self.orig_base = ThemeInstaller.USER_ICONS_BASE
        ThemeInstaller.USER_ICONS_BASE = self.user_icons_base

    def tearDown(self):
        ThemeInstaller.USER_ICONS_BASE = self.orig_base
        self.temp_dir.cleanup()

    def test_get_active_themes_includes_detected_desktop_theme(self):
        with patch.object(ThemeInstaller, "detect_desktop_theme", return_value="Papirus-Dark"):
            themes = ThemeInstaller.get_active_themes()
            self.assertIn("hicolor", themes)
            self.assertIn("Papirus-Dark", themes)

    def test_install_and_uninstall_icon(self):
        # Create mock source SVG
        src_svg = os.path.join(self.temp_dir.name, "test_icon.svg")
        with open(src_svg, "w") as f:
            f.write("<svg></svg>")

        installed = ThemeInstaller.install_icon(
            source_path=src_svg,
            target_name="test-target",
            theme="hicolor",
            subdirectories=["scalable/status", "22x22/panel"]
        )

        for p in installed:
            self.assertTrue(os.path.exists(p))

        # Uninstall
        ThemeInstaller.uninstall_files(installed)
        for p in installed:
            self.assertFalse(os.path.exists(p))


if __name__ == "__main__":
    unittest.main()
