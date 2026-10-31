import unittest
import subprocess
import sys
import json


class TestCLI(unittest.TestCase):

    def test_cli_version(self):
        cmd = [sys.executable, "-m", "tray_icons_flat.cli", "--version"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("tray-icons-flat", res.stdout)

    def test_cli_scan_json(self):
        cmd = [sys.executable, "-m", "tray_icons_flat.cli", "scan", "--json"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertIsInstance(data, list)
        self.assertTrue(any(item["id"] == "cameractrls" for item in data))

    def test_cli_fix_and_revert_dry_run(self):
        cmd_fix = [sys.executable, "-m", "tray_icons_flat.cli", "fix", "--all", "--dry-run"]
        res_fix = subprocess.run(cmd_fix, capture_output=True, text=True)
        self.assertEqual(res_fix.returncode, 0)
        self.assertIn("Dry run complete", res_fix.stdout)

        cmd_rev = [sys.executable, "-m", "tray_icons_flat.cli", "revert", "--all", "--dry-run"]
        res_rev = subprocess.run(cmd_rev, capture_output=True, text=True)
        self.assertEqual(res_rev.returncode, 0)
        self.assertIn("Dry run complete", res_rev.stdout)


if __name__ == "__main__":
    unittest.main()
