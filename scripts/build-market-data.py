#!/usr/bin/env python3
"""Build market/data.json for the personal market page from an Auctionator scan.

Prices come from the site owner's own Auctionator save (read-only; run /reload or
log out in game first). Item names, quality and categories come from the Forever
client tables on wago.tools (zhTW) for the installed build; items the client
tables lack, and every icon, come from Wowhead's Forever tooltip data. Lookups are
cached, and names and icons already in market/data.json are reused, so later runs
only fetch items that are new to the scan. Names still left as "[English]" in Forever data
use Wowhead's Classic zhTW name, as the game does.

    python3 scripts/build-market-data.py
"""

import argparse
import concurrent.futures
import csv
import datetime
import json
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / ".agents/skills/wow-forever/scripts"))
import auctionator_prices as ap  # noqa: E402

USER_AGENT = "Mozilla/5.0 (compatible; wow-forever-professions-site-build)"
WAGO = "https://wago.tools/db2/{table}/csv?build={build}&locale=zhTW"
WOWHEAD = "https://nether.wowhead.com/{env}/tw/tooltip/item/{id}"
DAY0 = datetime.date(2020, 1, 1)
GEAR_CLASSES = {2, 4}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def installed_build(root):
    info = Path(root) / ".build.info"
    lines = info.read_text(encoding="utf-8").splitlines()
    header = [h.split("!")[0] for h in lines[0].split("|")]
    for line in lines[1:]:
        row = dict(zip(header, line.split("|")))
        if row.get("Product") == "wowf" and row.get("Active") == "1":
            return row["Version"]
    sys.exit("no active wowf entry in .build.info; pass --build")


def client_table(cache, build, table):
    path = cache / build / f"{table}.csv"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(get(WAGO.format(table=table, build=build)))
    csv.field_size_limit(sys.maxsize)
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def wowhead_item(cache, item_id, env="forever"):
    path = cache / ("wowhead" if env == "forever" else f"wowhead-{env}") / f"{item_id}.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            data = json.loads(get(WOWHEAD.format(env=env, id=item_id)))
            break
        except urllib.error.HTTPError as error:
            if error.code == 404:
                data = {}  # Wowhead does not know the item; remember that
                break
            if attempt == 2:
                return None
            time.sleep(2 * (attempt + 1))
        except Exception:
            if attempt == 2:
                return None
            time.sleep(2 * (attempt + 1))
    keep = {"name": data.get("name"), "quality": data.get("quality"), "icon": data.get("icon")}
    level = re.search(r"需要等級\s*(?:<!--rlvl-->)?(\d+)", data.get("tooltip", ""))
    keep["level"] = int(level.group(1)) if level else None
    path.write_text(json.dumps(keep, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.1)
    return keep


def day_iso(day):
    return (DAY0 + datetime.timedelta(days=int(day))).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default="/Applications/World of Warcraft", help="WoW install root")
    parser.add_argument("--file", type=Path, help="a specific Auctionator.lua")
    parser.add_argument("--build", help="client build for name tables; default: the installed wowf build")
    parser.add_argument("--faction", default="部落", help="auction house the scan was taken at (shown on the page)")
    parser.add_argument("--out", type=Path, default=REPO / "market/data.json")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "wow-forever-site-cache")
    parser.add_argument("--workers", type=int, default=4, help="parallel Wowhead lookups")
    args = parser.parse_args()

    save = args.file or next(iter(ap.find_saved_files(args.root)), None)
    if save is None or not save.is_file():
        sys.exit("Auctionator.lua not found; type /reload in game (or log out) first")
    realms = ap.load_price_db(save)
    realm = max(realms, key=lambda k: len(realms[k]) if isinstance(realms[k], dict) else 0)
    scan = {int(k): v for k, v in realms[realm].items() if re.fullmatch(r"\d+", str(k)) and isinstance(v, dict)}

    started = ap.full_scan_started(save)
    scan_started = datetime.datetime.fromtimestamp(started).astimezone().isoformat(timespec="minutes") if started else None
    build = args.build or installed_build(args.root)
    sparse = {int(r["ID"]): r for r in client_table(args.cache, build, "ItemSparse")}
    classes_of = {int(r["ID"]): (int(r["ClassID"]), int(r["SubclassID"])) for r in client_table(args.cache, build, "Item")}
    class_names = {int(r["ClassID"]): r["ClassName_lang"] for r in client_table(args.cache, build, "ItemClass")}
    subclass_names = {f'{r["ClassID"]}.{r["SubClassID"]}': r["DisplayName_lang"]
                      for r in client_table(args.cache, build, "ItemSubClass")}

    previous = {}
    if args.out.is_file():
        old = json.loads(args.out.read_text(encoding="utf-8"))
        fields = old["fields"]
        previous = {row[0]: dict(zip(fields, row)) for row in old["items"]}

    need_wowhead = [i for i in scan if not (previous.get(i, {}).get("icon") and (i in sparse or previous.get(i, {}).get("name")))]
    print(f"{len(scan)} items; Wowhead lookups needed: {len(need_wowhead)}", file=sys.stderr)
    wowhead = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for item_id, data in zip(need_wowhead, pool.map(lambda i: wowhead_item(args.cache, i), need_wowhead)):
            wowhead[item_id] = data or {}

    fields = ["id", "name", "quality", "class", "subclass", "icon", "level", "price", "count", "day", "prev", "prevDay"]
    rows, unnamed = [], 0
    latest_day = 0
    for item_id, rec in scan.items():
        old = previous.get(item_id, {})
        web = wowhead.get(item_id, {})
        sp = sparse.get(item_id)
        name = (sp and sp["Display_lang"]) or web.get("name") or old.get("name")
        if name and name.startswith("["):
            # Forever data still has some untranslated "[English]" names; the game
            # shows the Classic zhTW name, which Wowhead's Classic data carries.
            name = (wowhead_item(args.cache, item_id, "classic") or {}).get("name") or name
        if not name:
            unnamed += 1
            continue
        quality = int(sp["OverallQualityID"]) if sp else web.get("quality", old.get("quality"))
        cls, sub = classes_of.get(item_id, (old.get("class"), old.get("subclass")))
        level = int(sp["RequiredLevel"]) if sp and sp["RequiredLevel"].isdigit() else None
        if level is None and cls in GEAR_CLASSES:
            level = web.get("level", old.get("level"))
        lows, highs, avail = rec.get("l") or {}, rec.get("h") or {}, rec.get("a") or {}
        days = sorted({int(d) for d in list(lows) + list(highs)})
        if not days:
            continue
        pick = lambda table, d: table.get(str(d), table.get(d))
        last = days[-1]
        latest_day = max(latest_day, last)
        prev_day = days[-2] if len(days) > 1 else None
        rows.append([
            item_id, name, quality, cls, sub, web.get("icon") or old.get("icon"), level or None,
            rec.get("m"), pick(avail, last), day_iso(last),
            (pick(lows, prev_day) or pick(highs, prev_day)) if prev_day is not None else None,
            day_iso(prev_day) if prev_day is not None else None,
        ])

    used_classes = {r[3] for r in rows}
    used_subclasses = {f"{r[3]}.{r[4]}" for r in rows}
    data = {
        "generatedAt": datetime.datetime.now().astimezone().isoformat(timespec="minutes"),
        "scanStartedAt": scan_started,
        "savedAt": datetime.datetime.fromtimestamp(save.stat().st_mtime).astimezone().isoformat(timespec="minutes"),
        "latestDay": day_iso(latest_day),
        "faction": args.faction,
        "build": build,
        "classes": {str(c): class_names.get(c, str(c)) for c in sorted(c for c in used_classes if c is not None)},
        "subclasses": {k: subclass_names.get(k, k) for k in sorted(used_subclasses)},
        "fields": fields,
        "items": sorted(rows, key=lambda r: r[0]),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {args.out.relative_to(REPO)}: {len(rows)} items, latest day {data['latestDay']}, "
          f"{unnamed} without a name skipped", file=sys.stderr)


if __name__ == "__main__":
    main()
