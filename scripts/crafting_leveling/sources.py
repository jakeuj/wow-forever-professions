"""Read versioned game and auction inputs for the leveling guide."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / ".agents/skills/wow-forever/scripts"))
from auctionator_prices import LuaReader, find_saved_files, horde_full_scan


PROFESSIONS = {
    "alchemy": "鍊金術", "blacksmithing": "鍛造", "enchanting": "附魔",
    "engineering": "工程學", "leatherworking": "製皮", "tailoring": "裁縫",
}
TAIPEI = timezone(timedelta(hours=8))
ROUTE_FACTS = REPO / "scripts/crafting-leveling-routes.json"


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
    output_range: tuple[int, int] | None = None
    battle_net_recipe_id: int | None = None


def verified_recipe_fields(product, materials, output, verified):
    if not verified or verified["product"] != product:
        return materials, output, None, None
    official_materials = tuple(map(tuple, verified.get("reagents", [])))
    material_match = "reagents" in verified and sorted(official_materials) == sorted(materials)
    if material_match:
        # Keep the guide's iteration order so the solver visits dependencies in the same order.
        official_pairs = {pair: pair for pair in official_materials}
        materials = tuple(official_pairs[pair] for pair in materials)
    output_match = verified.get("output") == output
    if output_match:
        output = verified["output"]
    interval = verified.get("outputRange")
    output_range = tuple(interval) if interval and interval[0] <= output <= interval[1] else None
    return materials, output, output_range, verified["recipeId"] if material_match or output_match or output_range else None


def load_recipes(data_dir, facts, name, official):
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
            materials, output, output_range, recipe_id = verified_recipe_fields(
                product or 0, materials, output or 0, official.get(slug, {}).get(str(spell)))
            fee = changes.get("fee")
            recipes[spell] = Recipe(
                changes.get("name") or title or name(product), product or 0, output or 0, learn,
                yellow or learn, green or ((yellow or learn) + grey) // 2, grey, materials,
                changes.get("formula", formula or 0), fee, fee is not None and fee > 0,
                tuple(tool for tool in changes.get("tools", []) if tool != product),
                changes.get("requirement", ""), tuple(map(tuple, changes.get("unlockMaterials", []))), orange, restricted,
                output_range, recipe_id,
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
    evidence = json.loads((REPO / "scripts/battle-net-leveling-data.json").read_text(encoding="utf-8"))
    recipes = load_recipes(data_dir, facts, name, evidence["professions"])
    return name, facts, supplies, formulas, handbook, recipes
