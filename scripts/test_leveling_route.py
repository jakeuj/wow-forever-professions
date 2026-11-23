import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".agents/skills/wow-forever/scripts"))
from leveling_route import apply_holdings, local_slug, smelt_producers  # noqa: E402


class SmeltTest(unittest.TestCase):
    def test_mining_skill_unlocks_smelting(self):
        names = {r["name"] for r in smelt_producers(201)}
        self.assertIn("熔煉鋼", names)
        self.assertIn("熔煉秘銀", names)
        self.assertNotIn("熔煉真銀", names)  # needs mining 230
        self.assertEqual(smelt_producers(None), [])
        steel = next(r for r in smelt_producers(201) if r["name"] == "熔煉鋼")
        self.assertEqual([i for i, _, _ in steel["mats"]], [3575, 3857])  # iron bar + coal, not ore


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


if __name__ == "__main__":
    unittest.main()
