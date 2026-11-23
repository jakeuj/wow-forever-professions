import datetime
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents/skills/wow-forever/scripts"))
from faction_spread import TAIPEI, screen, seen_time, spread_rows  # noqa: E402

spec = importlib.util.spec_from_file_location("build_cross_faction_page", ROOT / "scripts/build-cross-faction-page.py")
page_builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(page_builder)

G = 10000
NOW = datetime.datetime(2026, 11, 23, 18, 0, tzinfo=TAIPEI)


def item(item_id, horde, alliance=None, neutral=None, a_seen="11/23 01:11", n_seen="11/22 18:45"):
    faction_min, seen = {}, {}
    if alliance:
        faction_min["聯盟"], seen["聯盟"] = alliance, a_seen
    if neutral:
        faction_min["中立拍賣場"], seen["中立拍賣場"] = neutral, n_seen
    return {"id": item_id, "name": f"物品{item_id}", "quality": 2, "type": "配方", "h_min": horde,
            "h_min_qty": 1, "h_total": 2, "faction_min": faction_min, "seen": seen}


class ScreenTest(unittest.TestCase):
    def test_median_gap_first_then_expensive_horde_listings(self):
        levels = {1: [(2 * G, 1)], 2: [(10 * G, 1)], 3: [(1 * G, 3)], 4: [(6 * G, 1)]}
        rows = {1: [1, 30 * G], 2: [2, 10 * G], 3: [3, 4 * G], 4: [4, 6 * G]}
        # 1 and 3 pass the median screen (biggest gap first); 2 and 4 come from the 5g floor.
        self.assertEqual(screen(levels, rows, cap=10, min_horde=5), [1, 3, 2, 4])
        self.assertEqual(screen(levels, rows, cap=1, min_horde=50), [1])


class SpreadRowsTest(unittest.TestCase):
    def test_spread_resale_and_freshness(self):
        items = [
            item(1, 25 * G, alliance=500 * G),                                  # plain spread
            item(2, 337 * G, alliance=499 * G, neutral=300 * G),                # neutral undercuts: loss
            item(3, 30 * G, alliance=120 * G, neutral=40 * G, n_seen="11/18 19:38"),  # old neutral ignored
            item(4, 5 * G, alliance=60 * G, a_seen="11/22 03:20"),              # Alliance price not in latest scan
            item(5, 10 * G, alliance=8 * G),                                    # Alliance cheaper: left out
            item(6, 10 * G, alliance=12 * G, a_seen="11/23 01:11"),
        ]
        rows, scans = spread_rows(items, 0.15, NOW)
        self.assertEqual(scans, {"聯盟": "11/23 01:11", "中立拍賣場": "11/22 18:45"})
        by_id = {r["id"]: r for r in rows}
        self.assertEqual([r["id"] for r in rows], [1, 2, 3, 4, 6])
        self.assertEqual(by_id[1]["spread"], 475 * G)
        self.assertEqual(by_id[1]["resale"], 400 * G)
        self.assertTrue(by_id[2]["neutral_cheaper"])
        self.assertEqual(by_id[2]["resale"], 255 * G - 337 * G)
        self.assertFalse(by_id[3]["neutral_fresh"])
        self.assertEqual(by_id[3]["resale"], 102 * G - 30 * G)
        self.assertFalse(by_id[4]["fresh"])
        self.assertTrue(by_id[1]["fresh"])

    def test_seen_time_rolls_back_a_year_in_january(self):
        january = datetime.datetime(2027, 1, 2, 12, 0, tzinfo=TAIPEI)
        self.assertEqual(seen_time("12/31 23:00", january).year, 2026)
        self.assertIsNone(seen_time("", january))


class PageTest(unittest.TestCase):
    PAGE = ("<ul><!-- cf:chips --><!-- /cf:chips --></ul><caption><!-- cf:caption --><!-- /cf:caption --></caption>"
            "<tbody><!-- cf:rows --><!-- /cf:rows --></tbody><ul><!-- cf:stale --><!-- /cf:stale --></ul>"
            '<span class="verified-date">old</span><p><!-- cf:note --><!-- /cf:note --></p>')

    def test_fills_rows_stale_list_and_dates(self):
        items = [item(1, 25 * G, alliance=500 * G), item(2, 337 * G, alliance=499 * G, neutral=300 * G),
                 item(4, 5 * G, alliance=60 * G, a_seen="11/22 03:20"), item(6, 10 * G, alliance=10.5 * G)]
        rows, scans = spread_rows(items, 0.15, NOW)
        data = {"hordeModified": "Mon, 23 Nov 2026 09:26:29 GMT", "allianceScan": scans["聯盟"],
                "neutralScan": scans["中立拍賣場"], "cut": 0.15, "compared": 4, "rows": rows}
        page, count, gain, stale = page_builder.build(self.PAGE, data, 1, 12)
        self.assertEqual((count, gain, stale), (2, 1, 1))  # item 6 is under the 1g floor
        self.assertIn('<tr class="cf-loss">', page)
        self.assertIn('data-ah="物品1"', page)
        self.assertIn("https://wowamobi.com/items/1", page)
        self.assertIn("中立已有更便宜的", page)
        self.assertIn('<span class="verified-date">官方 API / 2026.11.23 17:26</span>', page)
        self.assertIn("部落價：官方 API 11/23 17:26", page)
        self.assertIn("（11/22 03:20 看到）", page)


if __name__ == "__main__":
    unittest.main()
