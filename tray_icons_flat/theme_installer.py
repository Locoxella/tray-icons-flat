"""
Manages installing symbolic/flat icons into user icon directories
(~/.local/share/icons) and updating icon caches.
"""

import os
import shutil
import subprocess
from typing import List, Optional, Set


class ThemeInstaller:
    """Installs tray icons into user themes and refreshes caches."""

    USER_ICONS_BASE = os.path.expanduser("~/.local/share/icons")

    @classmethod
    def get_active_themes(cls) -> List[str]:
        """Detects installed user themes that should receive tray icons."""
        themes = ["hicolor"]
        if os.path.isdir(cls.USER_ICONS_BASE):
            for entry in os.listdir(cls.USER_ICONS_BASE):
                entry_path = os.path.join(cls.USER_ICONS_BASE, entry)
                if os.path.isdir(entry_path) and entry != "hicolor":
                    # e.g., Papirus, Papirus-Dark, Papirus-Light, ePapirus
                    themes.append(entry)
        return list(dict.fromkeys(themes))

    @classmethod
    def install_icon(
        cls,
        source_path: str,
        target_name: str,
        theme: str = "hicolor",
        subdirectories: Optional[List[str]] = None
    ) -> List[str]:
        """
        Installs a source icon (SVG or PNG) into target directories.
        subdirectories: e.g. ["scalable/status", "scalable/apps", "22x22/panel"]
        Returns a list of created file paths.
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source icon not found: {source_path}")

        _, ext = os.path.splitext(source_path)
        if not target_name.endswith(ext):
            target_filename = f"{target_name}{ext}"
        else:
            target_filename = target_name

        if subdirectories is None:
            # Default target dirs based on extension
            if ext == ".svg":
                subdirectories = [
                    "scalable/apps",
                    "scalable/status",
                    "22x22/panel",
                    "24x24/panel",
                    "16x16/panel"
                ]
            else:
                subdirectories = [
                    "22x22/panel",
                    "24x24/panel",
                    "22x22/status",
                    "48x48/apps"
                ]

        installed_files = []
        theme_dir = os.path.join(cls.USER_ICONS_BASE, theme)

        for subdir in subdirectories:
            dest_dir = os.path.join(theme_dir, subdir)
            os.makedirs(dest_dir, exist_ok=True)
            dest_file = os.path.join(dest_dir, target_filename)
            shutil.copy2(source_path, dest_file)
            installed_files.append(dest_file)

        return installed_files

    @classmethod
    def uninstall_files(cls, file_paths: List[str]) -> None:
        """Removes installed icon files and cleans up empty parent dirs."""
        for p in file_paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

    @classmethod
    def refresh_icon_cache(cls) -> None:
        """Updates gtk-update-icon-cache and notifies KDE / FreeDesktop."""
        if not os.path.isdir(cls.USER_ICONS_BASE):
            return

        # Update cache for each user theme
        for entry in os.listdir(cls.USER_ICONS_BASE):
            theme_path = os.path.join(cls.USER_ICONS_BASE, entry)
            if os.path.isdir(theme_path):
                # Run gtk-update-icon-cache if available
                if shutil.which("gtk-update-icon-cache"):
                    try:
                        subprocess.run(
                            ["gtk-update-icon-cache", "-f", "-t", theme_path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            check=False
                        )
                    except Exception:
                        pass

        # Update KDE Sycoca cache if on KDE
        for cmd in ["kbuildsycoca6", "kbuildsycoca5"]:
            if shutil.which(cmd):
                try:
                    subprocess.run(
                        [cmd, "--noincremental"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False
                    )
                    break
                except Exception:
                    pass
