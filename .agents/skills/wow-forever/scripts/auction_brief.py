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

Route: when ~/.config/wow-forever/route.json exists (format: the skill's
references/route.example.json), adds a section for the leveling route in progress:
what its purchases cost now against the route's estimate, whether making an
intermediate (steel bars, grinding stones) beats buying it, how the materials you
hold are priced against their 7-day typical price, and ores listed above their bars.

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
# Who an item is for: by shopping-list prefix, else by page.
OWNERS = {"鐵匠": "自己（鍛造）", "鍛造": "自己（鍛造）", "煉金": "煉金朋友", "期貨": "期貨轉賣"}
PAGE_OWNERS = {"鍛造清單": "自己（鍛造）", "煉金清單": "煉金朋友", "配方期貨": "期貨轉賣"}
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
    """name -> {below: lowest trigger in copper or None, pages, lists, owners: who it is for, skip: all rows skipped}."""
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
    for entry in out.values():
        owners = [OWNERS.get(name.split("-")[0]) for name in entry["lists"]]
        owners = [o for o in owners if o] or [PAGE_OWNERS.get(page, page) for page in entry["pages"]]
        entry["owners"] = list(dict.fromkeys(owners))
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
            base = {"name": name, "id": item_id, "pages": info["pages"], "owners": info.get("owners", []), "price": lowest,
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


def buy_cost(levels, qty):
    """(copper, units) to buy `qty` units walking up the price levels; fewer units if the house runs out."""
    cost = got = 0
    for price, units in levels:
        take = min(units, qty - got)
        cost, got = cost + take * price, got + take
        if got >= qty:
            break
    return cost, got


def route_checks(route, lowest, levels_of, usual):
    """Rows for the leveling route section. Pure: lowest/levels_of/usual are lookups by item name."""
    rows = []
    for entry in route.get("buy", []):
        name, qty = entry["item"], entry["qty"]
        cost, got = buy_cost(levels_of(name), qty)
        vendor, planned = entry.get("vendor"), entry.get("planned")
        row = {"kind": "buy", "item": name, "qty": qty, "lowest": lowest(name), "got": got,
               "planned": planned, "vendor": vendor}
        if vendor:
            # Take the listings under the vendor price, buy the rest from the vendor.
            cheap = [(p, u) for p, u in levels_of(name) if p < vendor]
            ah_cost, ah_got = buy_cost(cheap, qty)
            row.update(source="vendor", ah_got=ah_got, ah_cost=ah_cost,
                       cost=ah_cost + (qty - ah_got) * vendor, unit=None)
        else:
            row.update(source="ah", cost=cost, unit=cost / got if got else None)
        rows.append(row)
    for entry in route.get("make", []):
        vendor = entry.get("vendor", {})
        parts, total = [], 0
        for name, count in entry["inputs"].items():
            ah = lowest(name)
            unit = vendor.get(name, ah)  # bulk inputs come from the vendor; cheap listings run out
            if unit is None:
                total = None
                break
            parts.append((name, count, unit))
            total += count * unit
        rows.append({"kind": "make", "item": entry["product"], "qty": entry.get("qty"), "buy": lowest(entry["product"]),
                     "make": total, "parts": parts})
    for entry in route.get("hold", []):
        name = entry["item"]
        now, typ = lowest(name), usual(name)
        rows.append({"kind": "hold", "item": name, "count": entry["count"], "use": entry.get("use"),
                     "now": now, "usual": typ, "ratio": now / typ if now and typ else None})
    for ore, bar in route.get("ore", []):
        ore_price, bar_price = lowest(ore), lowest(bar)
        if ore_price and bar_price and ore_price > bar_price:
            rows.append({"kind": "ore", "item": ore, "bar": bar, "ore_price": ore_price, "bar_price": bar_price})
    return rows


def route_lines(rows):
    out = []
    for r in rows:
        if r["kind"] == "buy":
            saving = r["ah_got"] * (r["vendor"] or 0) - r["ah_cost"] if r["source"] == "vendor" else 0
            if r["source"] == "vendor" and r["ah_got"] and saving >= 10000:
                rest = r["qty"] - r["ah_got"]
                line = (f"{r['item']} {r['qty']} 個：拍賣場比商人便宜的 {r['ah_got']} 個先買（{coin(r['lowest'])} 起）"
                        + (f"，其餘 {rest} 個向商人買 {coin(r['vendor'])}" if rest else "") + f"，共 {coin(r['cost'])}")
            elif r["source"] == "vendor":
                if r["ah_got"]:
                    ah = f"拍賣場有 {r['ah_got']} 個便宜一點，全買也只省 {coin(saving)}"
                    r = {**r, "cost": r["qty"] * r["vendor"]}
                else:
                    ah = f"拍賣場 {coin(r['lowest'])} 比較貴" if r["lowest"] else "拍賣場沒貨"
                line = f"{r['item']} {r['qty']} 個：向商人買 {coin(r['vendor'])}，共 {coin(r['cost'])}（{ah}）"
            elif not r["got"]:
                line = f"{r['item']} {r['qty']} 個：部落拍賣場沒貨"
            else:
                line = f"{r['item']} {r['qty']} 個：拍賣場 {coin(r['lowest'])} 起，買足共 {coin(r['cost'])}"
                if r["got"] < r["qty"]:
                    line += f"（部落只有 {r['got']} 個）"
                if r["planned"]:
                    ratio = r["unit"] / r["planned"]
                    verdict = "照買" if ratio <= 1.2 else f"比路線估價貴 {ratio - 1:.0%}"
                    line += f"；路線估 {coin(r['planned'])}／個，{verdict}"
            out.append(line + "。")
        elif r["kind"] == "make":
            if r["make"] is None:
                out.append(f"{r['item']}：材料缺價格，算不出自己做的成本。")
                continue
            how = "＋".join(f"{name}{'×' + str(n) if n != 1 else ''} {coin(u)}" for name, n, u in r["parts"])
            if r["buy"] is None:
                out.append(f"{r['item']}：拍賣場沒貨，自己做約 {coin(r['make'])}（{how}）。")
            elif r["make"] < r["buy"]:
                out.append(f"{r['item']}：拍賣場 {coin(r['buy'])}，自己做約 {coin(r['make'])}（{how}），自己做每個省 {coin(r['buy'] - r['make'])}。")
            else:
                out.append(f"{r['item']}：拍賣場 {coin(r['buy'])}，自己做約 {coin(r['make'])}（{how}），直接買比較省。")
        elif r["kind"] == "hold":
            have = f"{r['item']} 你有 {r['count']} 個" + (f"（路線用 {r['use']}）" if r.get("use") else "")
            if r["ratio"] is None:
                out.append(f"{have}：部落現在沒貨或沒有 7 天紀錄。")
                continue
            spare = r["count"] - (r.get("use") or 0)
            if r["ratio"] <= 0.85:
                advice = f"比 7 天常見價 {coin(r['usual'])} 低 {1 - r['ratio']:.0%}，先別賣；之後要用可以趁低補"
            elif r["ratio"] >= 1.3:
                advice = f"比 7 天常見價 {coin(r['usual'])} 高 {r['ratio'] - 1:.0%}" + (f"，用不到的 {spare} 個可以趁高賣" if spare > 0 else "")
            else:
                advice = f"和 7 天常見價 {coin(r['usual'])} 差不多"
            out.append(f"{have}：現在 {coin(r['now'])}，{advice}。")
        elif r["kind"] == "ore":
            out.append(f"{r['item']} {coin(r['ore_price'])} 比{r['bar']} {coin(r['bar_price'])} 還貴：挖到的礦直接賣，要用錠就直接買錠。")
    return out


def load_route(path):
    try:
        return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


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


def render(result, extra, modified, record_time, bags_note, route=None, route_rows=()):
    lines = [f"部落拍賣場快訊（官方即時快照 {taiwan_time(modified)}；網站每小時紀錄到 {record_time}）", "", "## 現在處理"]
    actions = []
    for r in result["now"]:
        where = "、".join(r["owners"] or r["pages"])
        actions.append(f"買 {r['name']} {coin(r['price'])}：{reason(r)}（{where}）")
    for r in result["sell"]:
        actions.append(f"賣 {r['name']} {coin(r['price'])}：平常約 {coin(r['usual'])}，你有 {r['count']} 個，"
                       f"部落共 {r['units']} 件在賣")
    lines += [f"{i}. {a}" for i, a in enumerate(actions, 1)] or ["現在沒有需要立刻處理的。"]
    if route:
        title = route.get("name", "練等路線")
        lines += ["", f"## 你的{title}"]
        if route.get("updated"):
            lines.append(f"（持有數量依 {route['updated']} 的紀錄）")
        lines += [f"- {line}" for line in route_lines(route_rows)]
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
    parser.add_argument("--route", default="~/.config/wow-forever/route.json",
                        help="leveling route in progress (default ~/.config/wow-forever/route.json; skipped if missing)")
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

    route, route_rows = load_route(args.route), []
    if route:
        names = {e["item"] for k in ("buy", "hold") for e in route.get(k, [])}
        names |= {e["product"] for e in route.get("make", [])} | {n for e in route.get("make", []) for n in e["inputs"]}
        names |= {n for pair in route.get("ore", []) for n in pair}
        route_ids = ac.resolve(sorted(names), meta, data["items"])
        first = lambda name: (route_ids.get(name) or [None])[0]
        levels_of = lambda name: levels.get(first(name)) or []
        lowest = lambda name: (levels_of(name)[0][0] if levels_of(name) else None)
        usual = lambda name: (typical(data["items"][str(first(name))][1], data["hours"], data["hours"][-1])
                              if str(first(name)) in data["items"] else None)
        route_rows = route_checks(route, lowest, levels_of, usual)

    if args.json:
        json.dump({"liveModified": modified, "recordUpdatedAt": data.get("updatedAt"), **result,
                   "offPage": extra, "unknownNames": unknown, "bags": bags is not None, "route": route_rows},
                  sys.stdout, ensure_ascii=False, indent=1)
        print()
        return
    print(render(result, extra, modified, data.get("updatedAt"), bags_note, route, route_rows))


if __name__ == "__main__":
    main()
