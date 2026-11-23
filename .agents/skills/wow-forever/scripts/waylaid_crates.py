#!/usr/bin/env python3
"""Cheapest Waylaid Crates (遭攔截的木箱) for Merchant's Favor on the Horde auction house.

Crates and their bundles come from the installed Waylaid Auction Helper
(WaylaidHelper/Data.lua), prices from one live request to the official auction
API (units at each unit price). The maths follows the addon's Optimizer.lua:
a crate costs the crate plus its cheapest bundle, less the copper a Sealed
Crate pays back; filling k crates walks up the price levels; a knapsack over
favor picks how many of each kind reach the goal.

By default bags and bank are not counted, so the list is what to buy. --owned
adds every character's crates and materials from Syndicator: an owned crate is
a free listing the plan may use or skip, an owned material is priced at the
lowest listing (what selling it would fetch), so it replaces a purchase but
never wins a fill by being free. --keep leaves items out (bars kept for a
profession). --scan prefers the in-game Waylaid Auction Helper scan (price
levels per item) and --auctionator the last Auctionator full scan (lowest
price and units only) over the hourly API snapshot.

    python3 waylaid_crates.py --root 'F:\\Program Files (x86)\\World of Warcraft' --level 34
    python3 waylaid_crates.py --root ... --level 34 --owned --keep 3860 3859 --scan --auctionator
    python3 waylaid_crates.py --root ... --goal 600 --level 40 --top 0
    python3 waylaid_crates.py --root ... --json
"""

import argparse
import json
import math
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auction_changes as ac  # noqa: E402
from auction_brief import search_term, taiwan_time  # noqa: E402

# Favor and copper a Sealed Crate pays, (white gathering crate, green crafting crate);
# the addon's Favor.lua defaults (Artisan copper is its guess).
FAVOR = {"apprentice": (5, 10), "journeyman": (10, 20), "expert": (15, 30), "artisan": (20, 40)}
REFUND = {"apprentice": (250, 500), "journeyman": (500, 1000), "expert": (750, 1500), "artisan": (1000, 2000)}
CRATE = re.compile(r'\{id=(\d+),name="([^"]*)",tier="(\w+)",quality=(\d),level=(\d+),bundles=\{(.*?)\}\}')
BUNDLE = re.compile(r"item=(\d+),qty=(\d+)")


def addon_data(root):
    root = Path(root)
    forever = root if root.name == "_forever_" else root / "_forever_"
    return forever / "Interface/AddOns/WaylaidHelper/Data.lua"


def parse_crates(text, max_level=None):
    """Data.lua's ns.Crates -> kinds: {id, name, tier, quality, level, favor, refund, bundles=[(item, qty)]}."""
    kinds = []
    for m in CRATE.finditer(text):
        tier, quality, level = m.group(3), int(m.group(4)), int(m.group(5))
        if max_level is not None and level > max_level:
            continue
        kinds.append({"id": int(m.group(1)), "name": m.group(2), "tier": tier, "quality": quality, "level": level,
                      "favor": FAVOR[tier][quality - 1], "refund": REFUND[tier][quality - 1],
                      "bundles": [(int(i), int(q)) for i, q in BUNDLE.findall(m.group(6))]})
    return kinds


def split(levels, skip, n):
    """`n` units after the cheapest `skip`: {cost, top, own, buy, value}, or None when the house runs dry.

    A level is (unit price, units) or (unit price, units, True) for units already owned; cost counts both,
    value is the owned units' part, top is the dearest price actually bought."""
    out = {"cost": 0, "top": 0, "own": 0, "buy": 0, "value": 0}
    for price, qty, *owned in levels:
        if skip >= qty:
            skip -= qty
            continue
        got = min(qty - skip, n)
        skip, n = 0, n - got
        out["cost"] += got * price
        if owned and owned[0]:
            out["own"] += got
            out["value"] += got * price
        else:
            out["buy"] += got
            out["top"] = max(out["top"], price)
        if n == 0:
            return out
    return None


def take(levels, skip, n):
    """(copper, dearest unit price bought) for `n` units after the cheapest `skip`, or None when the house runs dry."""
    got = split(levels, skip, n)
    return (got["cost"], got["top"]) if got else None


AH_CUT = 0.05  # the auction house keeps 5% of a sale


def with_owned(levels, owned, kinds, keep=()):
    """Owned units in front of each ladder: crates at 0, materials at what selling them at the lowest listing
    would bring after the auction house cut (0 when none is listed)."""
    crates = {k["id"] for k in kinds}
    materials = {item for k in kinds for item, _ in k["bundles"]}
    out = dict(levels)
    for item, count in owned.items():
        if count <= 0 or item in keep or (item not in crates and item not in materials):
            continue
        rows = [r for r in levels.get(item, []) if not (len(r) > 2 and r[2])]
        price = 0 if item in crates or not rows else int(rows[0][0] * (1 - AH_CUT))
        out[item] = [(price, count, True)] + rows
    return out


def curve(kind, levels, max_count):
    """steps[k-1] for k filled crates: spend, total (spend less refunds, not below 0) and the k-th crate's bundle."""
    steps, used, spend = [], {}, 0
    for k in range(1, max_count + 1):
        crate = take(levels.get(kind["id"], []), k - 1, 1)
        if not crate:
            break
        best = None
        for i, (item, qty) in enumerate(kind["bundles"]):
            got = take(levels.get(item, []), used.get(i, 0) * qty, qty)
            if got and (best is None or got[0] < best[1]):
                best = (i, got[0])
        if not best:
            break
        used[best[0]] = used.get(best[0], 0) + 1
        spend += crate[0] + best[1]
        steps.append({"spend": spend, "total": max(0, spend - k * kind["refund"]), "bundle": best[0]})
    return steps


def overview(kinds, levels):
    """One crate of every kind with its cheapest bundle, cheapest per favor first; unfillable kinds last."""
    rows = []
    for kind in kinds:
        step = (curve(kind, levels, 1) or [None])[0]
        crates = levels.get(kind["id"], [])
        row = {"kind": kind, "on_sale": sum(r[1] for r in crates if not (len(r) > 2 and r[2])),
               "owned": sum(r[1] for r in crates if len(r) > 2 and r[2]), "cost": None, "per_favor": None,
               "bundle": None}
        if step:
            row.update(cost=step["spend"], per_favor=step["total"] / kind["favor"], bundle=kind["bundles"][step["bundle"]])
        rows.append(row)
    rows.sort(key=lambda r: (r["per_favor"] is None, r["per_favor"] or 0, r["kind"]["id"]))
    return rows


def plan(kinds, levels, goal):
    """Cheapest crates worth at least `goal` favor: {favor, cost, spend, picks=[{kind, count, cost, spend, lines}]}.

    A line is {item, units, cost, top, own, buy, value} for the crates and for each bundle used: own units come
    from the bags, buy units from the house, value is what the owned units would sell for. cost is net of
    refunds and counts owned materials at that value; result["cash"] is what buying costs. Favor below the
    goal means the house cannot reach it."""
    options = [(k, curve(k, levels, math.ceil(goal / k["favor"]))) for k in kinds]
    options = [(k, c) for k, c in options if c]
    result = {"goal": goal, "favor": 0, "cost": 0, "spend": 0, "cash": 0, "value": 0, "refund": 0, "picks": []}
    if not options or goal <= 0:
        return result
    unit = 0
    for kind, _ in options:
        unit = math.gcd(unit, kind["favor"])
    need = math.ceil(goal / unit)
    best, choice = {0: 0}, []
    for kind, steps in options:
        weight, nxt, pick = kind["favor"] // unit, dict(best), {}
        for x, base in best.items():
            for n, step in enumerate(steps, 1):
                y, cost = min(need, x + n * weight), base + step["total"]
                if y not in nxt or cost < nxt[y]:
                    nxt[y], pick[y] = cost, (x, n)
        best = nxt
        choice.append(pick)
    y = max(best)
    counts = {}
    for t in range(len(options) - 1, -1, -1):
        if y in choice[t]:
            y, counts[t] = choice[t][y]
    for t, count in sorted(counts.items()):
        kind, steps = options[t]
        uses = {}
        for step in steps[:count]:
            uses[step["bundle"]] = uses.get(step["bundle"], 0) + 1
        lines = [dict(split(levels.get(kind["id"], []), 0, count), item=kind["id"], units=count)]
        for i, bundles in sorted(uses.items()):
            item, qty = kind["bundles"][i]
            lines.append(dict(split(levels.get(item, []), 0, bundles * qty), item=item,
                              units=bundles * qty, bundles=bundles, per=qty))
        step = steps[count - 1]
        result["picks"].append({"kind": kind, "count": count, "favor": count * kind["favor"], "cost": step["total"],
                                "spend": step["spend"], "lines": lines})
        result["favor"] += count * kind["favor"]
        result["cost"] += step["total"]
        result["spend"] += step["spend"]
        result["refund"] += count * kind["refund"]
        for line in lines:
            result["cash"] += line["cost"] - line["value"]
            result["value"] += line["value"]
    result["picks"].sort(key=lambda p: p["cost"] / p["favor"])
    return result


def import_line(result, name_of, title):
    """Auctionator import of the units to buy: exact names, quantity, and the dearest planned unit price
    (rounded up to silver) as max. Owned units are left out; buying the same item for two crates sums up."""
    wanted = {}
    for pick in result["picks"]:
        for line in pick["lines"]:
            if line.get("buy", line["units"]) > 0:
                got = wanted.setdefault(line["item"], {"item": line["item"], "units": 0, "top": 0})
                got["units"] += line.get("buy", line["units"])
                got["top"] = max(got["top"], line["top"])
    terms = []
    for line in wanted.values():
        fields = search_term(name_of(line["item"]), line["units"]).split(";")
        fields[9] = f"{max(1, math.ceil(line['top'] / 100)) / 100:.2f}"  # 0 would mean no cap
        terms.append(";".join(fields))
    return "^".join([title] + terms) if terms else None


def forever_dir(root):
    root = Path(root)
    return root if root.name == "_forever_" else root / "_forever_"


def lua_table(path, variable):
    """A saved-variables table as Python, or None when the file lacks it."""
    import auctionator_prices as ap
    text = path.read_bytes().decode("latin-1")
    m = re.search(rf"^{variable}\s*=\s*", text, re.M)
    if not m:
        return None
    reader = ap.LuaReader(text)
    reader.i = m.end()
    return reader.value()


def parse_addon_ladders(table):
    """WaylaidHelperCharDB.markets.favor -> (scan time, {item: [(unit price, units), ...]}).

    Rows marked guess only promise units at no less than that price; they are kept as the addon keeps them."""
    market = ((table or {}).get("markets") or {}).get("favor") or {}
    ladders = {}
    for item, rows in (market.get("ladders") or {}).items():
        rows = rows.values() if isinstance(rows, dict) else rows
        levels = [(int(r["price"]), int(r["qty"])) for r in rows if isinstance(r, dict) and r.get("price") and r.get("qty")]
        if levels:
            ladders[int(item)] = levels
    return market.get("time"), ladders


def addon_scan(root):
    """The newest in-game Waylaid Auction Helper scan of any character: (path, scan time, ladders) or None."""
    best = None
    for path in forever_dir(root).glob("WTF/Account/*/*/*/SavedVariables/WaylaidHelper.lua"):
        when, ladders = parse_addon_ladders(lua_table(path, "WaylaidHelperCharDB"))
        if ladders and (best is None or when > best[1]):
            best = (path, when, ladders)
    return best


def auctionator_levels(root):
    """Last Auctionator full scan: (saved time, {item: [(lowest unit price, units seen that day)]}) or None."""
    import auctionator_prices as ap
    path = next(iter(ap.find_saved_files(root)), None)
    if not path:
        return None
    realms = ap.load_price_db(path)
    realm = max(realms, key=lambda k: len(realms[k]) if isinstance(realms[k], dict) else 0, default=None)
    levels = {}
    for key, rec in (realms.get(realm) or {}).items():
        m = re.match(r"(?:[a-z]+:)?(\d+)$", str(key))
        if not m or not isinstance(rec, dict) or not rec.get("m"):
            continue
        avail = rec.get("a") or {}
        day = max(avail, key=lambda d: int(d), default=None)
        levels[int(m.group(1))] = [(int(rec["m"]), int(avail[day]) if day is not None else 1)]
    return path.stat().st_mtime, levels


def owned_items(root):
    """Every character's bags, bank and mail from Syndicator: {item: units}."""
    import syndicator_inventory as si
    files = si.find_saved_files(root)
    if not files:
        sys.exit("Syndicator.lua not found; /reload in game so Syndicator writes it")
    owned = {}
    for character in si.load_data(files[0]).get("Characters", {}).values():
        for part in si.summarise(character).values():
            for item in part["items"]:
                owned[item["id"]] = owned.get(item["id"], 0) + item["count"]
    return owned


def local_time(seconds):
    """Unix seconds -> '11/24 00:38' Taiwan time."""
    import datetime
    if not seconds:
        return "時間不明"
    return datetime.datetime.fromtimestamp(seconds, ac.TAIPEI).strftime("%m/%d %H:%M")


def gold(copper):
    return ac.coin(None if copper is None else round(copper))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default="/Applications/World of Warcraft", help="WoW install root holding _forever_")
    parser.add_argument("--goal", type=int, default=300, help="Merchant's Favor to reach (default 300)")
    parser.add_argument("--level", type=int, help="character level; leaves out crates that need more")
    parser.add_argument("--top", type=int, default=10, help="overview rows to print (0 hides it)")
    parser.add_argument("--list", default=None, help="Auctionator list name (default: 木箱貢獻<goal>)")
    parser.add_argument("--owned", action="store_true",
                        help="count every character's crates and materials (Syndicator); owned crates are optional")
    parser.add_argument("--keep", nargs="+", type=int, default=[], metavar="ITEM",
                        help="--owned: item ids to keep out of the crates, e.g. bars a profession still needs")
    parser.add_argument("--scan", action="store_true",
                        help="prefer the newest in-game Waylaid Auction Helper scan (price levels) per item")
    parser.add_argument("--auctionator", action="store_true",
                        help="prefer the last Auctionator full scan (lowest price, units) for items the addon scan lacks")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "wowamobi-cache")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    data = addon_data(args.root)
    if not data.exists():
        sys.exit(f"Waylaid Auction Helper not found: {data}")
    kinds = parse_crates(data.read_text(encoding="utf-8"), args.level)
    levels, modified = ac.live_levels()
    sources = [f"部落拍賣場 API 快照 {taiwan_time(modified)}"]
    scanned = {}
    if args.auctionator:
        got = auctionator_levels(args.root)
        if got:
            when, prices = got
            scanned.update({i: ("Auctionator", p) for i, p in prices.items()})
            sources.append(f"Auctionator 完整掃描（存檔 {local_time(when)}，只有最低價與件數）")
    if args.scan:
        got = addon_scan(args.root)
        if got:
            _, when, ladders = got
            scanned.update({i: ("插件掃描", p) for i, p in ladders.items()})
            sources.append(f"遭攔截木箱助手掃描 {local_time(when)}（{len(ladders)} 樣）")
    for item, (_, rows) in scanned.items():
        levels[item] = rows
    if args.owned:
        levels = with_owned(levels, owned_items(args.root), kinds, set(args.keep))
        sources.append("自有庫存：Syndicator 全部角色")
    meta = ac.load_market(args.cache, 6).get("meta", {})
    english = {k["id"]: k["name"] for k in kinds}

    def name_of(item):
        row = meta.get(str(item))
        return row[0] if row else english.get(item, str(item))

    rows, result = overview(kinds, levels), plan(kinds, levels, args.goal)
    line = import_line(result, name_of, args.list or f"木箱貢獻{args.goal}")
    if args.json:
        print(json.dumps({"snapshot": modified, "sources": sources, "overview": rows, "plan": result, "import": line},
                         ensure_ascii=False, indent=1, default=str))
        return

    print("價格：" + "；".join(sources) + "（台灣時間）"
          + (f"\n只算 {args.level} 級能填的木箱" if args.level else ""))
    if args.top:
        print("\n每 100 點貢獻的成本（一箱＋最便宜的一組，扣掉繳交退款）：")
        for r in rows[:args.top]:
            k = r["kind"]
            head = f"{name_of(k['id'])}（{k['favor']} 點，{k['level']} 級）"
            if r["per_favor"] is None:
                print(f"  --        {head}：箱子或材料沒貨")
                continue
            item, qty = r["bundle"]
            mine = f"，自有 {r['owned']}" if r["owned"] else ""
            print(f"  {gold(r['per_favor'] * 100):>9}  {head}：{name_of(item)} ×{qty}，一箱 {gold(r['cost'])}，箱子在售 {r['on_sale']}{mine}")
    print(f"\n{args.goal} 點購物清單：")
    for pick in result["picks"]:
        print(f"  {name_of(pick['kind']['id'])} ×{pick['count']}＝{pick['favor']} 點，淨 {gold(pick['cost'])}")
        for l in pick["lines"]:
            group = f"（{l['bundles']} 組，每組 {l['per']}）" if "bundles" in l else ""
            mine = f"，自有 {l['own']}、買 {l['buy']}" if l["own"] else ""
            src = f"，{scanned[l['item']][0]}" if l["buy"] and l["item"] in scanned else ""
            cost = f"買 {gold(l['cost'] - l['value'])}，最高單價 {gold(l['top'])}{src}" if l["buy"] else "全用自有"
            print(f"    {name_of(l['item'])} ×{l['units']}{group}{mine}  {cost}")
    if args.owned:
        unused = {r["kind"]["id"]: r["owned"] for r in rows if r["owned"]}
        for pick in result["picks"]:
            unused[pick["kind"]["id"]] = unused.get(pick["kind"]["id"], 0) - pick["lines"][0]["own"]
        left = "、".join(f"{name_of(i)} ×{n}" for i, n in unused.items() if n > 0)
        if left:
            print(f"  沒用到的自有木箱：{left}（填它們比買新箱子貴，先留著）")
    short = "，拍賣場的貨不夠達標" if result["favor"] < args.goal else ""
    print(f"合計 {result['favor']} 點，現金 {gold(result['cash'])}，退 {gold(result['refund'])}，"
          f"自有材料市值 {gold(result['value'])}，淨 {gold(result['cost'])}{short}")
    if line:
        print("\n拍賣小幫手匯入：\n" + line)


if __name__ == "__main__":
    main()
