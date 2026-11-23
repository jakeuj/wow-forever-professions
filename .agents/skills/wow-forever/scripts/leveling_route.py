#!/usr/bin/env python3
"""Plan the cheapest way to level a WoW Forever crafting profession at Horde auction prices.

Recipes, skill colours, reagents, NPC sale and vendor sell prices come from
wowamobi.com; prices and listing counts from the owner's Auctionator full scan
(or the market page's data.json). Trainer recipes have no "requires N" on Amobi,
so their learn skill comes from data/wowf-learn-skill-<profession>.json.

Skill points are walked in order. Each goes to the recipe with the lowest expected
net cost, (reagents - vendor sell price) / chance, where the chance is 1 below yellow
and (grey - skill) / (grey - yellow) from yellow to grey. Reagents come from the
cheapest source with stock left: the Horde listings (used up as the route buys them),
unlimited NPC vendors, or a trainer recipe already learned at that skill. Units beyond
the listings cost SHORT_PENALTY times the lowest price, so the route moves to another
recipe when it can and otherwise reports the shortfall. A plan that saves less than
its price over the route is dropped. Each segment also gets a spare-craft count
(90th percentile minus the expected crafts). Prices are lowest listing prices, never
sale prices; buying in bulk costs more than the listed total suggests.

Quick use for the owner's main character (slug from ~/.config/wow-forever/local.md):

    python3 leveling_route.py --me

--me = --character <slug> --live --bags. --character reads the current skill, its
cap, the character level and learned recipes from the Battle.net API, so --from and
--to default to the current skill and its cap; mining skill unlocks smelting
(steel = iron bar + coal) as a way to make bars. --live prices from the current
Horde API snapshot instead of a scan. --bags reads the Syndicator save: plans any
character holds cost nothing, and the material list shows what you already have
and what is left to buy. Holdings do not change which recipe is picked: owned
materials still count at market price, since they could be sold instead.
"""

import argparse
import datetime
import html
import json
import math
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import amobi_recipe_value as av  # noqa: E402
import auctionator_prices as ap  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
SHORT_PENALTY = 3  # price factor for units beyond the listed count when choosing recipes
P90 = 1.2816  # z for the 90th percentile of the craft count
SELL = re.compile(r'class="wl w sell">售價：(.*?)</div>', re.S)
REPO = SKILL_DIR.parents[2]
PROFESSION_IDS = {"alchemy": 171, "blacksmithing": 164, "enchanting": 333, "engineering": 202,
                  "leatherworking": 165, "tailoring": 197, "cooking": 185, "first-aid": 129}
MINING = 186
HOME_TOWNS = {"部落": ("奧格瑪", "幽暗城", "雷霆崖"), "聯盟": ("暴風城", "鐵爐堡", "達納蘇斯")}
GATE_LEVEL = {75: 10, 150: 20, 225: 35}  # passing this skill cap needs the next trainer rank, learnable at this level
# Smelting a blacksmith route can use to make bars; Forever keeps the Classic recipes and mining
# skills (steel = iron bar + coal, confirmed in game 2026-11-23).
SMELTS = [
    {"name": "熔煉鐵", "item_id": 3575, "mats": [(2772, "鐵礦石", 1)], "mining": 125},
    {"name": "熔煉金", "item_id": 3577, "mats": [(2776, "金礦石", 1)], "mining": 155},
    {"name": "熔煉鋼", "item_id": 3859, "mats": [(3575, "鐵錠", 1), (3857, "煤塊", 1)], "mining": 165},
    {"name": "熔煉秘銀", "item_id": 3860, "mats": [(3858, "秘銀礦石", 1)], "mining": 175},
    {"name": "熔煉真銀", "item_id": 6037, "mats": [(7911, "真銀礦石", 1)], "mining": 230},
    {"name": "熔煉瑟銀", "item_id": 12359, "mats": [(10620, "瑟銀礦石", 1)], "mining": 250},
]


def smelt_producers(mining_skill):
    """Smelting recipes usable at this mining skill, shaped like trainer producers."""
    return [{"name": s["name"], "item_id": s["item_id"], "qty": 1, "mats": s["mats"], "orange": 0,
             "learn": "trainer", "blocked": False} for s in SMELTS if mining_skill and mining_skill >= s["mining"]]


def local_slug(path):
    """The API slug the local notes record for the main character, or None."""
    try:
        text = Path(path).expanduser().read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    m = re.search(r"API 角色 slug[^`\n]*`([^`]+)`", text)
    return m.group(1) if m else None


def learned_names(known_ids, profession):
    """Battle.net recipe ids -> the zhTW recipe names the site's recipe library uses."""
    path = REPO / "crafting-leveling" / "auto-recipes.json"
    if not path.is_file():
        return set()
    recipes = json.loads(path.read_text(encoding="utf-8"))["professions"].get(profession, {}).get("recipes", {})
    return {r["name"] for r in recipes.values() if r.get("battle_net_recipe_id") in known_ids}


def character_state(slug, profession):
    """Level, {profession id: (skill, cap)}, learned recipe names and data time from the API."""
    import forever_api
    api = forever_api.Api("tw")
    base = f"/profile/wow/character/{slug.strip().lower()}"
    prof = api.get(base + "/professions")
    if prof["status"] != 200:
        sys.exit(f"character {slug}: HTTP {prof['status']} (Lv10+ and logged out once since)")
    profile = api.get(base)
    skills, known = {}, set()
    for p in (prof["payload"].get("primaries") or []) + (prof["payload"].get("secondaries") or []):
        for tier in p.get("tiers") or []:
            skills[p["profession"]["id"]] = (tier["skill_points"], tier["max_skill_points"])
            known |= {r["id"] for r in tier.get("known_recipes") or []}
    return {"level": (profile["payload"] or {}).get("level"), "skills": skills,
            "learned": learned_names(known, profession), "modified": prof["last_modified"]}


def apply_holdings(phases, holdings, made_inputs=None):
    """Mark what the bags already cover in each phase, using holdings up phase by phase.

    Held intermediates (bars, grinding stones) count first and take their inputs off the
    leaf materials through made_inputs {item id: [(input id, qty per unit)]}; held leaf
    materials count next. Each material gets covered (by held intermediates), have,
    buy and cash; each phase gets cash, what is left to spend."""
    made_inputs = made_inputs or {}
    left = {item_id: entry["count"] for item_id, entry in (holdings or {}).items()}
    for ph in phases:
        need = {m["id"]: m["qty"] for m in ph["materials"]}
        made_need = {m["id"]: m["qty"] for m in ph["made"]}

        def reduce(item_id, amount):
            if item_id in made_need:
                amount = min(amount, made_need[item_id])
                made_need[item_id] -= amount
                for inp, per in made_inputs.get(item_id, []):
                    reduce(inp, amount * per)
            elif item_id in need:
                need[item_id] -= min(amount, need[item_id])

        def depth(item_id):  # products before the intermediates they are made from
            users = [j for j in made_need if any(inp == item_id for inp, _ in made_inputs.get(j, []))]
            return 1 + max(depth(j) for j in users) if users else 0

        for m in sorted(ph["made"], key=lambda m: depth(m["id"])):
            m["have"] = min(left.get(m["id"], 0), made_need[m["id"]])
            left[m["id"]] = left.get(m["id"], 0) - m["have"]
            reduce(m["id"], m["have"])
        cash = 0
        for m in ph["materials"]:
            m["covered"] = round(m["qty"] - need[m["id"]])
            m["have"] = min(left.get(m["id"], 0), round(need[m["id"]]))
            left[m["id"]] = left.get(m["id"], 0) - m["have"]
            m["buy"] = max(0, round(need[m["id"]]) - m["have"])
            m["cash"] = round(m["subtotal"] * m["buy"] / m["qty"]) if m["qty"] else 0
            cash += m["cash"]
        ph["cash"] = cash


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
    if args.live:
        import auction_brief
        import auction_changes
        levels, modified = auction_changes.live_levels()
        return ({i: (lv[0][0], sum(q for _, q in lv)) for i, lv in levels.items()},
                f"部落官方即時快照（{auction_brief.taiwan_time(modified)}）")
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
    parser.add_argument("--from", dest="start", type=int, help="current skill (default with --character: the API's)")
    parser.add_argument("--to", dest="end", type=int, help="target skill (default: the skill cap with --character, else 300)")
    parser.add_argument("--me", action="store_true", help="the main character in local.md: --character <slug> --live --bags")
    parser.add_argument("--character", help="API slug name-surname: read skill, cap, level and learned recipes")
    parser.add_argument("--local", default="~/.config/wow-forever/local.md", help="local notes holding the main character's slug")
    parser.add_argument("--live", action="store_true", help="prices from the current Horde API snapshot")
    parser.add_argument("--bags", action="store_true", help="owned plans cost nothing; show held vs. still-to-buy materials")
    parser.add_argument("--mining", type=int, help="mining skill for smelting bars (default with --character: the API's)")
    parser.add_argument("--gate", type=int, default=225, help="rank cap that needs the next trainer rank (Artisan: 225)")
    parser.add_argument("--learn-skills", type=Path, help="wowf learn-skill JSON (default: data/wowf-learn-skill-<profession>.json)")
    parser.add_argument("--faction", default="部落", choices=["部落", "聯盟"])
    parser.add_argument("--neutral", action="store_true", help="also buy from neutral AH listings Amobi saw in the last two days")
    parser.add_argument("--exclude-formula", type=int, action="append", default=[], help="skip a formula by item ID")
    parser.add_argument("--no-vendor-sale", action="store_true", help="do not subtract the vendor sell price of crafted items")
    parser.add_argument("--market-json", help="read prices from the market page's data.json instead of the Auctionator save")
    parser.add_argument("--root", default="/Applications/World of Warcraft")
    parser.add_argument("--file", type=Path, help="a specific Auctionator.lua")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "wowamobi-cache")
    parser.add_argument("--max-age", type=float, default=24, help="hours Amobi pages stay cached")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.me:
        args.character = args.character or local_slug(args.local)
        if not args.character:
            parser.error(f"no 'API 角色 slug' in {args.local}; pass --character")
        args.live = args.bags = True
    state = character_state(args.character, args.profession) if args.character else None
    if state:
        skill, cap = state["skills"].get(PROFESSION_IDS.get(args.profession), (None, None))
        if skill is None:
            sys.exit(f"{args.character} has no {args.profession}")
        args.start = skill if args.start is None else args.start
        args.end = cap if args.end is None else args.end
        if args.mining is None:
            args.mining = state["skills"].get(MINING, (None,))[0]
    if args.start is None:
        parser.error("--from is required without --character or --me")
    args.end = 300 if args.end is None else args.end
    if args.end <= args.start:
        sys.exit(f"skill {args.start} is already at the target {args.end}; raise --to or learn the next rank")
    holdings, bags_saved = (None, None)
    if args.bags:
        import auction_brief
        holdings, bags_saved = auction_brief.read_bags(args.root)

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
        r["blocked"] = w.get("faction") == other or r["recipe_id"] in args.exclude_formula
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

    def sources(item_id):
        """Ways to buy the item, cheapest first: (copper per unit, listed count or None, label, kind)."""
        options = []
        if item_id in scan:
            price, count = scan[item_id]
            options.append((price, count, f"{args.faction}拍賣場", "ah"))
        info = page(item_id)
        towns = HOME_TOWNS[args.faction]
        for v in sorted(info["vendors"], key=lambda v: not any(town in v["zone"] for town in towns)):
            if not v["limited"] and v["unit_price"]:
                home = any(town in v["zone"] for town in towns)
                # Amobi lists only a few vendors per item; a far-off one usually means the capital's also sells it.
                where = f"NPC {v['npc']}（{v['zone']}）" if home else "NPC 商人（阿莫比列的不在主城，主城商人多半也有）"
                options.append((v["unit_price"], None, where, "npc"))
        seen = info["faction_seen"].get("中立拍賣場", "")
        if args.neutral and "中立拍賣場" in info["faction_min"] and seen[:5] in recent_days:
            options.append((info["faction_min"]["中立拍賣場"], None, f"中立拍賣場 {seen}", "neutral"))
        return sorted(options, key=lambda o: o[0])

    # Trainer recipes that make a reagent; usable once the route has reached their orange skill.
    producers = {}
    for r in recipes:
        if r["learn"] == "trainer" and r["item_id"] and r["orange"] is not None and not r["blocked"]:
            producers.setdefault(r["item_id"], []).append(r)
    for r in smelt_producers(args.mining):
        producers.setdefault(r["item_id"], []).append(r)

    def quote(item_id, qty, skill, stock, depth=0):
        """Cheapest way to get qty units at this skill with the auction stock left.

        Returns (cost for choosing, parts) or None. Parts are leaf purchases
        (item id, label, kind, quantity, copper per unit, quantity beyond the listings).
        Units the listings cannot cover cost SHORT_PENALTY times the lowest price, so
        the route only keeps a short material when nothing else comes close."""
        options = []
        for unit, limit, label, kind in sources(item_id):
            left = max(0, stock.get(item_id, limit)) if kind == "ah" and limit is not None else None
            options.append((unit, left, label, kind, None))
        if depth < 3:
            for r in producers.get(item_id, []):
                if r["orange"] <= skill:
                    one = quote_recipe(r, 1 / r["qty"], skill, stock, depth + 1)
                    if one is not None:
                        options.append((one[0], None, f"自製（{r['name']}）", "craft", r))
        options.sort(key=lambda o: o[0])
        need, cost, parts = qty, 0, []
        for unit, left, label, kind, r in options:
            if need <= 1e-9:
                break
            take = need if left is None else min(need, left)
            if take <= 0:
                continue
            if kind == "craft":
                made = quote_recipe(r, take / r["qty"], skill, stock, depth + 1)
                cost, parts = cost + made[0], parts + made[1] + [(item_id, label, "made", take, 0, 0)]
            else:
                cost += unit * take
                parts.append((item_id, label, kind, take, unit, 0))
            need -= take
        if need > 1e-9:
            listed = next((o for o in options if o[3] == "ah"), None)
            if listed is None:
                return None
            cost += listed[0] * SHORT_PENALTY * need
            parts.append((item_id, listed[2], "ah", need, listed[0], need))
        return cost, parts

    def quote_recipe(r, crafts, skill, stock, depth=0):
        cost, parts = 0, []
        for item_id, _, qty in r["mats"]:
            got = quote(item_id, qty * crafts, skill, stock, depth)
            if got is None:
                return None
            cost, parts = cost + got[0], parts + got[1]
        return cost, parts

    def chance(r, s):
        if r["orange"] is None or s < r["orange"] or s >= r["grey"]:
            return 0
        return 1 if s < r["yellow"] else (r["grey"] - s) / (r["grey"] - r["yellow"])

    full_stock = {i: c for i, (_, c) in scan.items() if c is not None}
    pool, missing_plans = [], []
    for r in recipes:
        if r["blocked"] or r["grey"] <= args.start or (r["orange"] or 999) >= args.end:
            continue
        priced = quote_recipe(r, 1, max(args.start, r["orange"] or args.start), full_stock)
        if priced is None:
            continue
        r["cost"] = sum(take * unit for _, _, _, take, unit, _ in priced[1])
        r["sell"] = 0 if args.no_vendor_sale or not r["item_id"] else page(r["item_id"])["sell"] * r["qty"]
        r["net"] = r["cost"] - r["sell"]
        owned = (holdings or {}).get(r["recipe_id"]) if r["recipe_id"] else None
        if r["learn"] in ("trainer", "auto"):
            r["acquire"], r["acquire_from"] = 0, "訓練師"
        elif state and r["name"] in state["learned"]:
            r["acquire"], r["acquire_from"] = 0, "已學"
        elif owned:
            r["acquire"], r["acquire_from"] = 0, f"已有設計圖（{'、'.join(owned['where'][:2])}）"
        else:
            plan = next(iter(sources(r["recipe_id"])), None)
            if plan is None:
                missing_plans.append(r)
                continue
            r["acquire"], r["acquire_from"] = plan[0], plan[2]
        pool.append(r)

    def route(candidates):
        """Walk the skill points in order; each takes the recipe with the lowest expected net
        cost at the stock still listed, then uses that stock up."""
        stock = dict(full_stock)
        steps = []
        for s in range(args.start, args.end):
            best = None
            for r in candidates:
                p = chance(r, s)
                if p <= 0:
                    continue
                got = quote_recipe(r, 1 / p, s, stock)
                if got is None:
                    continue
                score = got[0] - r["sell"] / p
                if best is None or score < best[0]:
                    best = (score, r, p, got[1])
            if best is None:
                return None
            for item_id, _, kind, take, _, short in best[3]:
                if kind == "ah" and item_id in stock:
                    stock[item_id] = max(0, stock[item_id] - (take - short))
            steps.append({"skill": s, "score": best[0], "recipe": best[1], "chance": best[2], "parts": best[3]})
        return steps

    active = list(pool)
    while True:
        steps = route(active)
        if steps is None:
            sys.exit("no obtainable recipe covers every skill point; try --neutral")
        used = {st["recipe"]["name"] for st in steps}
        total = sum(st["score"] for st in steps)
        worst = None
        for r in active:
            if r["acquire"] <= 0 or r["name"] not in used:
                continue
            alt = route([x for x in active if x is not r])
            if alt is None:
                continue
            saving = sum(st["score"] for st in alt) - total
            if saving < r["acquire"] and (worst is None or r["acquire"] - saving > worst[0]):
                worst = (r["acquire"] - saving, r)
        if not worst:
            break
        active.remove(worst[1])

    segments, phases = [], {}
    for st in steps:
        r, s, p = st["recipe"], st["skill"], st["chance"]
        phase = 1 if s < args.gate else 2
        if not (segments and segments[-1]["recipe"] == r["name"] and segments[-1]["phase"] == phase):
            segments.append({"recipe": r["name"], "from": s, "to": s, "phase": phase, "crafts": 0, "var": 0,
                             "spend": 0, "r": r})
        seg = segments[-1]
        seg["to"] = s + 1
        seg["crafts"] += 1 / p
        seg["var"] += (1 - p) / p ** 2
        seg["spend"] += sum(take * unit for _, _, _, take, unit, _ in st["parts"])
        ph = phases.setdefault(phase, {"phase": phase, "gross": 0, "vendor": 0, "need": {}, "made": {}})
        ph["vendor"] += r["sell"] / p
        for item_id, label, kind, take, unit, short in st["parts"]:
            if kind == "made":  # an intermediate crafted from the leaf purchases listed alongside
                made = ph["made"].setdefault(item_id, {"id": item_id, "qty": 0, "how": label})
                made["qty"] += take
                continue
            m = ph["need"].setdefault(item_id, {"id": item_id, "name": None, "ah_qty": 0, "ah_unit": None,
                                                "other_qty": 0, "other_cost": 0, "from": [], "short": 0})
            if kind == "ah":
                m["ah_qty"] += take
                m["ah_unit"] = unit
                m["short"] += short
            else:
                m["other_qty"] += take
                m["other_cost"] += take * unit
            if label not in m["from"]:
                m["from"].append(label)

    names = {item_id: name for r in recipes + smelt_producers(999) for item_id, name, _ in r["mats"]}
    names.update({s["item_id"]: s["name"].replace("熔煉", "") + "錠" for s in SMELTS})
    for seg in segments:
        r = seg.pop("r")
        seg["spare"] = math.ceil(P90 * math.sqrt(seg.pop("var")))
        seg.update(crafts=round(seg["crafts"], 1), cost=round(seg.pop("spend") / seg["crafts"]), sell=r["sell"],
                   mats=[[n, q] for _, n, q in r["mats"]], item_id=r["item_id"], learn=r["acquire_from"],
                   plan=r["recipe"] if r["acquire"] else None, plan_id=r["recipe_id"] if r["acquire"] else None,
                   plan_price=r["acquire"], yellow=r["yellow"], grey=r["grey"], orange=r["orange"])
    for ph in phases.values():
        mats = []
        for m in ph.pop("need").values():
            m["name"] = names.get(m["id"], str(m["id"]))
            m["ah_qty"], m["other_qty"], m["short"] = round(m["ah_qty"]), round(m["other_qty"]), round(m["short"])
            m["other_cost"] = round(m["other_cost"])
            m["qty"] = m["ah_qty"] + m["other_qty"]
            m["subtotal"] = m["ah_qty"] * (m["ah_unit"] or 0) + m["other_cost"]
            m["unit"] = round(m["subtotal"] / m["qty"]) if m["qty"] else 0
            m["listed"] = scan.get(m["id"], (None, None))[1]
            if m["qty"]:
                mats.append(m)
        ph["materials"] = sorted(mats, key=lambda m: -m["subtotal"])
        ph["made"] = [{"id": m["id"], "name": names.get(m["id"], str(m["id"])), "qty": math.ceil(m["qty"] - 1e-9),
                       "how": m["how"]} for m in ph["made"].values()]
        ph["gross"] = sum(m["subtotal"] for m in mats)  # what the rounded shopping list costs
        ph["vendor"] = round(ph["vendor"])
        ph["net"] = ph["gross"] - ph["vendor"]
    better_missing = []
    for r in missing_plans:
        points = [st["skill"] for st in steps
                  if chance(r, st["skill"]) > 0 and r["net"] / chance(r, st["skill"]) < 0.8 * st["score"]]
        if len(points) >= 3:  # one or two points near a colour change are noise
            info = page(r["recipe_id"])
            seen = "；".join(f"{k} {av.gold(v)}（{info['faction_seen'].get(k, '')}）" for k, v in info["faction_min"].items())
            better_missing.append({"plan": r["recipe"], "plan_id": r["recipe_id"], "from": min(points),
                                   "to": max(points) + 1, "net": r["net"], "last_seen": seen})

    result = {"profession": args.profession, "from": args.start, "to": args.end, "gate": args.gate,
              "prices": scan_label, "segments": segments, "phases": [phases[k] for k in sorted(phases)],
              "missing_plans": better_missing}
    if holdings is not None:
        made_inputs = {}
        for ph in result["phases"]:
            for m in ph["made"]:
                r = next((r for r in producers.get(m["id"], []) if r["name"] in m["how"]), None)
                if r:
                    made_inputs[m["id"]] = [(i, q / r["qty"]) for i, _, q in r["mats"]]
        apply_holdings(result["phases"], holdings, made_inputs)
        result["bags_saved"] = bags_saved
    notes = []
    if state:
        result["character"] = {"level": state["level"], "skill": state["skills"].get(PROFESSION_IDS.get(args.profession)),
                               "mining": args.mining, "api_modified": state["modified"]}
        for cap, level in GATE_LEVEL.items():
            if args.start < cap < args.end and (state["level"] or 0) < level:
                notes.append(f"過 {cap} 要先學下一階，需要角色 {level} 級（目前 {state['level']} 級）")
    if args.bags and holdings is None:
        notes.append("找不到 Syndicator 存檔，沒有扣掉已有的材料與設計圖")
    result["notes"] = notes
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return
    g = lambda c: f"{c / 10000:.2f}g"
    print(f"{args.profession} {args.start}→{args.end}・價格：{scan_label}・掛單價，非成交價")
    if state:
        import auction_brief
        c = result["character"]
        print(f"角色：{c['level']} 級・技能 {c['skill'][0]}/{c['skill'][1]}・採礦 {c['mining'] or '—'}"
              f"（API 角色資料 {auction_brief.taiwan_time(state['modified'])}）" + (f"・背包存檔 {bags_saved}" if bags_saved else ""))
    for note in notes:
        print(f"注意：{note}")
    for seg in segments:
        print(f"{seg['from']}→{seg['to']} {seg['recipe']} 約 {seg['crafts']:.0f} 次（多備 {seg['spare']} 次）｜"
              f"每次材料 {g(seg['cost'])}、賣店 {g(seg['sell'])}｜"
              f"{seg['plan'] + ' ' + g(seg['plan_price']) + '（' + seg['learn'] + '）' if seg['plan'] else seg['learn']}｜"
              + "、".join(f"{n}×{q}" for n, q in seg["mats"]))
    for ph in result["phases"]:
        label = f"到 {args.gate}" if ph["phase"] == 1 else f"{args.gate} 以後（要先學下一階）"
        cash = f"、扣掉已有要花 {g(ph['cash'])}" if "cash" in ph else ""
        print(f"\n階段 {ph['phase']}（{label}）：材料 {g(ph['gross'])}、賣店收回 {g(ph['vendor'])}、淨 {g(ph['net'])}{cash}")
        for m in ph["materials"]:
            listed = f"，掛單 {m['listed']} 件" if m["listed"] is not None else ""
            short = f"，缺 {m['short']} 件" if m["short"] else ""
            held = ""
            if m.get("have") or m.get("covered"):
                got = "、".join(x for x in (f"已有的半成品抵掉 {m['covered']}" if m.get("covered") else "",
                                            f"已有 {m['have']}" if m.get("have") else "") if x)
                held = f"｜{got}，" + (f"還要買 {m['buy']}（{g(m['cash'])}）" if m["buy"] else "不用買")
            print(f"  {m['name']} ×{m['qty']}（{g(m['unit'])}，{'、'.join(m['from'])}{listed}{short}）= {g(m['subtotal'])}{held}")
        for m in ph["made"]:
            held = f"，已有 {m['have']} 個可少做" if m.get("have") else ""
            print(f"  （{m['name']} ×{m['qty']} {m['how']}，材料已算在上面{held}）")
    if better_missing:
        print("\n目前買不到、但比路線便宜的配方：")
        for m in better_missing:
            print(f"  {m['plan']} 可用在 {m['from']}–{m['to']}，每次淨 {g(m['net'])}；{m['last_seen'] or '阿莫比沒紀錄'}")

if __name__ == "__main__":
    main()
