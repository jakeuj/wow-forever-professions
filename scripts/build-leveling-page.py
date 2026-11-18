#!/usr/bin/env python3
"""Fill the data sections of leveling/index.html from a leveling_route.py --json result.

The page marks each generated region with <!-- lv:NAME --> ... <!-- /lv:NAME -->:
the budget figures of the two phase cards and the plan card, the route table rows,
the two material tables (with the self-crafted intermediates), and the plan table
rows. Text outside the markers (lead, timeline, notes) stays hand-written; review it
after a new route. Plan counts and the snapshot date come from market/data.json.

    python3 .agents/skills/wow-forever/scripts/leveling_route.py --from 200 \\
        --market-json market/data.json --json > /tmp/route.json
    python3 scripts/build-leveling-page.py /tmp/route.json
"""

import argparse
import html
import json
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parent.parent
LISTS = {1: "鍛造-到225", 2: "鍛造-225以後"}


def unit(c):
    """Same formats as leveling/leveling.js: per-unit prices."""
    if c >= 10000:
        return f"{c / 10000:.2f}g"
    return f"{c / 100:.1f}".removesuffix(".0") + " 銀"


def total(c):
    return f"{c / 10000:.1f}g" if c >= 10000 else unit(c)


def esc(text):
    return html.escape(str(text), quote=True)


def ah_name(name):
    return f'<span data-ah="{esc(name)}">{esc(name)}</span>'


def card(ph):
    return ("<dl class=\"lv-figures\">\n"
            f"            <div><dt>材料</dt><dd data-lv-gross>{total(ph['gross'])}</dd></div>\n"
            f"            <div><dt>賣店收回</dt><dd>{total(ph['vendor'])}</dd></div>\n"
            f"            <div class=\"lv-net\"><dt>實際花費</dt><dd data-lv-net>{total(ph['net'])}</dd></div>\n"
            "          </dl>")


def plan_card(plans, counts):
    listed = [counts.get(p["plan_id"]) for p in plans if counts.get(p["plan_id"]) is not None]
    stock = (f"部落各只有 {min(listed)}～{max(listed)} 張在賣" if min(listed) != max(listed)
             else f"部落各只有 {listed[0]} 張在賣") if listed else "部落目前沒貨"
    price = sum(p["plan_price"] for p in plans)
    return (f"<h3>設計圖</h3><p>{stock}</p>\n"
            "          <dl class=\"lv-figures\">\n"
            f"            <div><dt>現在買的 {len(plans)} 張</dt><dd data-lv-plan-total>{total(price)}</dd></div>\n"
            f"            <div><dt>學到才用</dt><dd>{'／'.join(str(p['from']) for p in plans)}</dd></div>\n"
            "          </dl>")


def route_rows(segments):
    rows = []
    for s in segments:
        spare = f'<small class="lv-sub">多備 {s["spare"]} 次</small>' if s["spare"] else ""
        mats = "、".join(f"{esc(n)}×{q}" for n, q in s["mats"])
        learn = ah_name(s["plan"]) if s["plan"] else esc(s["learn"])
        rows.append(f'          <tr><th scope="row">{esc(s["recipe"])}</th><td class="eg-nowrap" data-label="技能">'
                    f'{s["from"]}→{s["to"]}</td><td data-label="次數"><span>約 {round(s["crafts"])} 次{spare}</span></td>'
                    f'<td data-label="每次材料"><span>{mats}<small class="lv-sub">約 {total(s["cost"])}</small></span></td>'
                    f'<td class="eg-price" data-label="賣店">{total(s["sell"])}</td><td data-label="學法">{learn}</td></tr>')
    return "\n".join(rows)


def mats_table(ph, gate, end):
    label = {1: f"階段 1・現在・{ph_from(ph)}→{gate}", 2: f"階段 2・35 級後・{gate}→{end}"}[ph["phase"]]
    rows = []
    for m in ph["materials"]:
        share = m["subtotal"] / ph["gross"] * 100 if ph["gross"] else 0
        fixed = f' data-lv-fixed="{m["other_cost"]}" data-lv-other="{m["other_qty"]}"' if m["other_qty"] else ""
        listed = f'{m["listed"]:,}' if m["listed"] is not None else "—"
        short = '<span class="eg-tag skip">不夠</span>' if m["short"] else ""
        rows.append(f'          <tr data-lv-id="{m["id"]}" data-lv-qty="{m["ah_qty"]}" data-lv-price="{m["ah_unit"] or m["unit"]}"{fixed}>'
                    f'<th scope="row">{ah_name(m["name"])}</th><td data-label="數量">{m["qty"]:,}</td>'
                    f'<td class="eg-price" data-label="單價" data-lv-unit>{unit(m["unit"])}</td>'
                    f'<td class="eg-price" data-label="小計" data-lv-sub>{total(m["subtotal"])}</td>'
                    f'<td data-label="部落件數"><span><span data-lv-listed>{listed}</span><span data-lv-short>{short}</span></span></td>'
                    f'<td class="lv-share-cell" data-label="佔比"><span class="lv-share" style="--share: {share:.1f}%">'
                    f'<span data-lv-pct>{round(share)}%</span></span></td></tr>')
    made = ""
    if ph["made"]:
        items = "、".join(f'{esc(m["name"])} ×{m["qty"]}' for m in ph["made"])
        made = (f'\n      <p class="lv-made"><span aria-hidden="true">⚒</span>自己做：{items}。拍賣場比較貴或不夠時，'
                "用上表的石頭照訓練師配方做，材料已經算在上表。</p>")
    return (f'      <table class="eg-table lv-mats" data-ah-list="{LISTS[ph["phase"]]}" data-lv-phase="{ph["phase"]}" '
            f'data-lv-vendor="{ph["vendor"]}">\n'
            f"        <caption>{label}：依小計排序，長條是佔這個階段材料費的比例</caption>\n"
            '        <thead><tr><th scope="col">材料</th><th scope="col">數量</th><th scope="col">單價</th><th scope="col">小計</th>'
            '<th scope="col">部落件數</th><th scope="col">佔比</th></tr></thead>\n'
            "        <tbody>\n" + "\n".join(rows) + "\n        </tbody>\n"
            f'        <tfoot><tr><th scope="row">合計</th><td colspan="2" data-label="說明">賣店收回 {total(ph["vendor"])}</td>'
            f'<td class="eg-price" data-label="材料合計" data-lv-total>{total(ph["gross"])}</td>'
            f'<td colspan="2" data-label="實際花費" data-lv-net>{total(ph["net"])}</td></tr></tfoot>\n'
            "      </table>" + made)


def ph_from(ph):
    return ph.get("start", 200)


def plan_rows(plans, missing, counts, prices):
    rows = []
    for p in plans:
        count = counts.get(p["plan_id"])
        rows.append(f'          <tr data-lv-id="{p["plan_id"]}" data-lv-buy><th scope="row">{plan_label(p["plan"])}</th>'
                    f'<td data-label="用在">{p["from"]}→{p["to"]}</td>'
                    f'<td class="eg-price" data-label="部落價" data-lv-unit>{unit(prices.get(p["plan_id"], p["plan_price"]))}</td>'
                    f'<td data-label="部落件數"><span data-lv-listed>{count if count is not None else "?"} 件</span></td>'
                    '<td data-label="建議"><span class="eg-tag buy">現在買</span></td></tr>')
    for m in missing:
        rows.append(f'          <tr data-lv-id="{m["plan_id"]}"><th scope="row">{plan_label(m["plan"])}</th>'
                    f'<td data-label="用在">{m["from"]}→{m["to"]} 更省：每次淨 {total(m["net"])}</td>'
                    '<td class="eg-price" data-label="部落價" data-lv-unit>部落沒貨</td>'
                    '<td data-label="部落件數"><span data-lv-listed>—</span></td>'
                    '<td data-label="建議"><span class="eg-tag watch">看到就買</span></td></tr>')
    return "\n".join(rows)


def plan_label(name):
    short = name.split("：", 1)[-1]
    return f'<span data-ah="{esc(name)}">{esc(short)}</span>'


def fill(page, name, content):
    pattern = re.compile(rf"(<!-- lv:{name} -->)(.*?)(<!-- /lv:{name} -->)", re.S)
    if not pattern.search(page):
        sys.exit(f"marker lv:{name} not found in the page")
    return pattern.sub(lambda m: f"{m.group(1)}{content}{m.group(3)}", page, count=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("route", type=Path, help="output of leveling_route.py --json")
    parser.add_argument("--page", type=Path, default=REPO / "leveling/index.html")
    parser.add_argument("--market", type=Path, default=REPO / "market/data.json")
    args = parser.parse_args()

    route = json.loads(args.route.read_text(encoding="utf-8"))
    market = json.loads(args.market.read_text(encoding="utf-8"))
    col = {k: market["fields"].index(k) for k in ("id", "price", "count")}
    counts = {r[col["id"]]: r[col["count"]] for r in market["items"]}
    prices = {r[col["id"]]: r[col["price"]] for r in market["items"] if r[col["price"]]}

    seen, plans = set(), []
    for s in route["segments"]:
        if s["plan"] and s["plan_id"] not in seen:
            seen.add(s["plan_id"])
            plans.append(s)
    phases = {ph["phase"]: ph for ph in route["phases"]}
    phases[1]["start"] = route["from"]

    page = args.page.read_text(encoding="utf-8")
    page = fill(page, "card-1", card(phases[1]))
    page = fill(page, "card-2", card(phases[2]))
    page = fill(page, "card-plans", plan_card(plans, counts))
    page = fill(page, "route", "\n" + route_rows(route["segments"]) + "\n          ")
    page = fill(page, "mats", "\n" + "\n".join(mats_table(phases[k], route["gate"], route["to"]) for k in sorted(phases)) + "\n      ")
    page = fill(page, "plans", "\n" + plan_rows(plans, route["missing_plans"], counts, prices) + "\n          ")
    stamp = (market.get("scanStartedAt") or market.get("savedAt") or "")[:16].replace("T", " ").replace("-", ".")
    page = re.sub(r"(<li data-lv-date>)[^<]*(</li>)", rf"\g<1>完整掃描 {stamp}\g<2>", page, count=1)
    saved = (market.get("savedAt") or "")[:16].replace("T", " ")
    page = re.sub(r'(<span class="verified-date">)[^<]*(</span>)', rf"\g<1>存檔 / {saved}\g<2>", page, count=1)
    args.page.write_text(page, encoding="utf-8")
    print(f"updated {args.page.relative_to(REPO)}: {len(route['segments'])} route rows, "
          f"{sum(len(ph['materials']) for ph in route['phases'])} material rows, {len(plans)} plans to buy, "
          f"{len(route['missing_plans'])} to watch", file=sys.stderr)


if __name__ == "__main__":
    main()
