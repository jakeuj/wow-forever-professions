import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents/skills/wow-forever/scripts"))
from craftsman_writs import daily, parse_writs, price  # noqa: E402

DATA = '''ns.Writs = {
{id=1,quest=91,name="Craftsman's Writ: Steel Plate Helm",rank="expert",item=11,count=1,zone=3},
{id=2,quest=92,name="Craftsman's Writ: Crafted Solid Shot",rank="journeyman",item=12,count=200,zone=16591},
{id=3,quest=93,name="Craftsman's Writ: Ebon Shiv",rank="artisan",item=13,count=1},
{id=4,quest=94,name="Craftsman's Writ: Bound Thing",rank="journeyman",item=14,count=1,bop=true},
}
ns.Zones = {
[3]="Badlands",
[16591]="Riverglades",
}'''


class ParseTest(unittest.TestCase):
    def test_rank_rep_zone_and_learned_override(self):
        writs = parse_writs(DATA, {"expert": 130})
        self.assertEqual([w["id"] for w in writs], [1, 2, 3, 4])
        self.assertEqual([w["rep"] for w in writs], [130, 75, 200, 75])
        self.assertEqual([w["zone"] for w in writs], ["荒蕪之地", "Riverglades", None, None])
        self.assertEqual(writs[1]["count"], 200)
        self.assertEqual([w["bop"] for w in writs], [False, False, False, True])


class PriceTest(unittest.TestCase):
    def setUp(self):
        self.writs = parse_writs(DATA)
        self.levels = {1: [(5000, 10)], 11: [(8000, 3)], 2: [(1000, 2)], 12: [(10, 900)], 3: [(10000, 1)]}

    def test_cost_counts_and_unlisted_item(self):
        rows = {r["id"]: r for r in price(self.writs, self.levels)}
        self.assertEqual(rows[1]["cost"], 13000)
        self.assertEqual(rows[1]["per100"], 13000 * 100 / 125)
        self.assertEqual(rows[2]["cost"], 1000 + 200 * 10)
        self.assertIsNone(rows[3]["cost"])  # the item has no listing
        self.assertIsNone(rows[4]["per100"])  # neither the writ nor the item is listed

    def test_owned_writ_and_item_cost_nothing(self):
        rows = {r["id"]: r for r in price(self.writs, self.levels, {11: 1, 3: 1, 13: 1})}
        self.assertEqual(rows[1]["cost"], 5000)
        self.assertTrue(rows[1]["own_item"])
        self.assertEqual(rows[3]["cost"], 0)
        self.assertTrue(rows[3]["own_writ"] and rows[3]["own_item"])

    def test_owned_item_needs_the_full_count(self):
        rows = {r["id"]: r for r in price(self.writs, self.levels, {12: 199})}
        self.assertFalse(rows[2]["own_item"])
        self.assertEqual(rows[2]["cost"], 3000)

    def test_sorted_cheapest_per_rep_first_unpriced_last(self):
        rows = price(self.writs, self.levels)
        self.assertEqual([r["id"] for r in rows][:2], [2, 1])
        self.assertIsNone(rows[-1]["per100"])

    def test_daily_adds_one_of_each_under_the_limit(self):
        rows = price(self.writs, self.levels)
        # per 100 rep: writ 2 costs 0.4g, writ 1 costs 1.04g
        self.assertEqual(daily(rows, (0.5, 1.1)), [(0.5, 1, 75, 3000), (1.1, 2, 200, 16000)])


if __name__ == "__main__":
    unittest.main()
