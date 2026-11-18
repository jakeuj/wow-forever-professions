#!/usr/bin/env python3
"""Look up Forever auction-house prices for named items on wowamobi.com.

Give item names, or HTML files whose data-ah="..." attributes hold exact in-game
names (the personal pages). Prints the realm-wide row from the market scan and
each auction house's lowest buyout with the time it was last seen. Prices are
listing (buyout) prices, never sale prices.
"""

import argparse
import datetime
import html
import json
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import amobi_recipe_value as av  # noqa: E402

QUALITY = {0: "垃圾", 1: "普通", 2: "優秀", 3: "精良", 4: "史詩", 5: "傳說"}
TAIPEI = datetime.timezone(datetime.timedelta(hours=8))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="exact in-game item names")
    parser.add_argument("--from-html", nargs="+", type=Path, default=[], metavar="FILE",
                        help="also look up every data-ah name in these HTML files")
    parser.add_argument("--realm", default="CAMWOW TW4 Realm 2 PvP", help="realm name as shown on /market")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "wowamobi-cache")
    parser.add_argument("--max-age", type=float, default=1, help="hours a cached page stays fresh; 0 refetches everything")
    parser.add_argument("--delay", type=float, default=0.4, help="seconds between uncached requests")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    names = {n: [] for n in args.names}
    for path in args.from_html:
        for n in re.findall(r'data-ah="([^"]+)"', path.read_text(encoding="utf-8")):
            names.setdefault(html.unescape(n), []).append(path.parent.name or path.name)
    if not names:
        parser.error("give item names or --from-html files")

    args.cache.mkdir(parents=True, exist_ok=True)
    get = lambda url, name: av.fetch(url, args.cache, name, args.max_age, args.delay)
    market = json.loads(get(f"{av.BASE}/api/market/items", "market-items.json"))
    group = next((g for g in market["groups"] if g["realm"] == args.realm), None)
    if group is None:
        sys.exit("realm not found; choose from: " + ", ".join(g["realm"] for g in market["groups"]))
    rows = {row[0]: row for row in group["items"]}
    by_name = {}
    for item_id, meta in market["meta"].items():
        by_name.setdefault(meta[0], []).append(int(item_id))

    results = []
    for name, pages in names.items():
        ids = by_name.get(name, [])
        if not ids:
            results.append({"name": name, "pages": sorted(set(pages)), "status": "unknown name"})
            continue
        for item_id in ids:
            meta = market["meta"][str(item_id)]
            rec = {"name": name, "id": item_id, "pages": sorted(set(pages)),
                   "quality": QUALITY.get(meta[1], meta[1]), "type": meta[3], "same_name": len(ids) > 1}
            row = rows.get(item_id)
            if row is None:
                rec["status"] = "no listing on realm"
            else:
                page = av.parse_item_page(get(f"{av.BASE}/items/{item_id}", f"item-{item_id}.html"))
                rec.update(min=row[2], median=row[1], count=row[3], date=row[4],
                           page_realm_matches=page["realm"] == args.realm)
                if rec["page_realm_matches"]:
                    rec["factions"] = {k: {"min": v, "seen": page["faction_seen"].get(k, "")}
                                       for k, v in page["faction_min"].items()}
                    if not rec["factions"] and page["factions"]:
                        # Only one auction house had it, so the page shows no per-house block.
                        rec["factions"] = {page["factions"][0]: {"min": row[2], "seen": row[4]}}
            results.append(rec)

    scan = datetime.datetime.fromtimestamp(group["lastFull"], TAIPEI).strftime("%Y-%m-%d %H:%M") if group.get("lastFull") else "?"
    if args.json:
        print(json.dumps({"realm": args.realm, "last_full_scan": scan, "items": results}, ensure_ascii=False, indent=1))
        return

    print(f"{args.realm}・最近全掃描 {scan}（台北時間）・掛單價，非成交價")
    for r in sorted(results, key=lambda r: r["name"]):
        label = r["name"] + (f"［{r['quality']}・{r['type']}］" if r.get("same_name") else "")
        if "min" not in r:
            print(f"- {label}：{'名稱對不到物品' if r['status'] == 'unknown name' else '本服沒有掛單紀錄'}")
            continue
        houses = "、".join(f"{k} {av.gold(v['min'])}（{v['seen']}）" for k, v in r.get("factions", {}).items())
        if not r["page_realm_matches"]:
            houses = "物品頁是其他伺服器的資料"
        print(f"- {label}：全服最低 {av.gold(r['min'])}・{r['count']} 個・{r['date']}｜{houses}")


if __name__ == "__main__":
    main()
