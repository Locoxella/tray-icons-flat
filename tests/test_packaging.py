import os
import unittest
import tempfile
import subprocess
import sys


class TestPackagingAndRecipes(unittest.TestCase):

    def test_recipe_assets_exist(self):
        """Verifies that all builtin recipes define existing assets."""
        from tray_icons_flat.recipes_engine import RecipeEngine
        engine = RecipeEngine()
        self.assertGreater(len(engine.recipes), 0)

        for recipe_id, recipe in engine.recipes.items():
            if recipe.strategy == "icon_theme":
                for icon in recipe.icons:
                    src = recipe.resolve_path(icon["source"])
                    self.assertTrue(os.path.exists(src), f"Missing icon asset {src} in recipe {recipe_id}")
            elif recipe.strategy == "electron_asar":
                for target, src_rel in recipe.config.get("replacements", {}).items():
                    src = recipe.resolve_path(src_rel)
                    self.assertTrue(os.path.exists(src), f"Missing replacement asset {src} in recipe {recipe_id}")

    def test_manifest_and_metadata(self):
        """Verifies MANIFEST.in and pyproject.toml exist and specify recipes inclusion."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manifest = os.path.join(repo_root, "MANIFEST.in")
        pyproject = os.path.join(repo_root, "pyproject.toml")

        self.assertTrue(os.path.isfile(manifest))
        with open(manifest, "r", encoding="utf-8") as f:
            manifest_content = f.read()
        self.assertIn("recursive-include recipes *", manifest_content)

        self.assertTrue(os.path.isfile(pyproject))
        with open(pyproject, "r", encoding="utf-8") as f:
            pyproject_content = f.read()
        self.assertIn("tray-icons-flat", pyproject_content)


if __name__ == "__main__":
    unittest.main()
