"""
Systemd user service and autostart integration for tray-icons-flat.
Ensures that icons stay fixed across application updates and reboots.
"""

import os
import sys
import shutil
import subprocess
from typing import Dict, Any


class ServiceManager:
    """Manages installation, uninstallation, and status of systemd user service."""

    SERVICE_DIR = os.path.expanduser("~/.config/systemd/user")
    SERVICE_FILE = os.path.join(SERVICE_DIR, "tray-icons-flat.service")
    AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
    AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "tray-icons-flat.desktop")

    @classmethod
    def get_bin_path(cls) -> str:
        """Finds the path to tray-icons-flat CLI executable."""
        which_bin = shutil.which("tray-icons-flat")
        if which_bin:
            return which_bin
        # Fallback to current python script execution
        cli_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cli.py")
        return f"{sys.executable} {cli_py}"

    @classmethod
    def install(cls) -> Dict[str, Any]:
        """Installs and enables systemd user service and autostart desktop entry."""
        bin_path = cls.get_bin_path()

        # 1. Setup systemd user service
        os.makedirs(cls.SERVICE_DIR, exist_ok=True)
        service_content = f"""[Unit]
Description=Flat Tray Icons Persistence Service
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=oneshot
ExecStart={bin_path} fix --all
RemainAfterExit=yes

[Install]
WantedBy=default.target
"""
        with open(cls.SERVICE_FILE, "w", encoding="utf-8") as f:
            f.write(service_content)

        # 2. Setup autostart desktop entry as secondary fallback
        os.makedirs(cls.AUTOSTART_DIR, exist_ok=True)
        autostart_content = f"""[Desktop Entry]
Type=Application
Name=Tray Icons Flat Service
Comment=Ensures tray icons remain flat and transparent after updates
Exec={bin_path} fix --all
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
"""
        with open(cls.AUTOSTART_FILE, "w", encoding="utf-8") as f:
            f.write(autostart_content)

        systemd_ok = False
        if shutil.which("systemctl"):
            try:
                subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
                subprocess.run(["systemctl", "--user", "enable", "tray-icons-flat.service"], check=False)
                subprocess.run(["systemctl", "--user", "start", "tray-icons-flat.service"], check=False)
                systemd_ok = True
            except Exception:
                pass

        return {
            "systemd_service": cls.SERVICE_FILE,
            "autostart_file": cls.AUTOSTART_FILE,
            "systemd_active": systemd_ok
        }

    @classmethod
    def uninstall(cls) -> Dict[str, Any]:
        """Disables and removes systemd service and autostart desktop entry."""
        if shutil.which("systemctl"):
            try:
                subprocess.run(["systemctl", "--user", "stop", "tray-icons-flat.service"], check=False)
                subprocess.run(["systemctl", "--user", "disable", "tray-icons-flat.service"], check=False)
            except Exception:
                pass

        removed_systemd = False
        if os.path.exists(cls.SERVICE_FILE):
            os.remove(cls.SERVICE_FILE)
            removed_systemd = True

        removed_autostart = False
        if os.path.exists(cls.AUTOSTART_FILE):
            os.remove(cls.AUTOSTART_FILE)
            removed_autostart = True

        if shutil.which("systemctl"):
            try:
                subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
            except Exception:
                pass

        return {
            "removed_systemd": removed_systemd,
            "removed_autostart": removed_autostart
        }

    @classmethod
    def status(cls) -> Dict[str, Any]:
        """Returns service installation and running status."""
        installed = os.path.exists(cls.SERVICE_FILE) or os.path.exists(cls.AUTOSTART_FILE)
        active = False
        if shutil.which("systemctl") and os.path.exists(cls.SERVICE_FILE):
            res = subprocess.run(
                ["systemctl", "--user", "is-active", "tray-icons-flat.service"],
                capture_output=True,
                text=True,
                check=False
            )
            active = (res.stdout.strip() == "active")

        return {
            "installed": installed,
            "systemd_file": cls.SERVICE_FILE if os.path.exists(cls.SERVICE_FILE) else None,
            "autostart_file": cls.AUTOSTART_FILE if os.path.exists(cls.AUTOSTART_FILE) else None,
            "active": active
        }
