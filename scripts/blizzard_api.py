"""Minimal Battle.net API client for the WoW Forever site scripts (standard library only).

Credentials come from BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET (repo Secrets in
GitHub Actions; never commit them). The access token is sent in a header, never in
a URL, and is masked in the Actions log.
"""

import base64
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TOKEN_URL = "https://oauth.battle.net/token"
LOCALES = {"tw": "zh_TW", "kr": "ko_KR", "us": "en_US", "eu": "en_GB"}
USER_AGENT = "wow-forever-professions-site"


def fetch(url, headers=None, data=None, timeout=180):
    """Return (status, headers, body); 4xx comes back as a status, other errors retry."""
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip", **(headers or {})}
    for attempt in range(4):
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return resp.status, resp.headers, body
        except urllib.error.HTTPError as error:
            if error.code in (400, 401, 403, 404) or attempt == 3:
                return error.code, error.headers, error.read()
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
        time.sleep(2 ** (attempt + 1))
    raise AssertionError("unreachable")


def get_token():
    client_id = os.environ.get("BLIZZARD_CLIENT_ID")
    client_secret = os.environ.get("BLIZZARD_CLIENT_SECRET")
    if not client_id or not client_secret:
        sys.exit("set BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET (in CI they come from repo Secrets)")
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    status, _, body = fetch(TOKEN_URL, {"Authorization": f"Basic {basic}",
                                        "Content-Type": "application/x-www-form-urlencoded"},
                            data=b"grant_type=client_credentials", timeout=30)
    if status != 200:
        # The error body names the problem (e.g. invalid_client) and holds no secret.
        sys.exit(f"token request failed: HTTP {status} {body[:300].decode('utf-8', 'replace')}")
    token = json.loads(body)["access_token"]
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::add-mask::{token}")  # hide it from the log even if something echoes it
    return token


class Api:
    """GET helper for one region's dynamic-forever namespace."""

    def __init__(self, region, token):
        self.base = f"https://{region}.api.blizzard.com"
        self.query = {"namespace": f"dynamic-forever-{region}", "locale": LOCALES.get(region, "en_US")}
        self.auth = {"Authorization": f"Bearer {token}"}
        self.calls = 0

    def get(self, path):
        url = f"{self.base}{path}?{urllib.parse.urlencode(self.query)}"
        self.calls += 1
        status, headers, body = fetch(url, self.auth)
        payload = json.loads(body) if status == 200 else None
        return {"url": url, "status": status, "payload": payload, "bytes": len(body),
                "last_modified": headers.get("Last-Modified") if headers else None}


def lowest_prices(auctions, commodities):
    """item id -> (lowest buyout / quantity, lowest buyout, largest quantity in one listing, listings)."""
    best = {}

    def add(item, unit, whole, quantity):
        old = best.get(item)
        best[item] = (unit, whole, quantity, 1) if old is None else \
            (min(unit, old[0]), min(whole, old[1]), max(quantity, old[2]), old[3] + 1)

    for row in auctions or []:
        buyout = row.get("buyout")
        item = (row.get("item") or {}).get("id")
        if buyout and item is not None:
            quantity = row.get("quantity") or 1
            add(item, buyout / quantity, buyout, quantity)
    for row in commodities or []:
        unit = row.get("unit_price")
        item = (row.get("item") or {}).get("id")
        if unit and item is not None:
            add(item, unit, unit, row.get("quantity") or 1)
    return best
