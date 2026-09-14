"""
Pure Python ASAR (Electron archive) reader, patcher, and restorer.
Supports non-destructive patching with automatic .stock backups.
"""

import os
import json
import struct
import hashlib
import shutil
from typing import Dict, Union, Tuple, Optional, Any


class AsarPatcher:
    """Manages reading, patching, and restoring Electron ASAR files."""

    @staticmethod
    def read_header(asar_path: str) -> Tuple[Dict[str, Any], int]:
        """
        Reads the ASAR header JSON and returns (header_dict, base_offset).
        base_offset is the byte position in the file where file payloads begin.
        """
        with open(asar_path, "rb") as f:
            header_bytes = f.read(16)
            if len(header_bytes) < 16:
                raise ValueError("Invalid ASAR archive: file too small")
            magic, total_size, size, header_size = struct.unpack("<IIII", header_bytes)
            if magic != 4:
                raise ValueError(f"Invalid ASAR magic number: {magic} (expected 4)")
            
            raw_json = f.read(header_size).decode("utf-8").rstrip("\x00")
            header = json.loads(raw_json)
            base_offset = 16 + header_size
            return header, base_offset

    @classmethod
    def _find_node(cls, header: Dict[str, Any], internal_path: str) -> Optional[Dict[str, Any]]:
        """Walks header directory tree to find a node by '/' delimited path."""
        parts = internal_path.strip("/").split("/")
        current = header
        for part in parts:
            if not isinstance(current, dict) or "files" not in current:
                return None
            current = current["files"].get(part)
            if current is None:
                return None
        return current

    @classmethod
    def get_file_bytes(cls, asar_path: str, internal_path: str) -> Optional[bytes]:
        """Extracts and returns the raw bytes of a file inside the ASAR archive."""
        header, base_offset = cls.read_header(asar_path)
        node = cls._find_node(header, internal_path)
        if not node or "offset" not in node or "size" not in node:
            return None

        file_offset = base_offset + int(node["offset"])
        file_size = int(node["size"])
        with open(asar_path, "rb") as f:
            f.seek(file_offset)
            return f.read(file_size)

    @classmethod
    def extract_file(cls, asar_path: str, internal_path: str, destination_path: str) -> bool:
        """Extracts a file from ASAR to destination_path."""
        data = cls.get_file_bytes(asar_path, internal_path)
        if data is None:
            return False
        os.makedirs(os.path.dirname(os.path.abspath(destination_path)), exist_ok=True)
        with open(destination_path, "wb") as f:
            f.write(data)
        return True

    @classmethod
    def replace_files(
        cls,
        asar_path: str,
        replacements: Dict[str, Union[bytes, str]],
        backup_suffix: str = ".stock"
    ) -> bool:
        """
        Replaces one or more files in the ASAR archive while preserving all others.
        `replacements` maps internal path (e.g. 'icon.png') to either:
          - raw bytes
          - filesystem path to replacement file
        Creates a pristine backup (e.g. app.asar.stock) if it does not already exist.
        """
        if not os.path.exists(asar_path):
            raise FileNotFoundError(f"ASAR file not found: {asar_path}")

        backup_path = asar_path + backup_suffix
        if not os.path.exists(backup_path):
            shutil.copy2(asar_path, backup_path)

        # Normalize replacements to bytes
        replacement_data: Dict[str, bytes] = {}
        for path_key, val in replacements.items():
            norm_key = path_key.strip("/")
            if isinstance(val, str):
                with open(val, "rb") as rf:
                    replacement_data[norm_key] = rf.read()
            elif isinstance(val, bytes):
                replacement_data[norm_key] = val
            else:
                raise TypeError(f"Replacement for {path_key} must be bytes or filepath string")

        header, old_base_offset = cls.read_header(asar_path)

        # Collect all files from old header in order of their offsets
        file_entries = []

        def collect(node: Dict[str, Any], current_path: str):
            if "files" in node:
                for name, child in node["files"].items():
                    subpath = f"{current_path}/{name}" if current_path else name
                    collect(child, subpath)
            elif "offset" in node and "size" in node:
                file_entries.append((current_path, node))

        collect(header, "")
        # Sort by offset to read sequentially
        file_entries.sort(key=lambda item: int(item[1]["offset"]))

        # Build new file payloads and update nodes in header
        new_header = json.loads(json.dumps(header))  # deep copy
        new_payloads = []
        current_offset = 0

        with open(asar_path, "rb") as original_file:
            for internal_path, old_node in file_entries:
                target_node = cls._find_node(new_header, internal_path)
                assert target_node is not None

                if internal_path in replacement_data:
                    data = replacement_data[internal_path]
                else:
                    original_file.seek(old_base_offset + int(old_node["offset"]))
                    data = original_file.read(int(old_node["size"]))

                # Calculate sha256 integrity block
                hasher = hashlib.sha256()
                hasher.update(data)
                digest = hasher.hexdigest()

                target_node["offset"] = str(current_offset)
                target_node["size"] = len(data)
                target_node["integrity"] = {
                    "algorithm": "SHA256",
                    "hash": digest,
                    "blockSize": 4194304,
                    "blocks": [digest],
                }

                new_payloads.append(data)
                current_offset += len(data)

        # Encode new header
        new_header_json = json.dumps(new_header, separators=(",", ":")).encode("utf-8")
        header_len = len(new_header_json)

        # ASAR header alignment (padded to 4 bytes if needed)
        padding = (4 - (header_len % 4)) % 4
        if padding > 0:
            new_header_json += b"\0" * padding
            header_len += padding

        temp_asar_path = asar_path + ".tmp"
        with open(temp_asar_path, "wb") as out:
            # Write 16-byte ASAR header
            # magic=4, total_size=header_len+8, size=header_len+4, header_size=header_len
            out.write(struct.pack("<IIII", 4, header_len + 8, header_len + 4, header_len))
            out.write(new_header_json)
            for chunk in new_payloads:
                out.write(chunk)

        # Atomic replace
        os.replace(temp_asar_path, asar_path)
        return True

    @classmethod
    def restore(cls, asar_path: str, backup_suffix: str = ".stock") -> bool:
        """Restores original ASAR from .stock backup."""
        backup_path = asar_path + backup_suffix
        if not os.path.exists(backup_path):
            return False
        shutil.copy2(backup_path, asar_path)
        return True

    @classmethod
    def is_patched(cls, asar_path: str, backup_suffix: str = ".stock") -> bool:
        """Returns True if a backup exists and differs from current asar."""
        backup_path = asar_path + backup_suffix
        if not os.path.exists(backup_path):
            return False
        return os.path.getmtime(backup_path) != os.path.getmtime(asar_path) or \
               os.path.getsize(backup_path) != os.path.getsize(asar_path)
