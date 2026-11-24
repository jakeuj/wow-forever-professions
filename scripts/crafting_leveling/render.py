"""Render the static leveling guide from compiled routes and quotes."""

from html import escape
from string import Template

from .routes import MILESTONES
from .sources import PROFESSIONS, REPO


TEMPLATE = REPO / "scripts/crafting-leveling.html"


def gold(copper):
    return f"{copper / 10000:,.2f} 金"


def item_link(item, name):
    return f'<a href="https://www.wowhead.com/forever/tw/item={item}">{escape(name(item))}</a>'


def price_label(quote):
    amount = gold(quote.total)
    flags = []
    if quote.missing:
        flags.append("待確認" if any(p.unknown for p in quote.missing) else "缺貨")
    if quote.missing_fees:
        flags.append("學費另計")
    lead = "已知 " if quote.missing else "約 "
    notes = f'<small>{" · ".join(flags)}</small>' if flags else ""
    return f'<span class="cl-price">{lead}{amount}{notes}</span>'


def html_table(headers, rows, *, css="", caption=""):
    head = "".join(f'<th scope="col">{escape(label)}</th>' for label in headers)
    body = []
    for title, cells in rows:
        values = "".join(f'<td data-label="{escape(label)}">{value}</td>'
                         for label, value in zip(headers[1:], cells, strict=True))
        body.append(f'<tr><th scope="row">{title}</th>{values}</tr>')
    cap = f"<caption>{escape(caption)}</caption>" if caption else ""
    return f'<table class="eg-table {css}">{cap}<thead><tr>{head}</tr></thead><tbody>\n' + "\n".join(body) + "\n</tbody></table>"


def priority_list(results, name):
    cards = []
    headings = ("起手到 150", "已到 150 → 225", "已到 225 → 300")
    for i, goal in enumerate(MILESTONES):
        entries = [(slug, detail[1][i], detail[2][i]) for slug, detail in results.items()]
        entries.sort(key=lambda e: (bool(e[2].missing), e[2].total))
        best = next(((slug, quote.total) for slug, phase, quote in entries
                     if not quote.missing and not phase.requirements), None)
        lines = []
        for slug, phase, quote in entries:
            tag = ""
            notes = []
            if quote.missing:
                tag = ' <span class="eg-tag skip">等補貨</span>'
                if any(p.unknown for p in quote.missing):
                    tag = ' <span class="eg-tag watch">待確認</span>'
                notes.extend(f"{name(p.item)}缺 {p.missing:,} 件" if not p.unknown else f"{name(p.item)}缺價"
                             for p in sorted(quote.missing, key=lambda p: -p.missing)[:2])
            elif best and slug == best[0]:
                tag = ' <span class="eg-tag buy">優先</span>'
            elif i and best and quote.total >= 2 * best[1]:
                tag = ' <span class="eg-tag watch">可等降價</span>'
            notes.extend(sorted(phase.requirements))
            if not quote.missing and quote.materials:
                material = max(quote.materials, key=lambda p: p.spent)
                notes.append(f"主要材料 {name(material.item)} ×{material.quantity:,}")
            note = f'<p class="cl-note">{escape(" · ".join(notes))}</p>' if notes else ""
            lines.append(
                f'<li><div class="cl-priority-row"><div class="cl-priority-name"><a href="#{slug}-{goal}">'
                f'{PROFESSIONS[slug]}</a>{tag}</div>{price_label(quote)}</div>{note}</li>'
            )
        cards.append(f'<article><h3>{headings[i]}</h3><ol>{"".join(lines)}</ol></article>')
    return "\n".join(cards)


RANKS = {
    1: "角色 5 級學初級。角色 10 級且技能 50 後可學中級，將上限提到 150。",
    150: "角色 20 級且技能 125 後可學進階，將上限提到 225。",
    225: "角色 35 級且技能 200 後可學工匠級，將上限提到 300。",
}


def stage_panel(slug, phase, quote, name):
    demands = {p.item: p for p in quote.formulas}
    step_rows = []
    for start, end, recipe, count in phase.steps:
        span = f"{start}→{end}" if start != end else f"{start}（補做）"
        if recipe.formula:
            plan = demands.get(recipe.formula)
            source = ("商人 " + plan.vendor if plan.npc else "拍賣場") if plan else "前段已學"
            acquisition = f"{item_link(recipe.formula, name)} · {escape(source)}"
        elif recipe.fee == 0:
            acquisition = "初始習得"
        else:
            acquisition = "訓練師"
        if recipe.requirement:
            acquisition += f'<small class="cl-wait"> · {escape(recipe.requirement)}</small>'
        if recipe.tools:
            acquisition += f'<br><small class="cl-note">工具 {escape("、".join(name(i) for i in recipe.tools))}</small>'
        materials = "、".join(f"{name(i)} ×{quantity}" for i, quantity in recipe.reagents)
        step_rows.append((escape(recipe.name), (span, f"{count:,} 次", escape(materials or "—"), acquisition)))

    shopping_rows = []
    purchases = [(p, False) for p in quote.materials] + [(p, True) for p in quote.formulas]
    purchases.sort(key=lambda p: (not p[1], -p[0].spent, p[0].item))
    for purchase, formula in purchases:
        source = []
        if purchase.auction:
            source.append(f"拍賣 {purchase.auction:,} 件")
        if purchase.npc:
            source.append(f"{purchase.vendor} {purchase.npc:,} 件")
        if purchase.missing:
            source.append(("缺價" if purchase.unknown else "缺貨") + f" {purchase.missing:,} 件")
        title = item_link(purchase.item, name) + ("<small> · 圖紙</small>" if formula else "")
        subtotal = gold(purchase.spent) if purchase.spent else "—"
        shopping_rows.append((title, (f"{purchase.quantity:,} 件", escape(" · ".join(source)), subtotal)))

    material_auction = sum(p.spent - p.npc_spent for p in quote.materials)
    material_npc = sum(p.npc_spent for p in quote.materials)
    formula_cost = sum(p.spent for p in quote.formulas)
    breakdown = (
        ("拍賣材料", gold(material_auction)), ("NPC 材料", gold(material_npc)),
        ("必要圖紙", gold(formula_cost)), ("已計學費", gold(quote.training)),
        ("成品售店估計", gold(phase.recovery)),
    )
    figures = "".join(f"<div><dt>{label}</dt><dd>{amount}</dd></div>" for label, amount in breakdown)
    notes = [RANKS[phase.start]]
    if carried := +phase.carried:
        notes.append("接續使用 " + "、".join(f"{name(i)} ×{n:,}" for i, n in carried.items()) + "。")
    if quote.estimated_training:
        notes.append("已計學費含來源站的訓練師估價。")
    if quote.missing_fees:
        notes.append("學費另計 " + "、".join(sorted(quote.missing_fees)) + "。")
    if phase.requirements:
        notes.append("、".join(sorted(phase.requirements)) + "。")
    note_html = "".join(f'<p class="cl-note">{escape(note)}</p>' for note in notes)
    steps = html_table(("配方", "技能", "預估製作", "每次材料", "學習與工具"), step_rows, caption="依序製作")
    shopping = html_table(("物品", "需要", "採買來源", "已知小計"), shopping_rows, caption="這一段要另外買的材料與圖紙")
    return (
        f'<details class="cl-stage" id="{slug}-{phase.end}" name="{slug}-stage">'
        f'<summary><strong>{phase.start}→{phase.end}</strong> {price_label(quote)}</summary>'
        f'<div class="cl-stage-body">{note_html}<dl class="cl-breakdown">{figures}</dl>\n'
        f'{steps}\n<h4>採買清單</h4>{shopping}\n</div></details>'
    )


def render(stamp, name, results, first_round, *, official=False):
    summary_rows, profession_panels, jump_links = [], [], []
    for slug, (label, phases, stages, cumulative) in results.items():
        title = PROFESSIONS[slug]
        jump = f'<a href="#{slug}">{title}</a>'
        jump_links.append(jump)
        summary_rows.append((jump, tuple(price_label(q) for q in cumulative)))
        reference = f"https://wowf.io/tw/professions/{slug}"
        links = [
            f'<a class="text-link" href="{reference}/leveling">WOWF.IO 升級參考 ↗</a>',
            f'<a class="text-link" href="{reference}/ranks">訓練師與升階 ↗</a>',
        ]
        if slug == "blacksmithing":
            links.append('<a class="text-link" href="../leveling/">既有鍛造 225→300</a>')
        if slug == "alchemy":
            links.append('<a class="text-link" href="../alchemy-leveling/">既有鍊金路線</a>')
        route_note = f'本次採用 {escape(label)}。'
        if slug == "alchemy":
            route_note += ' 想供應軍團鋼可在鍊金 275 另學轉化，需點金石。'
        panels = "\n".join(stage_panel(slug, p, q, name) for p, q in zip(phases, stages))
        profession_panels.append(
            f'<section class="cl-profession" id="{slug}" aria-labelledby="{slug}-title">'
            f'<h3 id="{slug}-title">{title}</h3><p class="cl-note">{route_note}</p>'
            f'<p class="cl-links">{"".join(links)}</p>\n{panels}\n</section>'
        )
    first_price = ("已知 " if first_round.missing else "約 ") + gold(first_round.total)
    first_note = "同批採買，合併六項共用材料。"
    if first_round.missing:
        shortage = "、".join(f"{name(p.item)} {p.missing:,} 件" for p in first_round.missing)
        first_note = f"合併採買仍有缺口 {shortage}。"
    if first_round.missing_fees:
        first_note += "另有未確認學費。"
    return Template(TEMPLATE.read_text(encoding="utf-8")).substitute(
        scan_iso=stamp.isoformat(), scan_label=stamp.strftime("%Y-%m-%d %H:%M"),
        source_label="官方快照" if official else "掃描",
        source_name="Blizzard 官方拍賣 API" if official else "拍賣小幫手",
        source_url="https://community.developer.battle.net/" if official else "https://www.curseforge.com/wow/addons/auctionator",
        first_price=escape(first_price), first_note=escape(first_note), jump_links="".join(jump_links),
        budget=html_table(("專業", "到 150 · 1 點", "到 225 · 2 點", "到 300 · 3 點"), summary_rows, css="cl-budget"),
        priority=priority_list(results, name), routes="\n".join(profession_panels),
    )
