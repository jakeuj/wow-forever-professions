#!/usr/bin/env python3
"""Read Auctionator's saved price scans for WoW Forever.

Auctionator writes AUCTIONATOR_PRICE_DATABASE to
_forever_/WTF/Account/<account>/SavedVariables/Auctionator.lua only on /reload or
logout. With C_EncodingUtil the current realm is stored as a CBOR string. Each
item key maps to {m: last seen lowest buyout, l/h: lowest and highest daily low,
a: most seen available}, days counted from 2020-01-01 local time. Item names come
from wowamobi.com's market list. Read-only: never writes into the game folder.
"""

import argparse
import datetime
import html
import json
from pathlib import Path
import re
import struct
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import amobi_recipe_value as av  # noqa: E402

DAY0 = datetime.date(2020, 1, 1)
ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "f": "\f", "v": "\v",
           "\\": "\\", '"': '"', "'": "'", "\n": "\n"}


class LuaReader:
    """Parses the table literals Blizzard writes into SavedVariables files."""

    def __init__(self, text):
        self.s, self.i = text, 0

    def skip(self):
        while self.i < len(self.s):
            if self.s[self.i].isspace() or self.s[self.i] in ",;":
                self.i += 1
            elif self.s.startswith("--", self.i):
                end = self.s.find("\n", self.i)
                self.i = len(self.s) if end < 0 else end + 1
            else:
                return

    def value(self):
        self.skip()
        c = self.s[self.i]
        if c == "{":
            return self.table()
        if c in "\"'":
            return self.string()
        m = re.compile(r"-?(?:0x[0-9a-fA-F]+|\d+\.?\d*(?:[eE][-+]?\d+)?)|true|false|nil").match(self.s, self.i)
        if not m:
            raise ValueError(f"unexpected {self.s[self.i:self.i + 20]!r}")
        self.i = m.end()
        word = m.group()
        if word in ("true", "false"):
            return word == "true"
        if word == "nil":
            return None
        return int(word, 16) if "x" in word else (float(word) if any(ch in word for ch in ".eE") else int(word))

    def string(self):
        quote, out = self.s[self.i], []
        self.i += 1
        while self.s[self.i] != quote:
            c = self.s[self.i]
            if c != "\\":
                out.append(c)
                self.i += 1
                continue
            nxt = self.s[self.i + 1]
            if nxt.isdigit():
                digits = re.compile(r"\d{1,3}").match(self.s, self.i + 1).group()
                out.append(chr(int(digits)))
                self.i += 1 + len(digits)
            elif nxt == "x":
                out.append(chr(int(self.s[self.i + 2:self.i + 4], 16)))
                self.i += 4
            else:
                out.append(ESCAPES.get(nxt, nxt))
                self.i += 2
        self.i += 1
        return "".join(out)  # one char per byte (file read as latin-1)

    def table(self):
        self.i += 1
        result, n = {}, 1
        while True:
            self.skip()
            if self.s[self.i] == "}":
                self.i += 1
                return result
            if self.s[self.i] == "[":
                self.i += 1
                key = self.value()
                self.expect("]")
                self.expect("=")
                result[key] = self.value()
                continue
            m = re.compile(r"([A-Za-z_]\w*)\s*=").match(self.s, self.i)
            if m:
                self.i = m.end()
                result[m.group(1)] = self.value()
            else:
                result[n] = self.value()
                n += 1

    def expect(self, char):
        while self.s[self.i].isspace():
            self.i += 1
        if self.s[self.i] != char:
            raise ValueError(f"expected {char!r} at {self.s[self.i:self.i + 20]!r}")
        self.i += 1


def cbor(data, i=0):
    """Minimal CBOR decoder: returns (value, next index)."""
    head = data[i]
    major, info = head >> 5, head & 31
    i += 1
    if major == 7:
        if info == 20: return False, i
        if info == 21: return True, i
        if info in (22, 23): return None, i
        if info == 25:
            return struct.unpack(">e", data[i:i + 2])[0], i + 2
        if info == 26:
            return struct.unpack(">f", data[i:i + 4])[0], i + 4
        if info == 27:
            return struct.unpack(">d", data[i:i + 8])[0], i + 8
        raise ValueError(f"unsupported simple value {info}")
    if info < 24:
        arg = info
    elif info in (24, 25, 26, 27):
        size = 1 << (info - 24)
        arg = int.from_bytes(data[i:i + size], "big")
        i += size
    elif info == 31:
        arg = None  # indefinite length
    else:
        raise ValueError(f"bad additional info {info}")
    if major == 0: return arg, i
    if major == 1: return -1 - arg, i
    if major in (2, 3):
        if arg is None:
            chunks = []
            while data[i] != 0xFF:
                chunk, i = cbor(data, i)
                chunks.append(chunk)
            return "".join(chunks), i + 1
        # C_EncodingUtil writes Lua strings as byte strings; they are UTF-8 text.
        return bytes(data[i:i + arg]).decode("utf-8", "replace"), i + arg
    if major == 4:
        out = []
        while (len(out) < arg) if arg is not None else data[i] != 0xFF:
            item, i = cbor(data, i)
            out.append(item)
        return out, (i if arg is not None else i + 1)
    if major == 5:
        out = {}
        while (len(out) < arg) if arg is not None else data[i] != 0xFF:
            key, i = cbor(data, i)
            out[key], i = cbor(data, i)
        return out, (i if arg is not None else i + 1)
    if major == 6:
        return cbor(data, i)  # ignore tags
    raise ValueError(f"unknown major type {major}")


def find_saved_files(root):
    root = Path(root)
    forever = root if root.name == "_forever_" else root / "_forever_"
    return sorted(forever.glob("WTF/Account/*/SavedVariables/Auctionator.lua"), key=lambda p: p.stat().st_mtime, reverse=True)


def load_price_db(path):
    text = path.read_bytes().decode("latin-1")
    m = re.search(r"^AUCTIONATOR_PRICE_DATABASE\s*=\s*", text, re.M)
    if not m:
        sys.exit("AUCTIONATOR_PRICE_DATABASE not in the file yet; /reload or log out first")
    reader = LuaReader(text)
    reader.i = m.end()
    db = reader.value()
    realms = {}
    for key, value in db.items():
        if key == "__dbversion":
            continue
        name = key.encode("latin-1").decode("utf-8", "replace") if isinstance(key, str) else str(key)
        if isinstance(value, str):
            value, _ = cbor(value.encode("latin-1"))
        realms[name] = value
    return realms


def full_scan_started(path):
    """When the last full scan started (Unix seconds), or None.

    Auctionator sets TimeOfLastReplicateScan (modern AH) or TimeOfLastGetAllScan
    (legacy AH) in AUCTIONATOR_SAVEDVARS when a full scan starts.
    """
    text = path.read_bytes().decode("latin-1")
    m = re.search(r"^AUCTIONATOR_SAVEDVARS\s*=\s*", text, re.M)
    if not m:
        return None
    reader = LuaReader(text)
    reader.i = m.end()
    state = reader.value()
    times = [state.get(k) for k in ("TimeOfLastReplicateScan", "TimeOfLastGetAllScan")]
    times = [t for t in times if isinstance(t, (int, float))]
    return max(times) if times else None


def horde_full_scan(path):
    """Return the timestamp and complete DungeonsForeverProf market rows for this scan."""
    handbook = path.with_name("DungeonsForeverProf.lua")
    if not handbook.is_file():
        return None
    lua = handbook.read_bytes().decode("latin-1")
    match = re.search(r"^DungeonsForeverProfDB\s*=\s*", lua, re.M)
    if not match:
        return None
    reader = LuaReader(lua)
    reader.i = match.end()
    market = "rules:1:forever:2:100:Horde"
    scan = reader.value().get("prof", {}).get("auctionFullScans", {}).get(market, {})
    started, stamp = full_scan_started(path), scan.get("t")
    if (not started or not stamp or not started <= stamp <= scan.get("completedAt", 0)
            or scan.get("mk") != market or scan.get("c") is not True or scan.get("dv") != 1
            or not scan.get("items") or not scan.get("received") or scan["received"] != scan.get("expected")):
        return None
    return stamp, scan["items"]


def day_label(day):
    return (DAY0 + datetime.timedelta(days=int(day))).strftime("%m/%d")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="*", help="exact in-game item names to show")
    parser.add_argument("--from-html", nargs="+", type=Path, default=[], metavar="FILE",
                        help="also show every data-ah name in these HTML files")
    parser.add_argument("--root", default="/Applications/World of Warcraft", help="WoW install root or its _forever_ folder")
    parser.add_argument("--file", type=Path, help="a specific Auctionator.lua (overrides --root)")
    parser.add_argument("--realm", help="Auctionator database key; default: the one with most items")
    parser.add_argument("--all", action="store_true", help="list every item in the scan")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "wowamobi-cache")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    path = args.file or next(iter(find_saved_files(args.root)), None)
    if path is None or not path.is_file():
        sys.exit("Auctionator.lua not found; type /reload in game (or log out) so the scan is written to disk")
    realms = load_price_db(path)
    if not realms:
        sys.exit("no realm data in AUCTIONATOR_PRICE_DATABASE yet")
    realm = args.realm or max(realms, key=lambda k: len(realms[k]) if isinstance(realms[k], dict) else 0)
    items = realms[realm]

    args.cache.mkdir(parents=True, exist_ok=True)
    market = json.loads(av.fetch(f"{av.BASE}/api/market/items", args.cache, "market-items.json", 24, 0.4))
    names_by_id = {int(k): v[0] for k, v in market["meta"].items()}

    rows = []
    for key, rec in items.items():
        if not isinstance(rec, dict):
            continue
        m = re.match(r"(?:[a-z]+:)?(\d+)", str(key))
        item_id = int(m.group(1)) if m else None
        lows, highs, avail = rec.get("l") or {}, rec.get("h") or {}, rec.get("a") or {}
        days = sorted({int(d) for d in list(lows) + list(highs)})
        last = days[-1] if days else None
        pick = lambda table, d: table.get(str(d), table.get(d)) if d is not None else None
        rows.append({
            "key": str(key), "id": item_id, "name": names_by_id.get(item_id, f"#{key}"),
            "last_min": rec.get("m"), "last_day": day_label(last) if last is not None else None,
            "day_low": pick(lows, last), "day_high": pick(highs, last), "available": pick(avail, last),
            "history": {day_label(d): pick(lows, d) or pick(highs, d) for d in days},
        })

    wanted = set(args.names)
    for f in args.from_html:
        wanted |= {html.unescape(n) for n in re.findall(r'data-ah="([^"]+)"', f.read_text(encoding="utf-8"))}
    shown = rows if args.all or not wanted else [r for r in rows if r["name"] in wanted]
    missing = sorted(wanted - {r["name"] for r in rows}) if wanted else []
    saved = datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    started = full_scan_started(path)
    scan = datetime.datetime.fromtimestamp(started).strftime("%Y-%m-%d %H:%M") if started else None

    if args.json:
        print(json.dumps({"realm_key": realm, "full_scan_started": scan, "saved": saved, "items": shown, "not_in_scan": missing}, ensure_ascii=False, indent=1))
        return
    print(f"Auctionator・資料庫 {realm}・{len(rows)} 件物品・完整掃描 {scan or '未記錄'}・存檔 {saved}（掛單價，非成交價）")
    for r in sorted(shown, key=lambda r: r["name"]):
        trend = " → ".join(f"{d} {av.gold(p)}" for d, p in list(r["history"].items())[-4:])
        count = f"・{r['available']} 件" if r["available"] else ""
        print(f"- {r['name']}：最近最低 {av.gold(r['last_min'])}（{r['last_day']}{count}）｜{trend}")
    if missing:
        print("掃描裡沒有：" + "、".join(missing))


if __name__ == "__main__":
    main()
