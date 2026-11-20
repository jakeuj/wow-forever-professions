#!/usr/bin/env python3
"""List the bags, banks and mail Syndicator recorded for each WoW Forever character.

Syndicator writes SYNDICATOR_DATA to
_forever_/WTF/Account/<account>/SavedVariables/Syndicator.lua only on /reload or
logout. A character appears after it logs in once with Syndicator loaded; its bank
and mail appear after it opens them. Read-only: never writes into the game folder.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auctionator_prices import LuaReader  # noqa: E402

PARTS = ("bags", "bankTabs", "bank", "mail")
LINK_NAME = re.compile(r"\[(.*?)\]")


def utf8(text):
    """LuaReader keeps one char per byte (file read as latin-1); restore UTF-8."""
    return text.encode("latin-1").decode("utf-8", "replace")


def find_saved_files(root):
    root = Path(root)
    forever = root if root.name == "_forever_" else root / "_forever_"
    return sorted(forever.glob("WTF/Account/*/SavedVariables/Syndicator.lua"),
                  key=lambda p: p.stat().st_mtime, reverse=True)


def load_data(path):
    text = path.read_bytes().decode("latin-1")
    m = re.search(r"^SYNDICATOR_DATA\s*=\s*", text, re.M)
    if not m:
        sys.exit("SYNDICATOR_DATA not in the file yet; /reload or log out first")
    reader = LuaReader(text)
    reader.i = m.end()
    return reader.value()


def ordered(value):
    """Lua arrays come back as {1: ..., 2: ...}; return the values in order."""
    if isinstance(value, dict):
        return [value[k] for k in sorted(value, key=lambda k: k if isinstance(k, int) else 0)]
    return value or []


def slots(part):
    """Every item slot in a part: a list of bags, of bank tabs ({slots = ...}) or of mail."""
    for container in ordered(part):
        if isinstance(container, dict) and "slots" in container:
            container = container["slots"]
        if isinstance(container, dict) and "itemID" in container:
            yield container  # a flat list of items (mail)
            continue
        yield from ordered(container)


def summarise(character):
    out = {}
    for part in PARTS:
        counts, names, used, total = Counter(), {}, 0, 0
        for slot in slots(character.get(part)):
            total += 1
            if not isinstance(slot, dict) or not slot.get("itemID"):
                continue
            used += 1
            item = slot["itemID"]
            counts[item] += slot.get("itemCount", 1)
            link = LINK_NAME.search(utf8(slot.get("itemLink", "")))
            names[item] = (link.group(1) if link else str(item), slot.get("quality"))
        if total or counts:
            out[part] = {"used": used, "slots": total, "items": [
                {"id": i, "name": names[i][0], "quality": names[i][1], "count": c}
                for i, c in sorted(counts.items(), key=lambda t: (-(names[t[0]][1] or 0), names[t[0]][0]))]}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default="/Applications/World of Warcraft", help="WoW install root or its _forever_ folder")
    parser.add_argument("--file", type=Path, help="a specific Syndicator.lua (overrides --root)")
    parser.add_argument("--character", help="only characters whose 'Name Surname-Realm' key contains this")
    parser.add_argument("--item", help="only items whose name contains this")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    files = [args.file] if args.file else find_saved_files(args.root)
    if not files or not files[0].is_file():
        sys.exit("Syndicator.lua not found; check --root or pass --file")
    data = load_data(files[0])

    result = []
    for key, character in ordered_items(data.get("Characters", {})):
        name = utf8(key)
        if args.character and args.character not in name:
            continue
        details = character.get("details", {})
        parts = summarise(character)
        if args.item:
            for part in parts.values():
                part["items"] = [i for i in part["items"] if args.item in i["name"]]
        result.append({"character": name, "class": details.get("className"),
                       "money": character.get("money", 0), "parts": parts})

    if args.json:
        json.dump({"file": str(files[0]), "characters": result}, sys.stdout, ensure_ascii=False, indent=1)
        return
    print(f"# {files[0]}")
    for c in result:
        print(f"== {c['character']} {c['class']} {c['money'] / 10000:.2f}g")
        for part, info in c["parts"].items():
            if args.item and not info["items"]:
                continue
            print(f"-- {part}: {info['used']}/{info['slots']} slots used")
            for i in info["items"]:
                print(f"   q{i['quality']} {i['name']} x{i['count']} ({i['id']})")


def ordered_items(table):
    return sorted(table.items(), key=lambda kv: str(kv[0]))


if __name__ == "__main__":
    main()
