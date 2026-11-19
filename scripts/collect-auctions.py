#!/usr/bin/env python3
"""Add the latest hourly snapshot of the Horde auction house to auctions.json.

Runs hourly in GitHub Actions (.github/workflows/auction-collect.yml), which keeps
the file on the `auction-data` branch; the market page reads it from there. The
Battle.net API refreshes WoW Forever auction data once an hour: the house endpoint
lists items that do not stack (gear, weapons, recipes) and /commodities lists the
stackable ones (herbs, ore, potions) under the key `auctions`.

    BLIZZARD_CLIENT_ID=... BLIZZARD_CLIENT_SECRET=... \\
        python3 scripts/collect-auctions.py --out auction-data/auctions.json

auctions.json keeps, per item id, the units on sale now and the lowest unit price as
change points: [count, [[hour, price], ...]], where hour is hours since
the Unix epoch (UTC) and price is copper, or null once the item is gone. `hours`
lists the snapshots taken since `hourlyFrom`; before that (Taiwan days older than
--hourly-days), each day is folded into one point at its midnight holding the
day's lowest price, and days older than --keep-days are dropped. A snapshot that is
already recorded, or one that looks broken (far fewer listings than the last one),
is skipped without touching the file, and so is an hour whose /commodities request
failed or comes from another hour, so stackables are not marked gone by mistake.
"""

import argparse
import datetime
import email.utils
import json
import os
from pathlib import Path
import sys

from blizzard_api import Api, commodity_rows, get_token, lowest_prices

TW = datetime.timezone(datetime.timedelta(hours=8))


def iso_tw(when):
    return when.astimezone(TW).isoformat(timespec="minutes")


def tw_midnight(hour):
    """Hour index of the Taiwan midnight at or before `hour`."""
    return (hour + 8) // 24 * 24 - 8


def fold_days(series, hourly_from):
    """Fold points before hourly_from (a Taiwan midnight) into one point per day: that day's lowest price."""
    old = [p for p in series if p[0] < hourly_from]
    if not old:
        return series
    recent = [p for p in series if p[0] >= hourly_from]
    by_day = {}
    for hour, price in old:
        by_day.setdefault(tw_midnight(hour), []).append((hour, price))
    folded, carry = [], None
    for day in sorted(by_day):
        points = by_day[day]
        prices = [price for _, price in points]
        if points[0][0] != day and carry is not None:
            prices.append(carry)  # the price in effect when the day began
        listed = [price for price in prices if price is not None]
        value = min(listed) if listed else None
        if not folded or folded[-1][1] != value:
            folded.append([day, value])
        carry = points[-1][1]
    # Keep the hourly part exact: restate the price in effect at hourly_from if folding changed it.
    if (not recent or recent[0][0] != hourly_from) and folded[-1][1] != carry:
        recent.insert(0, [hourly_from, carry])
    return folded + recent


def prune(items, hours, latest, hourly_days, keep_days):
    hourly_from = tw_midnight(latest) - hourly_days * 24
    keep_from = tw_midnight(latest) - keep_days * 24
    hours[:] = [h for h in hours if h >= hourly_from]
    for key in list(items):
        series = fold_days(items[key][1], hourly_from)
        older = [p for p in series if p[0] < keep_from]
        kept = [p for p in series if p[0] >= keep_from]
        if older and older[-1][1] is not None and not (kept and kept[0][0] == keep_from):
            kept.insert(0, [keep_from, older[-1][1]])
        if not kept or all(p[1] is None for p in kept):
            del items[key]
        else:
            items[key][1] = kept
    return hourly_from


def summarize(message):
    print(message)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(message + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True, help="auctions.json to update")
    parser.add_argument("--region", default="tw")
    parser.add_argument("--ruleset", type=int, default=1, help="TW: 1 = PvP")
    parser.add_argument("--house", type=int, default=113, help="TW: 113 = the Asia PvP Horde auction house")
    parser.add_argument("--faction", default="部落")
    parser.add_argument("--hourly-days", type=int, default=7, help="days kept hour by hour")
    parser.add_argument("--keep-days", type=int, default=90, help="days kept in all (older days: daily low)")
    parser.add_argument("--min-share", type=float, default=0.4,
                        help="skip a snapshot listing fewer items than this share of the last one")
    args = parser.parse_args()

    api = Api(args.region, get_token())
    base = f"/data/wow/ruleset/{args.ruleset}/auctions/{args.house}"
    auctions = api.get(base)
    if auctions["status"] != 200 or not auctions["last_modified"]:
        summarize(f"::warning::auction house {args.house}: HTTP {auctions['status']}; nothing recorded")
        return
    modified = email.utils.parsedate_to_datetime(auctions["last_modified"])
    hour = int(modified.timestamp() // 3600)
    commodities = api.get(f"{base}/commodities")
    c_modified = commodities["last_modified"]
    if commodities["status"] != 200 or not c_modified \
            or int(email.utils.parsedate_to_datetime(c_modified).timestamp() // 3600) != hour:
        summarize(f"::warning::commodities of house {args.house}: HTTP {commodities['status']}, "
                  f"Last-Modified {c_modified} vs {auctions['last_modified']}; nothing recorded")
        return
    prices = lowest_prices((auctions["payload"] or {}).get("auctions"), commodity_rows(commodities["payload"]))

    data = json.loads(args.out.read_text(encoding="utf-8")) if args.out.is_file() else {"hours": [], "items": {}}
    items, hours = data["items"], data["hours"]
    if hours and hour <= hours[-1]:
        summarize(f"Snapshot {iso_tw(modified)} is already recorded; nothing to do.")
        return
    listed_before = sum(1 for count, series in items.values() if series[-1][1] is not None)
    if not prices or len(prices) < args.min_share * listed_before:
        summarize(f"::warning::snapshot {iso_tw(modified)} lists {len(prices)} items against "
                  f"{listed_before} last time; skipped as incomplete")
        return

    changed = gone = new = 0
    for item, (unit, _whole, _largest, _listings, units) in prices.items():
        price = round(unit)
        entry = items.setdefault(str(item), [0, []])
        if not entry[1]:
            new += 1
        if not entry[1] or entry[1][-1][1] != price:
            entry[1].append([hour, price])
            changed += 1
        entry[0] = units
    for key, entry in items.items():
        if int(key) not in prices and entry[1][-1][1] is not None:
            entry[1].append([hour, None])
            entry[0] = 0
            gone += 1
    hours.append(hour)
    hourly_from = prune(items, hours, hour, args.hourly_days, args.keep_days)

    data.update({
        "source": f"Battle.net API {api.query['namespace']} ruleset {args.ruleset} auction house {args.house}",
        "region": args.region, "ruleset": args.ruleset, "house": args.house, "faction": args.faction,
        "updatedAt": iso_tw(modified),
        "fetchedAt": iso_tw(datetime.datetime.now(datetime.timezone.utc)),
        "hourlyFrom": hourly_from,
        "keepDays": args.keep_days,
        "hours": hours,
        "items": dict(sorted(items.items(), key=lambda kv: int(kv[0]))),
    })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    summarize(f"Snapshot {iso_tw(modified)}: {len(prices):,} items listed ({new:,} new, "
              f"{changed - new:,} new lowest price, {gone:,} gone); {len(hours)} snapshots kept; "
              f"{args.out.stat().st_size / 1024:.0f} KB.")


if __name__ == "__main__":
    sys.exit(main())
