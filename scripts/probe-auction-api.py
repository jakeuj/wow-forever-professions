#!/usr/bin/env python3
"""Probe the Battle.net auction API for WoW Forever and find the house we scan.

Reads BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET from the environment (repo
Secrets in GitHub Actions; never commit them), lists the rulesets and the auction
house index, downloads every house once, and compares each house's lowest unit
prices with the owner's Horde scan in market/data.json. The house whose prices
match the scan best is the one the scan was taken at.

    BLIZZARD_CLIENT_ID=... BLIZZARD_CLIENT_SECRET=... python3 scripts/probe-auction-api.py

Prints a Markdown report (also appended to $GITHUB_STEP_SUMMARY when set) and,
with --out, writes the findings as JSON. The access token is never printed.
"""

import argparse
import base64
import gzip
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REPO = Path(__file__).resolve().parent.parent
TOKEN_URL = "https://oauth.battle.net/token"
LOCALES = {"tw": "zh_TW", "kr": "ko_KR", "us": "en_US", "eu": "en_GB"}
USER_AGENT = "wow-forever-professions-auction-probe"


def fetch(url, headers=None, data=None, timeout=180):
    """Return (status, headers, body); 404 comes back as a status, other errors retry."""
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


def get_token(client_id, client_secret):
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
    def __init__(self, region, token):
        self.base = f"https://{region}.api.blizzard.com"
        self.query = {"namespace": f"dynamic-forever-{region}", "locale": LOCALES.get(region, "en_US")}
        self.auth = {"Authorization": f"Bearer {token}"}
        self.calls = 0

    def get(self, path):
        url = f"{self.base}{path}?{urllib.parse.urlencode(self.query)}"
        self.calls += 1
        status, headers, body = fetch(url, self.auth)
        payload = None
        if status == 200:
            payload = json.loads(body)
        return {"url": url, "status": status, "payload": payload, "bytes": len(body),
                "last_modified": headers.get("Last-Modified") if headers else None}


def strip_links(value):
    if isinstance(value, dict):
        return {k: strip_links(v) for k, v in value.items() if k != "_links"}
    if isinstance(value, list):
        return [strip_links(v) for v in value]
    return value


def text(value):
    if isinstance(value, dict):  # localized fields can come back as {"zh_TW": "..."}
        return next(iter(value.values()), "") if value else ""
    return "" if value is None else str(value)


def house_list(index):
    """The index's list of houses, whatever the key is called."""
    for value in (index or {}).values():
        if isinstance(value, list) and value and isinstance(value[0], dict) and "id" in value[0]:
            return value
    return []


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


def load_scan(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    fields = data["fields"]
    rows = [dict(zip(fields, row)) for row in data["items"]]
    rows = [r for r in rows if r["day"] == data["latestDay"] and r["price"]]
    latest = {r["id"]: r["price"] for r in rows}
    details = {r["id"]: {"class": data["classes"].get(str(r["class"]), str(r["class"])), "count": r["count"]}
               for r in rows}
    return latest, details, data.get("scanStartedAt") or data["latestDay"]


def compare(prices, scan):
    shared = [i for i in scan if i in prices]
    # Only listings of more than one unit tell whether buyout is per unit or for the whole stack.
    stacked = [i for i in shared if prices[i][2] > 1]
    same = lambda a, b: round(a) == b
    rate = lambda items, k: sum(same(prices[i][k], scan[i]) for i in items) / len(items) if items else 0
    return {
        "shared": len(shared),
        "unit_same": rate(shared, 0),
        "stack_same": rate(shared, 1),
        "unit_near": sum(abs(prices[i][0] - scan[i]) <= 0.05 * scan[i] for i in shared) / len(shared)
        if shared else 0,
        "stacked": len(stacked),
        "stacked_total_same": rate(stacked, 0),  # buyout is the stack total
        "stacked_unit_same": rate(stacked, 1),  # buyout is already per unit
    }


def pct(value):
    return f"{value * 100:.0f}%"


def ruleset_of(owner):
    """The ruleset id a house payload names, from its id or its key link."""
    if isinstance(owner, dict) and owner.get("id") is not None:
        return owner["id"]
    found = re.search(r"/ruleset/(\d+)", json.dumps(owner)) if owner else None
    return int(found.group(1)) if found else None


def by_class(prices, scan, details):
    """Per item class: shared items, share at the same lowest unit price, median listings / scanned units."""
    groups = {}
    for item in scan:
        if item in prices:
            groups.setdefault(details[item]["class"], []).append(item)
    rows = []
    for name, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        ratios = sorted(prices[i][3] / details[i]["count"] for i in items if details[i]["count"])
        rows.append({"class": name, "shared": len(items),
                     "unit_same": sum(round(prices[i][0]) == scan[i] for i in items) / len(items),
                     "listings_per_unit": ratios[len(ratios) // 2] if ratios else None})
    return rows


def probe_region(region, token, ruleset, scan, details, lines):
    api = Api(region, token)
    result = {"region": region, "namespace": api.query["namespace"], "rulesets": [], "houses": []}

    rulesets = api.get("/data/wow/ruleset/index")
    lines.append(f"## {region.upper()} `{api.query['namespace']}`\n")
    if rulesets["status"] != 200:
        lines.append(f"Ruleset index: HTTP {rulesets['status']}; skipping this region.\n")
        result["error"] = f"ruleset index HTTP {rulesets['status']}"
        return result
    lines.append("| Ruleset | Name | Status | Houses in index |\n| --- | --- | --- | --- |")
    index_ids = {}
    for entry in house_list(rulesets["payload"]):
        rid = entry["id"]
        detail = api.get(f"/data/wow/ruleset/{rid}")["payload"] or {}
        index = api.get(f"/data/wow/ruleset/{rid}/auctions/")
        ids = [h["id"] for h in house_list(index["payload"])]
        index_ids[rid] = ids
        if rid == ruleset:
            result["index"] = strip_links(index["payload"])
        status = text(detail.get("status"))  # {"type": "UP", ...} or a plain string
        result["rulesets"].append({"id": rid, "name": text(entry.get("name")), "status": status,
                                   "index_status": index["status"], "houses": ids})
        lines.append(f"| {rid} | {text(entry.get('name'))} | {status or '—'} | "
                     f"{len(ids)} (HTTP {index['status']}) |")
    same_sets = len({tuple(sorted(v)) for v in index_ids.values()}) == 1
    lines.append(f"\nEvery ruleset lists the same houses: **{'yes' if same_sets else 'no'}**.\n")

    lines.append(f"### Ruleset {ruleset} houses\n")
    lines.append("<details><summary>Index (links removed)</summary>\n\n```json\n"
                 + json.dumps(result.get("index"), ensure_ascii=False, indent=1)[:4000] + "\n```\n</details>\n")
    houses = house_list(result.get("index"))
    if not houses:
        lines.append(f"Ruleset {ruleset} has no auction house list.\n")
        return result
    lines.append("| House | Name | Ruleset | Listings | Stacks (max) | Items | Last-Modified | Items also in scan "
                 "| Same lowest price (unit) | Same (whole listing) | Within 5% (unit) |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    house_prices = {}
    for house in houses:
        hid = house["id"]
        base = f"/data/wow/ruleset/{ruleset}/auctions/{hid}"
        auctions, commodities = api.get(base), api.get(f"{base}/commodities")
        a_rows = (auctions["payload"] or {}).get("auctions")
        c_rows = (commodities["payload"] or {}).get("commodities")
        prices = lowest_prices(a_rows, c_rows)
        match = compare(prices, scan)
        owner = (auctions["payload"] or {}).get("ruleset")
        house_prices[hid] = prices
        info = {
            "id": hid, "name": text(house.get("name")),
            "ruleset": ruleset_of(owner), "ruleset_raw": strip_links(owner),
            "row_keys": sorted({k for row in a_rows or [] for k in row}),
            "item_keys": sorted({k for row in a_rows or [] for k in (row.get("item") or {})}),
            "sample": (a_rows or [])[:3],
            "stack_listings": sum((row.get("quantity") or 1) > 1 for row in a_rows or []),
            "max_quantity": max([row.get("quantity") or 1 for row in a_rows or []], default=0),
            "auctions_status": auctions["status"], "commodities_status": commodities["status"],
            "auctions": len(a_rows or []), "commodities": len(c_rows or []),
            "items": len(prices), "bytes": auctions["bytes"] + commodities["bytes"],
            "last_modified": auctions["last_modified"],
            "commodities_last_modified": commodities["last_modified"],
            "keys": sorted((auctions["payload"] or {}).keys()), **match,
        }
        result["houses"].append(info)
        listings = f"{info['auctions']:,} + {info['commodities']:,}"
        if auctions["status"] != 200 or commodities["status"] != 200:
            listings += f" (HTTP {auctions['status']}/{commodities['status']})"
        lines.append(f"| {hid} | {info['name'] or '—'} | {info['ruleset'] if info['ruleset'] is not None else '—'} | "
                     f"{listings} | {info['stack_listings']:,} ({info['max_quantity']}) | {info['items']:,} | "
                     f"{info['last_modified'] or '—'} | {match['shared']:,} | {pct(match['unit_same'])} | "
                     f"{pct(match['stack_same'])} | {pct(match['unit_near'])} |")
    ranked = sorted(result["houses"], key=lambda h: (h["unit_same"], h["shared"]), reverse=True)
    if ranked and ranked[0]["shared"]:
        top = ranked[0]
        runner = ranked[1] if len(ranked) > 1 else None
        result["best"] = top["id"]
        lines.append(f"\nBest match with the scan: **house {top['id']}** {top['name']} — "
                     f"{pct(top['unit_same'])} of {top['shared']:,} shared items at the same lowest unit price"
                     + (f"; next best is house {runner['id']} at {pct(runner['unit_same'])}." if runner else ".")
                     + "\n")
        if top["stacked"]:
            lines.append(f"Of its {top['stacked']:,} shared items listed in stacks, {pct(top['stacked_total_same'])} "
                         f"match if `buyout` is the stack total and {pct(top['stacked_unit_same'])} if it is "
                         "already per unit.\n")
        else:
            lines.append("No shared item is listed in stacks, so `buyout` per unit vs per stack is still open.\n")
        lines.append(f"Listing fields in house {top['id']}: `{', '.join(top['row_keys'])}`; "
                     f"item fields: `{', '.join(top['item_keys'])}`; house ruleset: "
                     f"`{json.dumps(top['ruleset_raw'], ensure_ascii=False)}`.\n")
        lines.append("<details><summary>First listings</summary>\n\n```json\n"
                     + json.dumps(top["sample"], ensure_ascii=False, indent=1) + "\n```\n</details>\n")
        classes = by_class(house_prices[top["id"]], scan, details)
        result["by_class"] = classes
        # Per-item lowest prices of the matched house, to compare offline with a newer scan.
        result["best_prices"] = {str(item): value for item, value in sorted(house_prices[top["id"]].items())}
        lines.append(f"House {top['id']} by item class (listings per unit: API listings of an item ÷ units "
                     "the scan counted; near 1 means each listing is one unit):\n")
        lines.append("| Class | Shared items | Same lowest price | Listings per unit (median) |\n| --- | --- | --- | --- |")
        for row in classes:
            ratio = f"{row['listings_per_unit']:.2f}" if row["listings_per_unit"] is not None else "—"
            lines.append(f"| {row['class']} | {row['shared']:,} | {pct(row['unit_same'])} | {ratio} |")
        lines.append("")
    lines.append(f"API calls in this region: {api.calls}.\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--regions", default="tw", help="comma-separated API regions to probe (tw, kr, us, eu)")
    parser.add_argument("--ruleset", type=int, default=1, help="ruleset whose houses to download (TW: 1 = PvP)")
    parser.add_argument("--scan", type=Path, default=REPO / "market/data.json", help="market page data to match")
    parser.add_argument("--out", type=Path, help="write the findings as JSON")
    args = parser.parse_args()

    client_id = os.environ.get("BLIZZARD_CLIENT_ID")
    client_secret = os.environ.get("BLIZZARD_CLIENT_SECRET")
    if not client_id or not client_secret:
        sys.exit("set BLIZZARD_CLIENT_ID and BLIZZARD_CLIENT_SECRET (in CI they come from repo Secrets)")

    scan, details, scan_time = load_scan(args.scan)
    started = time.time()
    token = get_token(client_id, client_secret)
    lines = [f"# Auction API probe\n",
             f"Compared with the Horde scan from {scan_time} ({len(scan):,} items seen in the latest scan day).\n"]
    report = {"scan": scan_time, "scanItems": len(scan), "regions": []}
    for region in [r.strip() for r in args.regions.split(",") if r.strip()]:
        report["regions"].append(probe_region(region, token, args.ruleset, scan, details, lines))
    lines.append(f"Finished in {time.time() - started:.0f} s.")

    markdown = "\n".join(lines) + "\n"
    print(markdown)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(markdown)
    if args.out:
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
