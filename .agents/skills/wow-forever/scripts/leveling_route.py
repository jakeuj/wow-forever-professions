#!/usr/bin/env python3
"""Plan the cheapest way to level a WoW Forever crafting profession at Horde auction prices.

Recipes, skill colours, reagents, NPC sale and vendor sell prices come from
wowamobi.com; prices and listing counts from the owner's Auctionator full scan
(or the market page's data.json). Trainer recipes have no "requires N" on Amobi,
so their learn skill comes from data/wowf-learn-skill-<profession>.json.

Each skill point goes to the recipe with the lowest expected net cost:
(reagents - vendor sell price) / chance, where the chance is 1 below yellow and
(grey - skill) / (grey - yellow) from yellow to grey. A plan that saves less than
its price over the route is dropped. Prices are listing prices, never sale prices.
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
import auctionator_prices as ap  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
SELL = re.compile(r'class="wl w sell">售價：(.*?)</div>', re.S)


def parse_profession(page):
    """Every recipe on /professions/<slug>, trainer ones included."""
    recipes = []
    for li in re.findall(r'<li class="pf-r"(.*?)</li>', page, re.S):
        hd = re.search(r'<p class="hd">(.*?)</p>', li, re.S)
        colours = hd and re.search(r'title="技能點數：變黃 (\d+)、變綠 (\d+)、變灰 (\d+)"', hd.group(1))
        name = hd and re.search(r'class="nm[^"]*"(?: href="/items/(\d+)")?>([^<]+)<', hd.group(1))
        if not colours or not name:
            continue
        qty = re.search(r"<em>×(\d+)</em>", hd.group(1))
        recipe = re.search(r'<span class="lm recipe">[^<]*</span><a[^>]*href="/items/(\d+)">([^<]+)</a>'
                           r'(?:<small>需要 (\d+)</small>)?', li)
        mats_html = re.search(r'<span class="k">材料</span><span class="v">(.*?)</span></p>', li, re.S)
        mats = [(int(m.group(1)), html.unescape(m.group(2)), int(m.group(3) or 1))
                for m in re.finditer(r'href="/items/(\d+)">([^<]+)</a>(?:<em>×(\d+)</em>)?',
                                     mats_html.group(1))] if mats_html else []
        recipes.append({
            "name": html.unescape(name.group(2)),
            "item_id": int(name.group(1)) if name.group(1) else None,
            "qty": int(qty.group(1)) if qty else 1,
            "learn": re.search(r'data-learn="([^"]*)"', li).group(1),
            "recipe_id": int(recipe.group(1)) if recipe else None,
            "recipe": html.unescape(recipe.group(2)) if recipe else None,
            "need": int(recipe.group(3)) if recipe and recipe.group(3) else None,
            "yellow": int(colours.group(1)), "green": int(colours.group(2)), "grey": int(colours.group(3)),
            "mats": mats,
        })
    return recipes


def load_scan(args):
    """{item id: (lowest buyout, listed count)} and a label for the source."""
    if args.market_json:
        data = json.loads(Path(args.market_json).read_text(encoding="utf-8"))
        col = {k: data["fields"].index(k) for k in ("id", "price", "count")}
        prices = {r[col["id"]]: (r[col["price"]], r[col["count"]]) for r in data["items"] if r[col["price"]]}
        return prices, f"行情頁資料（存檔 {data.get('savedAt', '?')}）"
    path = args.file or next(iter(ap.find_saved_files(args.root)), None)
    if path is None or not path.is_file():
        sys.exit("Auctionator.lua not found; /reload in game first, or pass --market-json market/data.json")
    realms = ap.load_price_db(path)
    items = realms[max(realms, key=lambda k: len(realms[k]) if isinstance(realms[k], dict) else 0)]
    prices = {}
    for key, rec in items.items():
        m = re.match(r"(?:[a-z]+:)?(\d+)", str(key))
        if not m or not isinstance(rec, dict) or not rec.get("m"):
            continue
        days = sorted({int(d) for d in list(rec.get("l") or {}) + list(rec.get("h") or {})})
        avail = rec.get("a") or {}
        count = avail.get(str(days[-1]), avail.get(days[-1])) if days else None
        item_id = int(m.group(1))
        if item_id not in prices or rec["m"] < prices[item_id][0]:
            prices[item_id] = (rec["m"], count)
    saved = datetime.datetime.fromtimestamp(path.stat().st_mtime)
    return prices, f"拍賣小幫手存檔（{saved:%Y-%m-%d %H:%M}）"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profession", default="blacksmithing", help="wowamobi slug, e.g. blacksmithing")
    parser.add_argument("--from", dest="start", type=int, required=True, help="current skill")
    parser.add_argument("--to", dest="end", type=int, default=300)
    parser.add_argument("--gate", type=int, default=225, help="rank cap that needs the next trainer rank (Artisan: 225)")
    parser.add_argument("--learn-skills", type=Path, help="wowf learn-skill JSON (default: data/wowf-learn-skill-<profession>.json)")
    parser.add_argument("--faction", default="部落", choices=["部落", "聯盟"])
    parser.add_argument("--neutral", action="store_true", help="also buy from neutral AH listings Amobi saw in the last two days")
    parser.add_argument("--no-vendor-sale", action="store_true", help="do not subtract the vendor sell price of crafted items")
    parser.add_argument("--market-json", help="read prices from the market page's data.json instead of the Auctionator save")
    parser.add_argument("--root", default="/Applications/World of Warcraft")
    parser.add_argument("--file", type=Path, help="a specific Auctionator.lua")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "wowamobi-cache")
    parser.add_argument("--max-age", type=float, default=24, help="hours Amobi pages stay cached")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    args.cache.mkdir(parents=True, exist_ok=True)
    get = lambda url, name: av.fetch(url, args.cache, name, args.max_age, 0.4)
    recipes = parse_profession(get(f"{av.BASE}/professions/{args.profession}", f"profession-{args.profession}.html"))
    if not recipes:
        sys.exit("no recipes parsed; the profession page layout may have changed")
    learn_path = args.learn_skills or SKILL_DIR / "data" / f"wowf-learn-skill-{args.profession}.json"
    learn = {r["name"]: r for r in json.loads(learn_path.read_text(encoding="utf-8"))["recipes"]} if learn_path.is_file() else {}
    other = "聯盟" if args.faction == "部落" else "部落"
    for r in recipes:
        w = learn.get(r["name"], {})
        r["orange"] = r["need"] if r["need"] is not None else w.get("skill")
        r["blocked"] = w.get("faction") == other
    scan, scan_label = load_scan(args)

    today = datetime.date.today()
    recent_days = {(today - datetime.timedelta(days=d)).strftime("%m/%d") for d in (0, 1)}
    pages = {}
    def page(item_id):
        if item_id not in pages:
            text = get(f"{av.BASE}/items/{item_id}", f"item-{item_id}.html")
            info = av.parse_item_page(text)
            sell = SELL.search(text)
            info["sell"] = (av.coins(sell.group(1)) or 0) if sell else 0
            pages[item_id] = info
        return pages[item_id]

    def buy(item_id):
        """Cheapest way to buy one: (copper, where) or (None, why)."""
        options = []
        if item_id in scan:
            options.append((scan[item_id][0], f"{args.faction}拍賣場 {scan[item_id][1] or '?'} 件"))
        info = page(item_id)
        for v in info["vendors"]:
            if not v["limited"] and v["unit_price"]:
                options.append((v["unit_price"], f"NPC {v['npc']}（{v['zone']}）"))
        seen = info["faction_seen"].get("中立拍賣場", "")
        if args.neutral and "中立拍賣場" in info["faction_min"] and seen[:5] in recent_days:
            options.append((info["faction_min"]["中立拍賣場"], f"中立 {seen}"))
        return min(options) if options else (None, "沒貨")

    producers = {}
    for r in recipes:
        if r["learn"] == "trainer" and r["item_id"] and (r["orange"] or 999) <= args.start and not r["blocked"]:
            producers.setdefault(r["item_id"], []).append(r)
    memo = {}
    def mat_cost(item_id, depth=0):
        if item_id in memo:
            return memo[item_id]
        best = buy(item_id)
        if depth < 3:
            for r in producers.get(item_id, []):
                c = craft_cost(r, depth + 1)
                if c is not None and (best[0] is None or c / r["qty"] < best[0]):
                    best = (c / r["qty"], f"自製（{r['name']}）")
        memo[item_id] = best
        return best
    def craft_cost(r, depth=0):
        total = 0
        for item_id, _, qty in r["mats"]:
            c, _ = mat_cost(item_id, depth)
            if c is None:
                return None
            total += c * qty
        return total

    def chance(r, s):
        if r["orange"] is None or s < r["orange"] or s >= r["grey"]:
            return 0
        return 1 if s < r["yellow"] else (r["grey"] - s) / (r["grey"] - r["yellow"])

    pool, missing_plans = [], []
    for r in recipes:
        if r["blocked"] or r["grey"] <= args.start or (r["orange"] or 999) >= args.end:
            continue
        cost = craft_cost(r)
        if cost is None:
            continue
        r["cost"] = cost
        r["sell"] = 0 if args.no_vendor_sale or not r["item_id"] else page(r["item_id"])["sell"] * r["qty"]
        r["net"] = cost - r["sell"]
        if r["learn"] in ("trainer", "auto"):
            r["acquire"], r["acquire_from"] = 0, "訓練師"
        else:
            r["acquire"], r["acquire_from"] = buy(r["recipe_id"])
            if r["acquire"] is None:
                missing_plans.append(r)
                continue
        pool.append(r)

    def route(candidates):
        steps = []
        for s in range(args.start, args.end):
            options = [(r["net"] / chance(r, s), r["name"]) for r in candidates if chance(r, s) > 0]
            if not options:
                return None
            steps.append(min(options))
        return steps
    active = list(pool)
    while True:
        steps = route(active)
        if steps is None:
            sys.exit("no obtainable recipe covers every skill point; try --neutral")
        used = {name for _, name in steps}
        worst = None
        for r in active:
            if r["acquire"] <= 0 or r["name"] not in used:
                continue
            alt = route([x for x in active if x is not r])
            if alt is None:
                continue
            saving = sum(e for e, _ in alt) - sum(e for e, _ in steps)
            if saving < r["acquire"] and (worst is None or r["acquire"] - saving > worst[0]):
                worst = (r["acquire"] - saving, r)
        if not worst:
            break
        active.remove(worst[1])

    by_name = {r["name"]: r for r in active}
    segments = []
    for s, (_, name) in zip(range(args.start, args.end), steps):
        phase = 1 if s < args.gate else 2
        if segments and segments[-1]["recipe"] == name and segments[-1]["phase"] == phase:
            segments[-1]["to"] = s + 1
        else:
            segments.append({"recipe": name, "from": s, "to": s + 1, "phase": phase})

    def expand(item_id, name, qty, need):
        cost, how = mat_cost(item_id)
        if how.startswith("自製"):
            r = next(x for x in producers[item_id] if x["name"] in how)
            for mid, mname, mq in r["mats"]:
                expand(mid, mname, qty * mq / r["qty"], need)
        else:
            need.setdefault(item_id, {"id": item_id, "name": name, "qty": 0, "unit": cost, "from": how})
            need[item_id]["qty"] += qty

    phases = {}
    for seg in segments:
        r = by_name[seg["recipe"]]
        crafts = sum(1 / chance(r, s) for s in range(seg["from"], seg["to"]))
        seg.update(crafts=round(crafts, 1), cost=r["cost"], sell=r["sell"], mats=[[n, q] for _, n, q in r["mats"]],
                   item_id=r["item_id"], learn=r["acquire_from"], plan=r["recipe"] if r["acquire"] else None,
                   plan_id=r["recipe_id"] if r["acquire"] else None, plan_price=r["acquire"],
                   yellow=r["yellow"], grey=r["grey"], orange=r["orange"])
        ph = phases.setdefault(seg["phase"], {"phase": seg["phase"], "gross": 0, "vendor": 0, "need": {}})
        ph["gross"] += r["cost"] * crafts
        ph["vendor"] += r["sell"] * crafts
        for item_id, name, qty in r["mats"]:
            expand(item_id, name, qty * crafts, ph["need"])
    for ph in phases.values():
        mats = sorted(ph.pop("need").values(), key=lambda m: -m["qty"] * m["unit"])
        for m in mats:
            m["qty"] = round(m["qty"])
            m["subtotal"] = m["qty"] * m["unit"]
            m["listed"] = scan.get(m["id"], (None, None))[1]
            m["short"] = m["listed"] is not None and m["listed"] < m["qty"]
        ph["materials"] = mats
        ph["gross"] = sum(m["subtotal"] for m in mats)  # what the rounded shopping list costs
        ph["net"] = ph["gross"] - ph["vendor"]
    better_missing = []
    for r in missing_plans:
        points = [s for s, (e, _) in zip(range(args.start, args.end), steps)
                  if chance(r, s) > 0 and r["net"] / chance(r, s) < 0.8 * e]
        if points:
            info = page(r["recipe_id"])
            seen = "；".join(f"{k} {av.gold(v)}（{info['faction_seen'].get(k, '')}）" for k, v in info["faction_min"].items())
            better_missing.append({"plan": r["recipe"], "from": min(points), "to": max(points) + 1, "net": r["net"], "last_seen": seen})

    result = {"profession": args.profession, "from": args.start, "to": args.end, "gate": args.gate,
              "prices": scan_label, "segments": segments, "phases": [phases[k] for k in sorted(phases)],
              "missing_plans": better_missing}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return
    g = lambda c: f"{c / 10000:.2f}g"
    print(f"{args.profession} {args.start}→{args.end}・價格：{scan_label}・掛單價，非成交價")
    for seg in segments:
        print(f"{seg['from']}→{seg['to']} {seg['recipe']} 約 {seg['crafts']:.0f} 次｜每次材料 {g(seg['cost'])}、賣店 {g(seg['sell'])}｜"
              f"{seg['plan'] + ' ' + g(seg['plan_price']) + '（' + seg['learn'] + '）' if seg['plan'] else seg['learn']}｜"
              + "、".join(f"{n}×{q}" for n, q in seg["mats"]))
    for ph in result["phases"]:
        label = f"到 {args.gate}" if ph["phase"] == 1 else f"{args.gate} 以後（要先學下一階）"
        print(f"\n階段 {ph['phase']}（{label}）：材料 {g(ph['gross'])}、賣店收回 {g(ph['vendor'])}、淨 {g(ph['net'])}")
        for m in ph["materials"]:
            short = "，不夠" if m["short"] else ""
            print(f"  {m['name']} ×{m['qty']}（{g(m['unit'])}，{m['from']}{short}）= {g(m['subtotal'])}")
    if better_missing:
        print("\n目前買不到、但比路線便宜的配方：")
        for m in better_missing:
            print(f"  {m['plan']} 可用在 {m['from']}–{m['to']}，每次淨 {g(m['net'])}；{m['last_seen'] or '阿莫比沒紀錄'}")


if __name__ == "__main__":
    main()
