#!/usr/bin/env python3
"""Rank a profession's recipe items by Forever auction-house value using wowamobi.com.

Reads only public wowamobi.com pages and the JSON the market page itself loads.
Prices are listing (buyout) prices, never sale prices. All money is in copper
internally and printed as gold.
"""

import argparse
import html
import json
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.request

BASE = "https://wowamobi.com"
USER_AGENT = "Mozilla/5.0 (compatible; wow-forever-skill)"
AH_CUT = 0.05
FACTIONS = ("聯盟", "部落", "中立拍賣場")


def fetch(url, cache, name, max_age_hours, delay):
    path = cache / name
    if path.is_file() and time.time() - path.stat().st_mtime < max_age_hours * 3600:
        return path.read_text(encoding="utf-8")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    path.write_text(text, encoding="utf-8")
    time.sleep(delay)
    return text


def coins(fragment):
    """Sum <span class="coin g|s|c">N</span> pieces into copper."""
    unit = {"g": 10000, "s": 100, "c": 1}
    pieces = re.findall(r'class="coin ([gsc])">([\d,]+)', fragment)
    if not pieces:
        return None
    return sum(int(value.replace(",", "")) * unit[kind] for kind, value in pieces)


def text_of(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def parse_recipes(page):
    recipes = []
    for li in re.findall(r'<li class="pf-r"(.*?)</li>', page, re.S):
        hd = re.search(r'<p class="hd">(.*?)</p>', li, re.S)
        product = hd and re.search(r'href="/items/(\d+)">([^<]+)</a>(?:\s*<em>×(\d+)</em>)?', hd.group(1))
        recipe = re.search(
            r'<span class="lm recipe">[^<]*</span><a[^>]*href="/items/(\d+)">([^<]+)</a>'
            r'(?:<small>需要 (\d+)</small>)?', li)
        if not hd or not recipe:
            continue
        if not product:
            # Enchants and other spell-only results have a name but no item to price.
            name = re.search(r'<span class="nm">([^<]+)</span>', hd.group(1))
            if not name:
                continue
            product = (None, name.group(1), None)
            product_id, product_name, product_qty = None, html.unescape(name.group(1)), 1
        else:
            product_id, product_name = int(product.group(1)), html.unescape(product.group(2))
            product_qty = int(product.group(3) or 1)
        mats_html = re.search(r'<span class="k">材料</span><span class="v">(.*?)</span></p>', li, re.S)
        mats = []
        if mats_html:
            for m in re.finditer(r'href="/items/(\d+)">([^<]+)</a>(?:<em>×(\d+)</em>)?', mats_html.group(1)):
                mats.append({"id": int(m.group(1)), "name": html.unescape(m.group(2)), "qty": int(m.group(3) or 1)})
        effect = re.search(r'<span class="k">效果</span><span class="v">(.*?)</p>', li, re.S)
        recipes.append({
            "recipe_id": int(recipe.group(1)),
            "recipe": html.unescape(recipe.group(2)),
            "skill": int(recipe.group(3)) if recipe.group(3) else None,
            "product_id": product_id,
            "product": product_name,
            "product_qty": product_qty,
            "forever_new": "pf-new" in hd.group(1),
            "mats": mats,
            "effect": text_of(effect.group(1)) if effect else "",
        })
    return recipes


def parse_item_page(page):
    """Per-faction lowest buyout and NPC vendors from an item page.

    The faction block belongs to whichever realm the page headlines (usually the
    realm that saw the item last), so callers must compare `realm` first.
    """
    info = {"realm": None, "factions": [], "faction_min": {}, "faction_seen": {}, "vendors": []}
    realm = re.search(r"(CAMWOW [^・<]+)・([^<・]*)・[^<]*全掃描", page)
    if realm:
        info["realm"] = realm.group(1).strip()
        info["factions"] = [f.strip() for f in realm.group(2).split("＋")]
    block = re.search(r"各陣營拍賣場最近看到的最低一口價</h3><ul>(.*?)</ul>", page, re.S)
    if block:
        for name, money, seen in re.findall(
                r"<li><span>([^<]+)</span><span class=\"ah-op\">(.*?)</span><small>([^<]*)</small>", block.group(1), re.S):
            if coins(money):
                info["faction_min"][name] = coins(money)
                info["faction_seen"][name] = seen.strip()
    player = re.search(r'<section class="card it-card it-player">(.*?)</section>', page, re.S)
    if player:
        vendor = re.search(r"<h3>商人</h3><ul[^>]*>(.*?)</ul>", player.group(1), re.S)
        if vendor:
            for li in re.findall(r"<li>(.*?)</li>", vendor.group(1), re.S):
                zone = re.search(r'class="cl-k">(.*?)</span>', li, re.S)
                npc = re.search(r'class="cl-n">(.*?)</span>', li, re.S)
                price = re.search(r'class="pl-price">(.*?)</span></span>', li, re.S)
                bundle = re.search(r"<i>一次 (\d+) 個</i>", li)
                bundle = int(bundle.group(1)) if bundle else 1
                price = coins(price.group(1)) if price else None
                info["vendors"].append({
                    "zone": text_of(zone.group(1)) if zone else "",
                    "npc": text_of(npc.group(1)) if npc else "",
                    "limited": "<i>限量</i>" in li,
                    "bundle": bundle,
                    "price": price,
                    "unit_price": price / bundle if price else None,
                })
    return info


def gold(copper):
    return "—" if copper is None else f"{copper / 10000:.2f}g"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profession", default="alchemy",
                        help="wowamobi slug: alchemy, blacksmithing, enchanting, engineering, leatherworking, tailoring, cooking, first-aid")
    parser.add_argument("--realm", default="CAMWOW TW4 Realm 2 PvP", help="realm name as shown on /market")
    parser.add_argument("--faction", choices=["部落", "聯盟"], help="add the lowest price this faction can reach (own AH or neutral)")
    parser.add_argument("--sources", action="store_true",
                        help="also fetch item pages: per-faction lowest buyout and NPC vendor prices for listed recipes and all reagents")
    parser.add_argument("--all", action="store_true", help="include recipes with no recipe-item listing on this realm")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "wowamobi-cache")
    parser.add_argument("--max-age", type=float, default=6, help="hours a cached page stays fresh; 0 refetches everything")
    parser.add_argument("--delay", type=float, default=0.4, help="seconds between uncached requests")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    args.cache.mkdir(parents=True, exist_ok=True)
    get = lambda url, name: fetch(url, args.cache, name, args.max_age, args.delay)

    market = json.loads(get(f"{BASE}/api/market/items", "market-items.json"))
    group = next((g for g in market["groups"] if g["realm"] == args.realm), None)
    if group is None:
        sys.exit("realm not found; choose from: " + ", ".join(g["realm"] for g in market["groups"]))
    # item row: [id, median, min_buyout, count, date, prev_median, prev_date]
    prices = {row[0]: row for row in group["items"]}
    recipes = parse_recipes(get(f"{BASE}/professions/{args.profession}", f"profession-{args.profession}.html"))
    if not recipes:
        sys.exit("no recipes parsed; the profession page layout may have changed")

    pages = {}
    if args.sources:
        wanted = {r["recipe_id"] for r in recipes if r["recipe_id"] in prices}
        wanted |= {m["id"] for r in recipes for m in r["mats"]}
        for item_id in sorted(wanted):
            pages[item_id] = parse_item_page(get(f"{BASE}/items/{item_id}", f"item-{item_id}.html"))

    rows = []
    for r in recipes:
        listing = prices.get(r["recipe_id"])
        if listing is None and not args.all:
            continue
        cost, missing = 0, []
        for m in r["mats"]:
            ah = prices.get(m["id"])
            # Only unlimited vendors set a dependable material price.
            vendor = [v["unit_price"] for v in pages.get(m["id"], {}).get("vendors", [])
                      if v["unit_price"] and not v["limited"]]
            unit = min([p for p in [ah[1] if ah else None, min(vendor) if vendor else None] if p is not None], default=None)
            if unit is None:
                missing.append(m["name"])
            else:
                cost += unit * m["qty"]
        product = prices.get(r["product_id"])
        value = product[1] * r["product_qty"] if product else None
        value_low = product[2] * r["product_qty"] if product else None
        page = pages.get(r["recipe_id"], {})
        same_realm = page.get("realm") == args.realm
        faction_min = page.get("faction_min", {}) if same_realm else {}
        if same_realm and not faction_min and len(page.get("factions", [])) == 1 and listing:
            # The page omits the per-faction block when only one auction house lists the item.
            faction_min = {page["factions"][0]: listing[2]}
        reach = None
        if args.faction:
            reachable = [faction_min.get(args.faction), faction_min.get("中立拍賣場")]
            reach = min([p for p in reachable if p], default=None)
        rows.append({
            **r,
            "recipe_median": listing[1] if listing else None,
            "recipe_min": listing[2] if listing else None,
            "recipe_count": listing[3] if listing else 0,
            "recipe_seen": listing[4] if listing else None,
            "faction_min": faction_min,
            "faction_seen": page.get("faction_seen", {}) if same_realm else {},
            "faction_reach": reach,
            "vendors": page.get("vendors", []),
            "item_page_realm": page.get("realm"),
            "product_median": product[1] if product else None,
            "product_min": product[2] if product else None,
            "product_count": product[3] if product else 0,
            "mat_cost": cost,
            "mats_missing": missing,
            "profit": value * (1 - AH_CUT) - cost if value is not None and not missing else None,
            "profit_at_min": value_low * (1 - AH_CUT) - cost if value_low is not None and not missing else None,
        })

    # Rank by the more conservative of median- and floor-based profit: one inflated
    # median listing should not push a recipe to the top.
    def rank(x):
        known = [p for p in (x["profit"], x["profit_at_min"]) if p is not None]
        return (not known, -min(known) if known else 0)

    rows.sort(key=rank)
    if args.json:
        print(json.dumps({"realm": args.realm, "scanned": group.get("lastFull"), "rows": rows}, ensure_ascii=False, indent=1))
        return

    latest = "{}/{}".format(*(int(p) for p in group["latest"].split("-")[1:]))
    print(f"{args.realm}・{args.profession}・最近全掃描 {time.strftime('%Y-%m-%d %H:%M', time.localtime(group['lastFull']))}")
    print("毛利＝成品（中位數／最低一口價）×數量×0.95−材料中位數（不限量 NPC 單價較低時取 NPC），依兩者較低值排序；都是掛單價。")
    for x in rows:
        line = (f"{x['recipe']}（需 {x['skill']}）配方 中位 {gold(x['recipe_median'])} 最低 {gold(x['recipe_min'])}"
                f" ×{x['recipe_count']}")
        if x["faction_min"]:
            def seen(k):
                day = x["faction_seen"].get(k, "").split(" ")[0]
                return f"（{day} 看到）" if day and day != latest else ""
            line += " | " + " ".join(f"{k[:2]} {gold(v)}{seen(k)}" for k, v in x["faction_min"].items() if k in FACTIONS)
        elif args.sources and x["recipe_count"] and x["item_page_realm"] != args.realm:
            line += f" | 分陣營價：物品頁顯示的是 {x['item_page_realm'] or '未知伺服器'}，已略過"
        if args.faction:
            line += f" | {args.faction}可買 {gold(x['faction_reach'])}"
        npc = [v for v in x["vendors"] if v["price"]]
        if npc:
            line += " | NPC " + "、".join(f"{v['zone']} {v['npc']} {gold(v['price'])}{'（限量）' if v['limited'] else ''}" for v in npc)
        line += (f" | 成品 {x['product']}×{x['product_qty']} 中位 {gold(x['product_median'])} 最低 {gold(x['product_min'])}"
                 f" 上架 {x['product_count']}"
                 f" | 材料 {gold(x['mat_cost'])}{' 缺價：' + '、'.join(x['mats_missing']) if x['mats_missing'] else ''}"
                 f" | 毛利 中位 {gold(x['profit'])}／最低 {gold(x['profit_at_min'])}{' | 永恆新增' if x['forever_new'] else ''}")
        print(line)


if __name__ == "__main__":
    main()
