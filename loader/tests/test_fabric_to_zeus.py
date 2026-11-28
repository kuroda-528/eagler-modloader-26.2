"""Tests for the Fabric-to-Zeus compatibility exporter."""
import importlib.util
import json
import os
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.abspath(os.path.join(HERE, "..", "..", "tools", "fabric-to-zeus.py"))
SPEC = importlib.util.spec_from_file_location("fabric_to_zeus", PATH)
converter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(converter)


class ConverterTests(unittest.TestCase):
    def make_jar(self, root, entries):
        path = os.path.join(root, "sample.jar")
        with zipfile.ZipFile(path, "w") as jar:
            jar.writestr("fabric.mod.json", json.dumps({
                "id": "sample_mod", "name": "Sample Mod", "version": "2.0",
                "authors": ["Tester"], "entrypoints": {"client": ["sample.Client"]},
                "mixins": ["sample.mixins.json"]
            }))
            for name, data in entries.items():
                jar.writestr(name, data)
        return path

    def test_creates_valid_zeus_package_and_preserves_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self.make_jar(tmp, {
                "assets/sample_mod/lang/en_us.json": '{"hello":"world"}',
                "sample/Client.class": b"not translated bytecode",
                "sample.mixins.json": '{"required":true}'
            })
            out = os.path.join(tmp, "out")
            package, report = converter.build_package(jar, out)
            with zipfile.ZipFile(package) as z:
                meta = json.loads(z.read("metadata.json"))
                self.assertEqual(meta["main"], "main.lua")
                self.assertEqual(meta["api"], 1)
                self.assertIn("assets/sample_mod/lang/en_us.json", z.namelist())
                self.assertIn("conversion-report.json", z.namelist())
                self.assertIn("log(", z.read("main.lua").decode())
            self.assertTrue(report["manual_port_required"])
            self.assertEqual(report["assets_copied"], 1)

    def test_rejects_zip_path_traversal_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = self.make_jar(tmp, {"assets/../../outside.txt": "bad"})
            package, _ = converter.build_package(jar, os.path.join(tmp, "out"))
            with zipfile.ZipFile(package) as z:
                self.assertNotIn("assets/../../outside.txt", z.namelist())

    def test_rejects_missing_fabric_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            jar = os.path.join(tmp, "bad.jar")
            with zipfile.ZipFile(jar, "w") as z:
                z.writestr("readme.txt", "no mod")
            with self.assertRaises(ValueError):
                converter.build_package(jar, os.path.join(tmp, "out"))

    def test_safe_id(self):
        self.assertEqual(converter.safe_id("My Mod!"), "my-mod")


if __name__ == "__main__":
    unittest.main()
