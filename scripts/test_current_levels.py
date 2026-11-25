import sys
import time
import unittest
from email.utils import formatdate
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".agents/skills/wow-forever/scripts"))
import auction_changes as ac  # noqa: E402
import auctionator_prices as ap  # noqa: E402

NOW = int(time.time())
API = {1: [(100, 5)], 2: [(200, 1)]}
SCAN = {1: [(90, 7)]}


class ScanLevelsTest(unittest.TestCase):
    def test_reads_levels_and_reports_unreadable_rows(self):
        levels, unread = ap.scan_levels({
            1: {"q": 3, "d": {1: {1: 300, 2: 1}, 2: {1: 100.7, 2: 2}}},
            2: {"q": 9, "d": {1: {1: 50, 2: 1}}},       # units do not add up
            3: {"q": 1, "failure": "x", "d": {1: {1: 50, 2: 1}}},
        })
        self.assertEqual(levels, {1: [(100, 2), (300, 1)]})
        self.assertEqual(unread, {2, 3})


class CurrentLevelsTest(unittest.TestCase):
    def pick(self, api_age=None, scan_age=None, unread=(), **kwargs):
        scan = None if scan_age is None else (NOW - scan_age, SCAN, set(unread))
        live = {"side_effect": SystemExit("HTTP 500")} if api_age is None else {
            "return_value": (API, formatdate(NOW - api_age, usegmt=True))}
        with patch.object(ap, "latest_scan", return_value=scan), patch.object(ac, "live_levels", **live):
            return ac.current_levels("root", **kwargs)

    def test_newer_scan_wins_and_sold_out_items_stay_out(self):
        levels, info = self.pick(api_age=2000, scan_age=60)
        self.assertEqual((levels, info["kind"]), (SCAN, "scan"))

    def test_unreadable_scan_rows_keep_the_api_price(self):
        levels, _ = self.pick(api_age=2000, scan_age=60, unread=[2])
        self.assertEqual(levels, {**SCAN, 2: API[2]})

    def test_newer_api_wins(self):
        levels, info = self.pick(api_age=60, scan_age=2000)
        self.assertEqual((levels, info["kind"]), (API, "api"))

    def test_no_scan_uses_the_api(self):
        self.assertEqual(self.pick(api_age=60)[0], API)

    def test_forced_source(self):
        self.assertEqual(self.pick(api_age=60, scan_age=9000, source="scan")[0], SCAN)
        self.assertEqual(self.pick(api_age=9000, scan_age=60, source="api")[0], API)

    def test_failed_api_falls_back_to_a_recent_scan_only(self):
        levels, info = self.pick(scan_age=600)
        self.assertEqual(levels, SCAN)
        self.assertIn("API 失敗", info["text"])
        with self.assertRaises(SystemExit):
            self.pick(scan_age=ac.SCAN_MAX_AGE + 60)
        with self.assertRaises(SystemExit):
            self.pick(scan_age=60, source="api")


if __name__ == "__main__":
    unittest.main()
