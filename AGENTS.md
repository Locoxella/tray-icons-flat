# AGENTS.md — Developer & AI Agent Context

This repository is **`tray-icons-flat`**, a universal Linux system tray icon fixer and converter created by `@locoxella`.
It operates across Linux desktop environments (KDE Plasma, GNOME, XFCE, Cinnamon, etc.) by adapting inconsistent, low-contrast, or opaque system tray icons into flat, monochrome/symbolic, transparent tray icons.

---

## 1. Project Philosophy & Core Invariants

1. **Zero Hardcoded Personal Paths**:
   - Never commit or assume user-specific paths (e.g. `/home/username`).
   - Always expand `~` using `os.path.expanduser("~")` or evaluate environment variables (`$XDG_DATA_HOME`, `$XDG_CONFIG_HOME`, `$HOME`).
2. **Rootless & Non-Destructive by Default**:
   - Operations must execute without `sudo` wherever possible.
   - For user icon themes, install into `~/.local/share/icons/hicolor/`, `~/.local/share/icons/Papirus/`, etc.
   - For file replacements (such as Electron ASAR archives), **always** create a pristine `.stock` backup prior to modifications, enabling seamless reversion with `tray-icons-flat revert`.
3. **No Secrets or Tokens**:
   - Never commit API keys, personal email addresses, machine IDs, or tokens.

---

## 2. Architecture & Fixing Strategies

The core execution engine is located in `tray_icons_flat/recipes_engine.py` and supports three modular strategies:

### A. `icon_theme` (`tray_icons_flat/theme_installer.py`)

- **Use case**: Standard GTK/Qt/DBus StatusNotifierItem applications that resolve tray icons by name from the XDG icon theme lookup mechanism (e.g. `cameractrls`).
- **Mechanism**:
  - Copies SVGs or multi-resolution PNGs (16x16, 22x22, 24x24, 32x32, 48x48, 64x64, 128x128, 512x512) to user-level icon directories:
    - `~/.local/share/icons/hicolor/<size>/<category>/`
    - `~/.local/share/icons/Papirus/...` and `~/.local/share/icons/breeze/...` (if installed)
    - `~/.local/share/flatpak/exports/share/icons/hicolor/...` (for Flatpak apps)
  - Invokes `gtk-update-icon-cache` (if available) without failing if missing.
  - Supports `ColorScheme-Text` (`currentColor`) inside SVG files for dynamic light/dark tray contrast.

### B. `electron_asar` (`tray_icons_flat/asar_patcher.py`)

- **Use case**: Electron applications that bundle tray icons directly inside `resources/app.asar` (e.g. Antigravity IDE, Discord, Slack) rather than querying the host icon theme.
- **Mechanism**:
  - Pure Python binary parser and re-packager for Electron's ASAR format.
  - **Crucial Serialization Detail**: The ASAR format stores metadata using Chromium's `Pickle` class.
    - Header structure (16 bytes): `[uint32 magic=4, uint32 total_size, uint32 size, uint32 header_size]`.
    - `header_size` represents the exact byte length of the UTF-8 JSON header string **without padding**.
    - If `header_size` is not a multiple of 4, `\x00` padding bytes are appended to DWORD-align the payload.
    - `total_size = len(padded_header) + 8`
    - `size = len(padded_header) + 4`
    - Never include the padding length inside `header_size`, otherwise Electron's `archive.cc` parser rejects the trailing null bytes with `Failed to parse header`.

### C. `bwrap_wrapper` (`tray_icons_flat/bwrap_wrapper.py`)

- **Use case**: Closed-source or proprietary binaries with hardcoded absolute filesystem paths (e.g., hardcoded `/opt/asus-rog/.../icon.png`) that run as regular users without system privileges.
- **Mechanism**:
  - Uses Bubblewrap (`bwrap`) to bind-mount the entire system root `/` in read-only/read-write mode while overlaying only the target icon file with `--ro-bind <replacement_icon> <hardcoded_path>`.
  - Wraps the application launcher in `~/.local/share/applications/` transparently.

---

## 3. Recipes Format (`recipes/<id>/recipe.yaml`)

Recipes are modular declarative configurations:

```yaml
id: app-identifier
name: Human Readable App Name
description: Brief explanation of what this fix does
strategy: icon_theme | electron_asar | bwrap_wrapper

# Detection criteria (any matching triggers detection)
detector:
  binary: binary-name-in-path
  desktop: application.desktop
  path: ~/apps/SomeApp/resources/app.asar
  flatpak_id: com.vendor.App

# Strategy-specific fields:
# For icon_theme:
icons:
  - name: tray-icon-name
    source: assets/tray-icon-name.svg

# For electron_asar:
asar_path: ~/apps/SomeApp/resources/app.asar
replacements:
  icon.png: assets/icon_flat.png
  trayTemplate.png: assets/icon_flat.png

# For bwrap_wrapper:
target_binary: /opt/someapp/bin/someapp
desktop_file: someapp.desktop
bind_mounts:
  /opt/someapp/resources/tray.png: assets/flat_tray.png
```

User-defined custom recipes can also be placed in `~/.config/tray-icons-flat/recipes/<id>/` without modifying the core repository.

---

## 4. Maintenance of `.gitignore` (Toptal gitignore.io)

This repository enforces strict clean workspace standards:

- The base `.gitignore` is generated using Toptal's online API for:
  `python,linux,visualstudiocode,pycharm+all,jetbrains+all`
- **Regeneration Procedure**:
  Whenever dependencies, IDE targets, or OS scopes expand, run:

  ```bash
  curl -sL "https://www.toptal.com/developers/gitignore/api/python,linux,visualstudiocode,pycharm+all,jetbrains+all"
  ```

  Keep the automatically generated block at the top, and preserve the bottom section:

  ```gitignore
  # ==============================================================================
  # CUSTOM PROJECT RULES (tray-icons-flat)
  # ==============================================================================
  *.stock
  *.bak
  *.tmp
  *.corrupt_backup
  state.json
  .tray_icons_state.json
  test_scratch/
  scratch/
  ```

---

## 5. Running Tests

Run test suite using system Python 3:

```bash
python3 -m unittest discover tests
```

Ensure all tests pass and no test writes files outside of `tempfile.TemporaryDirectory()`.
