import tempfile
import unittest
from pathlib import Path

from app_registry import AndroidApp, AppRegistry, default_registry


class AppRegistryTests(unittest.TestCase):
    def test_default_registry_contains_known_apps(self):
        names = [app.name for app in default_registry().apps()]
        self.assertEqual(names, ["bijli", "cast"])

    def test_duplicate_package_rejected(self):
        registry = AppRegistry()
        registry.register(AndroidApp("one", "com.example.same", "apps/one", 21, 35, "1.0", 1))
        with self.assertRaises(ValueError):
            registry.register(AndroidApp("two", "com.example.same", "apps/two", 21, 35, "1.0", 1))

    def test_duplicate_name_case_insensitive(self):
        registry = AppRegistry()
        registry.register(AndroidApp("Demo", "com.example.demo", "apps/demo", 21, 35, "1.0", 1))
        with self.assertRaises(ValueError):
            registry.register(AndroidApp("demo", "com.example.demo2", "apps/demo2", 21, 35, "1.0", 1))

    def test_target_sdk_must_not_be_below_min_sdk(self):
        with self.assertRaises(ValueError):
            AppRegistry([AndroidApp("bad", "com.example.bad", "apps/bad", 30, 29, "1.0", 1)])

    def test_manifest_is_deterministic(self):
        registry = default_registry()
        self.assertEqual(registry.release_manifest(), registry.release_manifest())

    def test_manifest_hash_changes_with_version(self):
        first = AppRegistry([AndroidApp("one", "com.example.one", "apps/one", 21, 35, "1.0", 1)])
        second = AppRegistry([AndroidApp("one", "com.example.one", "apps/one", 21, 35, "1.1", 2)])
        self.assertNotEqual(first.release_manifest()["sha256"], second.release_manifest()["sha256"])

    def test_checkout_validation_detects_missing_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = default_registry().validate_checkout(tmp)
        self.assertTrue(any("missing module" in error for error in errors))

    def test_checkout_validation_accepts_complete_minimal_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module = root / "apps/demo"
            (module / "src/main").mkdir(parents=True)
            (module / "play/listing/en-US").mkdir(parents=True)
            (module / "build.gradle.kts").write_text("", encoding="utf-8")
            (module / "src/main/AndroidManifest.xml").write_text("<manifest/>", encoding="utf-8")
            (module / "play/listing/en-US/title.txt").write_text("Demo", encoding="utf-8")
            registry = AppRegistry([AndroidApp("demo", "com.example.demo", "apps/demo", 21, 35, "1.0", 1)])
            self.assertEqual(registry.validate_checkout(root), [])


if __name__ == "__main__":
    unittest.main()
