import importlib.util
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".agents/skills/wow-forever/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))  # collect-auctions.py imports blizzard_api
from auction_hours import analyze, load, residuals, sign_p  # noqa: E402

spec = importlib.util.spec_from_file_location("collect_auctions", Path(__file__).with_name("collect-auctions.py"))
collect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect)

START = 498544  # 2026-11-16 00:00 Taiwan time


def series(days, price, units=lambda hour: 100):
    """Hourly snapshots of item 1: [low, units, first20] with first20 5% above low."""
    return [(h, {"1": [round(price(h)), units(h), round(price(h) * 1.05)]}) for h in range(START, START + days * 24)]


class DetrendTest(unittest.TestCase):
    def test_trend_alone_shows_no_hour_effect(self):
        # +5% a day for two weeks: a plain per-hour average would call late hours dearer.
        result = analyze(series(14, lambda h: 10000 * 1.05 ** ((h - START) / 24)), ["1"])
        for metric in ("low", "first"):
            for summary in result[metric].values():
                self.assertLess(abs(summary["change"]), 0.01)

    def test_cheap_bucket_found_through_a_trend(self):
        def price(h):
            cheap = 0.9 if 3 <= (h + 8) % 24 <= 5 else 1.0  # 03-05 Taiwan time
            return 10000 * 1.05 ** ((h - START) / 24) * cheap

        def units(h):
            return 300 if 21 <= (h + 8) % 24 <= 23 else 100  # more listed 21-23

        result = analyze(series(14, price, units), ["1"])
        cheap = result["first"][1]  # bucket 03-05
        self.assertAlmostEqual(cheap["change"], -0.1, delta=0.01)
        self.assertGreaterEqual(cheap["below"], 12)
        self.assertLess(cheap["p"], 0.05)
        self.assertAlmostEqual(result["units"][7]["change"], 301 / 101 - 1, delta=0.01)  # bucket 21-23
        others = [s["change"] for g, s in result["first"].items() if g != 1]
        self.assertTrue(all(abs(c) < 0.02 for c in others))

    def test_sparse_hours_are_not_compared(self):
        snapshots = series(3, lambda h: 10000)[::6]  # four snapshots a day, like GitHub's schedule
        self.assertEqual(residuals(snapshots, "1", "low", 12), {})

    def test_unlisted_hours_count_as_zero_units(self):
        snapshots = series(3, lambda h: 10000)
        snapshots[40] = (snapshots[40][0], {})
        self.assertIn(snapshots[40][0], residuals(snapshots, "1", "units", 12))
        self.assertNotIn(snapshots[40][0], residuals(snapshots, "1", "low", 12))

    def test_sign_test(self):
        self.assertAlmostEqual(sign_p(7, 7), 1.0)
        self.assertLess(sign_p(12, 1), 0.01)
        self.assertEqual(sign_p(0, 0), 1.0)


class HourlyFileTest(unittest.TestCase):
    def test_commodity_hour_averages_the_cheapest_units(self):
        rows = [{"item": {"id": 7}, "unit_price": 100, "quantity": 5},
                {"item": {"id": 7}, "unit_price": 200, "quantity": 30},
                {"item": {"id": 8}, "unit_price": 50, "quantity": 3}]
        self.assertEqual(collect.commodity_hour(rows, 20),
                         {"7": [100, 35, round((5 * 100 + 15 * 200) / 20)], "8": [50, 3, 50]})

    def test_append_skips_known_hours_and_prunes_old_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "2026-09-01.jsonl").write_text("{}\n", encoding="utf-8")
            first = collect.append_hourly(folder, START + 24 * 7, "a", {"1": [1, 2, 3]}, 56)
            self.assertEqual(first.name, "2026-11-23.jsonl")
            self.assertIsNone(collect.append_hourly(folder, START + 24 * 7, "a", {}, 56))
            collect.append_hourly(folder, START + 24 * 7 + 1, "b", {"1": [4, 5, 6]}, 56)
            lines = [json.loads(line) for line in first.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([line["hour"] for line in lines], [START + 168, START + 169])
            self.assertFalse((folder / "2026-09-01.jsonl").exists())
            loaded = load(tmp, 3, today=first_day(first))
            self.assertEqual([h for h, _ in loaded], [START + 168, START + 169])
            self.assertEqual(loaded[1][1], {"1": [4, 5, 6]})


def first_day(path):
    import datetime
    return datetime.date.fromisoformat(path.stem)


if __name__ == "__main__":
    unittest.main()
