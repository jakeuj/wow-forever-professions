#!/usr/bin/env python3
"""Build the six-profession guide from a verified Horde Auctionator scan."""

import argparse
import json
from pathlib import Path
import tempfile

from crafting_leveling.catalog import build_battle_net_recipe_map, export_leveling_catalog, export_verified_recipe_data
from crafting_leveling.render import gold, render
from crafting_leveling.routes import Market, select_route
from crafting_leveling.sources import PROFESSIONS, REPO, load_catalog_inputs, read_auction_snapshot, read_scan


def load_inputs(root, selected, snapshot=None):
    client = root if root.name == "_forever_" else root / "_forever_"
    data_dir = client / "Interface/AddOns/DungeonsForeverProf/Core/Data"
    stamp, depth = read_auction_snapshot(snapshot) if snapshot else read_scan(client, selected)
    name, facts, supplies, formulas, handbook, recipes = load_catalog_inputs(data_dir)
    market = Market(depth, supplies, formulas)
    results = {slug: select_route(slug, handbook[slug], recipes[slug], facts, market) for slug in PROFESSIONS}
    first_round = market.quote([phases[0] for _, phases, _, _ in results.values()])
    return stamp, name, results, first_round


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="WoW install root or _forever_")
    build = parser.add_mutually_exclusive_group()
    build.add_argument("--addon-zip", type=Path, help="verified DungeonsForever ZIP for a browser leveling catalog")
    build.add_argument("--battle-net-catalog", type=Path, help="local public recipes.json snapshot for the armory recipe map")
    build.add_argument("--battle-net-audit", type=Path, help="local audit JSON to extract verified recipe fields")
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
        if args.battle_net_audit:
            audit = json.loads(args.battle_net_audit.read_text(encoding="utf-8"))
            output = args.catalog_out or REPO / "scripts/battle-net-leveling-data.json"
            export_verified_recipe_data(audit, output)
            return
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
