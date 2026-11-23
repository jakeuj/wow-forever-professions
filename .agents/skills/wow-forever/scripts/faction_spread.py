#!/usr/bin/env python3
"""Rank items that are cheap on the Horde auction house but expensive on the Alliance one.

Horde prices come from one live request to the official auction API (lowest unit
buyout and units at each price). Alliance and neutral prices come from wowamobi
item pages ("各陣營拍賣場最近看到的最低一口價"), which have to be read one by
one, so the script screens first:

1. items whose realm-wide median on wowamobi is well above the Horde lowest price
   (the expensive side is usually the Alliance), the top --cap of them;
2. every Horde listing at --min-horde gold or more, which the median misses when
   Horde listings dominate the realm row.

Spread = Alliance lowest - Horde lowest. A Horde player can only reach Alliance
buyers through the neutral auction house, so the resale estimate sells at the
lower of the Alliance and neutral prices and pays --cut (classic: 15%) of it.
Alliance prices not seen in wowamobi's latest Alliance scan are reported apart
because they may have sold. Listing prices, never sale prices.

    python3 faction_spread.py                 # top 30 as text
    python3 faction_spread.py --json > spread.json
"""

import argparse
import collections
import datetime
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import amobi_recipe_value as av  # noqa: E402

REALM = "CAMWOW TW4 Realm 2 PvP"
TAIPEI = datetime.timezone(datetime.timedelta(hours=8))
G = 10000


def screen(levels, rows, cap, min_horde):
    """Item ids worth an item-page fetch, most promising first."""
    gaps = []
    for item_id, lv in levels.items():
        row = rows.get(item_id)
        if not row:
            continue
        low, median = lv[0][0], row[1] or 0
        gap = median - low
        if gap >= G or (median >= 3 * low and gap >= 3000):
            gaps.append((gap, item_id))
    picked = [i for _, i in sorted(gaps, reverse=True)[:cap]]
    seen = set(picked)
    extra = sorted((i for i, lv in levels.items() if i in rows and i not in seen and lv[0][0] >= min_horde * G),
                   key=lambda i: -levels[i][0][0])
    return picked + extra


def seen_time(text, now):
    """wowamobi's "MM/DD HH:MM" (Taiwan time, no year) as an aware datetime."""
    try:
        stamp = datetime.datetime.strptime(f"{now.year}/{text}", "%Y/%m/%d %H:%M").replace(tzinfo=TAIPEI)
    except ValueError:
        return None
    return stamp.replace(year=now.year - 1) if stamp > now + datetime.timedelta(days=1) else stamp


def latest_scan(items, now, house="聯盟"):
    """The time most items of one house share: wowamobi's last full scan of that house."""
    counts = collections.Counter(x["seen"].get(house) for x in items if x["seen"].get(house))
    for text, _ in counts.most_common():
        if seen_time(text, now):
            return text
    return None


def in_scan(text, scan_at, now):
    at = seen_time(text or "", now)
    return bool(at and scan_at and at >= scan_at)


def spread_rows(items, cut, now):
    """Rows with an Alliance price above the Horde one, by spread; plus the Alliance and neutral scans.

    A price older than its house's latest scan was not seen there and may have sold: older
    Alliance prices are marked not fresh, and older neutral prices do not lower the resale.
    """
    scans = {house: latest_scan(items, now, house) for house in ("聯盟", "中立拍賣場")}
    scan_at = {house: seen_time(text, now) if text else None for house, text in scans.items()}
    rows = []
    for x in items:
        alliance = x["faction_min"].get("聯盟")
        if not alliance or alliance <= x["h_min"]:
            continue
        neutral = x["faction_min"].get("中立拍賣場")
        neutral_seen = x["seen"].get("中立拍賣場", "") if neutral else ""
        neutral_fresh = bool(neutral) and in_scan(neutral_seen, scan_at["中立拍賣場"], now)
        sell = min(alliance, neutral) if neutral_fresh else alliance
        rows.append({
            **{k: x[k] for k in ("id", "name", "quality", "type", "h_min", "h_min_qty", "h_total")},
            "alliance": alliance, "alliance_seen": x["seen"].get("聯盟", ""),
            "neutral": neutral, "neutral_seen": neutral_seen, "neutral_fresh": neutral_fresh,
            "spread": alliance - x["h_min"], "ratio": round(alliance / x["h_min"], 1),
            "resale": int(sell * (1 - cut)) - x["h_min"],
            "neutral_cheaper": bool(neutral_fresh and neutral < alliance),
            "fresh": in_scan(x["seen"].get("聯盟"), scan_at["聯盟"], now),
        })
    rows.sort(key=lambda r: (-r["spread"], r["id"]))
    return rows, scans


def gold(copper):
    value = copper / G
    return f"{value:,.0f}g" if abs(value) >= 100 else f"{value:.2f}g"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--realm", default=REALM, help="realm name as shown on wowamobi /market")
    parser.add_argument("--cap", type=int, default=300, help="item pages to read from the median screen")
    parser.add_argument("--min-horde", type=float, default=5, help="also read every Horde listing at this many gold or more")
    parser.add_argument("--cut", type=float, default=0.15, help="neutral auction house cut (classic: 0.15)")
    parser.add_argument("--top", type=int, default=30, help="rows to print as text")
    parser.add_argument("--json", action="store_true", help="print everything as JSON (for scripts/build-cross-faction-page.py)")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "wowamobi-cache")
    parser.add_argument("--delay", type=float, default=0.5, help="seconds between uncached wowamobi requests")
    args = parser.parse_args()

    import auction_changes as ac  # needs Blizzard credentials for the live request
    market = ac.load_market(args.cache, 1)
    group = next((g for g in market["groups"] if g["realm"] == args.realm), None)
    if group is None:
        sys.exit("realm not found; choose from: " + ", ".join(g["realm"] for g in market["groups"]))
    rows = {r[0]: r for r in group["items"]}
    levels, modified = ac.live_levels()
    ids = screen(levels, rows, args.cap, args.min_horde)
    print(f"reading {len(ids)} wowamobi item pages (cached for this scan)...", file=sys.stderr)

    # A page cached after wowamobi's last full scan already shows that scan.
    max_age = max(0.5, (time.time() - group["lastFull"]) / 3600)
    items = []
    for n, item_id in enumerate(ids, 1):
        page = av.parse_item_page(av.fetch(f"{av.BASE}/items/{item_id}", args.cache, f"item-{item_id}.html", max_age, args.delay))
        if page["realm"] != args.realm:
            continue
        faction_min = page["faction_min"]
        if not faction_min and len(page["factions"]) == 1:
            # Only one auction house had it, so the page shows no per-house block.
            faction_min = {page["factions"][0]: rows[item_id][2]}
        meta = market["meta"].get(str(item_id), [str(item_id), None, None, ""])
        lv = levels[item_id]
        items.append({"id": item_id, "name": meta[0], "quality": meta[1], "type": meta[3] if len(meta) > 3 else "",
                      "h_min": lv[0][0], "h_min_qty": lv[0][1], "h_total": sum(q for _, q in lv),
                      "faction_min": faction_min, "seen": page["faction_seen"]})
        if n % 100 == 0:
            print(f"  {n}/{len(ids)}", file=sys.stderr)

    now = datetime.datetime.now(TAIPEI)
    result, scans = spread_rows(items, args.cut, now)
    scan = scans["聯盟"]
    out = {
        "realm": args.realm, "hordeModified": modified,
        "amobiLastFull": datetime.datetime.fromtimestamp(group["lastFull"], TAIPEI).isoformat(timespec="minutes"),
        "allianceScan": scan, "neutralScan": scans["中立拍賣場"], "cut": args.cut, "compared": len(items),
        "rows": result,
    }
    if args.json:
        json.dump(out, sys.stdout, ensure_ascii=False)
        print()
        return
    print(f"部落即時 {modified}；阿莫比聯盟 {scan}、中立 {scans['中立拍賣場']} 掃描；比了 {len(items)} 項，{len(result)} 項聯盟較貴")
    for i, r in enumerate([r for r in result if r["fresh"]][:args.top], 1):
        note = "中立較便宜" if r["neutral_cheaper"] else ""
        resale = f"+{gold(r['resale'])}" if r["resale"] > 0 else f"虧 {gold(-r['resale'])}"
        neutral = (gold(r["neutral"]) + ("" if r["neutral_fresh"] else f"（{r['neutral_seen']} 舊）")) if r["neutral"] else "-"
        print(f"{i:>3}. {r['name']}（{r['type']}）部落 {gold(r['h_min'])}×{r['h_min_qty']}/{r['h_total']}"
              f" 聯盟 {gold(r['alliance'])} 價差 {gold(r['spread'])} ×{r['ratio']} 中立 {neutral} 轉賣 {resale} {note}")
    stale = [r for r in result if not r["fresh"]]
    if stale:
        print(f"聯盟價不在最新掃描（可能已賣掉）{len(stale)} 項：" +
              "、".join(f"{r['name']} {gold(r['alliance'])}（{r['alliance_seen']}）" for r in stale[:8]))


if __name__ == "__main__":
    main()
