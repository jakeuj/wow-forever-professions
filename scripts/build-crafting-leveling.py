#!/usr/bin/env python3
"""Build the six-profession guide from a verified Horde Auctionator scan."""

import argparse
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from html import escape
import json
import math
from pathlib import Path
import re
from string import Template
import sys
import tempfile
from unicodedata import normalize
from zipfile import ZipFile
from profession_learning import learning_sources


REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / ".agents/skills/wow-forever/scripts"))
from auctionator_prices import LuaReader, find_saved_files, horde_full_scan

PROFESSIONS = {
    "alchemy": "鍊金術", "blacksmithing": "鍛造", "enchanting": "附魔",
    "engineering": "工程學", "leatherworking": "製皮", "tailoring": "裁縫",
}
MILESTONES = (150, 225, 300)
STARTS = (1, 150, 225)
TAIPEI = timezone(timedelta(hours=8))
RODS = (6218, 6339, 11130, 11145, 16207)
ROUTE_FACTS = REPO / "scripts/crafting-leveling-routes.json"
TEMPLATE = REPO / "scripts/crafting-leveling.html"


def literal(text, pattern):
    match = re.search(pattern, text, re.M)
    if not match:
        raise ValueError(f"找不到資料表 {pattern}")
    reader = LuaReader(text)
    reader.i = match.end()
    return reader.value()


def table(path, name):
    return literal(path.read_text(encoding="utf-8-sig"), rf"^{re.escape(name)}\s*=\s*")


def series(value):
    return tuple(value.values()) if value else ()


def checked_depth(item):
    if item.get("failure"):
        return None
    depth = []
    for row in series(item.get("d")):
        price, quantity = series(row)
        if not isinstance(quantity, int) or quantity <= 0 or not math.isfinite(price) or price <= 0:
            return None
        depth.append((Fraction(str(price)).limit_denominator(100000), quantity))
    if sum(quantity for _, quantity in depth) != item.get("q", 0):
        return None
    return sorted(depth)


def read_scan(root, selected):
    candidates = [selected] if selected else find_saved_files(root)
    scans = []
    for auctionator in candidates:
        try:
            scan = horde_full_scan(auctionator)
        except (OSError, ValueError, IndexError):
            continue
        if scan:
            scans.append(scan)
    if not scans:
        raise ValueError("找不到同一輪的部落完整掃描。請用拍賣小幫手完成慢速完整掃描，再 /reload。")
    stamp, items = max(scans, key=lambda pair: pair[0])
    return datetime.fromtimestamp(stamp, TAIPEI), {item: checked_depth(row) for item, row in items.items()}


def read_auction_snapshot(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if (data.get("region"), data.get("ruleset"), data.get("house")) != ("tw", 1, 113):
        raise ValueError("官方快照須來自亞服 PvP 部落拍賣場 113。")
    stamp = datetime.fromisoformat(data["updatedAt"])
    if stamp.tzinfo is None or not data.get("depth"):
        raise ValueError("官方快照須含有時區的時間與價位階梯。")
    depth = {}
    for item, tiers in data["depth"].items():
        if not tiers or any(not isinstance(count, int) or count <= 0 or price <= 0 for price, count in tiers):
            raise ValueError(f"物品 {item} 的官方價位階梯無效。")
        depth[int(item)] = sorted((Fraction(str(price)).limit_denominator(100000), count) for price, count in tiers)
    return stamp.astimezone(TAIPEI), depth


@dataclass(frozen=True)
class Recipe:
    name: str
    product: int
    output: int
    learn: int
    yellow: int
    green: int
    grey: int
    reagents: tuple
    formula: int = 0
    fee: int | None = None
    estimated_fee: bool = False
    tools: tuple = ()
    requirement: str = ""
    unlock_materials: tuple = ()
    orange: int | None = None
    restricted: bool = False


def load_recipes(data_dir, facts, name):
    text = (data_dir / "zhTW/Data_ProfRecipes.lua").read_text(encoding="utf-8-sig")
    handbook = table(data_dir / "zhTW/Data_ProfLeveling.lua", "ns.ProfLeveling")
    catalog = {}
    for slug in PROFESSIONS:
        part = literal(text, rf'^PARTS\["{slug}"\] = function\(\) return\s*')
        recipes = {}

        def add(spell, product, output, skills, reagents, formula=0, title=None, orange=None, restricted=False):
            if not spell:
                return
            learn, yellow, green, grey = skills
            if info := handbook[slug].get("rinfo", {}).get(spell):
                learn, yellow, green, grey = (info[k] for k in ("learn", "yellow", "green", "grey"))
                reagents = info["mats"]
                if info["trainer"]:
                    formula = 0
            changes = facts.get("recipeFacts", {}).get(str(spell), {})
            learn = changes.get("learn", learn)
            materials = tuple(tuple(row) for row in changes.get("reagents", [series(r) for r in series(reagents)]))
            fee = changes.get("fee")
            recipes[spell] = Recipe(
                changes.get("name") or title or name(product), product or 0, output or 0, learn,
                yellow or learn, green or ((yellow or learn) + grey) // 2, grey, materials,
                changes.get("formula", formula or 0), fee, fee is not None and fee > 0,
                tuple(tool for tool in changes.get("tools", []) if tool != product),
                changes.get("requirement", ""), tuple(map(tuple, changes.get("unlockMaterials", []))), orange, restricted,
            )

        for row in series(part.get("rows")):
            add(row[1], row[2], row[3], (row[7], row[8], row[9], row[10]), row[12],
                (row.get(13) or {}).get(1), orange=row.get("orange"),
                restricted=row.get(4) == "Transmutes" or bool(row.get("cooldownVerificationRequired")) or row[1] == 18560)
        for row in series(part.get("enchants")):
            add(row.get(14), 0, 0, (row[5], row[6], row[7], row[8]), row[9], row.get(16),
                f"附魔{row[3]} - {row[2]}", row.get("orange"))
        for row in series(part.get("crafted")):
            add(row[1], row[2], row[3], (row[4], row[5], row[6], row[7]), row[8],
                int(row[9]) if str(row.get(9)).isdigit() else 0, orange=row.get("orange"))
        catalog[slug] = recipes
    return catalog


@dataclass
class Phase:
    start: int
    end: int
    demands: Counter = field(default_factory=Counter)
    formulas: set = field(default_factory=set)
    training: int = 0
    estimated_training: bool = False
    missing_fees: set = field(default_factory=set)
    steps: list = field(default_factory=list)
    carried: Counter = field(default_factory=Counter)
    recovery: int = 0
    requirements: set = field(default_factory=set)


def expected_crafts(recipe, start, end):
    def probability(skill):
        if skill < recipe.yellow:
            return 1
        if skill < recipe.green:
            return 1 - 0.5 * (skill - recipe.yellow) / (recipe.green - recipe.yellow)
        return max(0.05, 0.5 - 0.45 * (skill - recipe.green) / max(1, recipe.grey - recipe.green))

    return math.ceil(sum(1 / probability(skill) for skill in range(start, end)))


def compile_route(slug, steps, recipes, facts):
    """Expand only materials with a verified same-profession producer."""
    phases = [Phase(a, b) for a, b in zip(STARTS, MILESTONES)]
    rank_fees = facts["rankFees"][slug]
    for phase, fees in zip(phases, (rank_fees[:2], rank_fees[2:3], rank_fees[3:])):
        phase.training = sum(fees)
    known, unlocked, inventory = set(), set(), Counter()
    carry_stock = Counter()
    producers = {recipes[spell].product: spell for spell in facts["components"].get(slug, [])}
    tools = {int(item): spell for item, spell in facts["tools"].items()}
    phase = phases[0]

    def craft(spell, count, start, end, visiting=frozenset()):
        recipe = recipes[spell]
        if (start < recipe.learn or (end > start and end > recipe.grey) or spell in visiting
                or (end > start and count < end - start)):
            raise ValueError(f"{slug} {start}→{end} 的配方或材料前置不符（法術 {spell}，學習 {recipe.learn}）")
        if start == end and recipe.product in tools and inventory[recipe.product]:
            return
        for tool in recipe.tools:
            upgraded = RODS[RODS.index(tool):] if tool in RODS else (tool,)
            owned = next((item for item in upgraded if inventory[item]), None)
            if owned and carry_stock[owned]:
                phase.carried[owned] = 1
            elif not owned and tool in tools:
                craft(tools[tool], 1, start, start, visiting | {spell})
            elif not owned:
                inventory[tool] = 1
                phase.demands[tool] += 1
        if spell not in known:
            known.add(spell)
            if recipe.requirement:
                phase.requirements.add(recipe.requirement)
                if recipe.requirement not in unlocked:
                    unlocked.add(recipe.requirement)
                    phase.demands.update(dict(recipe.unlock_materials))
            if recipe.formula:
                phase.formulas.add(recipe.formula)
            elif recipe.fee is None:
                phase.missing_fees.add(recipe.name)
            else:
                phase.training += recipe.fee
                phase.estimated_training |= recipe.estimated_fee
        for item, unit in recipe.reagents:
            need = count * unit
            if need > inventory[item] and item in producers:
                component = recipes[producers[item]]
                if start >= component.learn and producers[item] != spell:
                    batches = math.ceil((need - inventory[item]) / component.output)
                    craft(producers[item], batches, start, start, visiting | {spell})
            used = min(need, inventory[item])
            carried = min(used, carry_stock[item])
            phase.carried[item] += carried
            carry_stock[item] -= carried
            inventory[item] -= used
            phase.demands[item] += need - used
        if recipe.product:
            inventory[recipe.product] += count * recipe.output
        phase.steps.append((start, end, recipe, count))

    end = 1
    for start, target, spell, count in steps:
        if start != end or start > target:
            raise ValueError(f"{slug} 路線中斷於 {end}")
        if start == phase.end and start != 300:
            phase = phases[phases.index(phase) + 1]
            carry_stock = inventory.copy()
        if target > phase.end:
            raise ValueError(f"{slug} 路線跨過 {phase.end}")
        craft(spell, count, start, target)
        end = target
    if end != 300 or any(not stage.steps for stage in phases):
        raise ValueError(f"{slug} 路線未涵蓋全部里程碑")
    used_items = set(producers) | set(tools)
    for stage in phases:
        for _, _, recipe, _ in stage.steps:
            used_items.update(recipe.tools)
            used_items.update(item for item, _ in recipe.reagents)
    for stage in phases:
        stage.recovery = sum(
            count * recipe.output * facts["sellPrices"].get(str(recipe.product), 0)
            for _, _, recipe, count in stage.steps if recipe.product not in used_items
        )
    return phases


@dataclass(frozen=True)
class Purchase:
    item: int
    quantity: int
    auction: int
    npc: int
    spent: int
    missing: int
    unknown: bool = False
    vendor: str = ""
    npc_spent: int = 0


def buy(item, needed, depth, offer=None):
    """Price the requested units with a shared price ladder and a public NPC offer."""
    left, spent = needed, Fraction()
    for unit, listed in depth or ():
        if offer and unit >= Fraction(offer[0], offer[1]):
            break
        quantity = min(left, listed)
        spent += unit * quantity
        left -= quantity
        if not left:
            break
    auction, npc, npc_spent, vendor = needed - left, 0, 0, ""
    if left and offer:
        price, pack, vendor = offer
        npc = math.ceil(left / pack) * pack
        npc_spent = price * (npc // pack)
        spent += npc_spent
        left = 0
    return Purchase(item, needed, auction, npc, math.ceil(spent), left, bool(left and depth is None), vendor, npc_spent)


@dataclass
class Quote:
    materials: list
    formulas: list
    training: int
    missing_fees: set
    estimated_training: bool

    @property
    def total(self):
        return self.training + sum(p.spent for p in self.materials + self.formulas)

    @property
    def missing(self):
        return [p for p in self.materials + self.formulas if p.missing]


def offer_map(table_data, width, vendor_names, *, formulas=False):
    offers = {}
    for item, flat in table_data.items():
        values = series(flat)
        for row in zip(*([iter(values)] * width), strict=True):
            if formulas:
                npc, copper, stock, side, _, pack, currency, _ = row
                if stock == 0 or currency:
                    continue
            else:
                npc, copper, pack, side, _ = row
            if side not in (2, 3) or copper <= 0 or pack <= 0:
                continue
            offer = (copper, pack, vendor_names.get(npc, "商人"))
            if item not in offers or Fraction(copper, pack) < Fraction(*offers[item][:2]):
                offers[item] = offer
    return offers


class Market:
    def __init__(self, depth, supplies, formulas):
        self.depth, self.supplies, self.formulas = depth, supplies, formulas

    def quote(self, phases):
        demands, formulas, missing_fees = Counter(), Counter(), set()
        for phase in phases:
            demands.update(phase.demands)
            formulas.update(phase.formulas)
            missing_fees.update(phase.missing_fees)
        return Quote(
            [buy(i, n, self.depth.get(i, ()), self.supplies.get(i)) for i, n in demands.items() if n],
            [buy(i, n, self.depth.get(i, ()), self.formulas.get(i)) for i, n in formulas.items()],
            sum(p.training for p in phases), missing_fees, any(p.estimated_training for p in phases),
        )


def candidate_steps(slug, handbook, recipes, facts):
    steps = [series(row) for row in series(handbook["steps"])]
    for label, changes in facts.get("routes", {}).get(slug, {}).items():
        if any(row[2] not in recipes for section in changes for row in section):
            continue
        route = steps[:]
        for replacement in changes:
            start, end = replacement[0][0], replacement[-1][1]
            before = [row for row in route if row[0] < start and row[1] <= start]
            after = [row for row in route if row[0] >= end and row[0] != start]
            patched = []
            for left, right, spell, *count in replacement:
                bounds = [left, *(level for level in MILESTONES if left < level < right), right]
                for a, b in zip(bounds, bounds[1:]):
                    n = count[0] if count and len(bounds) == 2 else max(1, expected_crafts(recipes[spell], a, b))
                    patched.append((a, b, spell, n))
            route = before + patched + after
        yield label, route
    yield "無限副本手冊", steps


def select_route(slug, handbook, recipes, facts, market):
    candidates = []
    errors = []
    for label, steps in candidate_steps(slug, handbook, recipes, facts):
        try:
            phases = compile_route(slug, steps, recipes, facts)
        except (KeyError, ValueError) as error:
            errors.append(f"{label}：{error}")
            continue
        stages = [market.quote([phase]) for phase in phases]
        cumulative = [market.quote(phases[:index]) for index in range(1, 4)]
        # Secure the first point first, then compare the remaining reachable stages and their spend.
        score = (
            bool(stages[0].missing),
            sum(bool(q.missing) for q in stages),
            bool(cumulative[-1].missing),
            sum(p.missing for p in stages[0].missing),
            sum(p.missing for q in stages[1:] for p in q.missing),
            stages[0].total, cumulative[-1].total,
        )
        candidates.append((score, label, phases, stages, cumulative))
    if not candidates:
        raise ValueError(f"{slug} 找不到可執行的路線（{'；'.join(errors)}）")
    _, label, phases, stages, cumulative = min(candidates, key=lambda result: result[0])
    return label, phases, stages, cumulative


def load_catalog_inputs(data_dir):
    facts = json.loads(ROUTE_FACTS.read_text(encoding="utf-8"))
    base_names = table(data_dir / "zhTW/Data_ProfItemNames.lua", "ns.ProfItemNames")
    market_json = json.loads((REPO / "market/data.json").read_text(encoding="utf-8"))
    item_field, name_field = (market_json["fields"].index(key) for key in ("id", "name"))
    market_names = {row[item_field]: row[name_field] for row in market_json["items"]}
    curated_names = {int(item): value for item, value in facts["itemNames"].items()}

    def name(item):
        return curated_names.get(item) or market_names.get(item) or base_names.get(item) or f"物品 {item}"

    vendor_names = table(data_dir / "zhTW/Data_ProfVendorNames.lua", "ns.ProfVendorNames")
    supplies = offer_map(table(data_dir / "Data_ProfMaterialSupply.lua", "ns.ProfMaterialSupply"), 5, vendor_names)
    formulas = offer_map(table(data_dir / "Data_ProfFormulaOffers.lua", "ns.ProfFormulaOffers"), 8, vendor_names, formulas=True)
    handbook = table(data_dir / "zhTW/Data_ProfLeveling.lua", "ns.ProfLeveling")
    recipes = load_recipes(data_dir, facts, name)
    return name, facts, supplies, formulas, handbook, recipes


def load_inputs(root, selected, snapshot=None):
    client = root if root.name == "_forever_" else root / "_forever_"
    data_dir = client / "Interface/AddOns/DungeonsForeverProf/Core/Data"
    stamp, depth = read_auction_snapshot(snapshot) if snapshot else read_scan(client, selected)
    name, facts, supplies, formulas, handbook, recipes = load_catalog_inputs(data_dir)
    market = Market(depth, supplies, formulas)
    results = {slug: select_route(slug, handbook[slug], recipes[slug], facts, market) for slug in PROFESSIONS}
    first_round = market.quote([phases[0] for _, phases, _, _ in results.values()])
    return stamp, name, results, first_round


def leveling_catalog(data_dir, release):
    name, facts, supplies, formulas, handbook, recipes = load_catalog_inputs(data_dir)
    professions = {}
    items = set()
    for slug, label in PROFESSIONS.items():
        routes = []
        used = set(facts["components"].get(slug, ()))
        for title, steps in candidate_steps(slug, handbook[slug], recipes[slug], facts):
            try:
                compile_route(slug, steps, recipes[slug], facts)
            except (KeyError, ValueError):
                continue
            routes.append({"name": title, "steps": steps})
            used.update(row[2] for row in steps)
        if not routes:
            raise ValueError(f"{label}沒有完整的候選路線")
        used.update(facts["tools"].get(str(item)) for spell in tuple(used) for item in recipes[slug][spell].tools)
        exported = {spell: {key: value for key, value in asdict(recipes[slug][spell]).items()
                            if key not in ("orange", "restricted")}
                    for spell in sorted(used - {None})}
        professions[slug] = {
            "name": label, "routes": routes, "recipes": exported, "components": facts["components"].get(slug, []),
            "rankFees": facts["rankFees"][slug],
        }
        for recipe in exported.values():
            items.update((recipe["product"], recipe["formula"], *recipe["tools"]))
            items.update(item for item, _ in (*recipe["reagents"], *recipe["unlock_materials"]))
    return {
        "schema": 1, "release": release, "professions": professions, "tools": facts["tools"], "rods": RODS,
        "items": {item: name(item) for item in sorted(items - {0})},
        "supplies": {item: value for item, value in supplies.items() if item in items},
        "formulas": {item: value for item, value in formulas.items() if item in items},
    }


def auto_catalog(data_dir, release, enabled):
    name, facts, supplies, formulas, _, recipes = load_catalog_inputs(data_dir)
    text = (data_dir / "Data_ProfLearningSources.lua").read_text(encoding="utf-8-sig")
    sources, grants = learning_sources(text, literal, enabled)
    gated = table(data_dir / "Data_ProfSpecializations.lua", "ns.ProfSpecializations")
    trainers = table(data_dir / "Data_ProfTrainers.lua", "ns.ProfTrainers")
    professions = {}
    item_ids = set()
    for slug in enabled:
        available = {}
        for spell, recipe in sorted(recipes[slug].items()):
            if recipe.restricted or not (type(recipe.learn) is int and 1 <= recipe.learn <= 300
                    and recipe.learn <= recipe.yellow <= recipe.green <= recipe.grey
                    and all(type(i) is int and i > 0 and type(n) is int and n > 0 for i, n in recipe.reagents)):
                continue
            # For direct enchants the game supplies the required rod in its recipe UI. Use the checked rod data.
            if slug == "enchanting" and not recipe.product and not recipe.tools:
                continue
            restriction = gated.get(spell, {}).get(2) or recipe.requirement
            offers = [] if restriction else sources[slug].get(spell, [])
            # Checked fees and formula corrections used by the existing leveling guide.
            if not offers and not restriction and spell in facts["recipeFacts"]:
                if not recipe.formula and recipe.fee is not None:
                    offers = [{"item": 0, "fee": recipe.fee, "skill": recipe.learn, "level": 0}]
                elif recipe.formula and recipe.formula in formulas:
                    offers = [{"item": recipe.formula, "fee": 0, "skill": recipe.learn, "level": 0}]
            available[spell] = {**asdict(recipe), "offers": offers, "grant": grants[slug].get(spell, 0)}
            item_ids.update((recipe.product, *recipe.tools, *(row["item"] for row in offers)))
            item_ids.update(item for item, _ in (*recipe.reagents, *recipe.unlock_materials))
        ranks = series(trainers[slug]["ranks"])
        if tuple(row["cap"] for row in ranks) != (75, 150, 225, 300):
            raise ValueError(f"{slug} 的技能上限與現有學費不一致")
        professions[slug] = {"recipes": available, "ranks": [
            {"cap": row["cap"], "skill": row.get("sk") or 1, "level": row.get("lv") or 0, "fee": fee}
            for row, fee in zip(ranks, facts["rankFees"][slug], strict=True)
        ]}
    return {
        "schema": 1, "release": release, "professions": professions, "tools": facts["tools"], "rods": RODS,
        "items": {item: name(item) for item in sorted(item_ids - {0})},
        "supplies": {item: row for item, row in supplies.items() if item in item_ids},
        "formulas": {item: row for item, row in formulas.items() if item in item_ids},
    }


def export_leveling_catalog(archive, output, enabled=()):
    prefix = "DungeonsForeverProf/Core/Data/"
    names = ("Data_ProfMaterialSupply.lua", "Data_ProfFormulaOffers.lua",
             *(f"zhTW/Data_Prof{name}.lua" for name in ("ItemNames", "Leveling", "Recipes", "VendorNames")))
    if enabled:
        names += ("Data_ProfLearningSources.lua", "Data_ProfSpecializations.lua", "Data_ProfTrainers.lua")
    with ZipFile(archive) as package, tempfile.TemporaryDirectory() as staging:
        data_dir = Path(staging)
        (data_dir / "zhTW").mkdir()
        for filename in names:
            (data_dir / filename).write_bytes(package.read(prefix + filename))
        catalog = auto_catalog(data_dir, archive.name, enabled) if enabled else leveling_catalog(data_dir, archive.name)
    output.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def build_battle_net_recipe_map(catalog, snapshot):
    if snapshot["schema"] != 1 or not snapshot["recipes"]:
        raise ValueError("無法識別 Battle.net 配方快照。")
    profession_ids = {
        171: "alchemy", 164: "blacksmithing", 333: "enchanting",
        202: "engineering", 165: "leatherworking", 197: "tailoring",
    }

    def name_key(name):
        return "".join(char for char in normalize("NFKC", name) if char.isalnum()).casefold()

    def signature(product, output, name, materials):
        ingredients = tuple(sorted(materials))
        return (product, output, ingredients) if product else (name_key(name), ingredients)

    official = {slug: {} for slug in profession_ids.values()}
    for recipe in snapshot["recipes"]:
        slug = profession_ids.get(recipe["profession"])
        if not slug or recipe["materials"] is None:
            continue
        product = recipe["product"]
        if not product and slug != "enchanting":
            continue
        key = signature(product["id"] if product else 0, recipe["units"], recipe["name"],
                        ((item["id"], item["quantity"]) for item in recipe["materials"]))
        official[slug].setdefault(key, set()).add(recipe["id"])

    professions = {}
    for slug, profession in catalog["professions"].items():
        matches = []
        for spell, recipe in profession["recipes"].items():
            if not recipe["product"] and slug != "enchanting":
                continue
            key = signature(recipe["product"], recipe["output"], recipe["name"], map(tuple, recipe["reagents"]))
            candidates = official[slug].get(key, ())
            if len(candidates) == 1:
                matches.append((next(iter(candidates)), int(spell)))
        counts = Counter(recipe for recipe, _ in matches)
        professions[slug] = {recipe: spell for recipe, spell in sorted(matches) if counts[recipe] == 1}
    return {"schema": 1, "catalogRelease": catalog["release"], "fetchedAt": snapshot["fetchedAt"],
            "professions": professions}


def gold(copper):
    return f"{copper / 10000:,.2f} 金"


def item_link(item, name):
    return f'<a href="https://www.wowhead.com/forever/tw/item={item}">{escape(name(item))}</a>'


def price_label(quote):
    amount = gold(quote.total)
    flags = []
    if quote.missing:
        flags.append("待確認" if any(p.unknown for p in quote.missing) else "缺貨")
    if quote.missing_fees:
        flags.append("學費另計")
    lead = "已知 " if quote.missing else "約 "
    notes = f'<small>{" · ".join(flags)}</small>' if flags else ""
    return f'<span class="cl-price">{lead}{amount}{notes}</span>'


def html_table(headers, rows, *, css="", caption=""):
    head = "".join(f'<th scope="col">{escape(label)}</th>' for label in headers)
    body = []
    for title, cells in rows:
        values = "".join(f'<td data-label="{escape(label)}">{value}</td>'
                         for label, value in zip(headers[1:], cells, strict=True))
        body.append(f'<tr><th scope="row">{title}</th>{values}</tr>')
    cap = f"<caption>{escape(caption)}</caption>" if caption else ""
    return f'<table class="eg-table {css}">{cap}<thead><tr>{head}</tr></thead><tbody>\n' + "\n".join(body) + "\n</tbody></table>"


def priority_list(results, name):
    cards = []
    headings = ("起手到 150", "已到 150 → 225", "已到 225 → 300")
    for i, goal in enumerate(MILESTONES):
        entries = [(slug, detail[1][i], detail[2][i]) for slug, detail in results.items()]
        entries.sort(key=lambda e: (bool(e[2].missing), e[2].total))
        best = next(((slug, quote.total) for slug, phase, quote in entries
                     if not quote.missing and not phase.requirements), None)
        lines = []
        for slug, phase, quote in entries:
            tag = ""
            notes = []
            if quote.missing:
                tag = ' <span class="eg-tag skip">等補貨</span>'
                if any(p.unknown for p in quote.missing):
                    tag = ' <span class="eg-tag watch">待確認</span>'
                notes.extend(f"{name(p.item)}缺 {p.missing:,} 件" if not p.unknown else f"{name(p.item)}缺價"
                             for p in sorted(quote.missing, key=lambda p: -p.missing)[:2])
            elif best and slug == best[0]:
                tag = ' <span class="eg-tag buy">優先</span>'
            elif i and best and quote.total >= 2 * best[1]:
                tag = ' <span class="eg-tag watch">可等降價</span>'
            notes.extend(sorted(phase.requirements))
            if not quote.missing and quote.materials:
                material = max(quote.materials, key=lambda p: p.spent)
                notes.append(f"主要材料 {name(material.item)} ×{material.quantity:,}")
            note = f'<p class="cl-note">{escape(" · ".join(notes))}</p>' if notes else ""
            lines.append(
                f'<li><div class="cl-priority-row"><div class="cl-priority-name"><a href="#{slug}-{goal}">'
                f'{PROFESSIONS[slug]}</a>{tag}</div>{price_label(quote)}</div>{note}</li>'
            )
        cards.append(f'<article><h3>{headings[i]}</h3><ol>{"".join(lines)}</ol></article>')
    return "\n".join(cards)


RANKS = {
    1: "角色 5 級學初級。角色 10 級且技能 50 後可學中級，將上限提到 150。",
    150: "角色 20 級且技能 125 後可學進階，將上限提到 225。",
    225: "角色 35 級且技能 200 後可學工匠級，將上限提到 300。",
}


def stage_panel(slug, phase, quote, name):
    demands = {p.item: p for p in quote.formulas}
    step_rows = []
    for start, end, recipe, count in phase.steps:
        span = f"{start}→{end}" if start != end else f"{start}（補做）"
        if recipe.formula:
            plan = demands.get(recipe.formula)
            source = ("商人 " + plan.vendor if plan.npc else "拍賣場") if plan else "前段已學"
            acquisition = f"{item_link(recipe.formula, name)} · {escape(source)}"
        elif recipe.fee == 0:
            acquisition = "初始習得"
        else:
            acquisition = "訓練師"
        if recipe.requirement:
            acquisition += f'<small class="cl-wait"> · {escape(recipe.requirement)}</small>'
        if recipe.tools:
            acquisition += f'<br><small class="cl-note">工具 {escape("、".join(name(i) for i in recipe.tools))}</small>'
        materials = "、".join(f"{name(i)} ×{quantity}" for i, quantity in recipe.reagents)
        step_rows.append((escape(recipe.name), (span, f"{count:,} 次", escape(materials or "—"), acquisition)))

    shopping_rows = []
    purchases = [(p, False) for p in quote.materials] + [(p, True) for p in quote.formulas]
    purchases.sort(key=lambda p: (not p[1], -p[0].spent, p[0].item))
    for purchase, formula in purchases:
        source = []
        if purchase.auction:
            source.append(f"拍賣 {purchase.auction:,} 件")
        if purchase.npc:
            source.append(f"{purchase.vendor} {purchase.npc:,} 件")
        if purchase.missing:
            source.append(("缺價" if purchase.unknown else "缺貨") + f" {purchase.missing:,} 件")
        title = item_link(purchase.item, name) + ("<small> · 圖紙</small>" if formula else "")
        subtotal = gold(purchase.spent) if purchase.spent else "—"
        shopping_rows.append((title, (f"{purchase.quantity:,} 件", escape(" · ".join(source)), subtotal)))

    material_auction = sum(p.spent - p.npc_spent for p in quote.materials)
    material_npc = sum(p.npc_spent for p in quote.materials)
    formula_cost = sum(p.spent for p in quote.formulas)
    breakdown = (
        ("拍賣材料", gold(material_auction)), ("NPC 材料", gold(material_npc)),
        ("必要圖紙", gold(formula_cost)), ("已計學費", gold(quote.training)),
        ("成品售店估計", gold(phase.recovery)),
    )
    figures = "".join(f"<div><dt>{label}</dt><dd>{amount}</dd></div>" for label, amount in breakdown)
    notes = [RANKS[phase.start]]
    if carried := +phase.carried:
        notes.append("接續使用 " + "、".join(f"{name(i)} ×{n:,}" for i, n in carried.items()) + "。")
    if quote.estimated_training:
        notes.append("已計學費含來源站的訓練師估價。")
    if quote.missing_fees:
        notes.append("學費另計 " + "、".join(sorted(quote.missing_fees)) + "。")
    if phase.requirements:
        notes.append("、".join(sorted(phase.requirements)) + "。")
    note_html = "".join(f'<p class="cl-note">{escape(note)}</p>' for note in notes)
    steps = html_table(("配方", "技能", "預估製作", "每次材料", "學習與工具"), step_rows, caption="依序製作")
    shopping = html_table(("物品", "需要", "採買來源", "已知小計"), shopping_rows, caption="這一段要另外買的材料與圖紙")
    return (
        f'<details class="cl-stage" id="{slug}-{phase.end}" name="{slug}-stage">'
        f'<summary><strong>{phase.start}→{phase.end}</strong> {price_label(quote)}</summary>'
        f'<div class="cl-stage-body">{note_html}<dl class="cl-breakdown">{figures}</dl>\n'
        f'{steps}\n<h4>採買清單</h4>{shopping}\n</div></details>'
    )


def render(stamp, name, results, first_round, *, official=False):
    summary_rows, profession_panels, jump_links = [], [], []
    for slug, (label, phases, stages, cumulative) in results.items():
        title = PROFESSIONS[slug]
        jump = f'<a href="#{slug}">{title}</a>'
        jump_links.append(jump)
        summary_rows.append((jump, tuple(price_label(q) for q in cumulative)))
        reference = f"https://wowf.io/tw/professions/{slug}"
        links = [
            f'<a class="text-link" href="{reference}/leveling">WOWF.IO 升級參考 ↗</a>',
            f'<a class="text-link" href="{reference}/ranks">訓練師與升階 ↗</a>',
        ]
        if slug == "blacksmithing":
            links.append('<a class="text-link" href="../leveling/">既有鍛造 200→300</a>')
        if slug == "alchemy":
            links.append('<a class="text-link" href="../alchemy-leveling/">既有鍊金路線</a>')
        route_note = f'本次採用 {escape(label)}。'
        if slug == "alchemy":
            route_note += ' 想供應軍團鋼可在鍊金 275 另學轉化，需點金石。'
        panels = "\n".join(stage_panel(slug, p, q, name) for p, q in zip(phases, stages))
        profession_panels.append(
            f'<section class="cl-profession" id="{slug}" aria-labelledby="{slug}-title">'
            f'<h3 id="{slug}-title">{title}</h3><p class="cl-note">{route_note}</p>'
            f'<p class="cl-links">{"".join(links)}</p>\n{panels}\n</section>'
        )
    first_price = ("已知 " if first_round.missing else "約 ") + gold(first_round.total)
    first_note = "同批採買，合併六項共用材料。"
    if first_round.missing:
        shortage = "、".join(f"{name(p.item)} {p.missing:,} 件" for p in first_round.missing)
        first_note = f"合併採買仍有缺口 {shortage}。"
    if first_round.missing_fees:
        first_note += "另有未確認學費。"
    return Template(TEMPLATE.read_text(encoding="utf-8")).substitute(
        scan_iso=stamp.isoformat(), scan_label=stamp.strftime("%Y-%m-%d %H:%M"),
        source_label="官方快照" if official else "掃描",
        source_name="Blizzard 官方拍賣 API" if official else "拍賣小幫手",
        source_url="https://community.developer.battle.net/" if official else "https://www.curseforge.com/wow/addons/auctionator",
        first_price=escape(first_price), first_note=escape(first_note), jump_links="".join(jump_links),
        budget=html_table(("專業", "到 150 · 1 點", "到 225 · 2 點", "到 300 · 3 點"), summary_rows, css="cl-budget"),
        priority=priority_list(results, name), routes="\n".join(profession_panels),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="WoW install root or _forever_")
    build = parser.add_mutually_exclusive_group()
    build.add_argument("--addon-zip", type=Path, help="verified DungeonsForever ZIP for a browser leveling catalog")
    build.add_argument("--battle-net-catalog", type=Path, help="local public recipes.json snapshot for the armory recipe map")
    parser.add_argument("--catalog-out", type=Path)
    parser.add_argument("--auto-professions", nargs="+", choices=PROFESSIONS, help="produce the automatic routing catalogue")
    parser.add_argument("--scan-depth-out", type=Path, help="write the validated Horde scan as a browser fallback")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--file", type=Path, help="select a specific Auctionator.lua save")
    source.add_argument("--auction-snapshot", type=Path, help="official TW Horde snapshot JSON with updatedAt and depth by item id")
    parser.add_argument("--out", type=Path, default=REPO / "crafting-leveling/index.html")
    parser.add_argument("--check", action="store_true", help="verify that the published HTML matches the input")
    args = parser.parse_args()
    try:
        if args.battle_net_catalog:
            catalog = REPO / "crafting-leveling/auto-recipes.json"
            snapshot = json.loads(args.battle_net_catalog.read_text(encoding="utf-8"))
            mapping = build_battle_net_recipe_map(json.loads(catalog.read_text(encoding="utf-8")), snapshot)
            output = args.catalog_out or REPO / "crafting-leveling/battle-net-recipe-map.json"
            output.write_text(json.dumps(mapping, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
            return
        if args.addon_zip:
            filename = "auto-recipes.json" if args.auto_professions else "routes.json"
            output = args.catalog_out or REPO / "crafting-leveling" / filename
            export_leveling_catalog(args.addon_zip, output, args.auto_professions)
            return
        if not args.root:
            parser.error("--root is required when building the HTML guide")
        if args.scan_depth_out and (args.auction_snapshot or args.check):
            parser.error("--scan-depth-out requires a real scan and a normal build")
        stamp, name, results, first_round = load_inputs(args.root, args.file, args.auction_snapshot)
        html = render(stamp, name, results, first_round, official=bool(args.auction_snapshot))
        if args.scan_depth_out:
            client = args.root if args.root.name == "_forever_" else args.root / "_forever_"
            scan_stamp, depth = read_scan(client, args.file)
            ladder = {item: [[float(price), count] for price, count in levels] if levels else None
                      for item, levels in depth.items()}
            args.scan_depth_out.write_text(json.dumps({
                "schema": 1, "source": "scan", "region": "tw", "ruleset": 1, "house": 113,
                "updatedAt": scan_stamp.isoformat(), "depth": ladder,
            }, separators=(",", ":")) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        parser.exit(1, f"無法重建升級頁。{error}\n")
    if args.check:
        if not args.out.is_file() or args.out.read_text(encoding="utf-8") != html:
            parser.exit(1, "升級頁與目前行情不同，請重建。\n")
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=args.out.parent, delete=False, mode="w", encoding="utf-8", newline="\n") as temp:
            temp.write(html)
        pending = Path(temp.name)
        try:
            pending.replace(args.out)
        finally:
            pending.unlink(missing_ok=True)
    print(f"{stamp:%Y-%m-%d %H:%M} 部落行情 · 六項到 150 的已知開銷 {gold(first_round.total)}")


if __name__ == "__main__":
    main()
