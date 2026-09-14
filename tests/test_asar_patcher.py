import os
import json
import struct
import tempfile
import unittest
from tray_icons_flat.asar_patcher import AsarPatcher


class TestAsarPatcher(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.asar_path = os.path.join(self.temp_dir.name, "test_app.asar")

        # Create a valid mock ASAR archive
        file1_data = b"Hello, world!"
        file2_data = b"icon_original_data_png"

        header = {
            "files": {
                "hello.txt": {
                    "size": len(file1_data),
                    "offset": "0"
                },
                "icon.png": {
                    "size": len(file2_data),
                    "offset": str(len(file1_data))
                }
            }
        }
        header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
        header_len = len(header_json)
        padding = (4 - (header_len % 4)) % 4
        padded_header = header_json + (b"\0" * padding)
        pickled_size = len(padded_header)

        with open(self.asar_path, "wb") as f:
            f.write(struct.pack("<IIII", 4, pickled_size + 8, pickled_size + 4, header_len))
            f.write(padded_header)
            f.write(file1_data)
            f.write(file2_data)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_read_and_extract(self):
        data = AsarPatcher.get_file_bytes(self.asar_path, "hello.txt")
        self.assertEqual(data, b"Hello, world!")

        icon_data = AsarPatcher.get_file_bytes(self.asar_path, "icon.png")
        self.assertEqual(icon_data, b"icon_original_data_png")

    def test_replace_and_restore(self):
        new_icon = b"new_flat_icon_bytes"
        success = AsarPatcher.replace_files(self.asar_path, {"icon.png": new_icon})
        self.assertTrue(success)

        # Check that icon was replaced
        updated_icon = AsarPatcher.get_file_bytes(self.asar_path, "icon.png")
        self.assertEqual(updated_icon, new_icon)

        # Check that other file was unaffected
        hello_data = AsarPatcher.get_file_bytes(self.asar_path, "hello.txt")
        self.assertEqual(hello_data, b"Hello, world!")

        # Verify .stock backup exists
        self.assertTrue(os.path.exists(self.asar_path + ".stock"))
        self.assertTrue(AsarPatcher.is_patched(self.asar_path))

        # Restore
        restored = AsarPatcher.restore(self.asar_path)
        self.assertTrue(restored)
        restored_icon = AsarPatcher.get_file_bytes(self.asar_path, "icon.png")
        self.assertEqual(restored_icon, b"icon_original_data_png")


if __name__ == "__main__":
    unittest.main()
