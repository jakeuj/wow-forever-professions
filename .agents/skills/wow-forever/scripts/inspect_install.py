#!/usr/bin/env python3
"""Read WoW Forever build and addon declarations without changing the install."""

import argparse
import csv
import fnmatch
import io
import json
from pathlib import Path
import re
import sys


TOC_KEYS = {
    "interface": "interface",
    "interface-forever": "interface_forever",
    "title": "title",
    "title-zhtw": "title_zhTW",
    "version": "version",
    "dependencies": "dependencies",
    "requireddeps": "required_deps",
    "optionaldeps": "optional_deps",
    "loadondemand": "load_on_demand",
    "x-curse-project-id": "curse_project_id",
    "x-wago-id": "wago_id",
    "x-wowi-id": "wowi_id",
}


def read_text(path):
    return path.read_text(encoding="utf-8-sig", errors="replace")


def read_flavor(client):
    path = client / ".flavor.info"
    if not path.is_file():
        return None
    lines = [line.strip() for line in read_text(path).splitlines() if line.strip()]
    return lines[1] if len(lines) > 1 else None


def read_builds(root):
    path = root / ".build.info"
    if not path.is_file():
        return None
    reader = csv.reader(io.StringIO(read_text(path)), delimiter="|")
    header = next(reader, [])
    keys = [name.split("!", 1)[0] for name in header]
    result = []
    for values in reader:
        row = dict(zip(keys, values))
        if row.get("Product") == "wowf" and row.get("Active") == "1":
            result.append({
                "product": row["Product"],
                "branch": row.get("Branch"),
                "version": row.get("Version"),
            })
    return result


def read_toc(path):
    metadata = {"file": path.name}
    for line in read_text(path).splitlines():
        match = re.match(r"^\s*##\s*([^:]+):\s*(.*)$", line)
        if match:
            key = TOC_KEYS.get(match.group(1).strip().lower())
            if key:
                metadata[key] = match.group(2).strip()
    return metadata


def inspect_install(root_arg, addon_pattern):
    requested = Path(root_arg).expanduser().resolve()
    if not requested.is_dir():
        raise ValueError(f"Directory does not exist: {requested}")
    if requested.name.lower() == "_forever_":
        root, client = requested.parent, requested
    elif (requested / "_forever_").is_dir():
        root, client = requested, requested / "_forever_"
    else:
        raise ValueError("Expected a WoW install containing _forever_, or _forever_ itself")

    flavor = read_flavor(client)
    if flavor and flavor.lower() != "wowf":
        raise ValueError(f"Client flavor is {flavor!r}, expected 'wowf'")

    warnings = []
    if flavor is None:
        warnings.append("No readable product flavor declaration in .flavor.info")
    builds = read_builds(root)
    if builds is None:
        warnings.append("No .build.info; the installed game version is unverified")
    elif not builds:
        warnings.append("No active wowf build row; the installed game version is unverified")

    addons_path = client / "Interface" / "AddOns"
    addons = []
    if addons_path.is_dir():
        for folder in sorted(addons_path.iterdir(), key=lambda item: item.name.lower()):
            if folder.is_dir() and fnmatch.fnmatchcase(folder.name.lower(), addon_pattern.lower()):
                tocs = sorted(
                    (entry for entry in folder.iterdir()
                     if entry.is_file() and entry.suffix.lower() == ".toc"),
                    key=lambda item: item.name.lower(),
                )
                addons.append({"folder": folder.name, "toc_files": [read_toc(toc) for toc in tocs]})
    else:
        warnings.append("No Interface/AddOns directory")

    return {
        "root": str(root),
        "client": str(client),
        "flavor": flavor,
        "active_forever_builds": builds or [],
        "addon_pattern": addon_pattern,
        "matched_addon_folders": len(addons),
        "addons": addons,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="WoW installation or _forever_ directory")
    parser.add_argument("--addon", default="*", help="Case-insensitive addon folder glob (default: *)")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        result = inspect_install(args.root, args.addon)
    except (OSError, ValueError) as error:
        parser.exit(2, f"Error: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
