import importlib.util
import io
import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import Mock, call, patch
from urllib.error import HTTPError

from blizzard_api import Api

spec = importlib.util.spec_from_file_location("collect_auctions", Path(__file__).with_name("collect-auctions.py"))
collect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect)

HOUSE = "/data/wow/ruleset/1/auctions/113"
AUCTIONS_AT = "Thu, 26 Nov 2026 12:41:00 GMT"
COMMODITIES_AT = "Thu, 26 Nov 2026 12:41:05 GMT"
AUCTIONS = {"status": 200, "last_modified": AUCTIONS_AT,
            "payload": {"auctions": [{"item": {"id": 1}, "buyout": 900}]}}
COMMODITIES = {"status": 200, "last_modified": COMMODITIES_AT,
               "payload": {"auctions": [{"item": {"id": 12359}, "unit_price": 1600, "quantity": 20}]}}
NOT_MODIFIED = {"status": 304}


class ConditionalRequestTest(unittest.TestCase):
    def test_304_returns_without_retrying(self):
        headers = Message()
        headers["Last-Modified"] = AUCTIONS_AT
        response = HTTPError("https://tw.api.blizzard.com/", 304, "Not Modified", headers, io.BytesIO())
        with patch("blizzard_api.urllib.request.urlopen", side_effect=response) as request:
            result = Api("tw", "test-token").get(HOUSE, if_modified_since=AUCTIONS_AT)

        request.assert_called_once()
        self.assertEqual(request.call_args.args[0].get_header("If-modified-since"), AUCTIONS_AT)
        self.assertEqual((result["status"], result["payload"], result["bytes"]), (304, None, 0))


class AuctionPublicationTest(unittest.TestCase):
    def setUp(self):
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.history = directory / "auctions.json"
        self.hourly = directory / "hourly"
        self.publisher = Mock()
        self.api = Mock(query={"namespace": "dynamic-forever-tw"})
        self.enterContext(patch.object(collect, "get_token", return_value="test-token"))
        self.enterContext(patch.object(collect, "Publisher", return_value=self.publisher))
        self.enterContext(patch.object(collect, "Api", return_value=self.api))
        self.enterContext(patch.object(collect, "summarize"))
        self.enterContext(patch.dict("os.environ", DAWNBLADE_PUBLISH_URL="https://example.test",
                                     DAWNBLADE_PUBLISH_TOKEN="test-token"))

    def run_collection(self, *responses):
        self.api.get.reset_mock()
        self.api.get.side_effect = responses
        args = ["collector", "--out", str(self.history), "--hourly-dir", str(self.hourly), "--publish-depth"]
        with patch("sys.argv", args):
            collect.main()

    def test_304_leaves_price_ladder_and_history_at_last_publication(self):
        self.run_collection(AUCTIONS, COMMODITIES)
        self.assertEqual(self.api.get.call_args_list, [call(HOUSE, if_modified_since=None),
                                                      call(f"{HOUSE}/commodities", if_modified_since=None)])
        before = self.history.read_bytes()
        hourly = next(self.hourly.iterdir())
        hourly_before = hourly.read_bytes()

        for responses, expected_calls in [
            ((NOT_MODIFIED,), [call(HOUSE, if_modified_since=AUCTIONS_AT)]),
            ((AUCTIONS, NOT_MODIFIED), [call(HOUSE, if_modified_since=AUCTIONS_AT),
                                        call(f"{HOUSE}/commodities", if_modified_since=COMMODITIES_AT)]),
        ]:
            with self.subTest(responses=responses):
                self.publisher.send.reset_mock()
                self.run_collection(*responses)
                self.assertEqual(self.api.get.call_args_list, expected_calls)
                self.publisher.send.assert_called_once_with("battle-net-token", {"accessToken": "test-token"})
                self.assertEqual(self.history.read_bytes(), before)
                self.assertEqual(hourly.read_bytes(), hourly_before)

    def test_failed_publication_does_not_prevent_a_same_hour_retry(self):
        self.publisher.send.side_effect = [None, collect.SnapshotError("test failure")]
        self.run_collection(AUCTIONS, COMMODITIES)
        before = json.loads(self.history.read_bytes())
        self.assertNotIn("publishedLastModified", before)
        hourly = next(self.hourly.iterdir())
        hourly_before = hourly.read_bytes()

        self.publisher.send.side_effect = None
        self.publisher.send.reset_mock()
        self.run_collection(AUCTIONS, COMMODITIES)
        self.assertEqual(self.api.get.call_args_list, [call(HOUSE, if_modified_since=None),
                                                      call(f"{HOUSE}/commodities", if_modified_since=None)])
        self.assertEqual(self.publisher.send.call_args.args[0], "market-depth")
        after = json.loads(self.history.read_bytes())
        self.assertEqual(after.pop("publishedLastModified"), {"auctions": AUCTIONS_AT, "commodities": COMMODITIES_AT})
        self.assertEqual(before, after)
        self.assertEqual(hourly.read_bytes(), hourly_before)
