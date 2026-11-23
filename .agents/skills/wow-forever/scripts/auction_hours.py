#!/usr/bin/env python3
"""Compare Horde auction prices and supply by Taiwan hour of day (or weekday).

Reads the per-hour files that scripts/collect-auctions.py --hourly-dir writes to
hourly/<Taiwan date>.jsonl on the repo's `auction-data` branch: one line per snapshot
with, per stackable item id, [lowest unit price, units listed, average unit price of
the cheapest 20 units] (format in that script's header). Collection began
2026-11-23; time-of-day needs 1-2 weeks of it, weekdays several weeks.

Prices drift for days (patches, farming waves), so comparing raw hours, or one day
with another, mixes the trend into the hour. Each value is instead compared with the
median of the same item over the surrounding 24 hours (a window holding every hour of
the day once; 7 days with --weekday), and those ratios are averaged per Taiwan day
and hour bucket. Per bucket the table gives the median over days and on how many days
the bucket was below the usual level; `*` marks buckets at least 2% off where the
days agree well enough (two-sided sign test p < 0.05). A category pools its items
day by day.

    python3 auction_hours.py 秘銀錠 瑟銀錠 鐵礦石       # items by exact name
    python3 auction_hours.py --category 金屬與石頭       # one category, items pooled
    python3 auction_hours.py                            # every category, compact
    python3 auction_hours.py 秘銀錠 --weekday           # by day of week

Names and categories come from market/data.json in --repo (default: cwd). --source
reads a local folder of the .jsonl files instead of the branch, e.g. a worktree:
git worktree add <dir> origin/auction-data, then --source <dir>/hourly.
"""

import argparse
import datetime
import json
import math
from pathlib import Path
import statistics
import sys
import urllib.error
import urllib.request

SOURCE = "https://raw.githubusercontent.com/jakeuj/wow-forever-professions/auction-data/hourly/"
TW = datetime.timezone(datetime.timedelta(hours=8))
METRICS = {"low": 0, "units": 1, "first": 2}
TITLES = {"low": "最低價", "first": "前20件均價", "units": "件數"}
WEEKDAYS = "一二三四五六日"
COVER = 0.75  # share of the comparison window that must hold data
SMALL = 0.02  # differences under this are not worth timing a purchase for


def tw_day(hour):
    return (hour + 8) // 24


def load(source, days, today=None):
    """[(hour, items)] sorted by hour, from the hourly files of the last `days` Taiwan dates."""
    today = today or datetime.datetime.now(TW).date()
    names = [f"{today - datetime.timedelta(days=n)}.jsonl" for n in range(days - 1, -1, -1)]
    texts = []
    if source and not source.startswith(("http://", "https://")):
        folder = Path(source)
        texts = [(folder / name).read_text(encoding="utf-8") for name in names if (folder / name).is_file()]
    else:
        base = source or SOURCE
        for name in names:
            request = urllib.request.Request(base + name, headers={"User-Agent": "wow-forever-professions auction_hours"})
            try:
                with urllib.request.urlopen(request, timeout=60) as resp:
                    texts.append(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
    snapshots = {}
    for text in texts:
        for line in text.splitlines():
            if line.strip():
                row = json.loads(line)
                snapshots[row["hour"]] = row["items"]
    return sorted(snapshots.items())


def residuals(snapshots, item, metric, half):
    """{hour: log(value) - median log value within [hour - half, hour + half)}, where the window has enough data.

    Units count an unlisted hour as 0 (log1p); prices skip it."""
    index = METRICS[metric]
    values = {}
    for hour, items in snapshots:
        entry = items.get(item)
        if metric == "units":
            values[hour] = math.log1p(entry[index] if entry else 0)
        elif entry:
            values[hour] = math.log(entry[index])
    hours = sorted(values)
    need = COVER * 2 * half
    out, lo, hi = {}, 0, 0
    for hour in hours:
        while hours[lo] < hour - half:
            lo += 1
        while hi < len(hours) and hours[hi] < hour + half:
            hi += 1
        if hi - lo >= need:
            out[hour] = values[hour] - statistics.median(values[h] for h in hours[lo:hi])
    return out


def group_of(hour, bucket, weekday):
    if weekday:
        return datetime.datetime.fromtimestamp(hour * 3600, TW).weekday()
    return (hour + 8) % 24 // bucket


def by_day(res, bucket, weekday):
    """{group: {Taiwan day: mean residual}}."""
    sums = {}
    for hour, value in res.items():
        sums.setdefault(group_of(hour, bucket, weekday), {}).setdefault(tw_day(hour), []).append(value)
    return {g: {d: sum(v) / len(v) for d, v in days.items()} for g, days in sums.items()}


def pool(tables):
    """Average several items' {group: {day: value}} day by day, so each day counts once."""
    sums = {}
    for table in tables:
        for group, days in table.items():
            for day, value in days.items():
                sums.setdefault(group, {}).setdefault(day, []).append(value)
    return {g: {d: sum(v) / len(v) for d, v in days.items()} for g, days in sums.items()}


def sign_p(below, above):
    """Two-sided sign test: how likely a split at least this uneven is by chance."""
    n = below + above
    if not n:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(below, above) + 1)) / 2 ** n)


def notable(s):
    return s["p"] < 0.05 and abs(s["change"]) >= SMALL


def summarize(days):
    values = list(days.values())
    below, above = sum(v < 0 for v in values), sum(v > 0 for v in values)
    return {"change": math.expm1(statistics.median(values)), "days": len(values),
            "below": below, "above": above, "p": sign_p(below, above)}


def analyze(snapshots, items, bucket=3, weekday=False):
    """{metric: {group: summary}} for one item or several pooled."""
    half = 84 if weekday else 12
    out = {}
    for metric in TITLES:
        table = pool([by_day(residuals(snapshots, item, metric, half), bucket, weekday) for item in items])
        out[metric] = {g: summarize(days) for g, days in sorted(table.items())}
    return out


def label(group, bucket, weekday):
    if weekday:
        return f"週{WEEKDAYS[group]}"
    start = group * bucket
    return f"{start:02d} 時" if bucket == 1 else f"{start:02d}–{start + bucket - 1:02d} 時"


def cell(s, metric):
    if not s:
        return "—"
    word = "少" if metric == "units" else "低"
    star = "*" if notable(s) else " "
    return f"{s['change']:+.0%}{star} {s['below']}/{s['days']} 天較{word}"


def verdict(result, bucket, weekday):
    lines = []
    first = result["first"]
    if first:
        group = min(first, key=lambda g: first[g]["change"])
        s = first[group]
        where = f"{label(group, bucket, weekday)}，前20件均價比平常 {s['change']:+.0%}（{s['days']} 天中 {s['below']} 天較低）"
        lines.append(("較便宜的時段：" if notable(s) and s["change"] < 0 else
                      "沒有哪個時段在多數天都比較便宜；最低是 ") + where)
    units = result["units"]
    if units:
        group = max(units, key=lambda g: units[g]["change"])
        s = units[group]
        where = f"{label(group, bucket, weekday)}，件數比平常 {s['change']:+.0%}（{s['days']} 天中 {s['above']} 天較多）"
        lines.append(("貨最多的時段：" if notable(s) and s["change"] > 0 else "件數沒有穩定的時段差；最多是 ") + where)
    return lines


def market_names(repo):
    """id -> (name, category) from market/data.json; {} when the repo has none."""
    path = repo / "market" / "data.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    fields = data["fields"]
    out = {}
    for row in data["items"]:
        item = dict(zip(fields, row))
        category = data["subclasses"].get(f"{item['class']}.{item['subclass']}") or data["classes"].get(str(item["class"]), "")
        out[str(item["id"])] = (item["name"], category)
    return out


def steady(snapshots, item, min_price):
    """Listed in most snapshots and not priced in single coppers, so its ratios mean something."""
    lows = [items[item][0] for _, items in snapshots if item in items]
    return len(lows) >= COVER * len(snapshots) and statistics.median(lows) >= min_price


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="*", help="exact item names (market/data.json)")
    parser.add_argument("--ids", nargs="+", default=[], help="item ids")
    parser.add_argument("--category", help="pool every steady item whose category contains this, e.g. 金屬與石頭 or 草藥")
    parser.add_argument("--days", type=int, default=28, help="Taiwan days to read (default 28)")
    parser.add_argument("--bucket", type=int, default=3, choices=(1, 2, 3, 4, 6), help="hours per bucket (default 3)")
    parser.add_argument("--weekday", action="store_true", help="group by day of week instead (7-day comparison window)")
    parser.add_argument("--min-price", type=float, default=0.01, help="categories: skip items under this many gold (default 0.01)")
    parser.add_argument("--source", help="folder or URL prefix of the hourly .jsonl files (default: the auction-data branch)")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="repo root with market/data.json (default: cwd)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    snapshots = load(args.source, args.days)
    if not snapshots:
        sys.exit("no hourly files found; collect-auctions.py --hourly-dir writes them from 2026-11-23")
    names = market_names(args.repo)
    seen = set().union(*(items for _, items in snapshots))
    floor = args.min_price * 10000

    subjects, missing = [], []
    for name in dict.fromkeys(args.names):
        ids = [i for i, (n, _) in names.items() if n == name and i in seen]
        if ids:
            subjects += [(f"{name}[{i}]", [i]) for i in ids]
        else:
            missing.append(name)
    for item in args.ids:
        if str(item) in seen:
            subjects.append((f"{names.get(str(item), (f'物品 {item}',))[0]}[{item}]", [str(item)]))
        else:
            missing.append(f"物品 {item}")
    overview = not subjects and not missing and not args.category
    categories = {}
    if args.category or overview:
        if not names:
            sys.exit("categories need market/data.json (run from the repo root or pass --repo)")
        for item in sorted(seen, key=int):
            category = names.get(item, ("", ""))[1]
            if category and (overview or args.category in category) and steady(snapshots, item, floor):
                categories.setdefault(category, []).append(item)
        if args.category:
            pooled = [i for c, ids in categories.items() for i in ids]
            if pooled:
                subjects.append((f"{args.category}（{len(pooled)} 種一起算）", pooled))
            else:
                missing.append(f"分類 {args.category}")
        else:
            subjects += [(f"{c}（{len(ids)} 種）", ids) for c, ids in sorted(categories.items()) if len(ids) >= 3]

    results = [(title, analyze(snapshots, ids, args.bucket, args.weekday)) for title, ids in subjects]
    first, last = snapshots[0][0], snapshots[-1][0]
    per_day = {}
    for hour, _ in snapshots:
        per_day[tw_day(hour)] = per_day.get(tw_day(hour), 0) + 1
    full = sum(n >= 18 for n in per_day.values())

    if args.json:
        json.dump({"from": first, "to": last, "snapshots": len(snapshots), "fullDays": full,
                   "bucket": None if args.weekday else args.bucket, "weekday": args.weekday, "missing": missing,
                   "subjects": [{"title": t, "metrics": r} for t, r in results]},
                  sys.stdout, ensure_ascii=False, indent=1)
        print()
        return

    def when(hour):
        return datetime.datetime.fromtimestamp(hour * 3600, TW).strftime("%m/%d %H時")

    print(f"部落每小時紀錄 {when(first)} → {when(last)}：{len(snapshots)} 次快照，{len(per_day)} 天"
          f"（每天至少 18 次的有 {full} 天）")
    print("每個時點和同物品前後 " + ("3.5 天" if args.weekday else "12 小時") +
          "的中位數比，去掉多日漲跌後再依台灣" + ("星期" if args.weekday else "時段") + "彙整；"
          "數字是各天的中位數，* 表示差 2% 以上且多數天方向一致（符號檢定 p<0.05）。")
    if full < (21 if args.weekday else 7):
        print("⚠ 完整的天數還不夠" + ("（星期比較至少要三週）" if args.weekday else "（至少要 7 天）") + "，以下只供參考。")
    groups = range(7) if args.weekday else range(24 // args.bucket)
    if overview:
        for metric in ("first", "units"):
            print(f"\n## 各分類的{TITLES[metric]}（比當天平常）")
            print("分類 | " + " | ".join(label(g, args.bucket, args.weekday) for g in groups))
            for title, result in results:
                row = result[metric]
                print(title + " | " + " | ".join(
                    f"{row[g]['change']:+.0%}{'*' if notable(row[g]) else ''}" if g in row else "—" for g in groups))
    else:
        for title, result in results:
            print(f"\n## {title}")
            print("時段 | " + " | ".join(TITLES[m] for m in ("low", "first", "units")))
            for g in groups:
                print(label(g, args.bucket, args.weekday) + " | " +
                      " | ".join(cell(result[m].get(g), m) for m in ("low", "first", "units")))
            for line in verdict(result, args.bucket, args.weekday):
                print("- " + line)
    if missing:
        print("\n每小時紀錄沒有：" + "、".join(missing))
    print("\n價格是最低一口價與最便宜 20 件的均價（單價），不是成交價；件數是上架總數量。")


if __name__ == "__main__":
    main()
