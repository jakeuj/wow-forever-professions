#!/usr/bin/env python3
"""Show how Horde auction prices moved, from the site's hourly official record.

Reads auctions.json from the repo's `auction-data` branch: per item id, the units on
sale now and the lowest unit price at each hour it changed (null = sold out). For
item names, item ids, or every data-ah name in the personal pages, prints the price
at --since, the price now, the low and high in between, and the latest changes.
--movers lists the biggest moves of all items instead. --live adds the current units
at each price level from the newer of the Battle.net API snapshot (forever_api.py
credentials) and your complete Auctionator scan (--source forces one). Names come from wowamobi.com's item list.

Prices are lowest buyouts (unit price for stackables), never sale prices. The record
keeps only the lowest price, so a lone cheap or absurd listing skews the change;
check --live levels before calling a trend.
"""

import argparse
import datetime
import email.utils
import html
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import amobi_recipe_value as av  # noqa: E402
import auctionator_prices as ap  # noqa: E402

AUCTIONS_URL = "https://raw.githubusercontent.com/jakeuj/wow-forever-professions/auction-data/auctions.json"
API = "https://tw.api.blizzard.com/data/wow/ruleset/1/auctions/113"
SCAN_MAX_AGE = 3 * 3600  # a scan older than this is no stand-in for an API that failed
TAIPEI = datetime.timezone(datetime.timedelta(hours=8))
QUALITY = {0: "垃圾", 1: "普通", 2: "優秀", 3: "精良", 4: "史詩", 5: "傳說"}


def coin(copper):
    if copper is None:
        return "沒貨"
    if copper >= 10000:
        return f"{copper / 10000:.2f}g"
    return f"{copper / 100:.2f}s" if copper >= 100 else f"{copper}c"


def hour_text(hour):
    return datetime.datetime.fromtimestamp(hour * 3600, TAIPEI).strftime("%m/%d %H時")


def parse_since(text):
    """'YYYY-MM-DD HH' or 'YYYY-MM-DD HH:MM' in Taiwan time -> hours since the epoch."""
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H", "%Y-%m-%d"):
        try:
            when = datetime.datetime.strptime(text, fmt).replace(tzinfo=TAIPEI)
            return math.floor(when.timestamp() / 3600)
        except ValueError:
            pass
    raise argparse.ArgumentTypeError("use 'YYYY-MM-DD HH' (Taiwan time)")


def price_at(series, hour):
    """Lowest price in force at `hour`: a price, None (sold out), or 'absent' (not yet seen)."""
    value = "absent"
    for when, price in series:
        if when > hour:
            break
        value = price
    return value


def summarize(item_id, record, since, now):
    count, series = record
    before, current = price_at(series, since), price_at(series, now)
    between = [p for h, p in series if since < h <= now and p is not None]
    change = None
    if isinstance(before, int) and isinstance(current, int) and before:
        change = (current - before) / before
    return {"id": item_id, "units": count, "since": before, "now": current, "change": change,
            "low": min(between) if between else None, "high": max(between) if between else None,
            "points": [[h, p] for h, p in series if h > since]}


def live_levels():
    """Current units at each unit price per item id, from one house + commodities request."""
    import forever_api  # credentials from the environment, Keychain or DPAPI
    auth = {"Authorization": f"Bearer {forever_api.get_token()}"}
    query = "?namespace=dynamic-forever-tw&locale=zh_TW"
    levels, modified = {}, None
    for path, stackable in (("", False), ("/commodities", True)):
        status, headers, body = forever_api.fetch(API + path + query, auth, timeout=180)
        if status != 200:
            sys.exit(f"auction API {path or '/'}: HTTP {status}")
        modified = headers.get("Last-Modified") or modified
        payload = json.loads(body)
        # The house response links to commodities with a dict; Forever lists /commodities under `auctions`.
        rows = next((v for v in (payload.get("auctions"), payload.get("commodities")) if isinstance(v, list)), [])
        for row in rows:
            item = (row.get("item") or {}).get("id")
            quantity = row.get("quantity") or 1
            price = row.get("unit_price") if stackable else row.get("buyout")
            if not isinstance(item, int) or not price:
                continue
            unit = price if stackable else price // quantity
            levels.setdefault(item, {})
            levels[item][unit] = levels[item].get(unit, 0) + quantity
    return {k: sorted(v.items()) for k, v in levels.items()}, modified


def add_source_options(parser, root=True):
    parser.add_argument("--source", choices=("auto", "api", "scan"), default="auto",
                        help="current prices: the newer of API and Auctionator scan (auto, default), or only one")
    if root:
        parser.add_argument("--root", default="/Applications/World of Warcraft", help="WoW install root, for the scan")


def current_levels(root, source="auto"):
    """(levels, where they come from): the newer of the official API and the saved complete scan.

    The second value has kind (api/scan), at and text for display, plus apiAt/scanAt when known.
    The site's Worker and hourly record copy the API, so they are never newer than it.
    """
    stamp_text = lambda t: datetime.datetime.fromtimestamp(t, TAIPEI).strftime("%m/%d %H:%M")
    scan = ap.latest_scan(root) if source != "api" else None
    api, problem = None, None
    if source != "scan":
        try:
            levels, modified = live_levels()
            api = (email.utils.parsedate_to_datetime(modified).timestamp() if modified else None, levels)
        except (SystemExit, OSError, ValueError) as error:
            if source == "api":
                raise
            problem = str(error) or type(error).__name__
    if api is None:
        if scan is None:
            sys.exit(f"no complete Horde scan under {root}" + (f", and the auction API failed: {problem}" if problem else ""))
        if source == "auto" and time.time() - scan[0] > SCAN_MAX_AGE:
            sys.exit(f"the auction API failed ({problem}) and the last scan is too old ({stamp_text(scan[0])})")
    use_scan = api is None or (scan is not None and api[0] is not None and scan[0] > api[0])
    info = {"kind": "scan" if use_scan else "api",
            "apiAt": stamp_text(api[0]) if api and api[0] else None, "scanAt": stamp_text(scan[0]) if scan else None}
    if use_scan:
        levels = scan[1]
        if api:
            # Rows the scan could not read keep the API's price.
            levels = {**levels, **{i: api[1][i] for i in scan[2] if i in api[1]}}
        info["at"] = info["scanAt"]
        other = f"，比 API {info['apiAt']} 新" if api else f"，API 失敗：{problem}" if problem else ""
        info["text"] = f"拍賣小幫手掃描 {info['at']}{other}"
    else:
        levels = api[1]
        info["at"] = info["apiAt"] or "時間不明"
        other = f"，比掃描 {info['scanAt']} 新" if scan and api[0] else ""
        info["text"] = f"官方 API {info['at']}{other}"
    return levels, info


def load_record(source=None):
    """auctions.json from a path or URL (default: the auction-data branch)."""
    source = source or AUCTIONS_URL
    if re.match(r"https?://", source):
        request = urllib.request.Request(source, headers={"User-Agent": av.USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as resp:
            return json.loads(resp.read())
    return json.loads(Path(source).read_text(encoding="utf-8"))


def load_market(cache, max_age):
    """wowamobi's /api/market/items: `meta` (id -> name, quality, class, type) and per-realm rows."""
    cache.mkdir(parents=True, exist_ok=True)
    return json.loads(av.fetch(f"{av.BASE}/api/market/items", cache, "market-items.json", max_age, 0))


def resolve(names, meta, record):
    """name -> item ids; drop junk duplicates (e.g. 黑蓮花) and ids the record never saw."""
    by_name = {}
    for item_id, row in meta.items():
        by_name.setdefault(row[0], []).append(int(item_id))
    out = {}
    for name in names:
        ids = by_name.get(name, [])
        seen = [i for i in ids if str(i) in record] or ids
        good = [i for i in seen if meta[str(i)][1] > 0] or seen
        out[name] = good
    return out


def line(row, levels, history):
    head = f"{row['name']}[{row['id']}]"
    if row.get("label"):
        head += f"［{row['label']}］"
    since = "沒紀錄" if row["since"] == "absent" else coin(row["since"])
    text = f"{head} {since} → {coin(row['now'])}"
    if row["change"] is not None:
        text += f"（{row['change']:+.0%}）"
    text += f"・{row['units']} 件"
    if row["low"] is not None:
        text += f"｜期間 {coin(row['low'])}～{coin(row['high'])}"
    if levels is not None:
        level = levels.get(row["id"])
        text += "｜現價 " + ("沒貨" if not level else
                           f"{sum(q for _, q in level)} 件：" + "、".join(f"{coin(p)}×{q}" for p, q in level[:4]))
    if history and row["points"]:
        text += "｜最近 " + " ".join(f"{hour_text(h)} {coin(p)}" for h, p in row["points"][-history:])
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="*", help="exact in-game item names")
    parser.add_argument("--from-html", nargs="+", type=Path, default=[], metavar="FILE",
                        help="every data-ah name in these HTML files (the personal pages)")
    parser.add_argument("--ids", nargs="+", type=int, default=[], help="item ids")
    parser.add_argument("--movers", action="store_true", help="list the biggest moves of all items")
    parser.add_argument("--since", type=parse_since, help="'YYYY-MM-DD HH' Taiwan time; default 24 h before the latest snapshot")
    parser.add_argument("--min-price", type=float, default=0.1, help="--movers: ignore items under this many gold (default 0.1)")
    parser.add_argument("--type", help="--movers: only items whose wowamobi type contains this, e.g. 金屬 or 草藥")
    parser.add_argument("--top", type=int, default=15, help="--movers: rows per list (default 15)")
    parser.add_argument("--history", type=int, default=6, help="latest change points to show (0 hides them)")
    parser.add_argument("--live", action="store_true", help="add the current units per price level (newer of API and scan)")
    add_source_options(parser)
    parser.add_argument("--auctions", help="auctions.json path or URL (default: the auction-data branch)")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "wowamobi-cache")
    parser.add_argument("--max-age", type=float, default=6, help="hours wowamobi's item list stays cached")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    names = list(dict.fromkeys(args.names))
    for path in args.from_html:
        for name in re.findall(r'data-ah="([^"]+)"', path.read_text(encoding="utf-8")):
            if html.unescape(name) not in names:
                names.append(html.unescape(name))
    if not (names or args.ids or args.movers):
        parser.error("give item names, --from-html, --ids or --movers")

    data = load_record(args.auctions)
    record, hours = data["items"], data["hours"]
    now = hours[-1]
    since = args.since if args.since is not None else now - 24
    meta = load_market(args.cache, args.max_age)["meta"]
    levels, source = current_levels(args.root, args.source) if args.live else (None, None)
    name_count = {}
    for info in meta.values():
        name_count[info[0]] = name_count.get(info[0], 0) + 1

    def row_for(item_id, name=None):
        if str(item_id) not in record:
            if not (levels and levels.get(item_id)):
                return None
            # Listed now but new to the hourly record.
            row = {"id": item_id, "units": 0, "since": "absent", "now": None, "change": None,
                   "low": None, "high": None, "points": []}
        else:
            row = summarize(item_id, record[str(item_id)], since, now)
        info = meta.get(str(item_id))
        row["name"] = name or (info[0] if info else f"物品 {item_id}")
        if info and name_count[info[0]] > 1:
            row["label"] = f"{QUALITY.get(info[1], info[1])}・{info[3]}"
        return row

    rows, missing = [], []
    for name, ids in resolve(names, meta, record).items():
        found = [r for r in (row_for(i, name) for i in ids) if r]
        rows += found
        if not found:
            missing.append(name if ids else f"{name}（wowamobi 沒有這個名稱）")
    for item_id in args.ids:
        row = row_for(item_id)
        if row:
            rows.append(row)
        else:
            missing.append(f"物品 {item_id}")

    movers = {}
    if args.movers:
        floor = args.min_price * 10000
        pool = []
        for key in record:
            info = meta.get(key)
            if args.type and not (info and args.type in str(info[3])):
                continue
            row = row_for(int(key))
            before, current = row["since"], row["now"]
            if isinstance(before, int) and isinstance(current, int):
                if max(before, current) >= floor and before != current:
                    pool.append(row)
            elif isinstance(before, int) and current is None and before >= floor:
                movers.setdefault("sold_out", []).append(row)
            elif before in (None, "absent") and isinstance(current, int) and current >= floor:
                movers.setdefault("new", []).append(row)
        pool.sort(key=lambda r: r["change"])
        movers["down"] = [r for r in pool if r["change"] < 0][:args.top]
        movers["up"] = [r for r in reversed(pool) if r["change"] > 0][:args.top]
        for key in ("sold_out", "new"):
            movers[key] = sorted(movers.get(key, []), key=lambda r: -(r["since"] if key == "sold_out" else r["now"]))[:args.top]

    window = [h for h in hours if since < h <= now]
    if args.json:
        json.dump({"updatedAt": data.get("updatedAt"), "since": since, "now": now, "snapshots": len(window),
                   "priceSource": source, "items": rows, "movers": movers, "missing": missing,
                   "live": {str(r["id"]): levels.get(r["id"]) for r in rows} if levels is not None else None},
                  sys.stdout, ensure_ascii=False, indent=1)
        print()
        return
    print(f"部落官方每小時紀錄：{hour_text(since)} → {hour_text(now)}（最新快照 {data.get('updatedAt')}），"
          f"期間收到 {len(window)} 次快照" + (f"；現價用{source['text']}" if source else ""))
    for row in rows:
        print("- " + line(row, levels, args.history))
    titles = {"down": "跌最多", "up": "漲最多", "sold_out": "賣光或下架", "new": "新上架"}
    for key in ("down", "up", "sold_out", "new"):
        if movers.get(key):
            print(f"\n## {titles[key]}")
            for row in movers[key]:
                print("- " + line(row, levels, args.history))
    if missing:
        print("\n官方紀錄沒有：" + "、".join(missing))
    print("\n只記最低價：一兩張離群掛單會讓漲跌幅失真，判斷前用 --live 看各價位件數。")


if __name__ == "__main__":
    main()
