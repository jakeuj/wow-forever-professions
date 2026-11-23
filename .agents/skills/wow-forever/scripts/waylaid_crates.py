#!/usr/bin/env python3
"""Cheapest Waylaid Crates (遭攔截的木箱) for Merchant's Favor on the Horde auction house.

Crates and their bundles come from the installed Waylaid Auction Helper
(WaylaidHelper/Data.lua), prices from one live request to the official auction
API (units at each unit price). The maths follows the addon's Optimizer.lua:
a crate costs the crate plus its cheapest bundle, less the copper a Sealed
Crate pays back; filling k crates walks up the price levels; a knapsack over
favor picks how many of each kind reach the goal. Bags and bank are not
counted, so the list is what to buy.

    python3 waylaid_crates.py --root 'F:\\Program Files (x86)\\World of Warcraft' --level 34
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


def take(levels, skip, n):
    """(copper, dearest unit price) for `n` units after the cheapest `skip`, or None when the house runs dry."""
    cost = top = 0
    for price, qty in levels:
        if skip >= qty:
            skip -= qty
            continue
        got = min(qty - skip, n)
        skip = 0
        cost, top, n = cost + got * price, max(top, price), n - got
        if n == 0:
            return cost, top
    return None


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
        row = {"kind": kind, "on_sale": sum(q for _, q in levels.get(kind["id"], [])), "cost": None,
               "per_favor": None, "bundle": None}
        if step:
            row.update(cost=step["spend"], per_favor=step["total"] / kind["favor"], bundle=kind["bundles"][step["bundle"]])
        rows.append(row)
    rows.sort(key=lambda r: (r["per_favor"] is None, r["per_favor"] or 0, r["kind"]["id"]))
    return rows


def plan(kinds, levels, goal):
    """Cheapest crates worth at least `goal` favor: {favor, cost, spend, picks=[{kind, count, cost, spend, lines}]}.

    A line is {item, units, cost, top} for the crates and for each bundle used. Favor below the goal means the
    house cannot reach it."""
    options = [(k, curve(k, levels, math.ceil(goal / k["favor"]))) for k in kinds]
    options = [(k, c) for k, c in options if c]
    result = {"goal": goal, "favor": 0, "cost": 0, "spend": 0, "picks": []}
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
        lines = [dict(zip(("cost", "top"), take(levels.get(kind["id"], []), 0, count)), item=kind["id"], units=count)]
        for i, bundles in sorted(uses.items()):
            item, qty = kind["bundles"][i]
            lines.append(dict(zip(("cost", "top"), take(levels.get(item, []), 0, bundles * qty)), item=item,
                              units=bundles * qty, bundles=bundles, per=qty))
        step = steps[count - 1]
        result["picks"].append({"kind": kind, "count": count, "favor": count * kind["favor"], "cost": step["total"],
                                "spend": step["spend"], "lines": lines})
        result["favor"] += count * kind["favor"]
        result["cost"] += step["total"]
        result["spend"] += step["spend"]
    result["picks"].sort(key=lambda p: p["cost"] / p["favor"])
    return result


def import_line(result, name_of, title):
    """Auctionator import: exact names, quantity, and the dearest planned unit price (rounded up to silver) as max."""
    terms = []
    for pick in result["picks"]:
        for line in pick["lines"]:
            fields = search_term(name_of(line["item"]), line["units"]).split(";")
            fields[9] = f"{max(1, math.ceil(line['top'] / 100)) / 100:.2f}"  # 0 would mean no cap
            terms.append(";".join(fields))
    return "^".join([title] + terms) if terms else None


def gold(copper):
    return ac.coin(None if copper is None else round(copper))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default="/Applications/World of Warcraft", help="WoW install root holding _forever_")
    parser.add_argument("--goal", type=int, default=300, help="Merchant's Favor to reach (default 300)")
    parser.add_argument("--level", type=int, help="character level; leaves out crates that need more")
    parser.add_argument("--top", type=int, default=10, help="overview rows to print (0 hides it)")
    parser.add_argument("--list", default=None, help="Auctionator list name (default: 木箱貢獻<goal>)")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "wowamobi-cache")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    data = addon_data(args.root)
    if not data.exists():
        sys.exit(f"Waylaid Auction Helper not found: {data}")
    kinds = parse_crates(data.read_text(encoding="utf-8"), args.level)
    levels, modified = ac.live_levels()
    meta = ac.load_market(args.cache, 6).get("meta", {})
    english = {k["id"]: k["name"] for k in kinds}

    def name_of(item):
        row = meta.get(str(item))
        return row[0] if row else english.get(item, str(item))

    rows, result = overview(kinds, levels), plan(kinds, levels, args.goal)
    line = import_line(result, name_of, args.list or f"木箱貢獻{args.goal}")
    if args.json:
        print(json.dumps({"snapshot": modified, "overview": rows, "plan": result, "import": line},
                         ensure_ascii=False, indent=1, default=str))
        return

    print(f"部落拍賣場即時快照 {taiwan_time(modified)}（台灣時間）"
          + (f"，只算 {args.level} 級能填的木箱" if args.level else ""))
    if args.top:
        print("\n每 100 點貢獻的成本（一箱＋最便宜的一組，扣掉繳交退款）：")
        for r in rows[:args.top]:
            k = r["kind"]
            head = f"{name_of(k['id'])}（{k['favor']} 點，{k['level']} 級）"
            if r["per_favor"] is None:
                print(f"  --        {head}：箱子或材料沒貨")
                continue
            item, qty = r["bundle"]
            print(f"  {gold(r['per_favor'] * 100):>9}  {head}：{name_of(item)} ×{qty}，一箱 {gold(r['cost'])}，箱子在售 {r['on_sale']}")
    print(f"\n{args.goal} 點購物清單：")
    for pick in result["picks"]:
        print(f"  {name_of(pick['kind']['id'])} ×{pick['count']}＝{pick['favor']} 點，淨 {gold(pick['cost'])}")
        for l in pick["lines"]:
            group = f"（{l['bundles']} 組，每組 {l['per']}）" if "bundles" in l else ""
            print(f"    {name_of(l['item'])} ×{l['units']}{group}  {gold(l['cost'])}，最高單價 {gold(l['top'])}")
    short = "，拍賣場的貨不夠達標" if result["favor"] < args.goal else ""
    print(f"合計 {result['favor']} 點，買 {gold(result['spend'])}，淨 {gold(result['cost'])}{short}")
    if line:
        print("\n拍賣小幫手匯入：\n" + line)


if __name__ == "__main__":
    main()
