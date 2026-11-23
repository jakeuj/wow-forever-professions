import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".agents/skills/wow-forever/scripts"))
from leveling_pricing import (DE_MATERIALS, HELD_WEIGHT, SHORT_PENALTY, disenchant_value,  # noqa: E402
                              disenchant_yield, price_floor, smelt_producers)
from leveling_report import apply_holdings, route_file  # noqa: E402
from leveling_route import local_slug  # noqa: E402
from leveling_search import cash_cost, chance, prune_route, route_cash, value_route  # noqa: E402


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


class CashRouteTest(unittest.TestCase):
    def test_tally_counts_gold_held_materials_and_fees_once(self):
        x = {"name": "X", "acquire": 5000, "sell": 600, "recover": "分解"}
        y = {"name": "Y", "acquire": 0, "sell": 300, "recover": "賣店"}
        x_parts = [(1, "已有", "held", 3, 0, 0), (2, "部落拍賣場", "ah", 4, 100, 1), (3, "自製", "made", 2, 0, 0)]
        steps = [{"recipe": x, "chance": 0.5, "parts": x_parts}, {"recipe": x, "chance": 0.5, "parts": x_parts},
                 {"recipe": y, "chance": 1, "parts": [(4, "NPC", "npc", 2, 50, 0)]}]
        t = route_cash(steps, {1: 200}.get)
        self.assertEqual(t["held"], 2 * 3 * 200)
        self.assertEqual(t["spent"], 2 * 4 * 100 + 2 * 50)
        self.assertEqual(t["short_extra"], 2 * 1 * 100 * (SHORT_PENALTY - 1))
        self.assertEqual(t["fees"], 5000)  # the plan is bought once, however many steps use it
        self.assertEqual(t["back"], 2 * 600 / 0.5 + 300)
        self.assertEqual(t["gold_back"], 300)  # disenchanted products are not gold
        self.assertAlmostEqual(cash_cost(t), 900 + 5000 + 400 - 300 + HELD_WEIGHT * 1200)

    def test_dropping_a_recipe_that_burns_held_bars_early(self):
        # 2 held bars (weighing 1 each; buying one costs 10). A works at every point with a bar,
        # B only at points 2-3 with a bar, C at points 0-1 for 3 gold and no bar. Walking point by
        # point spends both bars on A, then buys bars for 2-3.
        a = {"name": "A", "points": range(4), "bars": 1, "gold": 0}
        b = {"name": "B", "points": (2, 3), "bars": 1, "gold": 0}
        c = {"name": "C", "points": (0, 1), "bars": 0, "gold": 3}

        def walk(candidates):
            held, steps = 2, []
            for s in range(4):
                best = None
                for r in candidates:
                    if s in r["points"]:
                        use = min(held, r["bars"])
                        score = r["gold"] + use + (r["bars"] - use) * 10
                        if best is None or score < best[0]:
                            best = (score, r, use)
                if best is None:
                    return None
                held -= best[2]
                steps.append({"recipe": best[1], "spent": best[1]["gold"] + (best[1]["bars"] - best[2]) * 10,
                              "held": best[2]})
            return steps

        cost = lambda steps: sum(st["spent"] + st["held"] for st in steps)
        self.assertEqual(cost(walk([a, b, c])), 22)
        best, steps, dropped = prune_route([a, b, c], walk, cost)
        self.assertEqual((best, dropped), (8, ["A"]))
        self.assertEqual([st["recipe"]["name"] for st in steps], ["C", "C", "B", "B"])
        self.assertIsNone(prune_route([b], walk, cost))  # nothing covers points 0-1


class ValueRouteTest(unittest.TestCase):
    def test_chance_falls_from_yellow_to_grey(self):
        r = {"orange": 200, "yellow": 210, "grey": 230}
        self.assertEqual(chance(r, 199), 0)  # not learnable yet
        self.assertEqual(chance(r, 205), 1)
        self.assertEqual(chance(r, 220), 0.5)
        self.assertEqual(chance(r, 230), 0)
        self.assertEqual(chance(dict(r, orange=None), 205), 0)  # learn skill unknown

    def test_plans_that_do_not_pay_for_themselves_are_dropped(self):
        # Two skill points. Trainer recipe T scores 10 a point; plan P scores 1 at both but costs 50
        # and saves only 13; plan Q only covers point 1, scores 5 and costs 2, saving 5.
        t = {"name": "T", "acquire": 0, "scores": (10, 10)}
        p = {"name": "P", "acquire": 50, "scores": (1, 1)}
        q = {"name": "Q", "acquire": 2, "scores": (None, 5)}

        def run(candidates):
            steps = []
            for s in range(2):
                options = [(r["scores"][s], r) for r in candidates if r["scores"][s] is not None]
                if not options:
                    return None
                score, r = min(options, key=lambda o: o[0])
                steps.append({"skill": s, "score": score, "recipe": r})
            return steps

        steps = value_route([t, p, q], run)
        self.assertEqual([st["recipe"]["name"] for st in steps], ["T", "Q"])
        self.assertIsNone(value_route([q], run))  # nothing covers point 0


class RouteFileTest(unittest.TestCase):
    def result(self):
        mat = lambda name, qty, unit, frm, **kw: {"name": name, "qty": qty, "ah_unit": unit if frm[0] == "部落拍賣場" else None,
                                                  "unit": unit, "from": frm, **kw}
        return {"profession": "blacksmithing", "from": 225, "to": 300, "products": "disenchant",
                "prices": "部落官方即時快照（11/23 16:26）", "notes": ["過 225 要先學下一階，需要角色 35 級（目前 34 級）"],
                "segments": [
                    {"recipe": "巨型黑色錘", "plan": None, "plan_price": 0, "learn": "訓練師（未學）"},
                    {"recipe": "秘銀符文戰錘", "plan": "設計圖：秘銀符文戰錘", "plan_price": 23800, "learn": "部落拍賣場"},
                    {"recipe": "巨型黑色錘", "plan": None, "plan_price": 0, "learn": "訓練師（未學）"}],
                "phases": [{"materials": [
                    mat("秘銀礦石", 618, 1025, ["部落拍賣場"], covered=83, have=0),
                    mat("暗影石", 40, 255, ["部落拍賣場"], covered=0, have=13),
                    mat("煤塊", 20, 500, ["NPC 蘇瑞（奧格瑪）"])],
                    "made": [
                        {"name": "秘銀錠", "qty": 619, "have": 83, "inputs": [[3858, "秘銀礦石", 1.0]]},
                        {"name": "緻密砂輪", "qty": 45, "have": 0, "inputs": [[12365, "厚重的石頭", 4.0]]}]}]}

    def test_route_file_for_the_brief(self):
        route = route_file(self.result(), "2026-11-23", "11/23 16:55")
        self.assertEqual(route["name"], "鍛造路線（225→300：巨型黑色錘→秘銀符文戰錘）")
        self.assertEqual(route["list"], "我的路線-鍛造300")
        buy = {r["item"]: r for r in route["buy"]}
        self.assertEqual(buy["秘銀礦石"], {"item": "秘銀礦石", "qty": 535, "planned": 1025})  # held bars cover 83 ore
        self.assertEqual(buy["暗影石"]["qty"], 40)  # the brief takes off the 13 in the bags itself
        self.assertEqual(buy["煤塊"], {"item": "煤塊", "qty": 20, "vendor": 500})
        self.assertEqual(buy["設計圖：秘銀符文戰錘"], {"item": "設計圖：秘銀符文戰錘", "qty": 1, "planned": 23800})
        self.assertEqual(route["make"], [{"product": "秘銀錠", "qty": 536, "inputs": {"秘銀礦石": 1.0}},
                                         {"product": "緻密砂輪", "qty": 45, "inputs": {"厚重的石頭": 4.0}}])
        self.assertEqual(route["hold"], [{"item": "秘銀錠", "count": 83, "use": 83}])
        self.assertEqual(route["ore"], [["秘銀礦石", "秘銀錠"]])
        self.assertIn("背包 11/23 16:55", route["source"])
        self.assertIn("35 級", route["source"])


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

    def test_me_plans_to_300_and_a_character_to_its_cap(self):
        import leveling_route
        from unittest import mock
        state = {"level": 34, "skills": {164: (200, 225), 186: (201, 300)}, "learned": set(), "fees": {},
                 "modified": None}
        with mock.patch.object(leveling_route, "character_state", return_value=state):
            with tempfile.TemporaryDirectory() as tmp:
                local = Path(tmp) / "local.md"
                local.write_text("- API 角色 slug：`名字-姓氏`\n", encoding="utf-8")
                me = ["--me", "--local", str(local), "--route", str(Path(tmp) / "route.json")]
                args, _ = leveling_route.resolve_options(me)
                self.assertEqual((args.start, args.end, args.mining), (200, 300, 201))
                self.assertEqual(leveling_route.resolve_options(me + ["--to", "225"])[0].end, 225)
                args, _ = leveling_route.resolve_options(["--character", "名字-姓氏"])
                self.assertEqual((args.start, args.end), (200, 225))


if __name__ == "__main__":
    unittest.main()
