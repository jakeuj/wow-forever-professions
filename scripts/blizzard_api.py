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
    """GET helper for one region's Forever namespaces; defaults to dynamic data."""

    def __init__(self, region, token):
        self.region = region
        self.base = f"https://{region}.api.blizzard.com"
        self.query = {"namespace": f"dynamic-forever-{region}", "locale": LOCALES.get(region, "en_US")}
        self.auth = {"Authorization": f"Bearer {token}"}
        self.calls = 0

    def get(self, path, kind=None, timeout=180, *, all_locales=False):
        query = dict(self.query)
        if kind is not None:
            query["namespace"] = f"{kind}-forever-{self.region}"
        if all_locales:
            query.pop("locale", None)
        encoded_path = urllib.parse.quote(path, safe="/-_.~")
        url = f"{self.base}{encoded_path}?{urllib.parse.urlencode(query)}"
        self.calls += 1
        status, headers, body = fetch(url, self.auth, timeout=timeout)
        payload = json.loads(body) if status == 200 else None
        return {"url": url, "status": status, "payload": payload, "bytes": len(body),
                "last_modified": headers.get("Last-Modified") if headers else None}


def commodity_rows(payload):
    """Listings of a /commodities response. Forever names the list `auctions`; Retail calls it `commodities`."""
    payload = payload or {}
    return payload.get("commodities") or payload.get("auctions") or []


def lowest_prices(auctions, commodities):
    """item id -> (lowest buyout / quantity, lowest buyout, largest quantity in one listing, listings, units)."""
    best = {}

    def add(item, unit, whole, quantity):
        old = best.get(item)
        best[item] = (unit, whole, quantity, 1, quantity) if old is None else \
            (min(unit, old[0]), min(whole, old[1]), max(quantity, old[2]), old[3] + 1, old[4] + quantity)

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


def auction_depth(auctions, commodities):
    """Roll up immediately purchasable listings at each unit price."""
    depth = {}
    invalid = set()
    for rows, stackable in ((auctions, False), (commodities, True)):
        for row in rows:
            item = (row.get("item") or {}).get("id")
            price = row.get("unit_price" if stackable else "buyout")
            quantity = row.get("quantity", 1)
            if not isinstance(item, int) or not isinstance(price, int) or price <= 0:
                continue
            if not isinstance(quantity, int) or quantity <= 0 or (not stackable and quantity != 1):
                invalid.add(item)
                continue
            levels = depth.setdefault(item, {})
            levels[price] = levels.get(price, 0) + quantity
    return {str(item): None if item in invalid else sorted(depth[item].items())
            for item in sorted(depth.keys() | invalid)}
