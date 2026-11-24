import datetime
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents/skills/wow-forever/scripts"))
from waylaid_crates import (auctionator_levels, corrected, curve, import_line, merge_sources, overview,  # noqa: E402
                            parse_addon_ladders, parse_crates, plan, split, take, with_owned)

DATA = '''ns.Crates = {
{id=1,name="Waylaid Crate: Expert Ingots",tier="expert",quality=2,level=20,bundles={{item=11,qty=10},{item=12,qty=20}}},
{id=2,name="Waylaid Crate: Journeyman Textiles",tier="journeyman",quality=1,level=10,bundles={{item=21,qty=20}}},
{id=3,name="Waylaid Crate: Artisan Ore",tier="artisan",quality=1,level=35,bundles={{item=31,qty=10}}},
}'''


class ParseTest(unittest.TestCase):
    def test_favor_refund_bundles_and_level_cap(self):
        kinds = parse_crates(DATA, max_level=34)
        self.assertEqual([k["id"] for k in kinds], [1, 2])
        self.assertEqual((kinds[0]["favor"], kinds[0]["refund"]), (30, 1500))
        self.assertEqual((kinds[1]["favor"], kinds[1]["refund"]), (10, 500))
        self.assertEqual(kinds[0]["bundles"], [(11, 10), (12, 20)])


class CostTest(unittest.TestCase):
    def test_take_walks_up_and_runs_dry(self):
        levels = [(100, 3), (200, 5)]
        self.assertEqual(take(levels, 0, 4), (500, 200))
        self.assertEqual(take(levels, 3, 2), (400, 200))
        self.assertIsNone(take(levels, 0, 9))

    def test_curve_switches_bundle_when_the_cheap_one_gets_dear(self):
        kind = parse_crates(DATA)[0]
        # 10 bars at 500c, then 2000c; the 20-bar bundle stays at 600c a unit.
        levels = {1: [(10, 5)], 11: [(500, 10), (2000, 50)], 12: [(600, 100)]}
        steps = curve(kind, levels, 3)
        self.assertEqual([s["bundle"] for s in steps], [0, 1, 1])
        self.assertEqual(steps[0]["spend"], 10 + 5000)
        self.assertEqual(steps[0]["total"], 5010 - 1500)


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.kinds = parse_crates(DATA, max_level=34)
        # Expert ingots: 30 favor for 15s net once, then dear; textiles: 10 favor for 20s net each.
        self.levels = {1: [(0, 1), (90000, 9)], 11: [(300, 10)], 2: [(500, 40)], 21: [(100, 800)]}

    def test_overview_ranks_by_cost_per_favor(self):
        rows = overview(self.kinds, self.levels)
        self.assertEqual([r["kind"]["id"] for r in rows], [1, 2])
        self.assertAlmostEqual(rows[0]["per_favor"], (3000 - 1500) / 30)

    def test_plan_mixes_kinds_to_hit_the_goal(self):
        result = plan(self.kinds, self.levels, 60)
        counts = {p["kind"]["id"]: p["count"] for p in result["picks"]}
        self.assertEqual(counts, {1: 1, 2: 3})
        self.assertEqual(result["favor"], 60)
        self.assertEqual(result["cost"], 1500 + 3 * (500 + 2000 - 500))

    def test_import_line_carries_quantity_and_max_price(self):
        result = plan(self.kinds, self.levels, 60)
        line = import_line(result, lambda i: f"物品{i}", "木箱")
        self.assertTrue(line.startswith('木箱^"物品1";;;;;;;;;0.01;;#;;1^"物品11";;;;;;;;;0.03;;#;;10'))
        self.assertIn('"物品21";;;;;;;;;0.01;;#;;60', line)


class OwnedTest(unittest.TestCase):
    def setUp(self):
        self.kinds = parse_crates(DATA, max_level=34)
        self.levels = {1: [(0, 1), (90000, 9)], 11: [(300, 10)], 2: [(500, 40)], 21: [(100, 800)]}

    def test_split_books_owned_units_apart(self):
        got = split([(95, 30, True), (100, 50)], 0, 40)
        self.assertEqual((got["own"], got["buy"], got["value"], got["cost"], got["top"]), (30, 10, 2850, 3850, 100))

    def test_owned_crates_are_free_and_materials_sell_after_the_cut(self):
        levels = with_owned(self.levels, {2: 3, 21: 60, 99: 5, 11: 10}, self.kinds, keep={11})
        self.assertEqual(levels[2][0], (0, 3, True))
        self.assertEqual(levels[21][0], (95, 60, True))  # 100c listing less the 5% cut
        self.assertNotIn(99, levels)  # not a crate or bundle
        self.assertEqual(levels[11], self.levels[11])  # kept for a profession

    def test_owned_crates_are_optional(self):
        # A free crate whose bundle is dear is skipped when bought crates are cheaper per favor.
        kinds = parse_crates(DATA, max_level=34)
        levels = {1: [(0, 1, True), (10, 5)], 11: [(9000, 50)], 2: [(500, 40)], 21: [(100, 800)]}
        counts = {p["kind"]["id"]: p["count"] for p in plan(kinds, levels, 30)["picks"]}
        self.assertEqual(counts, {2: 3})

    def test_plan_and_import_only_buy_what_is_missing(self):
        levels = with_owned(self.levels, {2: 3, 21: 50}, self.kinds)
        result = plan(self.kinds, levels, 60)
        textiles = next(p for p in result["picks"] if p["kind"]["id"] == 2)
        self.assertEqual([(l["own"], l["buy"]) for l in textiles["lines"]], [(3, 0), (50, 10)])
        self.assertEqual(result["cash"], 3000 + 10 * 100)  # expert ingots bundle, 10 leather
        line = import_line(result, lambda i: f"物品{i}", "木箱")
        self.assertNotIn('"物品2"', line)
        self.assertIn('"物品21";;;;;;;;;0.01;;#;;10', line)


class ScanTest(unittest.TestCase):
    def test_addon_ladders_from_saved_variables(self):
        table = {"markets": {"favor": {"time": 1795450804, "ladders": {
            3577: {1: {"price": 750, "qty": 1}, 2: {"price": 788, "qty": 13}},
            2772: {1: {"price": 200, "qty": 1}, 2: {"price": 200, "qty": 1491, "guess": True}}}}}}
        when, ladders = parse_addon_ladders(table)
        self.assertEqual(when, 1795450804)
        self.assertEqual(ladders[3577], ([(750, 1), (788, 13)], 0))
        self.assertEqual(ladders[2772], ([(200, 1)], 1491))  # guessed units have no known price
        self.assertEqual(parse_addon_ladders(None), (None, {}))

    def test_newest_source_wins_whatever_its_kind(self):
        # Liferoot on 2026-11-24: the addon saw 1s at 00:20, those were bought, Auctionator saw dearer ones at 00:38.
        api = {3357: [(100, 11), (199, 30), (220, 70)]}
        addon = (1200, "插件掃描", {3357: ([(100, 11), (145, 132)], 0)})
        auctionator = (2280, "Auctionator", {3357: ([(199, 1)], 99)})
        for looks in ([addon, auctionator], [auctionator, addon]):
            levels, used, skipped = merge_sources(api, 600, looks)
            self.assertEqual(levels[3357][0][0], 199)
            self.assertEqual((used[3357], skipped), ("Auctionator", []))
        levels, used, skipped = merge_sources(api, 1800, [addon, (None, "Auctionator", auctionator[2])])
        self.assertEqual((levels, used), (api, {}))
        self.assertEqual(sorted(skipped), ["Auctionator", "插件掃描"])

    def test_a_lowest_price_alone_keeps_the_deeper_levels(self):
        api = [(500, 8), (700, 28), (788, 16)]
        # The 5s and 7s bars are gone: one at the new lowest price, then the API's dearer levels.
        self.assertEqual(corrected(api, [(750, 1)], 60), [(750, 1), (788, 16)])
        # The lowest price is unchanged: the same units, none counted twice.
        self.assertEqual(corrected(api, [(500, 1)], 51), [(500, 1), (500, 7), (700, 28), (788, 16)])
        # A complete look replaces everything; with nothing older the lowest price is all there is.
        self.assertEqual(corrected(api, [(600, 2)], 0), [(600, 2)])
        self.assertEqual(corrected([], [(600, 1)], 9), [(600, 1), (600, 9)])

    def test_auctionator_leaves_out_what_sold_out_before_the_scan(self):
        started = datetime.datetime(2026, 11, 24, 0, 38).timestamp()
        realm = {"1": {"m": 50, "h": {"2518": 50}, "a": {"2518": 9}}, "2": {"m": 70, "h": {"2519": 70}, "a": {"2519": 4}}}
        with mock.patch("auctionator_prices.find_saved_files", return_value=[Path("Auctionator.lua")]), \
                mock.patch("auctionator_prices.load_price_db", return_value={"PvP Horde": realm}), \
                mock.patch("auctionator_prices.full_scan_started", return_value=started):
            self.assertEqual(auctionator_levels("root"), (started, {2: [(70, 4)]}))


class NetTest(unittest.TestCase):
    def test_net_counts_the_whole_refund_even_below_zero(self):
        kinds = parse_crates(DATA, max_level=34)
        result = plan(kinds, {2: [(0, 2, True)], 21: [(5, 40, True)]}, 20)
        self.assertEqual((result["cash"], result["value"], result["refund"]), (0, 200, 1000))
        self.assertEqual((result["net"], result["cost"]), (-800, 0))


if __name__ == "__main__":
    unittest.main()
