import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".agents/skills/wow-forever/scripts"))
from leveling_route import (DE_MATERIALS, apply_holdings, disenchant_value, disenchant_yield, local_slug,  # noqa: E402
                            price_floor, smelt_producers)


class SmeltTest(unittest.TestCase):
    def test_mining_skill_unlocks_smelting(self):
        names = {r["name"] for r in smelt_producers(201)}
        self.assertIn("熔煉鋼", names)
        self.assertIn("熔煉秘銀", names)
        self.assertNotIn("熔煉真銀", names)  # needs mining 230
        self.assertEqual(smelt_producers(None), [])
        steel = next(r for r in smelt_producers(201) if r["name"] == "熔煉鋼")
        self.assertEqual([i for i, _, _ in steel["mats"]], [3575, 3857])  # iron bar + coal, not ore


class DisenchantTest(unittest.TestCase):
    def test_armor_gives_mostly_dust_and_weapons_mostly_essence(self):
        armor = dict(disenchant_yield(2, 4, 46))   # green mail helm, ilvl 46
        weapon = dict(disenchant_yield(2, 2, 48))  # green sword, ilvl 48
        self.assertAlmostEqual(armor[11176], 0.75 * 1.5)   # dream dust 1-2 at 75%
        self.assertAlmostEqual(armor[11175], 0.20 * 1.5)   # greater nether essence
        self.assertAlmostEqual(weapon[11175], 0.75 * 1.5)
        self.assertAlmostEqual(weapon[11178], 0.05)        # large radiant shard

    def test_what_cannot_be_disenchanted(self):
        self.assertIsNone(disenchant_yield(2, 0, 43))   # spurs: not armor or weapon
        self.assertIsNone(disenchant_yield(1, 4, 40))   # white item
        self.assertEqual(disenchant_yield(3, 2, 42), [(11177, 1)])  # blue: one shard

    def test_spikes_fall_back_to_the_typical_price(self):
        today = {11175: 27700, 11176: 2300}
        self.assertEqual(price_floor(today, {11175: 8800, 11176: 2500}), {11175: 8800})  # only the spike moves
        self.assertEqual(price_floor(today, {}), {})
        self.assertIn(11175, DE_MATERIALS)

    def test_value_at_prices(self):
        meta = ["秘銀罩帽", 2, 4, "鎖甲・頭部", 41, 46]
        prices = {11176: 2300, 11175: 27700, 11178: 18000}
        self.assertEqual(round(disenchant_value(meta, prices)), round(1.125 * 2300 + 0.3 * 27700 + 0.05 * 18000))
        self.assertIsNone(disenchant_value(["秘銀馬刺", 2, 0, "永久", 0, 43], prices))


class LocalSlugTest(unittest.TestCase):
    def test_reads_the_main_character_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "local.md"
            path.write_text("## 角色\n\n- API 角色 slug：`名字-姓氏`（說明）\n", encoding="utf-8")
            self.assertEqual(local_slug(path), "名字-姓氏")
            self.assertIsNone(local_slug(Path(tmp) / "missing.md"))


class HoldingsTest(unittest.TestCase):
    def phase(self):
        # steel bars from iron bars + coal, iron bars from ore; grinding stones from 4 solid stones
        return {"materials": [
            {"id": 2772, "qty": 100, "subtotal": 100 * 230},   # iron ore
            {"id": 3857, "qty": 100, "subtotal": 100 * 500},   # coal
            {"id": 7912, "qty": 40, "subtotal": 40 * 200},     # solid stone
        ], "made": [
            {"id": 3575, "qty": 100, "how": "自製（熔煉鐵）"},
            {"id": 3859, "qty": 100, "how": "自製（熔煉鋼）"},
            {"id": 7966, "qty": 10, "how": "自製（堅固的砂輪）"},
        ]}

    MADE = {3575: [(2772, 1)], 3859: [(3575, 1), (3857, 1)], 7966: [(7912, 4)]}

    def test_held_intermediates_cover_their_inputs(self):
        ph = self.phase()
        holdings = {3859: {"count": 5, "where": []}, 7966: {"count": 2, "where": []},
                    2772: {"count": 60, "where": []}, 7912: {"count": 10, "where": []}}
        apply_holdings([ph], holdings, self.MADE)
        ore, coal, stone = ph["materials"]
        self.assertEqual((ore["covered"], ore["have"], ore["buy"]), (5, 60, 35))  # 5 steel bars cover 5 ore
        self.assertEqual((coal["covered"], coal["have"], coal["buy"]), (5, 0, 95))
        self.assertEqual((stone["covered"], stone["have"], stone["buy"]), (8, 10, 22))  # 2 stones cover 8
        self.assertEqual(ph["cash"], 35 * 230 + 95 * 500 + 22 * 200)

    def test_holdings_carry_over_to_the_next_phase(self):
        first, second = self.phase(), self.phase()
        apply_holdings([first, second], {2772: {"count": 150, "where": []}}, self.MADE)
        self.assertEqual(first["materials"][0]["have"], 100)
        self.assertEqual(second["materials"][0]["have"], 50)


class OptionsTest(unittest.TestCase):
    def test_cash_goal_needs_the_bags(self):
        import leveling_route
        from contextlib import redirect_stderr
        from io import StringIO
        from unittest import mock
        argv = ["leveling_route.py", "--from", "200", "--to", "225", "--goal", "cash"]
        with mock.patch.object(sys, "argv", argv), redirect_stderr(StringIO()) as err, self.assertRaises(SystemExit):
            leveling_route.main()
        self.assertIn("--goal cash needs --bags", err.getvalue())


if __name__ == "__main__":
    unittest.main()
