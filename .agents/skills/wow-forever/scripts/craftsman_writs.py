#!/usr/bin/env python3
"""Cheapest Craftsman's Writs (工匠令狀) for supply-faction reputation on the Horde auction house.

Writs and what each wants come from the installed Waylaid Auction Helper
(WaylaidHelper/Data.lua, ns.Writs). A writ is a daily: buy the writ, use it,
hand the wanted item to its customer for 75 / 125 / 200 reputation (journeyman /
expert / artisan; WaylaidHelperDB.rep overrides once a turn-in taught the addon).
Each distinct writ counts once a day, so the ranking is per writ and the daily
totals add one of each.

Prices default to the last Auctionator full scan (lowest unit price per item,
which covers every writ in one go); --api takes one live official snapshot
instead. --owned counts every character's writs and wanted items from
Syndicator as already paid for (cash view), and marks them.

    python3 craftsman_writs.py --root 'F:\\Program Files (x86)\\World of Warcraft'
    python3 craftsman_writs.py --root ... --owned --max 1.2 --zone 塔納利斯 菲拉斯
    python3 craftsman_writs.py --root ... --api --json
"""

import argparse
import json
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auction_changes as ac  # noqa: E402
from waylaid_crates import addon_data, auctionator_levels, forever_dir, gold, local_time, lua_table, owned_items  # noqa: E402

REP = {"journeyman": 75, "expert": 125, "artisan": 200}
RANK = {"journeyman": "中級", "expert": "高級", "artisan": "專家級"}
SEALED = {262887: "apprentice", 262888: "journeyman", 262889: "expert", 262890: "artisan"}
WRIT = re.compile(r'\{id=(\d+),quest=(\d+),name="Craftsman\'s Writ: ([^"]*)",rank="(\w+)",item=(\d+),count=(\d+)'
                  r'(?:,zone=(\d+))?(,bop=true)?\}')
# Data.lua's ns.Zones are English; the zhTW client names. Riverglades is new in Forever and stays English.
ZONES = {
    "Badlands": "荒蕪之地", "Blasted Lands": "詛咒之地", "Swamp of Sorrows": "悲傷沼澤", "Duskwood": "暮色森林",
    "Wetlands": "濕地", "Dustwallow Marsh": "塵泥沼澤", "Azshara": "艾薩拉", "Western Plaguelands": "西瘟疫之地",
    "Stranglethorn Vale": "荊棘谷", "Alterac Mountains": "奧特蘭克山脈", "Deadwind Pass": "逆風小徑",
    "Arathi Highlands": "阿拉希高地", "Burning Steppes": "燃燒平原", "The Hinterlands": "辛特蘭",
    "Searing Gorge": "灼熱峽谷", "Eastern Plaguelands": "東瘟疫之地", "Hillsbrad Foothills": "希爾斯布萊德丘陵",
    "Ashenvale": "梣谷", "Feralas": "菲拉斯", "Felwood": "費伍德森林", "Thousand Needles": "千針石林",
    "Desolace": "淒涼之地", "Stonetalon Mountains": "石爪山脈", "Tanaris": "塔納利斯", "Un'Goro Crater": "安戈洛環形山",
    "Moonglade": "月光林地", "Silithus": "希利蘇斯",
}


def parse_writs(text, rep=None):
    """Data.lua -> writs: {id, quest, name, rank, rep, item, count, zone, bop}."""
    rep = {**REP, **(rep or {})}
    start = text.find("ns.Zones")
    zones = dict((int(a), b) for a, b in re.findall(r'\[(\d+)\]="([^"]+)"', text[start:text.find("}", start)])) if start >= 0 else {}
    writs = []
    for m in WRIT.finditer(text):
        zone = zones.get(int(m.group(7))) if m.group(7) else None
        writs.append({"id": int(m.group(1)), "quest": int(m.group(2)), "name": m.group(3), "rank": m.group(4),
                      "rep": rep.get(m.group(4)), "item": int(m.group(5)), "count": int(m.group(6)),
                      "zone": ZONES.get(zone, zone), "bop": bool(m.group(8))})
    return writs


def price(writs, levels, owned=None):
    """Adds writ_price, item_price (None when unlisted and not owned), cost, per100 and owned flags to each writ."""
    owned = owned or {}
    rows = []
    for w in writs:
        lw, li = levels.get(w["id"]), levels.get(w["item"])
        own_writ = owned.get(w["id"], 0) > 0
        own_item = owned.get(w["item"], 0) >= w["count"]
        writ_price = 0 if own_writ else (lw[0][0] if lw else None)
        item_price = 0 if own_item else (li[0][0] * w["count"] if li else None)
        cost = None if writ_price is None or item_price is None else writ_price + item_price
        rows.append({**w, "writ_price": writ_price, "writ_units": sum(q for _, q in lw) if lw else 0,
                     "item_price": item_price, "own_writ": own_writ, "own_item": own_item, "cost": cost,
                     "per100": None if cost is None or not w["rep"] else cost * 100 / w["rep"]})
    rows.sort(key=lambda r: (r["per100"] is None, r["per100"] or 0))
    return rows


def daily(rows, limits=(1.0, 1.2, 1.5, 2.0)):
    """One of each priced writ up to each gold-per-100-rep limit: [(limit, writs, rep, copper)]."""
    out = []
    for limit in limits:
        picked = [r for r in rows if r["per100"] is not None and r["per100"] <= limit * 10000]
        out.append((limit, len(picked), sum(r["rep"] for r in picked), sum(r["cost"] for r in picked)))
    return out


def saved_rep(root):
    """Reputation per rank the addon learned from turn-ins (WaylaidHelperDB.rep), or {}."""
    for path in forever_dir(root).glob("WTF/Account/*/SavedVariables/WaylaidHelper.lua"):
        table = lua_table(path, "WaylaidHelperDB") or {}
        if isinstance(table.get("rep"), dict):
            return {k: int(v) for k, v in table["rep"].items()}
    return {}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default="/Applications/World of Warcraft", help="WoW install root holding _forever_")
    parser.add_argument("--api", action="store_true", help="price from one live official snapshot instead of Auctionator")
    parser.add_argument("--owned", action="store_true", help="count every character's writs and wanted items (Syndicator)")
    parser.add_argument("--max", type=float, help="only writs at or under this many gold per 100 reputation")
    parser.add_argument("--zone", nargs="+", default=[], help="only writs handed in at zones containing these words")
    parser.add_argument("--rank", choices=sorted(REP), help="only this rank")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "wowamobi-cache")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    writs = parse_writs(addon_data(args.root).read_text(encoding="utf-8"), saved_rep(args.root))
    if args.api:
        levels, modified = ac.live_levels()
        source = f"官方 API 即時快照（{modified}）"
    else:
        scan = auctionator_levels(args.root)
        if not scan:
            sys.exit("Auctionator.lua not found; run a full scan and /reload, or use --api")
        when, levels = scan
        source = f"Auctionator 完整掃描（存檔 {local_time(when)}，只有最低價）"
    owned = owned_items(args.root) if args.owned else {}
    rows = price(writs, levels, owned)
    totals = daily(rows)
    if args.rank:
        rows = [r for r in rows if r["rank"] == args.rank]
    if args.zone:
        rows = [r for r in rows if r["zone"] and any(z in r["zone"] for z in args.zone)]
    if args.max is not None:
        rows = [r for r in rows if r["per100"] is not None and r["per100"] <= args.max * 10000]

    meta = ac.load_market(args.cache, 6).get("meta", {})
    name = lambda i: (meta.get(str(i)) or [None])[0]
    sealed = {rank: levels.get(i, [(None, 0)])[0] for i, rank in SEALED.items() if levels.get(i)}

    if args.json:
        for r in rows:
            r["writ_name"], r["item_name"] = name(r["id"]), name(r["item"])
        print(json.dumps({"source": source, "sealed": sealed, "daily": totals, "writs": rows}, ensure_ascii=False, indent=1))
        return

    print(f"價格：{source}")
    if sealed:
        print("密封的令狀（打開隨機變成同階級一種）：" + "、".join(
            f"{RANK.get(rank, rank)} {gold(p)}（{u} 張，{REP.get(rank, '?')} 聲望）" for rank, (p, u) in sealed.items()))
    print("每天每種各交一份：" + "；".join(
        f"每 100 聲望 ≤{limit:g}g 有 {n} 份、{rep} 聲望、{gold(c)}" for limit, n, rep, c in totals))
    print()
    for r in rows:
        per = "缺價" if r["per100"] is None else f"{gold(r['per100'])}/100"
        writ = "自有" if r["own_writ"] else ("—" if r["writ_price"] is None else f"{gold(r['writ_price'])}（{r['writ_units']} 張）")
        item = "自有" if r["own_item"] else ("無掛單" if r["item_price"] is None else gold(r["item_price"]))
        count = f" ×{r['count']}" if r["count"] > 1 else ""
        print(f"{per:>12}  {RANK[r['rank']]} {r['rep']}  {name(r['id']) or r['name']}  令狀 {writ} ＋ "
              f"{name(r['item']) or r['item']}{count} {item}  @ {r['zone'] or '地點未知'}")


if __name__ == "__main__":
    main()
