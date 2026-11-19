"""Build browser catalogs and verify Battle.net recipe cross-references."""

from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
from unicodedata import normalize
from zipfile import ZipFile

from profession_learning import learning_sources

from .routes import RODS, candidate_steps, compile_route
from .sources import PROFESSIONS, literal, load_catalog_inputs, series, table


def browser_recipe(recipe, exclude=()):
    optional = {"output_range", "battle_net_recipe_id"}
    return {key: value for key, value in asdict(recipe).items()
            if key not in exclude and (key not in optional or value is not None)}


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
        exported = {spell: browser_recipe(recipes[slug][spell], ("orange", "restricted"))
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
            available[spell] = {**browser_recipe(recipe), "offers": offers, "grant": grants[slug].get(spell, 0)}
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


def export_verified_recipe_data(audit, output):
    professions = {slug: {} for slug in PROFESSIONS}
    for row in audit["recipes"]:
        official = row.get("official")
        if not official or not official["productMatches"]:
            continue
        fields = {"recipeId": official["recipeId"], "product": row["local"]["productId"]}
        if official["materialStatus"] == "equal":
            fields["reagents"] = official["reagents"]
        if official["outputStatus"] == "fixed-equal":
            fields["output"] = official["quantity"]
        if official["outputStatus"] == "range-contains-local":
            fields["outputRange"] = official["quantity"]
        professions[row["profession"]][str(row["spellId"])] = fields
    data = {"schema": 1, "namespace": audit["namespace"], "checkedAt": audit["checkedAt"], "professions": professions}
    output.write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")
