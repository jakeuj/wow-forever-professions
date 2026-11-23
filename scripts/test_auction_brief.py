import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".agents/skills/wow-forever/scripts"))
from auction_brief import classify, off_page, page_items, reference  # noqa: E402

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


class OffPageTest(unittest.TestCase):
    def test_lists_cheap_recipes_not_on_pages(self):
        meta = {"7": ["配方：便宜", 2, 9, "鍊金術"], "8": ["材料", 1, 7, "其他"], "6": ["配方：在頁面", 2, 9, "鍊金術"]}
        realm = {7: [7, 40 * G, 40 * G, 1, "", 40 * G, ""], 8: [8, 40 * G, 40 * G, 1, "", 40 * G, ""],
                 6: [6, 40 * G, 40 * G, 1, "", 40 * G, ""]}
        levels = {7: [(5 * G, 1)], 8: [(5 * G, 1)], 6: [(5 * G, 1)]}
        rows = off_page({6}, levels, realm, {}, HOURS, meta, 5)
        self.assertEqual([r["name"] for r in rows], ["配方：便宜"])


if __name__ == "__main__":
    unittest.main()
