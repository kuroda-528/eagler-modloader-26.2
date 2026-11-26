"""Unit tests for the lightweight Fabric mod scanner (standard library only)."""
import importlib.util
import os
import struct
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCANNER = os.path.abspath(os.path.join(HERE, "..", "scan-mods.py"))
SPEC = importlib.util.spec_from_file_location("scan_mods", SCANNER)
scan_mods = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scan_mods)


class ClassReferenceTests(unittest.TestCase):
    def test_reads_class_reference_from_constant_pool(self):
        name = b"java/lang/String"
        constant_pool = b"\x01" + struct.pack(">H", len(name)) + name
        constant_pool += b"\x07" + struct.pack(">H", 1)
        class_file = b"\xca\xfe\xba\xbe" + struct.pack(">HHH", 0, 52, 3) + constant_pool
        self.assertEqual(scan_mods.class_refs(class_file), {"java/lang/String"})

    def test_ignores_truncated_constant_pool(self):
        class_file = b"\xca\xfe\xba\xbe" + struct.pack(">HHH", 0, 52, 2) + b"\x01\x00"
        self.assertEqual(scan_mods.class_refs(class_file), set())

    def test_ignores_non_class_files(self):
        self.assertEqual(scan_mods.class_refs(b"not a class"), set())


class MetadataTests(unittest.TestCase):
    def test_detects_fabric_metadata(self):
        import io
        import zipfile

        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as jar:
            jar.writestr("fabric.mod.json", '{"id":"example","version":"1.0.0"}')
        with zipfile.ZipFile(io.BytesIO(data.getvalue())) as jar:
            self.assertEqual(scan_mods.loader_kind(jar), "fabric")

    def test_detects_non_fabric_metadata(self):
        import io
        import zipfile

        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as jar:
            jar.writestr("META-INF/mods.toml", 'modLoader="javafml"')
        with zipfile.ZipFile(io.BytesIO(data.getvalue())) as jar:
            self.assertEqual(scan_mods.loader_kind(jar), "Forge")


if __await__:
    pass


if __name__ == "__main__":
    unittest.main()
