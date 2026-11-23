"""Pricing for leveling_route.py: what reagents, crafts and crafted products cost.

A reagent comes from the cheapest source with stock left: the auction listings (used up
as a route buys them), unlimited NPC vendors, neutral listings Amobi saw in the last two
days (--neutral), units the bags hold (--goal cash), or a trainer recipe or smelt the
route can already make. Units beyond the listings cost SHORT_PENALTY times the lowest
price. A crafted product brings back its vendor price, its expected disenchant value or
nothing (--products).
"""

import datetime
import html
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import amobi_recipe_value as av  # noqa: E402
import auctionator_prices as ap  # noqa: E402

SHORT_PENALTY = 3  # price factor for units beyond the listed count when choosing recipes
HELD_WEIGHT = 0.1  # --goal cash: share of its buy price a held unit costs when comparing routes (it costs no gold)
SELL = re.compile(r'class="wl w sell">售價：(.*?)</div>', re.S)
HOME_TOWNS = {"部落": ("奧格瑪", "幽暗城", "雷霆崖"), "聯盟": ("暴風城", "鐵爐堡", "達納蘇斯")}
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


# Disenchanting, warcraft.wiki.gg "Disenchanting tables" (pre-BfA, matches Classic; Forever not
# verified). Green items: (ilvl from, to, dust (id, min, max), essence (id, min, max), shard id,
# armor chances (dust, essence, shard), weapon chances). Quantities split evenly over the range.
DE_GREEN = [
    (5, 15, (10940, 1, 2), (10938, 1, 2), None, (.80, .20, 0), (.20, .80, 0)),
    (16, 20, (10940, 2, 3), (10939, 1, 2), 10978, (.75, .20, .05), (.20, .75, .05)),
    (21, 25, (10940, 4, 6), (10998, 1, 2), 10978, (.75, .15, .10), (.15, .75, .10)),
    (26, 30, (11083, 1, 2), (11082, 1, 2), 11084, (.75, .20, .05), (.20, .75, .05)),
    (31, 35, (11083, 2, 5), (11134, 1, 2), 11138, (.75, .20, .05), (.20, .75, .05)),
    (36, 40, (11137, 1, 2), (11135, 1, 2), 11139, (.75, .20, .05), (.20, .75, .05)),
    (41, 45, (11137, 2, 5), (11174, 1, 2), 11177, (.75, .20, .05), (.20, .75, .05)),
    (46, 50, (11176, 1, 2), (11175, 1, 2), 11178, (.75, .20, .05), (.20, .75, .05)),
    (51, 55, (11176, 2, 5), (16202, 1, 2), 14343, (.75, .20, .05), (.22, .75, .03)),
    (56, 60, (16204, 1, 2), (16203, 1, 2), 14344, (.75, .20, .05), (.22, .75, .03)),
    (61, 65, (16204, 2, 5), (16203, 2, 3), 14344, (.75, .20, .05), (.22, .75, .03)),
]
DE_BLUE = [(1, 25, 10978), (26, 30, 11084), (31, 35, 11138), (36, 40, 11139), (41, 45, 11177),
           (46, 50, 11178), (51, 55, 14343), (56, 65, 14344)]
PRODUCT_MODES = ("vendor", "disenchant", "keep")
DE_MATERIALS = ({m[0] for row in DE_GREEN for m in (row[2], row[3])} | {row[4] for row in DE_GREEN if row[4]}
                | {s for _, _, s in DE_BLUE})


def price_floor(today, usual):
    """{item id: price} lowered to the typical price wherever today's listing is above it."""
    return {i: min(p, usual[i]) for i, p in today.items() if usual.get(i) and usual[i] < p}


def disenchant_yield(quality, item_class, item_level):
    """[(material id, expected units)] for one item, or None when it cannot be disenchanted."""
    if item_class not in (2, 4) or quality not in (2, 3) or not item_level:
        return None
    if quality == 3:
        shard = next((s for lo, hi, s in DE_BLUE if lo <= item_level <= hi), None)
        return [(shard, 1)] if shard else None
    row = next((r for r in DE_GREEN if r[0] <= item_level <= r[1]), None)
    if row is None:
        return None
    _, _, dust, essence, shard, armor, weapon = row
    chances = weapon if item_class == 2 else armor
    out = [(dust[0], chances[0] * (dust[1] + dust[2]) / 2), (essence[0], chances[1] * (essence[1] + essence[2]) / 2)]
    if shard and chances[2]:
        out.append((shard, chances[2]))
    return out


def disenchant_value(meta_row, prices):
    """Expected copper from disenchanting one item at these prices; None if it cannot be disenchanted.

    meta_row is wowamobi's item meta [name, quality, class, type, required level, item level, ...]."""
    if not meta_row or len(meta_row) < 6:
        return None
    parts = disenchant_yield(meta_row[1], meta_row[2], meta_row[5])
    if parts is None:
        return None
    return sum(units * prices.get(item_id, 0) for item_id, units in parts)


def disenchant_prices(prices):
    """(prices with enchanting materials at the lower of today's and the 7-day typical price, note).

    Enchanting materials jump around (greater nether essence 0.88g -> 2.77g within a day on
    2026-11-23). Without the hourly record, today's prices stay and the note says why."""
    prices = dict(prices)
    try:
        import auction_brief
        import auction_changes
        record = auction_changes.load_record()
        hours = record["hours"]
        usual = {}
        for item_id in DE_MATERIALS:
            series = record["items"].get(str(item_id))
            usual[item_id] = auction_brief.typical(series[1], hours, hours[-1]) if series else None
        prices.update(price_floor(prices, usual))
        return prices, "分解材料取今天與 7 天常見價的較低者"
    except Exception as error:  # the record is a nice-to-have; keep today's prices
        return prices, f"讀不到 7 天紀錄（{error.__class__.__name__}），分解材料用今天價格"


def smelt_producers(mining_skill):
    """Smelting recipes usable at this mining skill, shaped like trainer producers."""
    return [{"name": s["name"], "item_id": s["item_id"], "qty": 1, "mats": s["mats"], "orange": 0,
             "learn": "trainer", "blocked": False} for s in SMELTS if mining_skill and mining_skill >= s["mining"]]


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


class Pricer:
    """Prices for one run, keeping the wowamobi item pages it has read.

    get(url, cache name) returns a page; scan is {item id: (lowest buyout, listed count)};
    recipes are parsed ones with "orange" and "blocked" set, whose trainer recipes (and the
    smelts this mining skill allows) become producers of the reagents they make.
    held_weight is what a held unit weighs against its buy price while choosing; route
    walks set it (--goal cash)."""

    def __init__(self, get, scan, recipes, faction="部落", neutral=False, mining=None, products="vendor",
                 today=None):
        self.get, self.scan, self.faction, self.neutral, self.products = get, scan, faction, neutral, products
        today = today or datetime.date.today()
        self.recent_days = {(today - datetime.timedelta(days=d)).strftime("%m/%d") for d in (0, 1)}
        self.pages = {}
        self.held_weight = HELD_WEIGHT
        # Trainer recipes that make a reagent; usable once the route has reached their orange skill.
        self.producers = {}
        for r in recipes:
            if r["learn"] == "trainer" and r["item_id"] and r["orange"] is not None and not r["blocked"]:
                self.producers.setdefault(r["item_id"], []).append(r)
        for r in smelt_producers(mining):
            self.producers.setdefault(r["item_id"], []).append(r)
        self.meta, self.product_note = {}, ""
        self.product_prices = {i: p for i, (p, _) in scan.items()}
        if products == "disenchant":
            self.meta = json.loads(get(f"{av.BASE}/api/market/items", "market-items.json")).get("meta", {})
            self.product_prices, self.product_note = disenchant_prices(self.product_prices)

    def page(self, item_id):
        """The item's wowamobi page: vendors, faction prices and the vendor sell price ("sell")."""
        if item_id not in self.pages:
            text = self.get(f"{av.BASE}/items/{item_id}", f"item-{item_id}.html")
            info = av.parse_item_page(text)
            sell = SELL.search(text)
            info["sell"] = (av.coins(sell.group(1)) or 0) if sell else 0
            self.pages[item_id] = info
        return self.pages[item_id]

    def sources(self, item_id):
        """Ways to buy the item, cheapest first: (copper per unit, listed count or None, label, kind)."""
        options = []
        if item_id in self.scan:
            price, count = self.scan[item_id]
            options.append((price, count, f"{self.faction}拍賣場", "ah"))
        info = self.page(item_id)
        towns = HOME_TOWNS[self.faction]
        for v in sorted(info["vendors"], key=lambda v: not any(town in v["zone"] for town in towns)):
            if not v["limited"] and v["unit_price"]:
                home = any(town in v["zone"] for town in towns)
                # Amobi lists only a few vendors per item; a far-off one usually means the capital's also sells it.
                where = f"NPC {v['npc']}（{v['zone']}）" if home else "NPC 商人（阿莫比列的不在主城，主城商人多半也有）"
                options.append((v["unit_price"], None, where, "npc"))
        seen = info["faction_seen"].get("中立拍賣場", "")
        if self.neutral and "中立拍賣場" in info["faction_min"] and seen[:5] in self.recent_days:
            options.append((info["faction_min"]["中立拍賣場"], None, f"中立拍賣場 {seen}", "neutral"))
        return sorted(options, key=lambda o: o[0])

    def buy_price(self, item_id):
        """Copper to buy one now: the cheapest listing or NPC, 0 if nowhere sells it."""
        options = self.sources(item_id)
        return options[0][0] if options else 0

    def quote(self, item_id, qty, skill, stock, depth=0):
        """Cheapest way to get qty units at this skill with the auction stock left.

        Returns (cost for choosing, parts) or None. Parts are leaf purchases
        (item id, label, kind, quantity, copper per unit, quantity beyond the listings).
        Units the listings cannot cover cost SHORT_PENALTY times the lowest price, so
        the route only keeps a short material when nothing else comes close."""
        options = []
        held = stock.get(("held", item_id), 0)
        if held > 1e-9:
            # --goal cash: what the bags hold costs no gold. While walking it weighs a share of its buy
            # price (route walks try several), so held units go first but are not burnt for nothing.
            options.append((self.held_weight * self.buy_price(item_id), held, "已有", "held", None))
        for unit, limit, label, kind in self.sources(item_id):
            left = max(0, stock.get(item_id, limit)) if kind == "ah" and limit is not None else None
            options.append((unit, left, label, kind, None))
        if depth < 3:
            for r in self.producers.get(item_id, []):
                if r["orange"] <= skill:
                    one = self.quote_recipe(r, 1 / r["qty"], skill, stock, depth + 1)
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
                made = self.quote_recipe(r, take / r["qty"], skill, stock, depth + 1)
                cost, parts = cost + made[0], parts + made[1] + [(item_id, label, "made", take, 0, 0)]
            else:
                cost += unit * take
                parts.append((item_id, label, kind, take, 0 if kind == "held" else unit, 0))
            need -= take
        if need > 1e-9:
            listed = next((o for o in options if o[3] == "ah"), None)
            if listed is None:
                return None
            cost += listed[0] * SHORT_PENALTY * need
            parts.append((item_id, listed[2], "ah", need, listed[0], need))
        return cost, parts

    def quote_recipe(self, r, crafts, skill, stock, depth=0):
        """quote() over the recipe's reagents for this many crafts; None if one cannot be had."""
        cost, parts = 0, []
        for item_id, _, qty in r["mats"]:
            got = self.quote(item_id, qty * crafts, skill, stock, depth)
            if got is None:
                return None
            cost, parts = cost + got[0], parts + got[1]
        return cost, parts

    def product_value(self, r):
        """(copper back per craft, how): vendor price, expected disenchant value, or nothing."""
        if self.products == "keep" or not r["item_id"]:
            return 0, "保留"
        vendor = self.page(r["item_id"])["sell"] * r["qty"]
        if self.products == "disenchant":
            de = disenchant_value(self.meta.get(str(r["item_id"])), self.product_prices)
            if de is not None:
                return round(de * r["qty"]), "分解"
        return vendor, "賣店"
