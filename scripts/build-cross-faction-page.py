#!/usr/bin/env python3
"""Fill cross-faction/index.html from a faction_spread.py --json result.

The page marks each generated region with <!-- cf:NAME --> ... <!-- /cf:NAME -->:
the data chips, the table caption and rows, the list of older Alliance prices and
the scope note; the verified date follows the Horde snapshot. Text outside the
markers stays hand-written.

    python3 .agents/skills/wow-forever/scripts/faction_spread.py --json > /tmp/spread.json
    python3 scripts/build-cross-faction-page.py /tmp/spread.json
"""

import argparse
import datetime
import email.utils
import html
import json
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parent.parent
TAIPEI = datetime.timezone(datetime.timedelta(hours=8))
AMOBI = "https://wowamobi.com/items/"
G = 10000


def esc(text):
    return html.escape(str(text), quote=True)


def gold(copper):
    value = copper / G
    return f"{value:,.0f}g" if abs(value) >= 100 else f"{value:.2f}g"


def horde_time(http_date):
    """Last-Modified of the official snapshot in Taiwan time, e.g. 2026-11-23 17:26."""
    return email.utils.parsedate_to_datetime(http_date).astimezone(TAIPEI).strftime("%Y-%m-%d %H:%M")


def cell(label, content, cls=""):
    # One child span: on phones the cell is a two-column grid (label, value), so sub-lines must stay inside it.
    attr = f' class="{cls}"' if cls else ""
    return f'<td{attr} data-label="{label}"><span>{content}</span></td>'


def row_html(rank, r):
    loss = r["resale"] <= 0
    name = esc(r["name"])
    link = (f'<a href="{AMOBI}{r["id"]}" target="_blank" rel="noopener noreferrer" '
            f'aria-label="在阿莫比看{name}的各陣營價格（另開分頁）">{gold(r["alliance"])}<span aria-hidden="true"> ↗</span></a>')
    if not r["neutral"]:
        neutral = "沒有掛單"
    elif r["neutral_fresh"]:
        neutral = f'{gold(r["neutral"])}<small>{esc(r["neutral_seen"])} 看到</small>'
    else:
        neutral = f'{gold(r["neutral"])}<small>{esc(r["neutral_seen"])} 看到，可能已賣掉</small>'

    if loss:
        why = "中立已有更便宜的" if r["neutral_cheaper"] else "扣掉抽成不划算"
        resale = cell("轉賣淨利", f'虧 {gold(-r["resale"])}<small>{why}</small>', "cf-none")
    else:
        resale = cell("轉賣淨利", f'+{gold(r["resale"])}', "cf-gain")
    cls = ' class="cf-loss"' if loss else ""
    return (f'<tr{cls}>'
            f'<th scope="row"><span class="cf-rank">{rank}</span><span data-ah="{name}">{name}</span></th>'
            + cell("類型", esc(r["type"] or "—"))
            + cell("部落最低", f'{gold(r["h_min"])}<small>{r["h_min_qty"]}／{r["h_total"]} 件</small>', "eg-price")
            + cell("聯盟最低", link)
            + cell("價差", f'{gold(r["spread"])}<small>×{r["ratio"]}</small>', "cf-spread")
            + cell("中立最低", neutral)
            + resale + '</tr>')


def stale_html(r):
    return (f'<li><strong><span data-ah="{esc(r["name"])}">{esc(r["name"])}</span></strong> '
            f'部落 {gold(r["h_min"])}，聯盟 <a href="{AMOBI}{r["id"]}" target="_blank" rel="noopener noreferrer">'
            f'{gold(r["alliance"])}<span aria-hidden="true"> ↗</span></a>（{esc(r["alliance_seen"])} 看到）</li>')


def fill(page, name, content):
    pattern = re.compile(rf"(<!-- cf:{name} -->)(.*?)(<!-- /cf:{name} -->)", re.S)
    if not pattern.search(page):
        sys.exit(f"marker cf:{name} not found in the page")
    return pattern.sub(lambda m: f"{m.group(1)}{content}{m.group(3)}", page, count=1)


def build(page, data, min_spread, stale_count):
    horde = horde_time(data["hordeModified"])
    scan = data["allianceScan"] or "—"
    floor = min_spread * G
    rows = [r for r in data["rows"] if r["fresh"] and r["spread"] >= floor]
    stale = [r for r in data["rows"] if not r["fresh"] and r["spread"] >= floor][:stale_count]
    gain = sum(r["resale"] > 0 for r in rows)
    cut = round(data["cut"] * 100)

    chips = (f"<li>部落・亞服 PvP（台灣）</li><li>部落價：官方 API {horde[5:].replace('-', '/')}</li>"
             f"<li>聯盟價：阿莫比 {esc(scan)}</li><li>{len(rows)} 項價差 {min_spread:g}g 以上・{gain} 項轉賣有賺</li>")
    caption = (f"部落 {horde} 官方快照的最低一口價；聯盟與中立是阿莫比記到的掛單（聯盟 {esc(scan)} 掃描）。"
               f"轉賣淨利照中立抽成 {cut}% 估算。")
    note = (f"部落現價與件數來自 {horde} Blizzard 官方拍賣 API 的亞服 PvP 部落快照（單件掛單與可堆疊商品）。"
            f"聯盟與中立拍賣場的價格是阿莫比記到的最低一口價，聯盟以 {esc(scan)} 那次掃描為準，比較舊的另外列出；"
            f"中立以 {esc(data.get('neutralScan') or '—')} 那次掃描為準，比較舊的中立價只顯示、不拿來算轉賣淨利。"
            f"這次比對 {data['compared']} 項：先挑出阿莫比全服中位數明顯高於部落價的物品，再加上部落 5g 以上的掛單，"
            f"部落 5g 以下、而且掛單多半在部落的便宜物品可能漏列。中立抽成照經典版 {cut}% 估算，沒算押金，永恆以遊戲內為準。")

    page = fill(page, "chips", chips)
    page = fill(page, "caption", caption)
    page = fill(page, "rows", "\n" + "\n".join(row_html(i, r) for i, r in enumerate(rows, 1)) + "\n        ")
    stale_items = "\n".join(stale_html(r) for r in stale) if stale else "<li>這次沒有。</li>"
    page = fill(page, "stale", "\n" + stale_items + "\n          ")
    page = fill(page, "note", note)
    page = re.sub(r'(<span class="verified-date">)[^<]*(</span>)', rf"\g<1>官方 API / {horde.replace('-', '.')}\g<2>", page, count=1)
    return page, len(rows), gain, len(stale)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("spread", type=Path, help="output of faction_spread.py --json")
    parser.add_argument("--page", type=Path, default=REPO / "cross-faction/index.html")
    parser.add_argument("--min-spread", type=float, default=1, help="gold; smaller spreads are left out")
    parser.add_argument("--stale", type=int, default=12, help="older Alliance prices to list below the table")
    args = parser.parse_args()

    data = json.loads(args.spread.read_text(encoding="utf-8"))
    page, rows, gain, stale = build(args.page.read_text(encoding="utf-8"), data, args.min_spread, args.stale)
    args.page.write_text(page, encoding="utf-8")
    print(f"updated {args.page}: {rows} rows ({gain} profitable through the neutral house), {stale} older Alliance prices",
          file=sys.stderr)


if __name__ == "__main__":
    main()
