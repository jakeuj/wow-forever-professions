#!/usr/bin/env python3
"""Fill the data sections of leveling/index.html from a leveling_route.py --json result.

The page marks each generated region with <!-- lv:NAME --> ... <!-- /lv:NAME -->:
the budget figures of the phase cards and the plan card, the route table rows, the
material tables (with the self-crafted intermediates), and the plan table rows. A
route that starts at the gate (225) has no phase 1, so the page needs no card-1.
Text outside the markers (lead, timeline, notes) stays hand-written; review it after
a new route. Plan counts and the snapshot date come from --market.

    python3 .agents/skills/wow-forever/scripts/leveling_route.py --from 225 --to 300 \\
        --mining 250 --products disenchant --live --json > /tmp/route.json
    python3 scripts/build-leveling-page.py /tmp/route.json --owned 12684,12704

--prefix de- fills the second tab's markers (lv:de-card-2, ...) instead. --owned takes
plan item IDs already bought: plain names outside the shopping list and plan total.
--market also takes an official snapshot: {"source": "official", "updatedAt": ...,
"fields": ["id", "price", "count"], "items": [...]}.
"""

import argparse
import html
import json
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parent.parent
LISTS = {"": {1: "鍛造-到225", 2: "鍛造-225以後"}, "de-": {1: "鍛造分解-到225", 2: "鍛造分解-225以後"}}
BOUGHT = '<span class="eg-tag bop">已買到</span>'


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


def card(ph, back):
    return ("<dl class=\"lv-figures\">\n"
            f"            <div><dt>材料</dt><dd data-lv-gross>{total(ph['gross'])}</dd></div>\n"
            f"            <div><dt>{back}</dt><dd>{total(ph['vendor'])}</dd></div>\n"
            f"            <div class=\"lv-net\"><dt>淨成本估算</dt><dd data-lv-net>{total(ph['net'])}</dd></div>\n"
            "          </dl>")


def plan_card(plans, counts, owned):
    to_buy = [p for p in plans if p["plan_id"] not in owned]
    auction = [p for p in to_buy if not p["learn"].startswith("NPC ")]
    listed = [counts[p["plan_id"]] for p in auction if counts.get(p["plan_id"])]
    stock = (f"部落各只有 {min(listed)}～{max(listed)} 張在賣" if min(listed) != max(listed)
             else f"部落各只有 {listed[0]} 張在賣") if listed else "部落目前沒貨" if auction else "拍賣場的都已買到"
    price = sum(p["plan_price"] for p in to_buy)
    figure = f"還要買 {len(to_buy)} 張" if len(to_buy) < len(plans) else f"本路線 {len(plans)} 張"
    npc_price = round(sum(p["plan_price"] for p in plans if p["learn"].startswith("NPC ")))
    return (f"<h3>設計圖</h3><p>{stock}{'・另有商人圖紙' if npc_price else ''}</p>\n"
            "          <dl class=\"lv-figures\">\n"
            f'            <div><dt>{figure}</dt><dd data-lv-plan-total data-lv-plan-fixed="{npc_price}">{total(price) if price else "0"}</dd></div>\n'
            f"            <div><dt>首次用在</dt><dd>{'／'.join(str(p['from']) for p in plans)}</dd></div>\n"
            "          </dl>")


def route_rows(segments, owned, show_recover):
    rows = []
    for s in segments:
        spare = f'<small class="lv-sub">多備 {s["spare"]} 次</small>' if s["spare"] else ""
        mats = "、".join(f"{esc(n)}×{q}" for n, q in s["mats"])
        if s["plan"] and s["plan_id"] in owned:
            learn = f"{esc(s['plan'])}{BOUGHT}"
        elif s["plan"] and s["learn"].startswith("NPC "):
            learn = f"{esc(s['plan'])}<small class=\"lv-sub\">{esc(s['learn'][4:])}</small>"
        else:
            learn = ah_name(s["plan"]) if s["plan"] else esc(s["learn"])
        label = "每件回收" if show_recover else "賣店"
        back = (f'<span>{total(s["sell"])}<small class="lv-sub">{esc(s["recover"])}</small></span>' if show_recover
                else total(s["sell"]))
        rows.append(f'          <tr><th scope="row">{esc(s["recipe"])}</th><td class="eg-nowrap" data-label="技能">'
                    f'{s["from"]}→{s["to"]}</td><td data-label="次數"><span>約 {round(s["crafts"])} 次{spare}</span></td>'
                    f'<td data-label="每次材料"><span>{mats}<small class="lv-sub">約 {total(s["cost"])}</small></span></td>'
                    f'<td class="eg-price" data-label="{label}">{back}</td><td data-label="學法">{learn}</td></tr>')
    return "\n".join(rows)


def mats_table(ph, gate, end, back, prefix, only):
    label = (f"{gate}→{end}" if only else
             {1: f"階段 1・現在・{ph_from(ph)}→{gate}", 2: f"階段 2・35 級後・{gate}→{end}"}[ph["phase"]])
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
        smelts = [m for m in ph["made"] if "熔煉" in m["how"]]
        how = "，".join((["錠用上表的礦石熔煉"] if smelts else [])
                       + (["砂輪用上表的石頭照訓練師配方做"] if len(smelts) < len(ph["made"]) else []))
        made = (f'\n      <p class="lv-made"><span aria-hidden="true">⚒</span>自己做：{items}。拍賣場比較貴或不夠時，'
                f"{how}，材料已經算在上表。</p>")
    return (f'      <table class="eg-table lv-mats" data-ah-list="{LISTS[prefix][ph["phase"]]}" data-lv-phase="{prefix}{ph["phase"]}" '
            f'data-lv-vendor="{ph["vendor"]}">\n'
            f"        <caption>{label}：依小計排序，長條是佔這個階段材料費的比例</caption>\n"
            '        <thead><tr><th scope="col">材料</th><th scope="col">數量</th><th scope="col">單價</th><th scope="col">小計</th>'
            '<th scope="col">部落件數</th><th scope="col">佔比</th></tr></thead>\n'
            "        <tbody>\n" + "\n".join(rows) + "\n        </tbody>\n"
            f'        <tfoot><tr><th scope="row">合計</th><td colspan="2" data-label="說明">{back} {total(ph["vendor"])}</td>'
            f'<td class="eg-price" data-label="材料合計" data-lv-total>{total(ph["gross"])}</td>'
            f'<td colspan="2" data-label="淨成本估算" data-lv-net>{total(ph["net"])}</td></tr></tfoot>\n'
            "      </table>" + made)


def ph_from(ph):
    return ph.get("start", 200)


def plan_rows(plans, missing, counts, prices, owned):
    rows = []
    for p in plans:
        if p["learn"].startswith("NPC "):
            rows.append(f'          <tr><th scope="row">{esc(p["plan"])}</th>'
                        f'<td data-label="用在">{p["from"]}→{p["to"]}</td>'
                        f'<td class="eg-price" data-label="商人價">{unit(p["plan_price"])}</td>'
                        '<td data-label="部落件數">—</td>'
                        f'<td data-label="建議">{esc(p["learn"][4:])}</td></tr>')
            continue
        count = counts.get(p["plan_id"])
        if p["plan_id"] in owned:
            rows.append(f'          <tr data-lv-id="{p["plan_id"]}" class="is-skip"><th scope="row">{esc(p["plan"].split("：", 1)[-1])}</th>'
                        f'<td data-label="用在">{p["from"]}→{p["to"]}</td>'
                        f'<td class="eg-price" data-label="部落價" data-lv-unit>{unit(prices.get(p["plan_id"], p["plan_price"]))}</td>'
                        f'<td data-label="部落件數"><span data-lv-listed>{count if count is not None else "?"} 件</span></td>'
                        f'<td data-label="建議">{BOUGHT}</td></tr>')
            continue
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
                    '<td data-label="建議"><span class="eg-tag watch">補貨再看</span></td></tr>')
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
    parser.add_argument("--prefix", choices=sorted(LISTS), default="", help="marker prefix of the tab to fill")
    parser.add_argument("--owned", default="", help="plan item IDs already bought, comma-separated")
    args = parser.parse_args()
    owned = {int(i) for i in args.owned.split(",") if i.strip()}

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
    only = len(phases) == 1  # starts at the gate: one stage, so no stage numbers
    if 1 in phases:
        phases[1]["start"] = route["from"]
    show_recover = route.get("products") == "disenchant"
    back = "成品回收" if show_recover else "賣店收回"
    pre = args.prefix

    page = args.page.read_text(encoding="utf-8")
    for k in sorted(phases):
        page = fill(page, f"{pre}card-{k}", card(phases[k], back))
    page = fill(page, f"{pre}card-plans", plan_card(plans, counts, owned))
    page = fill(page, f"{pre}route", "\n" + route_rows(route["segments"], owned, show_recover) + "\n          ")
    page = fill(page, f"{pre}mats", "\n" + "\n".join(
        mats_table(phases[k], route["gate"], route["to"], back, pre, only) for k in sorted(phases)) + "\n      ")
    page = fill(page, f"{pre}plans", "\n" + plan_rows(plans, route["missing_plans"], counts, prices, owned) + "\n          ")
    official = market.get("source") == "official"
    timestamp = market["updatedAt"] if official else market.get("scanStartedAt") or market.get("savedAt") or ""
    stamp = timestamp[:16].replace("T", " ").replace("-", ".")
    label = "官方快照" if official else "完整掃描"
    attr = f' data-lv-snapshot="{esc(timestamp)}"' if official else ""
    page = re.sub(r'<li data-lv-date(?: data-lv-snapshot="[^"]*")?>[^<]*</li>',
                  f"<li data-lv-date{attr}>{label} {stamp}</li>", page, count=1)
    saved = (timestamp if official else market.get("savedAt", ""))[:16].replace("T", " ")
    source = "官方 API" if official else "存檔"
    page = re.sub(r'(<span class="verified-date">)[^<]*(</span>)', rf"\g<1>{source} / {saved}\g<2>", page, count=1)
    args.page.write_text(page, encoding="utf-8", newline="\n")
    print(f"updated {args.page.name}: {len(route['segments'])} route rows, "
          f"{sum(len(ph['materials']) for ph in route['phases'])} material rows, {len(plans)} plans to buy, "
          f"{len(route['missing_plans'])} to watch", file=sys.stderr)


if __name__ == "__main__":
    main()
