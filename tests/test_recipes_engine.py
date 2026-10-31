import os
import json
import tempfile
import unittest
from tray_icons_flat.recipes_engine import RecipeEngine, AppStatus


class TestRecipeEngine(unittest.TestCase):

    def test_load_builtin_recipes(self):
        engine = RecipeEngine()
        self.assertIn("asus-rog", engine.recipes)
        self.assertIn("cameractrls", engine.recipes)
        self.assertIn("antigravity", engine.recipes)
        self.assertIn("zoom", engine.recipes)

    def test_scan_returns_results(self):
        engine = RecipeEngine()
        results = engine.scan()
        ids = [r["id"] for r in results]
        self.assertIn("asus-rog", ids)
        self.assertIn("cameractrls", ids)
        self.assertIn("antigravity", ids)
        self.assertIn("zoom", ids)

    def test_atomic_state_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = RecipeEngine()
            engine.STATE_PATH = os.path.join(tmp_dir, "test_state.json")

            data = {"apps": {"test": {"status": "FIXED"}}}
            engine.save_state(data)

            self.assertTrue(os.path.exists(engine.STATE_PATH))
            # Verify temporary file was cleanly replaced
            self.assertFalse(os.path.exists(engine.STATE_PATH + ".tmp"))

            loaded = engine.load_state()
            self.assertEqual(loaded, data)

    def test_dry_run_fix_and_revert(self):
        engine = RecipeEngine()
        fix_results = engine.fix(dry_run=True)
        self.assertIsInstance(fix_results, list)
        for _, ok, msg in fix_results:
            self.assertTrue(ok)
            self.assertIn("Dry-run", msg)

        rev_results = engine.revert(dry_run=True)
        self.assertIsInstance(rev_results, list)
        for _, ok, msg in rev_results:
            self.assertTrue(ok)
            self.assertIn("Dry-run", msg)


if __name__ == "__main__":
    unittest.main()
