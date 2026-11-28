#!/usr/bin/env python3
"""Plan the cheapest way to level a WoW Forever crafting profession at Horde auction prices.

Recipes, skill colours, reagents, NPC sale and vendor sell prices come from
wowamobi.com; prices and listing counts from the owner's Auctionator full scan
(or the market page's data.json). Trainer recipes have no "requires N" on Amobi,
so their learn skill comes from data/wowf-learn-skill-<profession>.json. Amobi marks every
trainer recipe 「訓練師 待確認」, so one counts as learnable only when the site's recipe
library (crafting-leveling/auto-recipes.json, DungeonsForever's confirmed learning sources)
has a trainer for it or the character already knows it; --unconfirmed adds the rest, marked
待確認. "unobtainable" in the learn-skill JSON keeps a recipe out either way.

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

--me = --character <slug> --live --bags, to 300 unless --to says otherwise. --character
reads the current skill, its cap, the character level and learned recipes from the
Battle.net API, so --from defaults to the current skill and, without --me, --to to its
cap; mining skill unlocks smelting
(steel = iron bar + coal) as a way to make bars. --live prices from the
newer of the Horde API snapshot and the complete scan (--source forces one). --bags reads the Syndicator save: plans any
character holds cost nothing, and the material list shows what you already have
and what is left to buy. Holdings do not change which recipe is picked: owned
materials still count at market price, since they could be sold instead.

--goal cash picks the route that spends the least gold instead: held materials go
first at no cost. The walk is tried with held units at several weights, with and
without the product value, and recipes are dropped while that saves gold (prune_route),
because one point-by-point walk can spend held bars early and buy them back later.
"""

# This file reads the options and the character, then runs the three parts:
# leveling_pricing.py (what reagents and products cost), leveling_search.py (which
# recipe at each skill point) and leveling_report.py (result JSON, route.json, text).

import argparse
import datetime
import json
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import amobi_recipe_value as av  # noqa: E402
import auction_changes  # noqa: E402
from leveling_pricing import PRODUCT_MODES, Pricer, load_scan, parse_profession  # noqa: E402
from leveling_report import apply_holdings, print_report, save_route, summarize  # noqa: E402
from leveling_search import candidate_pool, cheaper_missing_plans, find_route  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
REPO = SKILL_DIR.parents[2]
PROFESSION_IDS = {"alchemy": 171, "blacksmithing": 164, "enchanting": 333, "engineering": 202,
                  "leatherworking": 165, "tailoring": 197, "cooking": 185, "first-aid": 129}
MINING = 186
GATE_LEVEL = {75: 10, 150: 20, 225: 35}  # passing this skill cap needs the next trainer rank, learnable at this level


def local_slug(path):
    """The API slug the local notes record for the main character, or None."""
    try:
        text = Path(path).expanduser().read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    m = re.search(r"API 角色 slug[^`\n]*`([^`]+)`", text)
    return m.group(1) if m else None


def recipe_library(profession):
    """The profession's recipes in the site's recipe library, or None without the library file."""
    path = REPO / "crafting-leveling" / "auto-recipes.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))["professions"].get(profession, {}).get("recipes", {})


def trainer_taught(library):
    """Product item IDs and zhTW names the library has a trainer offer (offer item 0) for, or
    None without the library.

    The library keeps only learning sources DungeonsForever marks confirmed. Amobi labels every
    trainer recipe 「訓練師 待確認」, so this is the check that a trainer really teaches one.
    Products match first: some library names are placeholders such as 「物品 7945」."""
    if library is None:
        return None
    taught = [r for r in library.values() if any(o.get("item") == 0 for o in r.get("offers") or [])]
    return {r["product"] for r in taught if r.get("product")} | {r["name"] for r in taught}


def recipe_book(known_ids, profession):
    """(learned recipes, trainer fee in copper) from the site's recipe library, both keyed by
    zhTW name and by product item ID, since some library names are placeholders (「物品 250574」)."""
    recipes = recipe_library(profession) or {}
    learned = set()
    for r in recipes.values():
        if r.get("battle_net_recipe_id") in known_ids:
            learned |= {r["name"], r.get("product")} - {None, 0}
    fees = {}
    for r in recipes.values():
        fee = r.get("fee") or next((o.get("fee") for o in r.get("offers") or [] if o.get("fee")), None)
        if fee:
            fees.setdefault(r["name"], fee)
            if r.get("product"):
                fees.setdefault(r["product"], fee)
    return learned, fees


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
    learned, fees = recipe_book(known, profession)
    return {"level": (profile["payload"] or {}).get("level"), "skills": skills,
            "learned": learned, "fees": fees, "modified": prof["last_modified"]}


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profession", default="blacksmithing", help="wowamobi slug, e.g. blacksmithing")
    parser.add_argument("--from", dest="start", type=int, help="current skill (default with --character: the API's)")
    parser.add_argument("--to", dest="end", type=int, help="target skill (default: 300; the skill cap with --character alone)")
    parser.add_argument("--me", action="store_true", help="the main character in local.md: --character <slug> --live --bags, to 300")
    parser.add_argument("--character", help="API slug name-surname: read skill, cap, level and learned recipes")
    parser.add_argument("--local", default="~/.config/wow-forever/local.md", help="local notes holding the main character's slug")
    parser.add_argument("--live", action="store_true", help="prices from the newer of the Horde API snapshot and the complete scan")
    auction_changes.add_source_options(parser, root=False)
    parser.add_argument("--bags", action="store_true", help="owned plans cost nothing; show held vs. still-to-buy materials")
    parser.add_argument("--mining", type=int, help="mining skill for smelting bars (default with --character: the API's)")
    parser.add_argument("--level", type=int,
                        help="character level (default with --character: the API's); skips plans from higher-level gated vendors")
    parser.add_argument("--gate", type=int, default=225, help="rank cap that needs the next trainer rank (Artisan: 225)")
    parser.add_argument("--learn-skills", type=Path, help="wowf learn-skill JSON (default: data/wowf-learn-skill-<profession>.json)")
    parser.add_argument("--faction", default="部落", choices=["部落", "聯盟"])
    parser.add_argument("--neutral", action="store_true", help="also buy from neutral AH listings Amobi saw in the last two days")
    parser.add_argument("--exclude-formula", type=int, action="append", default=[], help="skip a formula by item ID")
    parser.add_argument("--unconfirmed", action="store_true",
                        help="also use trainer recipes the recipe library has no trainer for (marked 待確認); "
                             "recipes the learn-skill JSON marks unobtainable stay out")
    parser.add_argument("--use", action="append", default=[], metavar="NAMES",
                        help="only these recipes (zhTW names, comma-separated or repeated), e.g. 鋼質頭盔,秘銀馬刺")
    parser.add_argument("--avoid", action="append", default=[], metavar="NAMES",
                        help="never these recipes (zhTW names, comma-separated or repeated)")
    parser.add_argument("--goal", choices=("value", "cash"), default="value",
                        help="value (default): held materials count at market price, since they could be sold; "
                             "cash: with --bags, held materials are used first for free, minimising gold spent")
    parser.add_argument("--no-vendor-sale", action="store_true", help="same as --products keep")
    parser.add_argument("--products", choices=PRODUCT_MODES,
                        help="what happens to crafted items: vendor (default), disenchant (expected enchanting "
                             "materials at Horde prices; items that cannot be disenchanted are vendored), keep")
    parser.add_argument("--route", default="~/.config/wow-forever/route.json",
                        help="route in progress; --me takes its \"products\" setting")
    parser.add_argument("--save-route", action="store_true",
                        help="write this route to --route for auction_brief.py (the old file is kept as route-<time>.json)")
    parser.add_argument("--market-json", help="read prices from the market page's data.json instead of the Auctionator save")
    parser.add_argument("--root", default="/Applications/World of Warcraft")
    parser.add_argument("--file", type=Path, help="a specific Auctionator.lua")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "wowamobi-cache")
    parser.add_argument("--max-age", type=float, default=24, help="hours Amobi pages stay cached")
    parser.add_argument("--json", action="store_true")
    return parser


def resolve_options(argv=None):
    """(options, character state or None): --me, --products, --use/--avoid and the skill
    range resolved, the range defaulting to the character's skill and cap (--me: to 300)."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.me:
        args.character = args.character or local_slug(args.local)
        if not args.character:
            parser.error(f"no 'API 角色 slug' in {args.local}; pass --character")
        args.live = args.bags = True
        if args.products is None:
            try:
                args.products = json.loads(Path(args.route).expanduser().read_text(encoding="utf-8")).get("products")
            except (FileNotFoundError, ValueError):
                pass
    if args.no_vendor_sale:
        args.products = "keep"
    args.products = args.products or "vendor"
    args.use = {n.strip() for v in args.use for n in v.split(",") if n.strip()}
    args.avoid = {n.strip() for v in args.avoid for n in v.split(",") if n.strip()}
    if args.goal == "cash" and not args.bags:
        parser.error("--goal cash needs --bags (or --me) to know what you hold")
    state = character_state(args.character, args.profession) if args.character else None
    if state:
        skill, cap = state["skills"].get(PROFESSION_IDS.get(args.profession), (None, None))
        if skill is None:
            sys.exit(f"{args.character} has no {args.profession}")
        args.start = skill if args.start is None else args.start
        if args.end is None and not args.me:  # --me plans to 300; the notes flag a rank the level cannot learn yet
            args.end = cap
        if args.mining is None:
            args.mining = state["skills"].get(MINING, (None,))[0]
        if args.level is None:
            args.level = state["level"]
    if args.start is None:
        parser.error("--from is required without --character or --me")
    args.end = 300 if args.end is None else args.end
    if args.end <= args.start:
        sys.exit(f"skill {args.start} is already at the target {args.end}; raise --to or learn the next rank")
    return args, state


def load_recipes(args, get, learned=(), taught=None):
    """The profession's recipes from wowamobi, with orange (learn skill) from the learn-skill data.

    blocked: the other faction's, --exclude-formula, "unobtainable" in the learn-skill data, or
    (without --unconfirmed) unconfirmed: a trainer recipe whose product and name are both outside
    taught (trainer_taught). Recipes the character has learned (learned) are never either.
    taught None (no library) checks nothing."""
    recipes = parse_profession(get(f"{av.BASE}/professions/{args.profession}", f"profession-{args.profession}.html"))
    if not recipes:
        sys.exit("no recipes parsed; the profession page layout may have changed")
    learn_path = args.learn_skills or SKILL_DIR / "data" / f"wowf-learn-skill-{args.profession}.json"
    learn = {r["name"]: r for r in json.loads(learn_path.read_text(encoding="utf-8"))["recipes"]} if learn_path.is_file() else {}
    other = "聯盟" if args.faction == "部落" else "部落"
    for r in recipes:
        w = learn.get(r["name"], {})
        known = r["name"] in learned or r["item_id"] in learned
        r["orange"] = r["need"] if r["need"] is not None else w.get("skill")
        r["unobtainable"] = None if known else w.get("unobtainable")
        r["unconfirmed"] = (not known and r["learn"] == "trainer" and taught is not None
                            and r["item_id"] not in taught and r["name"] not in taught)
        r["blocked"] = (w.get("faction") == other or r["recipe_id"] in args.exclude_formula
                        or bool(r["unobtainable"]) or (r["unconfirmed"] and not args.unconfirmed))
    return recipes


def skipped_notes(recipes, start, end, unconfirmed):
    """Notes naming the recipes in start..end left out as unobtainable or unconfirmed."""
    in_range = [r for r in recipes if r["grey"] > start and (r["orange"] or 0) < end]
    notes = [f"{r['name']}學不到：{r['unobtainable']}" for r in in_range if r["unobtainable"]]
    unsure = [r["name"] for r in in_range if r["unconfirmed"] and not r["unobtainable"]]
    if unsure and not unconfirmed:
        names = "、".join(unsure[:6]) + ("等" if len(unsure) > 6 else "")
        notes.append(f"略過 {len(unsure)} 個網站配方庫查無訓練師的配方（{names}），"
                     "阿莫比只標「訓練師 待確認」；確認學得到再加 --unconfirmed")
    return notes


def character_notes(state, start, end):
    """Warnings for skill caps the route passes before the character is old enough to learn the next rank."""
    notes = []
    for cap, level in GATE_LEVEL.items():
        # Starting right at the cap (225 → 300) needs the next rank before the first craft.
        if start <= cap < end and (state["level"] or 0) < level:
            notes.append(f"過 {cap} 要先學下一階，需要角色 {level} 級（目前 {state['level']} 級）")
    return notes


def gated_vendor_notes(recipes, pool, pricer, level):
    """Notes for recipes skipped because their vendor requires a quest/item gate above this level."""
    usable = {r["name"] for r in pool}
    by_vendor = {}
    for r in recipes:
        if r["name"] in usable or r["recipe_id"] not in pricer.gated_plans:
            continue
        npc, gate = pricer.gated_plans[r["recipe_id"]]
        by_vendor.setdefault(npc, (gate, []))[1].append(r["name"])
    notes = []
    for npc, (gate, names) in by_vendor.items():
        shown = "、".join(names[:6]) + ("等" if len(names) > 6 else "")
        who = f"（目前 {level} 級）" if level is not None else ""
        notes.append(f"略過 {npc} 販售的配方（{shown}）：{gate['note']}{who}")
    return notes


def main():
    args, state = resolve_options()
    holdings, bags_saved = (None, None)
    if args.bags:
        import auction_brief
        holdings, bags_saved = auction_brief.read_bags(args.root)

    args.cache.mkdir(parents=True, exist_ok=True)
    get = lambda url, name: av.fetch(url, args.cache, name, args.max_age, 0.4)
    taught = trainer_taught(recipe_library(args.profession))
    recipes = load_recipes(args, get, state["learned"] if state else (), taught)
    scan, scan_label = load_scan(args)
    unknown = sorted((args.use | args.avoid) - {r["name"] for r in recipes})
    if unknown:
        sys.exit("unknown recipe names (use the zhTW names wowamobi shows): " + "、".join(unknown))

    pricer = Pricer(get, scan, recipes, args.faction, args.neutral, args.mining, args.products, level=args.level)
    stock = {i: c for i, (_, c) in scan.items() if c is not None}
    if args.goal == "cash":
        stock.update({("held", i): e["count"] for i, e in (holdings or {}).items()})
    pool, missing_plans = candidate_pool(recipes, pricer, args.start, args.end, stock,
                                         args.use, args.avoid, state, holdings)
    steps, compared = find_route(pool, pricer, args.start, args.end, stock, args.goal)
    if steps is None:
        sys.exit("no obtainable recipe covers every skill point; "
                 + ("loosen --use/--avoid" if args.use or args.avoid else "try --neutral"))
    segments, phases = summarize(steps, args.gate, recipes, pricer.producers, scan)

    result = {"profession": args.profession, "from": args.start, "to": args.end, "gate": args.gate,
              "products": args.products, "goal": args.goal, "use": sorted(args.use), "avoid": sorted(args.avoid),
              "prices": scan_label, "segments": segments, "phases": phases,
              "missing_plans": cheaper_missing_plans(missing_plans, steps, pricer.page)}
    if compared:
        result["compared"] = compared
    if holdings is not None and args.goal == "cash":
        for ph in result["phases"]:
            ph["cash"] = ph["gross"]  # held materials already went in at no cost
        result["bags_saved"] = bags_saved
    elif holdings is not None:
        made_inputs = {m["id"]: [(i, per) for i, _, per in m["inputs"]] for ph in result["phases"] for m in ph["made"]}
        apply_holdings(result["phases"], holdings, made_inputs)
        result["bags_saved"] = bags_saved
    notes = skipped_notes(recipes, args.start, args.end, args.unconfirmed)
    notes += gated_vendor_notes(recipes, pool, pricer, args.level)
    if taught is None:
        notes.append("找不到網站配方庫（crafting-leveling/auto-recipes.json），訓練師配方沒有核對學習來源")
    if state:
        result["character"] = {"level": state["level"], "skill": state["skills"].get(PROFESSION_IDS.get(args.profession)),
                               "mining": args.mining, "api_modified": state["modified"]}
        notes += character_notes(state, args.start, args.end)
    if args.bags and holdings is None:
        notes.append("找不到 Syndicator 存檔，沒有扣掉已有的材料與設計圖")
    result["notes"] = notes
    if args.save_route:
        save_route(result, args.route, datetime.date.today().isoformat(), bags_saved)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        print_report(result, pricer.product_note)


if __name__ == "__main__":
    main()
