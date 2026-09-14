"""
Main CLI entry point for tray-icons-flat.
"""

import sys
import os
import argparse
from typing import Optional

from .recipes_engine import RecipeEngine, AppStatus
from .converter import IconConverter
from .service import ServiceManager


# Terminal ANSI styling
class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    DIM = "\033[90m"


def print_status(scan_results):
    print(f"\n{Color.BOLD}{Color.CYAN}=== Linux Tray Icons Scanner ==={Color.RESET}\n")
    print(f"{'Application':<28} {'ID':<16} {'Strategy':<16} {'Status':<14}")
    print("-" * 76)

    for item in scan_results:
        status = item["status"]
        if status == AppStatus.FIXED.value:
            status_str = f"{Color.GREEN}✓ Fixed{Color.RESET}"
        elif status == AppStatus.BROKEN.value:
            status_str = f"{Color.YELLOW}⚠ Broken/Stock{Color.RESET}"
        else:
            status_str = f"{Color.DIM}Not Installed{Color.RESET}"

        print(f"{item['name']:<28} {item['id']:<16} {item['strategy']:<16} {status_str}")

    print("\n" + Color.DIM + "Run 'tray-icons-flat fix --all' to apply all fixes." + Color.RESET + "\n")


def cmd_scan(args):
    engine = RecipeEngine()
    results = engine.scan()
    print_status(results)


def cmd_fix(args):
    engine = RecipeEngine()
    app_id = args.app_id if not args.all else None

    if not args.all and not app_id:
        print(f"{Color.RED}Error: specify an app ID or pass --all{Color.RESET}")
        sys.exit(1)

    print(f"\n{Color.CYAN}Applying flat tray icon fixes...{Color.RESET}\n")
    results = engine.fix(app_id)
    for a_id, ok, msg in results:
        symbol = f"{Color.GREEN}✓{Color.RESET}" if ok else f"{Color.RED}✗{Color.RESET}"
        print(f"  [{symbol}] {a_id:<16} : {msg}")
    print("\n" + Color.GREEN + "Done! Icons refreshed. (Note: Running applications may need to be restarted to reload the new icon)." + Color.RESET + "\n")


def cmd_revert(args):
    engine = RecipeEngine()
    app_id = args.app_id if not args.all else None

    if not args.all and not app_id:
        print(f"{Color.RED}Error: specify an app ID or pass --all{Color.RESET}")
        sys.exit(1)

    print(f"\n{Color.CYAN}Reverting tray icon fixes to stock...{Color.RESET}\n")
    results = engine.revert(app_id)
    for a_id, ok, msg in results:
        symbol = f"{Color.GREEN}✓{Color.RESET}" if ok else f"{Color.RED}✗{Color.RESET}"
        print(f"  [{symbol}] {a_id:<16} : {msg}")
    print("\n" + Color.YELLOW + "Reverted to stock icons." + Color.RESET + "\n")


def cmd_convert(args):
    print(f"\n{Color.CYAN}Converting image {args.input} -> {args.output}...{Color.RESET}")
    try:
        IconConverter.convert_file(
            input_path=args.input,
            output_path=args.output,
            size=args.size,
            padding=args.padding,
            strip_bg=not args.no_strip_bg,
            preserve_accents=not args.no_accents,
            foreground_hex=args.color
        )
        print(f"{Color.GREEN}✓ Saved converted flat icon to: {args.output}{Color.RESET}\n")
    except Exception as e:
        print(f"{Color.RED}Error during conversion: {e}{Color.RESET}")
        sys.exit(1)


def cmd_add(args):
    """Wizard to create a new recipe."""
    print(f"\n{Color.BOLD}{Color.CYAN}=== Add New App Recipe Wizard ==={Color.RESET}\n")
    app_id = args.app_id or input("Application ID (e.g., myapp): ").strip()
    if not app_id:
        print("App ID is required.")
        return

    name = input(f"Application Name [{app_id}]: ").strip() or app_id
    description = input("Description: ").strip() or f"Flat tray icon fix for {name}"
    
    print("\nStrategy:")
    print(" 1) icon_theme (status notifier item or standard XDG icon)")
    print(" 2) electron_asar (Electron application asar package)")
    choice = input("Select strategy [1]: ").strip() or "1"
    strategy = "electron_asar" if choice == "2" else "icon_theme"

    recipe_dir = os.path.join(os.path.expanduser("~/.config/tray-icons-flat/recipes"), app_id)
    os.makedirs(os.path.join(recipe_dir, "assets"), exist_ok=True)

    config = {
        "id": app_id,
        "name": name,
        "description": description,
        "strategy": strategy,
        "detector": {}
    }

    if strategy == "icon_theme":
        icon_name = input("Tray icon name used by app (e.g. myapp-tray): ").strip()
        detector_bin = input("Binary executable name (leave blank if not applicable): ").strip()
        detector_flatpak = input("Flatpak ID (leave blank if not applicable): ").strip()
        if detector_bin:
            config["detector"]["binary"] = detector_bin
        if detector_flatpak:
            config["detector"]["flatpak_id"] = detector_flatpak

        config["icons"] = [{
            "name": icon_name,
            "source": f"assets/{icon_name}.svg"
        }]
    else:
        asar_path = input("Path to app.asar (e.g. ~/apps/MyApp/resources/app.asar): ").strip()
        config["detector"]["path"] = asar_path
        config["asar_path"] = asar_path
        config["replacements"] = {
            "icon.png": "assets/icon_flat.png"
        }

    import yaml
    recipe_path = os.path.join(recipe_dir, "recipe.yaml")
    with open(recipe_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, sort_keys=False)

    print(f"\n{Color.GREEN}✓ Recipe generated at: {recipe_path}{Color.RESET}")
    print(f"Place the corresponding flat asset in: {os.path.join(recipe_dir, 'assets')}\n")


def cmd_service(args):
    action = args.action
    if action == "install":
        print(f"\n{Color.CYAN}Installing and enabling systemd user service & autostart...{Color.RESET}")
        res = ServiceManager.install()
        print(f"  {Color.GREEN}✓ Systemd unit:{Color.RESET} {res['systemd_service']}")
        print(f"  {Color.GREEN}✓ Autostart entry:{Color.RESET} {res['autostart_file']}")
        if res['systemd_active']:
            print(f"  {Color.GREEN}✓ Systemd service is active.{Color.RESET}")
        print()
    elif action == "uninstall":
        print(f"\n{Color.CYAN}Removing service and autostart...{Color.RESET}")
        res = ServiceManager.uninstall()
        print(f"  Systemd removed: {res['removed_systemd']}")
        print(f"  Autostart removed: {res['removed_autostart']}\n")
    elif action == "status":
        info = ServiceManager.status()
        print(f"\n{Color.BOLD}{Color.CYAN}Service Status:{Color.RESET}")
        print(f"  Installed: {info['installed']}")
        print(f"  Systemd Unit: {info['systemd_file']}")
        print(f"  Autostart: {info['autostart_file']}")
        print(f"  Active: {info['active']}\n")


def main():
    parser = argparse.ArgumentParser(
        prog="tray-icons-flat",
        description="Universal Linux tool to detect, adapt, and fix broken system tray icons."
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # scan
    sub_scan = subparsers.add_parser("scan", help="Scan system for installed apps and report tray icon status")
    sub_scan.set_defaults(func=cmd_scan)

    # fix
    sub_fix = subparsers.add_parser("fix", help="Apply flat tray icon fixes")
    sub_fix.add_argument("app_id", nargs="?", help="Specific application ID to fix")
    sub_fix.add_argument("--all", action="store_true", help="Fix all detected broken applications")
    sub_fix.set_defaults(func=cmd_fix)

    # revert
    sub_rev = subparsers.add_parser("revert", help="Revert applications to their stock tray icons")
    sub_rev.add_argument("app_id", nargs="?", help="Specific application ID to revert")
    sub_rev.add_argument("--all", action="store_true", help="Revert all applications to stock")
    sub_rev.set_defaults(func=cmd_revert)

    # convert
    sub_conv = subparsers.add_parser("convert", help="Convert any icon into a flat/monochrome transparent tray icon")
    sub_conv.add_argument("input", help="Path to input image (PNG/SVG/JPEG)")
    sub_conv.add_argument("-o", "--output", required=True, help="Output image file path")
    sub_conv.add_argument("--size", type=int, default=22, help="Canvas size in px (default: 22)")
    sub_conv.add_argument("--padding", type=int, default=2, help="Padding in px (default: 2)")
    sub_conv.add_argument("--no-strip-bg", action="store_true", help="Do not attempt to remove solid background")
    sub_conv.add_argument("--no-accents", action="store_true", help="Do not preserve saturated accent/badge dots")
    sub_conv.add_argument("--color", default="#dfdfdf", help="Foreground monochrome hex color (default: #dfdfdf)")
    sub_conv.set_defaults(func=cmd_convert)

    # add
    sub_add = subparsers.add_parser("add", help="Wizard to generate a new app recipe")
    sub_add.add_argument("app_id", nargs="?", help="App ID for the new recipe")
    sub_add.set_defaults(func=cmd_add)

    # service
    sub_serv = subparsers.add_parser("service", help="Manage systemd user service and autostart")
    sub_serv.add_argument("action", choices=["install", "uninstall", "status"], help="Action to perform")
    sub_serv.set_defaults(func=cmd_service)

    args = parser.parse_args()

    if not args.command:
        # Default to scan
        cmd_scan(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
