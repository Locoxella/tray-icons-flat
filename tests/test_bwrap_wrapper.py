import os
import stat
import tempfile
import unittest
from tray_icons_flat.bwrap_wrapper import BwrapWrapper


class TestBwrapWrapper(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.wrapper_bin = os.path.join(self.temp_dir.name, "bin", "test-app")
        self.desktop_file = os.path.join(self.temp_dir.name, "apps", "test-app.desktop")
        self.target_bin = "/usr/bin/test-app"
        self.replacement_icon = os.path.join(self.temp_dir.name, "icon.png")

        with open(self.replacement_icon, "w") as f:
            f.write("fake-icon")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_wrapper_script(self):
        binds = {
            "/usr/share/icons/app.png": self.replacement_icon
        }
        script = BwrapWrapper.generate_wrapper_script(
            target_binary=self.target_bin,
            bind_mounts=binds,
            bwrap_path="/usr/bin/bwrap"
        )
        self.assertTrue(script.startswith("#!/bin/sh"))
        self.assertIn("/usr/bin/bwrap --dev-bind / /", script)
        self.assertIn(f'--ro-bind "{self.replacement_icon}" "/usr/share/icons/app.png"', script)
        self.assertIn(f'"{self.target_bin}" "$@"', script)

    def test_install_and_uninstall(self):
        binds = {
            "/usr/share/icons/app.png": self.replacement_icon
        }
        updated_desktops = BwrapWrapper.install(
            target_binary=self.target_bin,
            wrapper_bin=self.wrapper_bin,
            bind_mounts=binds,
            desktop_files=[self.desktop_file],
            desktop_name="Test App",
            desktop_icon="test-icon",
            desktop_comment="Test Description",
            restart_process=False
        )

        # Check wrapper script exists and is executable
        self.assertTrue(os.path.exists(self.wrapper_bin))
        mode = os.stat(self.wrapper_bin).st_mode
        self.assertTrue(bool(mode & stat.S_IXUSR))

        # Check desktop file
        self.assertEqual(updated_desktops, [self.desktop_file])
        self.assertTrue(os.path.exists(self.desktop_file))
        with open(self.desktop_file, "r") as f:
            content = f.read()
        self.assertIn("Name=Test App", content)
        self.assertIn(f"Exec={self.wrapper_bin}", content)
        self.assertIn("Icon=test-icon", content)

        # Test uninstall
        BwrapWrapper.uninstall(
            wrapper_bin=self.wrapper_bin,
            desktop_files=[self.desktop_file],
            target_binary=self.target_bin,
            restart_process=False
        )
        self.assertFalse(os.path.exists(self.wrapper_bin))
        self.assertFalse(os.path.exists(self.desktop_file))


if __name__ == "__main__":
    unittest.main()
