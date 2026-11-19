from fractions import Fraction
from pathlib import Path
import runpy
import unittest


guide = runpy.run_path(str(Path(__file__).with_name("build-crafting-leveling.py")))
buy = guide["buy"]
Market = guide["Market"]
Phase = guide["Phase"]
Recipe = guide["Recipe"]
build_battle_net_recipe_map = guide["build_battle_net_recipe_map"]


class BattleNetRecipeMapTests(unittest.TestCase):
    def test_requires_unique_matches_in_both_directions_and_matching_materials(self):
        def local(product, name="物品"):
            return {"product": product, "output": 1, "name": name, "reagents": [[7, 2], [6, 1]]}

        def official(recipe_id, profession, product, name="物品", quantity=2):
            return {"id": recipe_id, "profession": profession, "product": {"id": product} if product else None,
                    "units": 1, "name": name, "materials": [{"id": 6, "quantity": 1}, {"id": 7, "quantity": quantity}]}

        catalog = {"release": "fixture.zip", "professions": {
            "blacksmithing": {"recipes": {3493: local(3850), 1: local(21), 2: local(22),
                                          3: local(22), 4: local(23), 5: local(24)}},
            "enchanting": {"recipes": {7418: local(0, "附魔護腕 - 下級耐力")}},
        }}
        snapshot = {"schema": 1, "fetchedAt": "2026-11-20T00:00:00+08:00", "recipes": [
            official(1986, 164, 3850), official(4289, 333, 0, "附魔護腕－下級耐力"),
            official(11, 164, 21), official(12, 164, 21),
            official(13, 164, 22), official(14, 164, 23, quantity=3), official(15, 171, 24),
        ]}
        result = build_battle_net_recipe_map(catalog, snapshot)
        self.assertEqual(result["professions"], {"blacksmithing": {1986: 3493}, "enchanting": {4289: 7418}})
        self.assertEqual(result["catalogRelease"], catalog["release"])


class CraftingCostsTests(unittest.TestCase):
    def test_prices_every_unit_at_its_tier(self):
        purchase = buy(7, 8, [(Fraction(10), 5), (Fraction(20), 10)])
        self.assertEqual((purchase.spent, purchase.auction, purchase.missing), (110, 8, 0))

    def test_does_not_fill_missing_auction_stock_at_the_last_price(self):
        purchase = buy(7, 8, [(Fraction(10), 5)])
        self.assertEqual((purchase.spent, purchase.missing, purchase.unknown), (50, 3, False))
        self.assertTrue(buy(7, 8, None).unknown)

    def test_npc_supply_can_cover_the_auction_shortage(self):
        purchase = buy(7, 8, [(Fraction(10), 5)], (40, 2, "商人"))
        self.assertEqual((purchase.spent, purchase.npc_spent, purchase.npc, purchase.missing), (130, 80, 4, 0))

    def test_combined_budget_shares_stock_across_professions(self):
        market = Market({7: [(Fraction(10), 5), (Fraction(20), 2)]}, {}, {})
        first = Phase(1, 150)
        second = Phase(1, 150)
        first.demands[7] = second.demands[7] = 4
        self.assertFalse(market.quote([first]).missing)
        self.assertFalse(market.quote([second]).missing)
        combined = market.quote([first, second])
        self.assertEqual(combined.total, 90)
        self.assertEqual(combined.missing[0].missing, 1)

    def test_bad_ladder_stays_unpriced(self):
        row = {"q": 5, "d": {1: {1: 20, 2: 4}}}
        self.assertIsNone(guide["checked_depth"](row))
        row["q"] = 4
        self.assertEqual(guide["checked_depth"](row), [(Fraction(20), 4)])
        row["failure"] = "incomplete"
        self.assertIsNone(guide["checked_depth"](row))

    def test_restock_and_price_change_reorders_the_next_point(self):
        phases = {
            name: [Phase(1, 150), Phase(150, 225), Phase(225, 300)]
            for name in ("alchemy", "tailoring")
        }
        phases["alchemy"][1].demands[7] = 10
        phases["tailoring"][1].demands[8] = 10

        def after_150(depth):
            market = Market(depth, {}, {})
            results = {
                name: ("", stages, [market.quote([phase]) for phase in stages], [])
                for name, stages in phases.items()
            }
            return guide["priority_list"](results, str).split("</article>")[1]

        initial = after_150({7: [(Fraction(100), 10)], 8: [(Fraction(50), 1)]})
        rebuilt = after_150({7: [(Fraction(100), 10)], 8: [(Fraction(50), 10)]})
        self.assertLess(initial.index("#alchemy-225"), initial.index("#tailoring-225"))
        self.assertIn("等補貨", initial)
        self.assertLess(rebuilt.index("#tailoring-225"), rebuilt.index("#alchemy-225"))
        self.assertNotIn("等補貨", rebuilt)

    def test_route_carries_components_and_charges_formula_and_tool_once(self):
        recipes = {
            20: Recipe("零件", 2, 2, 1, 150, 160, 200, ((5, 1),), fee=0),
            30: Recipe("成品", 3, 1, 150, 300, 310, 320, ((2, 4),), formula=9, tools=(4,)),
            40: Recipe("工具", 4, 1, 100, 150, 160, 200, ((6, 1),), fee=50),
        }
        facts = {"rankFees": {"test": [10, 500, 5000, 50000]}, "components": {"test": [20]},
                 "tools": {"4": 40}, "sellPrices": {"3": 30}}
        stages = guide["compile_route"]("test", [(1, 150, 20, 149), (150, 225, 30, 75),
                                                  (225, 300, 30, 75)], recipes, facts)
        self.assertEqual(stages[0].demands[5], 149)
        self.assertEqual(stages[1].carried[2], 298)
        self.assertEqual(stages[1].demands[5], 1)
        self.assertEqual((stages[1].demands[6], stages[2].demands[6]), (1, 0))
        self.assertEqual(stages[1].formulas, {9})
        self.assertEqual(stages[2].formulas, set())
        self.assertEqual(stages[2].carried[4], 1)
        self.assertEqual(stages[2].recovery, 2250)

    def test_route_rejects_recipe_before_learning_or_after_it_turns_grey(self):
        facts = {"rankFees": {"test": [10, 500, 5000, 50000]}, "components": {},
                 "tools": {}, "sellPrices": {}}
        recipes = {20: Recipe("材料", 2, 1, 25, 100, 130, 140, (), fee=0)}
        for row in [(1, 150, 20, 149), (1, 25, 20, 24)]:
            with self.subTest(row=row), self.assertRaises(ValueError):
                guide["compile_route"]("test", [row], recipes, facts)


if __name__ == "__main__":
    unittest.main()
