# Recipe Authoring & Contribution Guide 🧩

This guide walks you through creating custom recipes to fix tray icons for Linux applications and submitting them upstream to `tray-icons-flat`.

---

## 📑 Contents

- [Overview & Recipe Structure](#overview--recipe-structure)
- [Choosing the Right Strategy](#choosing-the-right-strategy)
  - [1. `icon_theme`](#1-icon_theme)
  - [2. `electron_asar`](#2-electron_asar)
  - [3. `bwrap_wrapper`](#3-bwrap_wrapper)
- [Step-by-Step: Adding a Recipe](#step-by-step-adding-a-recipe)
- [Testing & Validating Locally](#testing--validating-locally)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Best Practices Checklist](#best-practices-checklist)

---

## <a id="overview--recipe-structure"></a>Overview & Recipe Structure

A recipe defines how `tray-icons-flat` detects an application and replaces or redirects its tray icon.

Every recipe lives in its own directory:

```text
recipes/<app-id>/
├── recipe.yaml        # Recipe definition and metadata
└── assets/            # Replacement icon files (SVG or PNG)
    ├── icon_flat.png
    └── tray-icon.svg
```

Alternatively, user-local custom recipes can be placed in `~/.config/tray-icons-flat/recipes/<app-id>/` without modifying the package.

---

## <a id="choosing-the-right-strategy"></a>Choosing the Right Strategy

`tray-icons-flat` provides three modular fixing strategies:

### 1. `icon_theme`

- **When to use:** Native Linux applications (GTK, Qt, DBus `StatusNotifierItem`) that load tray icons through standard XDG icon theme lookups.
- **Example app:** Camera Controls (`cameractrls`).
- **How it works:** Installs flat monochrome icons into user-level icon theme directories (`~/.local/share/icons/hicolor/`, Papirus, Breeze) without requiring root privileges.
- **Example `recipe.yaml`:**

  ```yaml
  id: cameractrls
  name: Camera Controls
  description: Replaces the dark square lens icon with a clean monochrome camera aperture.
  strategy: icon_theme
  detector:
    flatpak_id: hu.irl.cameractrls
    desktop: hu.irl.cameractrls.desktop
  icons:
    - name: hu.irl.cameractrls
      source: assets/hu.irl.cameractrls.svg
  ```

> [!TIP]
> SVGs using `style="fill: currentColor;"` or `class="ColorScheme-Text"` automatically adjust their contrast based on whether your desktop panel is light or dark.

---

### 2. `electron_asar`

- **When to use:** Electron apps that pack their tray icons directly inside `resources/app.asar` rather than querying the desktop icon theme.
- **Example apps:** Antigravity IDE, Slack, Discord, Element.
- **How it works:** Directly inspects and rewrites the ASAR binary package using pure Python, creating an untouched `.stock` backup before replacing the specified asset files.
- **Example `recipe.yaml`:**

  ```yaml
  id: antigravity
  name: Antigravity IDE
  description: Replaces the opaque white rainbow box with a flat monochrome transparent waveform.
  strategy: electron_asar
  detector:
    path: ~/apps/Antigravity/resources/app.asar
  asar_path: ~/apps/Antigravity/resources/app.asar
  replacements:
    icon.png: assets/icon_flat.png
    trayTemplate.png: assets/icon_flat.png
    trayTemplate@2x.png: assets/icon_flat@2x.png
  ```

---

### 3. `bwrap_wrapper`

- **When to use:** Proprietary or closed-source binaries that hardcode absolute system paths (e.g. `/opt/.../tray.png` or `/usr/share/...`) and cannot be recompiled.
- **Example app:** ASUS ROG Control Center (`asus-rog`).
- **How it works:** Creates a lightweight user wrapper script using Bubblewrap (`bwrap`) to bind-mount the system root while overlaying only the hardcoded icon path with the flat version. No `sudo` needed.
- **Example `recipe.yaml`:**

  ```yaml
  id: asus-rog
  name: ASUS ROG Control Center
  description: Overrides hardcoded ROG tray notification icons with flat transparent symbolic icons.
  strategy: bwrap_wrapper
  detector:
    binary: rog-control-center
    desktop: rog-control-center.desktop
  target_binary: /usr/bin/rog-control-center
  wrapper_bin: ~/.local/bin/rog-control-center
  desktop_icon: rog-control-center
  desktop_files:
    - ~/.config/autostart/rog-control-center.desktop
    - ~/.local/share/applications/rog-control-center.desktop
  binds:
    /usr/share/icons/hicolor/512x512/apps/asus_notif_red.png: assets/asus_notif_flat.png
  ```

---

## <a id="step-by-step-adding-a-recipe"></a>Step-by-Step: Adding a Recipe

### Option A: Using the Interactive CLI Wizard

The easiest way to scaffold a new recipe is using the built-in wizard:

```bash
tray-icons-flat add
```

Follow the prompts to enter the application name, detection rules, and chosen strategy.

### Option B: Creating Manually

1. Create a folder named after your application's kebab-case identifier:

   ```bash
   mkdir -p recipes/<my-app>/assets
   ```

2. Convert or generate your transparent, flat monochrome icon:

   ```bash
   tray-icons-flat convert /path/to/original-icon.png -o recipes/<my-app>/assets/tray_flat.png
   ```

3. Create `recipes/<my-app>/recipe.yaml` matching one of the strategies described above.

---

## <a id="testing--validating-locally"></a>Testing & Validating Locally

Always test your recipe before opening a Pull Request:

1. **Verify Detection:**

   ```bash
   python3 -m tray_icons_flat.cli scan
   ```

   Ensure your application appears in the table with its correct ID and strategy.

2. **Test Fix Application:**

   ```bash
   python3 -m tray_icons_flat.cli fix <my-app>
   ```

   Restart the target application or verify that the tray icon updates to the flat version.

3. **Test Revert:**

   ```bash
   python3 -m tray_icons_flat.cli revert <my-app>
   ```

   Ensure the original state is restored cleanly.

4. **Run the Test Suite & Linters:**

   ```bash
   python3 -m unittest discover tests
   yamllint -d "{extends: relaxed, rules: {line-length: disable}}" recipes/
   ```

---

## <a id="submitting-a-pull-request"></a>Submitting a Pull Request

We follow a strict Pull Request workflow: **no direct pushes to `main`**.

1. Fork the repository on GitHub: `https://github.com/Locoxella/tray-icons-flat`
2. Create a feature branch:

   ```bash
   git checkout -b recipe/<my-app>
   ```

3. Commit your recipe and asset files:

   ```bash
   git add recipes/<my-app>/
   git commit -m "feat(recipe): add flat tray icon recipe for <my-app>"
   ```

4. Push your branch to your fork and open a Pull Request against `main`.
5. GitHub Actions will automatically validate your YAML formatting, run the test suite, and check for clean packaging.

---

## <a id="best-practices-checklist"></a>Best Practices Checklist

Before submitting your PR, verify:

- [ ] **No hardcoded personal paths:** Paths never contain `/home/username` — use `~` or standard XDG variables.
- [ ] **Transparent backgrounds:** Icon assets have clean transparent backgrounds and high contrast against dark and light panels.
- [ ] **Small asset footprint:** SVGs are optimized or PNGs are reasonably sized.
- [ ] **Non-destructive:** Changes can be reversed cleanly with `tray-icons-flat revert <my-app>`.
- [ ] **Valid YAML:** `recipe.yaml` contains all required fields (`id`, `name`, `description`, `strategy`, `detector`).
