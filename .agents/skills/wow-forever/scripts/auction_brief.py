#!/usr/bin/env python3
"""What to buy or sell at the Horde auction house right now: a short brief.

Reads every data-ah item on the personal pages; data-ah-buy-below="<gold>" on an
item marks the buy trigger that the page text states. Takes the current Horde
listings from the Battle.net API (one house + commodities request, credentials as
in forever_api.py), the hourly record on the auction-data branch for 7-day
context, wowamobi's realm-wide median (all three auction houses), and
Syndicator's bags when that save file exists. The market reference is the lowest of
wowamobi's median today, its median the day before and the Horde 7-day typical
price, so a single absurd listing cannot make something look like a bargain.

Now:   a page item at or under its trigger (items without one: a quarter of the
       market reference or less) with at most 3 units left at that price; something
       in your bags listed at 1.5x its 7-day typical price or more (sell).
Later: the same with plenty of units left, page items within 30 % of their
       trigger, triggers with nothing listed, and recipes not on the pages at a
       quarter of the market reference.

Prices are lowest buyouts (unit price for stackables), never sale prices.
"""

import argparse
import email.utils
from html.parser import HTMLParser
import json
from pathlib import Path
import statistics
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auction_changes as ac  # noqa: E402

REALM = "CAMWOW TW4 Realm 2 PvP"
PAGES = {"endgame": "鍛造清單", "alchemy": "煉金清單", "speculation": "配方期貨"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
FAR_BELOW = 0.25   # listed at a quarter of the market reference or less
NEAR = 1.3         # within 30 % of the trigger
SPIKE = 1.5        # bags: listed at 1.5x the 7-day typical price or more
SCARCE = 3         # units at the good price; more than this can wait
WEEK = 168


class PageItems(HTMLParser):
    """data-ah items with their trigger, shopping list and whether the row is skipped."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.items = [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "span" and "data-ah" in attrs and "data-ah-prefix" not in attrs:
            lists = [a.get("data-ah-list") for _, a in self.stack if a.get("data-ah-list")]
            skip = any("is-skip" in (a.get("class") or "").split() for _, a in self.stack)
            below = attrs.get("data-ah-buy-below")
            self.items.append({"name": attrs["data-ah"], "below": round(float(below) * 10000) if below else None,
                               "list": lists[-1] if lists else None, "skip": skip})
        if tag not in VOID:
            self.stack.append((tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def page_items(paths):
    """name -> {below: lowest trigger in copper or None, pages: [...], lists: [...], skip: all rows skipped}."""
    out = {}
    for path in paths:
        parser = PageItems()
        parser.feed(Path(path).read_text(encoding="utf-8"))
        page = PAGES.get(Path(path).parent.name, Path(path).parent.name)
        for item in parser.items:
            entry = out.setdefault(item["name"], {"below": None, "pages": [], "lists": [], "skip": True})
            if item["below"] is not None:
                entry["below"] = item["below"] if entry["below"] is None else min(entry["below"], item["below"])
            if page not in entry["pages"]:
                entry["pages"].append(page)
            if item["list"] and item["list"] not in entry["lists"]:
                entry["lists"].append(item["list"])
            entry["skip"] = entry["skip"] and item["skip"]
    return out


def typical(series, hours, now):
    """Median of the lowest price in force at each snapshot of the last 7 days, ignoring sold-out hours."""
    prices = [ac.price_at(series, h) for h in hours if now - WEEK < h <= now]
    prices = [p for p in prices if isinstance(p, int)]
    return statistics.median(prices) if prices else None


def units_at_or_below(levels, price):
    return sum(q for p, q in levels if p <= price)


def reference(item_id, realm_rows, record, hours):
    """Market reference: the lowest of wowamobi's realm-wide median today and the day before
    and the Horde 7-day typical price, so one absurd listing on any side cannot make a bargain."""
    row, series = realm_rows.get(item_id), record.get(str(item_id))
    values = [row[1], row[5]] if row else []
    if series:
        values.append(typical(series[1], hours, hours[-1]))
    values = [v for v in values if v]
    return min(values) if values else None


def classify(items, ids, levels, record, hours, realm_rows, meta, bags=None, max_now=5):
    """Sort page items (and bag items) into now / later lists. Pure: all inputs passed in.

    now:    at or under the trigger (items without a trigger: a quarter of the market
            reference or less) with only a few units left at that price
    plenty: the same, but enough units that it can wait
    """
    now_rows, plenty, near, empty, sell = [], [], [], [], []
    for name, info in items.items():
        if info["skip"]:
            continue
        for item_id in ids.get(name, []):
            level = levels.get(item_id) or []
            lowest = level[0][0] if level else None
            ref = reference(item_id, realm_rows, record, hours)
            base = {"name": name, "id": item_id, "pages": info["pages"], "price": lowest,
                    "units": sum(q for _, q in level), "below": info["below"], "reference": ref}
            if lowest is None:
                if info["below"] is not None:
                    empty.append(base)
                continue
            if info["below"] is not None:
                limit, why = (info["below"], "trigger") if lowest <= info["below"] else (None, None)
            elif ref and ref >= 10000 and lowest <= FAR_BELOW * ref:
                limit, why = FAR_BELOW * ref, "far_below"
            else:
                limit = why = None
            if limit is None:
                if info["below"] is not None and lowest <= NEAR * info["below"]:
                    near.append(base)
                continue
            row = {**base, "why": why, "units_ok": units_at_or_below(level, limit),
                   "value": info["below"] if why == "trigger" else ref}
            (now_rows if row["units_ok"] <= SCARCE else plenty).append(row)
    for item_id, count in (bags or {}).items():
        level = levels.get(item_id) or []
        record_row = record.get(str(item_id))
        if not level or not record_row:
            continue
        usual = typical(record_row[1], hours, hours[-1])
        lowest = level[0][0]
        if usual and lowest >= SPIKE * usual and lowest * count >= 10000:
            info = meta.get(str(item_id)) or [f"物品 {item_id}"]
            sell.append({"name": info[0], "id": item_id, "price": lowest, "usual": usual, "count": count,
                         "units": sum(q for _, q in level)})
    now_rows.sort(key=lambda r: -r["value"])
    plenty += now_rows[max_now:]
    del now_rows[max_now:]
    plenty.sort(key=lambda r: -r["value"])
    near.sort(key=lambda r: r["price"] / r["below"])
    sell.sort(key=lambda r: -r["price"] * r["count"])
    return {"now": now_rows, "sell": sell, "plenty": plenty, "near": near, "empty": empty}


def off_page(page_ids, levels, realm_rows, record, hours, meta, top):
    """Recipes and plans not on the pages, at a quarter of the market reference or less (reference >= 5g)."""
    out = []
    for item_id, level in levels.items():
        info = meta.get(str(item_id))
        if item_id in page_ids or not info or info[2] != 9:
            continue
        ref = reference(item_id, realm_rows, record, hours)
        if ref and ref >= 50000 and level[0][0] <= FAR_BELOW * ref:
            out.append({"name": info[0], "id": item_id, "price": level[0][0], "reference": ref,
                        "units": sum(q for _, q in level)})
    return sorted(out, key=lambda r: r["price"] / r["reference"])[:top]


def read_bags(root):
    """item id -> count over every character's bags, bank and mail; None when there is no save file."""
    import syndicator_inventory as si
    files = si.find_saved_files(root)
    if not files:
        return None
    counts = {}
    for _, character in si.ordered_items(si.load_data(files[0]).get("Characters", {})):
        for part in si.summarise(character).values():
            for item in part["items"]:
                counts[item["id"]] = counts.get(item["id"], 0) + item["count"]
    return counts


def coin(copper):
    return ac.coin(None if copper is None else round(copper))


def taiwan_time(http_date):
    """'Mon, 23 Nov 2026 03:26:29 GMT' -> '11/23 11:26'."""
    if not http_date:
        return "時間不明"
    when = email.utils.parsedate_to_datetime(http_date).astimezone(ac.TAIPEI)
    return when.strftime("%m/%d %H:%M")


def reason(r):
    if r["why"] == "trigger":
        return f"觸發價 {coin(r['below'])}，這價位以下 {r['units_ok']} 件"
    return f"行情約 {coin(r['reference'])}，只要四分之一以下，有 {r['units_ok']} 件"


def render(result, extra, modified, record_time, bags_note):
    lines = [f"部落拍賣場快訊（官方即時快照 {taiwan_time(modified)}；網站每小時紀錄到 {record_time}）", "", "## 現在處理"]
    actions = []
    for r in result["now"]:
        where = "、".join(r["pages"])
        actions.append(f"買 {r['name']} {coin(r['price'])}：{reason(r)}（{where}）")
    for r in result["sell"]:
        actions.append(f"賣 {r['name']} {coin(r['price'])}：平常約 {coin(r['usual'])}，你有 {r['count']} 個，"
                       f"部落共 {r['units']} 件在賣")
    lines += [f"{i}. {a}" for i, a in enumerate(actions, 1)] or ["現在沒有需要立刻處理的。"]
    lines += ["", "## 可以等"]
    if result["plenty"]:
        lines.append("- 到價、貨還多：" + "、".join(
            f"{r['name']} {coin(r['price'])}（{reason(r)}）" for r in result["plenty"]))
    if result["near"]:
        lines.append("- 接近觸發價：" + "、".join(
            f"{r['name']} {coin(r['price'])}（觸發 {coin(r['below'])}）" for r in result["near"]))
    if result["empty"]:
        lines.append("- 有觸發價、現在沒貨：" + "、".join(
            f"{r['name']}（{coin(r['below'])}）" for r in result["empty"]))
    if extra:
        lines.append("- 頁面外、遠低於全服行情的配方：" + "、".join(
            f"{r['name']} {coin(r['price'])}（行情約 {coin(r['reference'])}）" for r in extra))
    if not (result["plenty"] or result["near"] or result["empty"] or extra):
        lines.append("- 沒有。")
    if bags_note:
        lines += ["", bags_note]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="repo root holding the personal pages (default: cwd)")
    parser.add_argument("--pages", nargs="+", default=list(PAGES), help="page folders to read (default: endgame alchemy speculation)")
    parser.add_argument("--root", default="/Applications/World of Warcraft", help="WoW install root, for Syndicator's bags")
    parser.add_argument("--no-bags", action="store_true", help="skip the sell check")
    parser.add_argument("--max-now", type=int, default=5, help="most items under 現在處理 (default 5)")
    parser.add_argument("--top", type=int, default=5, help="recipes off the pages to list (default 5)")
    parser.add_argument("--auctions", help="auctions.json path or URL (default: the auction-data branch)")
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "wowamobi-cache")
    parser.add_argument("--max-age", type=float, default=6, help="hours wowamobi's item list stays cached")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    paths = [args.repo / p / "index.html" for p in args.pages]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        sys.exit("pages not found (run from the repo root or pass --repo): " + ", ".join(missing))
    items = page_items(paths)
    data = ac.load_record(args.auctions)
    market = ac.load_market(args.cache, args.max_age)
    meta = market["meta"]
    group = next((g for g in market["groups"] if g["realm"] == REALM), {"items": []})
    realm_rows = {row[0]: row for row in group["items"]}
    ids = ac.resolve(list(items), meta, data["items"])
    levels, modified = ac.live_levels()

    bags, bags_note = None, None
    if not args.no_bags:
        bags = read_bags(args.root)
        if bags is None:
            bags_note = "背包：這台電腦找不到 Syndicator 存檔，沒有列賣出建議。"
    result = classify(items, ids, levels, data["items"], data["hours"], realm_rows, meta, bags, args.max_now)
    page_ids = {i for v in ids.values() for i in v}
    extra = off_page(page_ids, levels, realm_rows, data["items"], data["hours"], meta, args.top)
    unknown = [n for n, v in ids.items() if not v]

    if args.json:
        json.dump({"liveModified": modified, "recordUpdatedAt": data.get("updatedAt"), **result,
                   "offPage": extra, "unknownNames": unknown, "bags": bags is not None},
                  sys.stdout, ensure_ascii=False, indent=1)
        print()
        return
    print(render(result, extra, modified, data.get("updatedAt"), bags_note))


if __name__ == "__main__":
    main()
