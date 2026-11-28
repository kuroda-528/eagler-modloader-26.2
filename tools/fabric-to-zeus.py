#!/usr/bin/env python3
"""Export Fabric mod jars as Zeus Lua mod packages.

This is a compatibility exporter, not a Java-to-Lua compiler. It preserves safe
resource assets and Fabric metadata, then creates a Zeus Lua starter package and
a report describing Java entrypoints/mixins that still need a Lua port.
"""
import argparse
import json
import os
import re
import sys
import zipfile
from pathlib import PurePosixPath

MAX_FILES = 4096
MAX_UNPACKED = 64 * 1024 * 1024
MAX_SINGLE_FILE = 16 * 1024 * 1024
ASSET_PREFIX = "assets/"
LICENSE_NAMES = {"LICENSE", "LICENSE.txt", "COPYING", "NOTICE", "NOTICE.txt"}


def safe_id(value):
    value = re.sub(r"[^a-z0-9_.-]+", "-", str(value or "").lower()).strip("-.")
    value = value[:64].rstrip("._-")
    return value or "fabric-mod"


def safe_member(name):
    if "\\" in name or name.startswith("/"):
        return False
    path = PurePosixPath(name)
    return not any(part in ("", ".", "..") for part in path.parts) and not (path.parts and ":" in path.parts[0])


def read_fabric_metadata(jar):
    try:
        raw = jar.read("fabric.mod.json")
        meta = json.loads(raw.decode("utf-8"))
    except KeyError:
        raise ValueError("fabric.mod.json is missing")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("fabric.mod.json is invalid: %s" % exc)
    if not isinstance(meta, dict) or not meta.get("id"):
        raise ValueError("fabric.mod.json must contain a mod id")
    return meta


def inspect_jar(path):
    with zipfile.ZipFile(path) as jar:
        meta = read_fabric_metadata(jar)
        names = set(jar.namelist())
        entrypoints = meta.get("entrypoints", {})
        mixins = meta.get("mixins", [])
        mixin_files = []
        for item in mixins if isinstance(mixins, list) else []:
            name = item if isinstance(item, str) else item.get("config") if isinstance(item, dict) else None
            if name:
                mixin_files.append(name)
        classes = sum(1 for n in names if n.endswith(".class"))
        nested = sum(1 for n in names if n.startswith("META-INF/jars/") and n.endswith(".jar"))
        return meta, {
            "java_class_files": classes,
            "nested_jars": nested,
            "entrypoints": entrypoints if isinstance(entrypoints, dict) else {},
            "mixin_configs": mixin_files,
            "has_access_widener": bool(meta.get("accessWidener") and meta.get("accessWidener") in names),
            "has_assets": any(n.startswith(ASSET_PREFIX) for n in names),
        }


def build_package(jar_path, out_dir):
    with zipfile.ZipFile(jar_path) as jar:
        meta = read_fabric_metadata(jar)
        details = inspect_jar(jar_path)[1]
        mod_id = safe_id(meta["id"])
        name = str(meta.get("name") or meta["id"])[:120]
        version = str(meta.get("version") or "1.0.0")[:64]
        authors = meta.get("authors", [])
        if not isinstance(authors, list):
            authors = [authors] if authors else []
        authors = [str(a.get("name", "")) if isinstance(a, dict) else str(a) for a in authors]
        authors = [a[:100] for a in authors if a][:20]

        selected = []
        total = 0
        for info in jar.infolist():
            n = info.filename
            if info.is_dir() or not safe_member(n):
                continue
            keep = n.startswith(ASSET_PREFIX) or PurePosixPath(n).name in LICENSE_NAMES
            if not keep:
                continue
            if info.file_size > MAX_SINGLE_FILE:
                raise ValueError("file exceeds 16 MiB export limit: %s" % n)
            total += info.file_size
            selected.append(info)
            if len(selected) > MAX_FILES or total > MAX_UNPACKED:
                raise ValueError("assets exceed Zeus package limits (4096 files / 64 MiB unpacked)")

        report = {
            "source_file": os.path.basename(jar_path),
            "source_mod_id": str(meta["id"]),
            "source_name": name,
            "source_version": version,
            "target": "Zeus Lua API 1 / Minecraft 26.2",
            "conversion": "metadata-and-assets-export; Java behavior not translated",
            "java_class_files": details["java_class_files"],
            "nested_jars": details["nested_jars"],
            "fabric_entrypoints": details["entrypoints"],
            "mixin_configs": details["mixin_configs"],
            "access_widener_present": details["has_access_widener"],
            "assets_copied": len([i for i in selected if i.filename.startswith(ASSET_PREFIX)]),
            "assets_unpacked_bytes": total,
            "manual_port_required": bool(details["java_class_files"] or details["entrypoints"] or details["mixin_configs"]),
            "limitations": [
                "Java bytecode, Fabric entrypoints, mixins, access wideners and Java libraries are not executable Lua and are not translated.",
                "Client behavior must be reimplemented using the Zeus Lua API.",
                "Server-side code, native libraries and arbitrary Java dependencies are not included."
            ]
        }

        os.makedirs(out_dir, exist_ok=True)
        package_path = os.path.join(out_dir, mod_id + ".zip")
        lua = (
            "-- name: " + name.replace("\n", " ") + "\n"
            "-- id: " + mod_id + "\n"
            "-- version: " + version.replace("\n", " ") + "\n"
            "-- author: " + ", ".join(authors).replace("\n", " ") + "\n"
            "-- description: Fabric metadata/assets export; Java behavior needs a Lua port.\n"
            "\n"
            "log(\"" + mod_id + ": Zeus package loaded.\")\n"
            "log(\"This package contains exported metadata/assets only; Fabric Java code was not converted.\")\n"
            "log(\"See conversion-report.json in this package for entrypoints, mixins and porting notes.\")\n"
        )
        zeus_meta = {
            "id": mod_id,
            "name": name,
            "version": version,
            "description": "Exported from Fabric. Java behavior requires a Lua port.",
            "authors": authors,
            "main": "main.lua",
            "api": 1,
            "minecraft": ["26.2"]
        }
        with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as out:
            out.writestr("metadata.json", json.dumps(zeus_meta, ensure_ascii=False, indent=2) + "\n")
            out.writestr("main.lua", lua)
            out.writestr("conversion-report.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n")
            for info in selected:
                out.writestr(info.filename, jar.read(info.filename))
        return package_path, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mods_dir")
    parser.add_argument("out_dir")
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    jars = sorted(n for n in os.listdir(args.mods_dir) if n.lower().endswith(".jar"))
    results, errors = [], []
    for filename in jars:
        source = os.path.join(args.mods_dir, filename)
        try:
            package, report = build_package(source, args.out_dir)
            results.append(report)
            print("[zeus] %s -> %s (%d assets; Java port required: %s)" %
                  (filename, os.path.basename(package), report["assets_copied"], report["manual_port_required"]))
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            errors.append("%s: %s" % (filename, exc))
    summary = {
        "target": "Zeus Lua API 1 / Minecraft 26.2",
        "packages_created": len(results),
        "source_jars": len(jars),
        "results": results,
        "errors": errors,
        "notice": "This exporter does not compile or translate Java bytecode into Lua."
    }
    with open(os.path.join(args.out_dir, "conversion-summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
