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

With --hourly-dir, each newly recorded hour also appends one line to
<dir>/<Taiwan date YYYY-MM-DD>.jsonl, for time-of-day and day-of-week studies
(.agents/skills/wow-forever/scripts/auction_hours.py). The market page never reads
these files. A line is one snapshot of the stackable items (/commodities):

    {"hour": 498719, "at": "2026-11-23T07:26+08:00",
     "items": {"2772": [low, units, firstN], ...}}

hour is the same hour index as above, at the snapshot's Last-Modified in Taiwan time;
low is the lowest unit price in copper, units the units listed, and firstN the average
unit price of the cheapest --first-units units (all of them when fewer are listed),
roughly what a buyer of that many pays. An item missing from a line was not listed.
Day files older than --hourly-keep-days are deleted; git history keeps them.
"""

import argparse
import datetime
import email.utils
import json
import os
from pathlib import Path
import sys
from urllib.error import URLError

from blizzard_api import Api, auction_depth, commodity_rows, get_token, lowest_prices
from collect_guild import Publisher, SnapshotError

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


def commodity_hour(stackable_rows, first):
    """item id -> [lowest unit price, units listed, average unit price of the cheapest `first` units]."""
    out = {}
    for item, ladder in auction_depth([], stackable_rows).items():
        if not ladder:
            continue
        units = sum(quantity for _, quantity in ladder)
        need = left = min(first, units)
        cost = 0
        for price, quantity in ladder:
            take = min(quantity, left)
            cost += take * price
            left -= take
            if not left:
                break
        out[item] = [ladder[0][0], units, round(cost / need)]
    return out


def append_hourly(directory, hour, at, values, keep_days):
    """Append one snapshot to <directory>/<Taiwan date>.jsonl unless that hour is there; prune old days."""
    day = datetime.datetime.fromtimestamp(hour * 3600, TW).date()
    path = directory / f"{day.isoformat()}.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    if lines and json.loads(lines[-1])["hour"] >= hour:
        return None
    directory.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"hour": hour, "at": at, "items": values}, separators=(",", ":")) + "\n")
    oldest = day - datetime.timedelta(days=keep_days - 1)
    for old in directory.glob("*.jsonl"):
        try:
            stale = datetime.date.fromisoformat(old.stem) < oldest
        except ValueError:
            continue
        if stale:
            old.unlink()
    return path


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
    parser.add_argument("--publish-depth", action="store_true", help="publish the latest TW Horde ladder to Workers KV")
    parser.add_argument("--hourly-dir", type=Path, help="also append stackables' price and units to <dir>/<date>.jsonl")
    parser.add_argument("--hourly-keep-days", type=int, default=56, help="Taiwan days of --hourly-dir files kept")
    parser.add_argument("--first-units", type=int, default=20, help="units averaged for the third --hourly-dir value")
    args = parser.parse_args()

    token = get_token()
    publisher = None
    if args.publish_depth:
        if (args.region, args.ruleset, args.house) != ("tw", 1, 113):
            parser.error("--publish-depth requires the TW PvP Horde auction house 113")
        publisher = Publisher(os.environ["DAWNBLADE_PUBLISH_URL"], os.environ["DAWNBLADE_PUBLISH_TOKEN"])
        try:
            publisher.send("battle-net-token", {"accessToken": token})
        except (SnapshotError, URLError, TimeoutError):
            summarize("::warning::Armory authorization could not be refreshed.")
    api = Api(args.region, token)
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
    single_rows = (auctions["payload"] or {}).get("auctions") or []
    stackable_rows = commodity_rows(commodities["payload"])
    if not isinstance(single_rows, list) or not isinstance(stackable_rows, list) or (
        (args.region, args.ruleset, args.house) == ("tw", 1, 113) and not (single_rows and stackable_rows)
    ):
        summarize("::warning::The latest Horde snapshot is missing auction rows; nothing recorded.")
        return
    prices = lowest_prices(single_rows, stackable_rows)

    data = json.loads(args.out.read_text(encoding="utf-8")) if args.out.is_file() else {"hours": [], "items": {}}
    items, hours = data["items"], data["hours"]
    listed_before = sum(1 for count, series in items.values() if series[-1][1] is not None)
    if not prices or len(prices) < args.min_share * listed_before:
        summarize(f"::warning::snapshot {iso_tw(modified)} lists {len(prices)} items against "
                  f"{listed_before} last time; skipped as incomplete")
        return

    if publisher:
        try:
            publisher.send("market-depth", {
                "schema": 1, "source": "official", "region": args.region, "ruleset": args.ruleset,
                "house": args.house, "updatedAt": modified.isoformat(),
                "depth": auction_depth(single_rows, stackable_rows),
            })
        except (SnapshotError, URLError, TimeoutError):
            summarize("::warning::Price ladder could not be published; continuing with market history.")
        else:
            summarize(f"Price ladder published for {iso_tw(modified)}.")
    if hours and hour <= hours[-1]:
        summarize(f"Snapshot {iso_tw(modified)} is already recorded; nothing to do.")
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
    if args.hourly_dir:
        stackables = commodity_hour(stackable_rows, args.first_units)
        path = append_hourly(args.hourly_dir, hour, iso_tw(modified), stackables, args.hourly_keep_days)
        if path:
            summarize(f"Hourly units: {len(stackables):,} stackable items added to {path.name} "
                      f"({path.stat().st_size / 1024:.0f} KB).")


if __name__ == "__main__":
    sys.exit(main())
