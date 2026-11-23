import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".agents/skills/wow-forever/scripts"))
from auction_brief import buy_cost, classify, off_page, page_items, reference, route_checks, route_import, route_lines, search_term  # noqa: E402

PAGE = """<!doctype html><html><body>
<table data-ah-list="期貨-C觀望"><tbody>
<tr><th><span data-ah="設計圖：便宜貨" data-ah-buy-below="10">便宜貨</span><img src="x.png"></th></tr>
<tr class="is-skip"><th><span data-ah="設計圖：略過">略過</span></th></tr>
</tbody></table>
<p><span data-ah="設計圖：套裝" data-ah-prefix>套裝</span> <span data-ah="材料">材料</span></p>
</body></html>"""

HOURS = list(range(1000, 1170, 10))  # snapshots in the last 7 days
G = 10000


def item(below=None, skip=False):
    return {"below": below, "pages": ["配方期貨"], "lists": [], "skip": skip}


class PageItemsTest(unittest.TestCase):
    def test_reads_triggers_lists_and_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "speculation" / "index.html"
            page.parent.mkdir()
            page.write_text(PAGE, encoding="utf-8")
            items = page_items([page])
        self.assertEqual(items["設計圖：便宜貨"]["below"], 10 * G)
        self.assertEqual(items["設計圖：便宜貨"]["lists"], ["期貨-C觀望"])
        self.assertEqual(items["設計圖：便宜貨"]["pages"], ["配方期貨"])
        self.assertTrue(items["設計圖：略過"]["skip"])
        self.assertNotIn("設計圖：套裝", items)  # prefixes name no single item
        self.assertIsNone(items["材料"]["below"])
        self.assertEqual(items["材料"]["lists"], [])  # the <img> did not leave the table open
        self.assertEqual(items["設計圖：便宜貨"]["owners"], ["期貨轉賣"])  # from the list name
        self.assertEqual(items["材料"]["owners"], ["期貨轉賣"])  # no list: from the page

    def test_alchemy_items_are_for_the_friend(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "alchemy" / "index.html"
            page.parent.mkdir()
            page.write_text('<table data-ah-list="煉金-配方"><tr><td><span data-ah="配方：甲">甲</span></td></tr></table>'
                            '<p><span data-ah="配方：乙">乙</span></p>', encoding="utf-8")
            items = page_items([page])
        self.assertEqual(items["配方：甲"]["owners"], ["煉金朋友"])
        self.assertEqual(items["配方：乙"]["owners"], ["煉金朋友"])


class ReferenceTest(unittest.TestCase):
    def test_takes_the_lowest_market_view(self):
        realm = {1: [1, 120 * G, 120 * G, 1, "", 7 * 100, ""]}  # a troll listing today, 7s yesterday
        record = {"1": [3, [[1000, 6 * 100]]]}
        self.assertEqual(reference(1, realm, record, HOURS), 6 * 100)

    def test_uses_wowamobi_when_horde_never_listed_it(self):
        realm = {2: [2, 100 * G, 100 * G, 1, "", 150 * G, ""]}
        self.assertEqual(reference(2, realm, {}, HOURS), 100 * G)


class ClassifyTest(unittest.TestCase):
    def run_classify(self, items, ids, levels, record=None, realm=None, bags=None, max_now=5):
        meta = {"9": ["材料甲", 1, 7, "金屬與石頭"]}
        return classify(items, ids, levels, record or {}, HOURS, realm or {}, meta, bags, max_now)

    def test_scarce_items_at_trigger_come_first(self):
        result = self.run_classify(
            {"稀少": item(5 * G), "很多": item(1 * G), "快到": item(10 * G), "沒貨": item(15 * G), "略過": item(5 * G, True)},
            {"稀少": [1], "很多": [2], "快到": [3], "沒貨": [4], "略過": [5]},
            {1: [(5 * G, 1), (8 * G, 4)], 2: [(80 * 100, 9)], 3: [(12 * G, 2)], 5: [(1 * G, 1)]})
        self.assertEqual([r["name"] for r in result["now"]], ["稀少"])
        self.assertEqual(result["now"][0]["units_ok"], 1)
        self.assertEqual([r["name"] for r in result["plenty"]], ["很多"])
        self.assertEqual([r["name"] for r in result["near"]], ["快到"])
        self.assertEqual([r["name"] for r in result["empty"]], ["沒貨"])

    def test_far_below_only_without_a_trigger(self):
        realm = {1: [1, 100 * G, 100 * G, 1, "", 150 * G, ""], 2: [2, 200 * G, 200 * G, 1, "", 200 * G, ""]}
        result = self.run_classify({"設計圖：好貨": item(), "有觸發價": item(5 * G)},
                                   {"設計圖：好貨": [1], "有觸發價": [2]},
                                   {1: [(5 * G, 1)], 2: [(10 * G, 1)]}, realm=realm)
        self.assertEqual([(r["name"], r["why"]) for r in result["now"]], [("設計圖：好貨", "far_below")])

    def test_overflow_moves_to_plenty(self):
        items = {f"項{i}": item((i + 1) * G) for i in range(3)}
        ids = {f"項{i}": [i] for i in range(3)}
        levels = {i: [((i + 1) * G, 1)] for i in range(3)}
        result = self.run_classify(items, ids, levels, max_now=2)
        self.assertEqual([r["name"] for r in result["now"]], ["項2", "項1"])  # higher value first
        self.assertEqual([r["name"] for r in result["plenty"]], ["項0"])

    def test_sells_bag_items_listed_well_above_usual(self):
        record = {"9": [50, [[1000, 20 * 100]]]}
        result = self.run_classify({}, {}, {9: [(40 * 100, 50)]}, record=record, bags={9: 100})
        self.assertEqual([(r["name"], r["count"]) for r in result["sell"]], [("材料甲", 100)])
        quiet = self.run_classify({}, {}, {9: [(25 * 100, 50)]}, record=record, bags={9: 100})
        self.assertEqual(quiet["sell"], [])


class HoldingsTest(unittest.TestCase):
    META = {"9": ["材料甲", 1, 7, "金屬與石頭"], "8": ["配方：天價", 2, 9, "鍊金術"], "7": ["小東西", 1, 7, "其他"]}

    def test_owned_page_items_are_not_suggested(self):
        bags = {1: {"count": 5, "where": ["法師 銀行"]}}
        result = classify({"配方：已有": item(5 * G)}, {"配方：已有": [1]}, {1: [(4 * G, 1)]}, {}, HOURS, {}, self.META, bags)
        self.assertEqual(result["now"], [])
        self.assertEqual([(r["name"], r["have"]) for r in result["owned"]], [("配方：已有", 5)])

    def test_sales_split_by_size_and_plausibility(self):
        record = {"9": [50, [[1000, 2000]]], "8": [1, [[1000, 3 * G]]], "7": [9, [[1000, 100]]]}
        bags = {9: {"count": 100, "where": ["聖騎 銀行"]}, 8: {"count": 1, "where": ["法師 銀行"]},
                7: {"count": 50, "where": ["獵人 背包"]}}
        levels = {9: [(4000, 50)], 8: [(50 * G, 1)], 7: [(1000, 9)]}
        result = classify({}, {}, levels, record, HOURS, {}, self.META, bags)
        self.assertEqual([(r["name"], r["where"]) for r in result["sell"]], [("材料甲", ["聖騎 銀行"])])
        # 50g against a 3g market, and 50 x 10s against a 1s market: worth mentioning, flagged as unlikely to sell
        self.assertEqual([(r["name"], r["outlier"]) for r in result["try_sell"]], [("配方：天價", True), ("小東西", True)])
        bags[7]["count"] = 5  # a 0.5g lot listed far above the market is dropped
        result = classify({}, {}, levels, record, HOURS, {}, self.META, bags)
        self.assertNotIn("小東西", [r["name"] for r in result["sell"] + result["try_sell"]])


class OffPageTest(unittest.TestCase):
    def test_lists_cheap_recipes_not_on_pages(self):
        meta = {"7": ["配方：便宜", 2, 9, "鍊金術"], "8": ["材料", 1, 7, "其他"], "6": ["配方：在頁面", 2, 9, "鍊金術"]}
        realm = {7: [7, 40 * G, 40 * G, 1, "", 40 * G, ""], 8: [8, 40 * G, 40 * G, 1, "", 40 * G, ""],
                 6: [6, 40 * G, 40 * G, 1, "", 40 * G, ""]}
        levels = {7: [(5 * G, 1)], 8: [(5 * G, 1)], 6: [(5 * G, 1)]}
        rows = off_page({6}, levels, realm, {}, HOURS, meta, 5)
        self.assertEqual([r["name"] for r in rows], ["配方：便宜"])


class RouteTest(unittest.TestCase):
    LEVELS = {
        "魔紋布": [(460, 30), (470, 2000)],
        "煤塊": [(400, 17), (600, 60)],
        "鋼錠": [(1059, 500)],
        "鐵礦石": [(230, 75)],
        "秘銀錠": [(1000, 2000)],
        "沉重的石頭": [(400, 100)],
        "秘銀礦石": [(2574, 100)],
        "真銀礦石": [(1000, 10)],
        "真銀錠": [(2395, 10)],
    }
    USUAL = {"秘銀錠": 2000, "沉重的石頭": 250}
    ROUTE = {
        "buy": [{"item": "魔紋布", "qty": 78, "planned": 400},
                {"item": "煤塊", "qty": 163, "vendor": 500}],
        "make": [{"product": "鋼錠", "inputs": {"鐵礦石": 1, "煤塊": 1}, "vendor": {"煤塊": 500}}],
        "hold": [{"item": "秘銀錠", "count": 143, "use": 130}, {"item": "沉重的石頭", "count": 181}],
        "ore": [["秘銀礦石", "秘銀錠"], ["真銀礦石", "真銀錠"]],
    }

    def rows(self):
        levels_of = lambda name: self.LEVELS.get(name, [])
        lowest = lambda name: levels_of(name)[0][0] if levels_of(name) else None
        return route_checks(self.ROUTE, lowest, levels_of, self.USUAL.get)

    def test_bags_reduce_what_is_left_to_buy(self):
        levels_of = lambda name: self.LEVELS.get(name, [])
        lowest = lambda name: levels_of(name)[0][0] if levels_of(name) else None
        route = {"buy": [{"item": "魔紋布", "qty": 78, "have": 1, "planned": 400},
                         {"item": "煤塊", "qty": 163, "have": 200, "vendor": 500}]}
        lines = route_lines(route_checks(route, lowest, levels_of, self.USUAL.get))
        self.assertTrue(lines[0].startswith("魔紋布 還要 77 個（已有 1）"))
        self.assertEqual(lines[1], "煤塊：已有 200 個，夠用了。")

    def test_import_line_carries_quantities(self):
        self.assertEqual(search_term("堅固的石頭", 167), '"堅固的石頭";;;;;;;;;;;#;;167')
        self.assertEqual(search_term("堅固的石頭"), '"堅固的石頭"')
        rows = self.rows()  # 魔紋布 78 from the auction house; 煤塊 goes to the vendor
        self.assertEqual(route_import({"list": "我的路線-測試"}, rows), '我的路線-測試^"魔紋布";;;;;;;;;;;#;;78')

    def test_buy_cost_walks_up_the_levels(self):
        self.assertEqual(buy_cost([(400, 10), (500, 100)], 50), (10 * 400 + 40 * 500, 50))
        self.assertEqual(buy_cost([(400, 10)], 50), (4000, 10))

    def test_route_lines(self):
        lines = route_lines(self.rows())
        self.assertIn("路線估 4.00s／個，照買", lines[0])
        self.assertIn("向商人買 5.00s，共 8.15g", lines[1])  # 17 cheap listings save under 1g
        self.assertIn("自己做每個省 3.29s", lines[2])  # 10.59s vs 2.30s ore + 5s coal
        self.assertIn("先別賣", lines[3])  # mithril bars at half their usual price
        self.assertIn("用不到的 181 個可以趁高賣", lines[4])
        self.assertEqual(len(lines), 6)  # only mithril ore is dearer than its bar
        self.assertIn("秘銀礦石 25.74s 比秘銀錠 10.00s 還貴", lines[5])


if __name__ == "__main__":
    unittest.main()
