import unittest
from tray_icons_flat.recipes_engine import RecipeEngine, AppStatus


class TestRecipeEngine(unittest.TestCase):

    def test_load_builtin_recipes(self):
        engine = RecipeEngine()
        self.assertIn("asus-rog", engine.recipes)
        self.assertIn("cameractrls", engine.recipes)
        self.assertIn("antigravity", engine.recipes)

    def test_scan_returns_results(self):
        engine = RecipeEngine()
        results = engine.scan()
        ids = [r["id"] for r in results]
        self.assertIn("asus-rog", ids)
        self.assertIn("cameractrls", ids)
        self.assertIn("antigravity", ids)


if __name__ == "__main__":
    unittest.main()
