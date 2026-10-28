"""
Recipe engine to discover, inspect, apply, and revert tray icon fixes.
"""

import os
import sys
import json
import yaml
import shutil
import subprocess
import time
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from .asar_patcher import AsarPatcher
from .theme_installer import ThemeInstaller


class AppStatus(str, Enum):
    NOT_INSTALLED = "NOT_INSTALLED"
    BROKEN = "BROKEN"      # Installed but using default colored/broken tray icon
    FIXED = "FIXED"        # Installed and patched with flat/monochrome icon


class Recipe:
    """Represents an application tray fix recipe."""

    def __init__(self, recipe_dir: str, config: Dict[str, Any]):
        self.recipe_dir = recipe_dir
        self.config = config
        self.id = config.get("id", os.path.basename(recipe_dir))
        self.name = config.get("name", self.id)
        self.description = config.get("description", "")
        self.strategy = config.get("strategy", "icon_theme")
        self.detector = config.get("detector", {})
        self.target_files = config.get("target_files", {})
        self.icons = config.get("icons", [])

    def resolve_path(self, path_str: str) -> str:
        """Expands ~ and environment variables, or resolves relative to recipe_dir."""
        expanded = os.path.expanduser(os.path.expandvars(path_str))
        if not os.path.isabs(expanded):
            return os.path.join(self.recipe_dir, expanded)
        return expanded

    def is_installed(self) -> bool:
        """Checks if the application is installed on the system."""
        # Check binary
        if "binary" in self.detector:
            if shutil.which(self.detector["binary"]):
                return True

        # Check path
        if "path" in self.detector:
            path = self.resolve_path(self.detector["path"])
            if os.path.exists(path):
                return True

        # Check flatpak
        if "flatpak_id" in self.detector:
            f_id = self.detector["flatpak_id"]
            paths = [
                os.path.expanduser(f"~/.local/share/flatpak/app/{f_id}"),
                f"/var/lib/flatpak/app/{f_id}"
            ]
            if any(os.path.exists(p) for p in paths):
                return True

        # Check desktop file
        if "desktop" in self.detector:
            d_name = self.detector["desktop"]
            desktop_dirs = [
                os.path.expanduser("~/.local/share/applications"),
                "/usr/share/applications"
            ]
            for d in desktop_dirs:
                if os.path.exists(os.path.join(d, d_name)):
                    return True

        return False

    def get_status(self, state_data: Dict[str, Any]) -> AppStatus:
        """Determines the current status of the app."""
        if not self.is_installed():
            return AppStatus.NOT_INSTALLED

        if self.strategy == "electron_asar":
            asar_path = self.resolve_path(self.config.get("asar_path", ""))
            if os.path.exists(asar_path):
                # Check if .stock backup exists and current differs, or state recorded
                if AsarPatcher.is_patched(asar_path):
                    return AppStatus.FIXED
            return AppStatus.BROKEN

        elif self.strategy == "bwrap_wrapper":
            wrapper_bin = self.resolve_path(self.config.get("wrapper_bin", ""))
            if os.path.exists(wrapper_bin) and os.access(wrapper_bin, os.X_OK):
                return AppStatus.FIXED
            return AppStatus.BROKEN

        elif self.strategy == "icon_theme":
            app_state = state_data.get("apps", {}).get(self.id, {})
            installed_files = app_state.get("installed_files", [])
            if installed_files and all(os.path.exists(f) for f in installed_files):
                return AppStatus.FIXED
            return AppStatus.BROKEN

        elif self.strategy == "flatpak_binary_patch":
            patched_bin = os.path.expanduser(f"~/.local/share/tray-icons-flat/patched_bins/{self.config.get('flatpak_id', self.id)}/{os.path.basename(self.config.get('target_binary_rel', 'zoom'))}")
            desktop_file = os.path.expanduser(f"~/.local/share/applications/{self.config.get('flatpak_id', self.id)}.desktop")
            if os.path.exists(patched_bin) and os.path.exists(desktop_file):
                return AppStatus.FIXED
            return AppStatus.BROKEN

        return AppStatus.BROKEN

    def apply(self, state_data: Dict[str, Any]) -> bool:
        """Applies the fix for this recipe."""
        if not self.is_installed():
            return False

        app_state = state_data.setdefault("apps", {}).setdefault(self.id, {})

        if self.strategy == "bwrap_wrapper":
            target_binary = self.config.get("target_binary", shutil.which(self.detector.get("binary", "")))
            wrapper_bin = self.resolve_path(self.config.get("wrapper_bin", ""))
            os.makedirs(os.path.dirname(os.path.abspath(wrapper_bin)), exist_ok=True)

            bind_args = []
            for target_path, source_rel in self.config.get("binds", {}).items():
                resolved_src = self.resolve_path(source_rel)
                bind_args.append(f'--ro-bind "{resolved_src}" "{target_path}"')

            binds_str = " \\\n  ".join(bind_args)
            script_content = f"""#!/bin/sh
# Wrapper generated by tray-icons-flat
exec /usr/bin/bwrap --dev-bind / / \\
  {binds_str} \\
  {target_binary} "$@"
"""
            with open(wrapper_bin, "w", encoding="utf-8") as wf:
                wf.write(script_content)
            os.chmod(wrapper_bin, 0o755)

            # Update desktop files if specified
            desktop_files = self.config.get("desktop_files", [])
            updated_desktops = []
            for df in desktop_files:
                resolved_df = self.resolve_path(df)
                os.makedirs(os.path.dirname(os.path.abspath(resolved_df)), exist_ok=True)
                # Create desktop entry pointing to wrapper_bin
                desktop_entry = f"""[Desktop Entry]
Type=Application
Name={self.name}
Exec={wrapper_bin}
Icon={self.config.get('desktop_icon', self.id)}
Comment={self.description}
Terminal=false
"""
                with open(resolved_df, "w", encoding="utf-8") as df_file:
                    df_file.write(desktop_entry)
                updated_desktops.append(resolved_df)

            app_state["wrapper_bin"] = wrapper_bin
            app_state["desktop_files"] = updated_desktops
            app_state["status"] = AppStatus.FIXED.value

            # If application is currently running, restart it to apply the new icon
            bin_name = os.path.basename(target_binary)
            proc_check = subprocess.run(["killall", "-0", bin_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if proc_check.returncode == 0:
                subprocess.run(["killall", "-9", bin_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                import time
                time.sleep(0.5)
                # Launch in background
                subprocess.Popen([wrapper_bin], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

            return True

        elif self.strategy == "icon_theme":
            installed_all: List[str] = []
            active_themes = ThemeInstaller.get_active_themes()

            for icon_spec in self.icons:
                name = icon_spec["name"]
                source_rel = icon_spec.get("source")
                source_path = self.resolve_path(source_rel)
                subdirs = icon_spec.get("subdirectories")

                for theme in active_themes:
                    created = ThemeInstaller.install_icon(
                        source_path=source_path,
                        target_name=name,
                        theme=theme,
                        subdirectories=subdirs
                    )
                    installed_all.extend(created)

            ThemeInstaller.refresh_icon_cache()
            app_state["installed_files"] = list(dict.fromkeys(installed_all))
            app_state["status"] = AppStatus.FIXED.value
            return True

        elif self.strategy == "electron_asar":
            asar_path = self.resolve_path(self.config.get("asar_path", ""))
            replacements = {}
            for target_internal, source_rel in self.config.get("replacements", {}).items():
                replacements[target_internal] = self.resolve_path(source_rel)

            if replacements and os.path.exists(asar_path):
                success = AsarPatcher.replace_files(asar_path, replacements)
                if success:
                    app_state["asar_path"] = asar_path
                    app_state["status"] = AppStatus.FIXED.value
                    return True

        elif self.strategy == "flatpak_binary_patch":
            flatpak_id = self.config.get("flatpak_id", self.id)
            target_rel = self.config.get("target_binary_rel", "")
            repl_svg_rel = self.config.get("replacement_svg", "")
            repl_svg_path = self.resolve_path(repl_svg_rel)
            repl_size = int(self.config.get("replacement_size", 2048))

            # Find base binary in flatpak installation
            base_bin = None
            search_roots = [
                f"/var/lib/flatpak/app/{flatpak_id}/x86_64/stable/active",
                os.path.expanduser(f"~/.local/share/flatpak/app/{flatpak_id}/x86_64/stable/active")
            ]
            for root in search_roots:
                candidate = os.path.join(root, target_rel)
                if os.path.exists(candidate):
                    base_bin = candidate
                    break

            if not base_bin or not os.path.exists(repl_svg_path):
                return False

            with open(base_bin, "rb") as f:
                orig_data = f.read()

            with open(repl_svg_path, "rb") as f:
                svg_data = f.read()

            if len(svg_data) > repl_size:
                return False

            padded_svg = svg_data + b" " * (repl_size - len(svg_data))
            repl_offset = self.config.get("replacement_offset")
            if repl_offset is not None:
                offset = int(repl_offset)
            else:
                pattern = self.config.get("target_pattern", "").encode("utf-8")
                offset = orig_data.find(pattern)
                if offset == -1:
                    return False

            patched_data = orig_data[:offset] + padded_svg + orig_data[offset + repl_size:]
            dest_dir = os.path.expanduser(f"~/.local/share/tray-icons-flat/patched_bins/{flatpak_id}")
            os.makedirs(dest_dir, exist_ok=True)
            patched_bin = os.path.join(dest_dir, os.path.basename(target_rel))

            with open(patched_bin, "wb") as f:
                f.write(patched_data)
            os.chmod(patched_bin, 0o755)

            # Generate user desktop override
            user_desktop_dir = os.path.expanduser("~/.local/share/applications")
            os.makedirs(user_desktop_dir, exist_ok=True)
            desktop_path = os.path.join(user_desktop_dir, f"{flatpak_id}.desktop")

            # Look for stock desktop file to preserve metadata
            stock_desktop = None
            for root in search_roots:
                c1 = os.path.join(root, "export/share/applications", f"{flatpak_id}.desktop")
                c2 = os.path.join(root, "files/share/applications", f"{flatpak_id}.desktop")
                if os.path.exists(c1):
                    stock_desktop = c1
                    break
                elif os.path.exists(c2):
                    stock_desktop = c2
                    break

            exec_override = (
                f"flatpak run --filesystem={patched_bin}:ro --command=sh {flatpak_id} -c '"
                f"rm -f $HOME/.zoom/data/cefcache/*/SingletonSocket; exec {patched_bin} \"$@\"' sh %U"
            )

            if stock_desktop and os.path.exists(stock_desktop):
                with open(stock_desktop, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                new_lines = []
                for line in lines:
                    if line.startswith("Exec="):
                        new_lines.append(f"Exec={exec_override}\n")
                    else:
                        new_lines.append(line)
                with open(desktop_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
            else:
                with open(desktop_path, "w", encoding="utf-8") as f:
                    f.write(f"""[Desktop Entry]
Type=Application
Name={self.name}
Exec={exec_override}
Icon={flatpak_id}
Comment={self.description}
Terminal=false
""")

            app_state["patched_bin"] = patched_bin
            app_state["desktop_path"] = desktop_path
            app_state["status"] = AppStatus.FIXED.value
            return True

        return False

    def revert(self, state_data: Dict[str, Any]) -> bool:
        """Reverts the fix for this recipe."""
        app_state = state_data.get("apps", {}).get(self.id, {})

        if self.strategy == "bwrap_wrapper":
            wrapper_bin = app_state.get("wrapper_bin") or self.resolve_path(self.config.get("wrapper_bin", ""))
            if os.path.exists(wrapper_bin):
                try:
                    os.remove(wrapper_bin)
                except OSError:
                    pass
            for df in app_state.get("desktop_files", []):
                if os.path.exists(df):
                    try:
                        os.remove(df)
                    except OSError:
                        pass
            app_state["status"] = AppStatus.BROKEN.value
            # If application is running, restart with original binary
            target_binary = self.config.get("target_binary", shutil.which(self.detector.get("binary", "")))
            bin_name = os.path.basename(target_binary)
            proc_check = subprocess.run(["killall", "-0", bin_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if proc_check.returncode == 0:
                subprocess.run(["killall", "-9", bin_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                import time
                time.sleep(0.5)
                subprocess.Popen([target_binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return True

        elif self.strategy == "icon_theme":
            installed_files = app_state.get("installed_files", [])
            ThemeInstaller.uninstall_files(installed_files)
            ThemeInstaller.refresh_icon_cache()
            app_state["installed_files"] = []
            app_state["status"] = AppStatus.BROKEN.value
            return True

        elif self.strategy == "electron_asar":
            asar_path = self.resolve_path(self.config.get("asar_path", ""))
            if os.path.exists(asar_path):
                AsarPatcher.restore(asar_path)
            app_state["status"] = AppStatus.BROKEN.value
            return True

        elif self.strategy == "flatpak_binary_patch":
            flatpak_id = self.config.get("flatpak_id", self.id)
            target_rel = self.config.get("target_binary_rel", "zoom")
            patched_bin = app_state.get("patched_bin") or os.path.expanduser(f"~/.local/share/tray-icons-flat/patched_bins/{flatpak_id}/{os.path.basename(target_rel)}")
            desktop_path = app_state.get("desktop_path") or os.path.expanduser(f"~/.local/share/applications/{flatpak_id}.desktop")
            if patched_bin and os.path.exists(patched_bin):
                try:
                    os.remove(patched_bin)
                except OSError:
                    pass
            if desktop_path and os.path.exists(desktop_path):
                try:
                    os.remove(desktop_path)
                except OSError:
                    pass
            app_state["status"] = AppStatus.BROKEN.value
            return True

        return False


class RecipeEngine:
    """Manages the catalog of recipes and persistent state."""

    STATE_PATH = os.path.expanduser("~/.local/share/tray-icons-flat/state.json")

    def __init__(self, recipes_dirs: Optional[List[str]] = None):
        if recipes_dirs is None:
            # Default to built-in recipes/ dir in repo or package
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            pkg_dir = os.path.dirname(os.path.abspath(__file__))
            recipes_dirs = [
                os.path.join(base_dir, "recipes"),
                os.path.join(pkg_dir, "recipes"),
                os.path.expanduser("~/.config/tray-icons-flat/recipes")
            ]
        self.recipes_dirs = recipes_dirs
        self.recipes: Dict[str, Recipe] = {}
        self.load_recipes()

    def load_recipes(self) -> None:
        """Loads all recipe YAML files found in recipes directories."""
        self.recipes.clear()
        for r_dir in self.recipes_dirs:
            if not os.path.isdir(r_dir):
                continue
            for item in os.listdir(r_dir):
                subpath = os.path.join(r_dir, item)
                if os.path.isdir(subpath):
                    # Check for recipe.yaml or <item>.yaml
                    recipe_file = None
                    for candidate in ["recipe.yaml", "recipe.yml", f"{item}.yaml", f"{item}.yml"]:
                        p = os.path.join(subpath, candidate)
                        if os.path.isfile(p):
                            recipe_file = p
                            break
                    if recipe_file:
                        with open(recipe_file, "r", encoding="utf-8") as f:
                            cfg = yaml.safe_load(f) or {}
                        recipe = Recipe(subpath, cfg)
                        self.recipes[recipe.id] = recipe

    def load_state(self) -> Dict[str, Any]:
        """Loads state.json."""
        if os.path.exists(self.STATE_PATH):
            try:
                with open(self.STATE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_state(self, state: Dict[str, Any]) -> None:
        """Saves state.json."""
        os.makedirs(os.path.dirname(self.STATE_PATH), exist_ok=True)
        with open(self.STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def scan(self) -> List[Dict[str, Any]]:
        """Scans all recipes and returns their detection and fix status."""
        state = self.load_state()
        results = []
        for r_id, recipe in self.recipes.items():
            status = recipe.get_status(state)
            results.append({
                "id": recipe.id,
                "name": recipe.name,
                "description": recipe.description,
                "strategy": recipe.strategy,
                "status": status.value
            })
        return results

    def fix(self, app_id: Optional[str] = None) -> List[Tuple[str, bool, str]]:
        """
        Applies fixes for a specific app_id or all installed apps.
        Returns list of (app_id, success, message).
        """
        state = self.load_state()
        results = []
        targets = [self.recipes[app_id]] if app_id and app_id in self.recipes else list(self.recipes.values())

        for recipe in targets:
            status = recipe.get_status(state)
            if status == AppStatus.NOT_INSTALLED:
                results.append((recipe.id, False, "Application not installed"))
                continue
            if status == AppStatus.FIXED:
                # Still re-apply to ensure icons and caches are fresh
                pass

            try:
                ok = recipe.apply(state)
                if ok:
                    results.append((recipe.id, True, "Successfully applied flat icon fix"))
                else:
                    results.append((recipe.id, False, "Failed to apply fix"))
            except Exception as e:
                results.append((recipe.id, False, str(e)))

        self.save_state(state)
        return results

    def revert(self, app_id: Optional[str] = None) -> List[Tuple[str, bool, str]]:
        """Reverts fixes for a specific app_id or all apps."""
        state = self.load_state()
        results = []
        targets = [self.recipes[app_id]] if app_id and app_id in self.recipes else list(self.recipes.values())

        for recipe in targets:
            try:
                ok = recipe.revert(state)
                if ok:
                    results.append((recipe.id, True, "Successfully reverted to stock icon"))
                else:
                    results.append((recipe.id, False, "Failed to revert fix"))
            except Exception as e:
                results.append((recipe.id, False, str(e)))

        self.save_state(state)
        return results
