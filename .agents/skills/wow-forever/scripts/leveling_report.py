"""Output for leveling_route.py: a walked route as segments and phases, what the bags cover,
the route.json for auction_brief.py, and the printed plan."""

import datetime
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from leveling_pricing import SMELTS, smelt_producers  # noqa: E402

P90 = 1.2816  # z for the 90th percentile of the craft count
PROFESSION_ZH = {"alchemy": "煉金", "blacksmithing": "鍛造", "enchanting": "附魔", "engineering": "工程學",
                 "leatherworking": "製皮", "tailoring": "裁縫", "cooking": "烹飪", "first-aid": "急救"}


def summarize(steps, gate, recipes, producers, scan):
    """(segments, phases) of a walked route.

    A segment is a run of skill points on one recipe within a phase (phase 1 below gate,
    2 from it), with crafts, a spare-craft count (90th percentile minus expected crafts),
    cost and product value per craft, and how the recipe is learned. A phase lists its
    materials (rounded shopping list, cheapest source labels, listed count, shortfall),
    the intermediates it crafts with their inputs per unit, gross, vendor (product value)
    and net. producers are the Pricer's, scan its {item id: (price, listed count)}."""
    segments, phases = [], {}
    for st in steps:
        r, s, p = st["recipe"], st["skill"], st["chance"]
        phase = 1 if s < gate else 2
        if not (segments and segments[-1]["recipe"] == r["name"] and segments[-1]["phase"] == phase):
            segments.append({"recipe": r["name"], "from": s, "to": s, "phase": phase, "crafts": 0, "var": 0,
                             "spend": 0, "r": r})
        seg = segments[-1]
        seg["to"] = s + 1
        seg["crafts"] += 1 / p
        seg["var"] += (1 - p) / p ** 2
        seg["spend"] += sum(take * unit for _, _, _, take, unit, _ in st["parts"])
        ph = phases.setdefault(phase, {"phase": phase, "gross": 0, "vendor": 0, "need": {}, "made": {}})
        ph["vendor"] += r["sell"] / p
        for item_id, label, kind, take, unit, short in st["parts"]:
            if kind == "made":  # an intermediate crafted from the leaf purchases listed alongside
                made = ph["made"].setdefault(item_id, {"id": item_id, "qty": 0, "how": label})
                made["qty"] += take
                continue
            m = ph["need"].setdefault(item_id, {"id": item_id, "name": None, "ah_qty": 0, "ah_unit": None,
                                                "other_qty": 0, "other_cost": 0, "from": [], "short": 0})
            if kind == "ah":
                m["ah_qty"] += take
                m["ah_unit"] = unit
                m["short"] += short
            else:
                m["other_qty"] += take
                m["other_cost"] += take * unit
            if label not in m["from"]:
                m["from"].append(label)

    names = {item_id: name for r in recipes + smelt_producers(999) for item_id, name, _ in r["mats"]}
    names.update({s["item_id"]: s["name"].replace("熔煉", "") + "錠" for s in SMELTS})
    for seg in segments:
        r = seg.pop("r")
        seg["spare"] = math.ceil(P90 * math.sqrt(seg.pop("var")))
        seg.update(crafts=round(seg["crafts"], 1), cost=round(seg.pop("spend") / seg["crafts"]), sell=r["sell"],
                   recover=r["recover"], fee=r["acquire"] if r["learn"] == "trainer" else 0,
                   mats=[[n, q] for _, n, q in r["mats"]], item_id=r["item_id"], learn=r["acquire_from"],
                   plan=r["recipe"] if r["acquire"] and r["learn"] != "trainer" else None,
                   plan_id=r["recipe_id"] if r["acquire"] and r["learn"] != "trainer" else None,
                   plan_price=r["acquire"], yellow=r["yellow"], grey=r["grey"], orange=r["orange"])
    for ph in phases.values():
        mats = []
        for m in ph.pop("need").values():
            m["name"] = names.get(m["id"], str(m["id"]))
            m["ah_qty"], m["other_qty"], m["short"] = round(m["ah_qty"]), round(m["other_qty"]), round(m["short"])
            m["other_cost"] = round(m["other_cost"])
            m["qty"] = m["ah_qty"] + m["other_qty"]
            m["subtotal"] = m["ah_qty"] * (m["ah_unit"] or 0) + m["other_cost"]
            m["unit"] = round(m["subtotal"] / m["qty"]) if m["qty"] else 0
            m["listed"] = scan.get(m["id"], (None, None))[1]
            if m["qty"]:
                mats.append(m)
        ph["materials"] = sorted(mats, key=lambda m: -m["subtotal"])
        made_list = []
        for m in ph["made"].values():
            r = next((r for r in producers.get(m["id"], []) if r["name"] in m["how"]), None)
            made_list.append({"id": m["id"], "name": names.get(m["id"], str(m["id"])), "qty": math.ceil(m["qty"] - 1e-9),
                              "how": m["how"], "inputs": [[i, n, q / r["qty"]] for i, n, q in r["mats"]] if r else []})
        ph["made"] = made_list
        ph["gross"] = sum(m["subtotal"] for m in mats)  # what the rounded shopping list costs
        ph["vendor"] = round(ph["vendor"])
        ph["net"] = ph["gross"] - ph["vendor"]
    return segments, [phases[k] for k in sorted(phases)]


def apply_holdings(phases, holdings, made_inputs=None):
    """Mark what the bags already cover in each phase, using holdings up phase by phase.

    Held intermediates (bars, grinding stones) count first and take their inputs off the
    leaf materials through made_inputs {item id: [(input id, qty per unit)]}; held leaf
    materials count next. Each material gets covered (by held intermediates), have,
    buy and cash; each phase gets cash, what is left to spend."""
    made_inputs = made_inputs or {}
    left = {item_id: entry["count"] for item_id, entry in (holdings or {}).items()}
    for ph in phases:
        need = {m["id"]: m["qty"] for m in ph["materials"]}
        made_need = {m["id"]: m["qty"] for m in ph["made"]}

        def reduce(item_id, amount):
            if item_id in made_need:
                amount = min(amount, made_need[item_id])
                made_need[item_id] -= amount
                for inp, per in made_inputs.get(item_id, []):
                    reduce(inp, amount * per)
            elif item_id in need:
                need[item_id] -= min(amount, need[item_id])

        def depth(item_id):  # products before the intermediates they are made from
            users = [j for j in made_need if any(inp == item_id for inp, _ in made_inputs.get(j, []))]
            return 1 + max(depth(j) for j in users) if users else 0

        for m in sorted(ph["made"], key=lambda m: depth(m["id"])):
            m["have"] = min(left.get(m["id"], 0), made_need[m["id"]])
            left[m["id"]] = left.get(m["id"], 0) - m["have"]
            reduce(m["id"], m["have"])
        cash = 0
        for m in ph["materials"]:
            m["covered"] = round(m["qty"] - need[m["id"]])
            m["have"] = min(left.get(m["id"], 0), round(need[m["id"]]))
            left[m["id"]] = left.get(m["id"], 0) - m["have"]
            m["buy"] = max(0, round(need[m["id"]]) - m["have"])
            m["cash"] = round(m["subtotal"] * m["buy"] / m["qty"]) if m["qty"] else 0
            cash += m["cash"]
        ph["cash"] = cash


def route_file(result, updated, bags_saved=None):
    """route.json for auction_brief.py (references/route.example.json) from a leveling result.

    buy: every material at the route's total need, less what held intermediates already
    cover (the brief only takes off what the bags hold of that same item), with the
    route's auction price as "planned" or the NPC price as "vendor"; plus the plans to buy.
    make: intermediates still to craft. hold: intermediates the bags already cover.
    ore: smelting pairs the route uses, so the brief can say when the bar is cheaper."""
    zh = PROFESSION_ZH.get(result["profession"], result["profession"])
    order = []
    for seg in result["segments"]:
        if seg["recipe"] not in order:
            order.append(seg["recipe"])
    buy, make, hold = {}, {}, {}
    for ph in result["phases"]:
        for m in ph["materials"]:
            row = buy.setdefault(m["name"], {"item": m["name"], "qty": 0})
            row["qty"] += m["qty"] - (m.get("covered") or 0)
            if m["from"] and all(f.startswith("NPC") for f in m["from"]):
                row["vendor"] = m["unit"]
            elif m["ah_unit"]:
                row["planned"] = m["ah_unit"]
        for m in ph["made"]:
            have = m.get("have") or 0
            if m["qty"] > have:
                row = make.setdefault(m["name"], {"product": m["name"], "qty": 0,
                                                  "inputs": {n: round(per, 3) for _, n, per in m["inputs"]}})
                row["qty"] += m["qty"] - have
            if have:
                row = hold.setdefault(m["name"], {"item": m["name"], "count": 0, "use": 0})
                row["count"] += have
                row["use"] += have
    for seg in result["segments"]:
        if seg["plan"] and seg["plan"] not in buy:
            buy[seg["plan"]] = {"item": seg["plan"], "qty": 1,
                                ("vendor" if seg["learn"].startswith("NPC") else "planned"): round(seg["plan_price"])}
    used = set(buy) | set(make) | set(hold)
    ore = [[s["mats"][0][1], s["name"].replace("熔煉", "") + "錠"] for s in SMELTS
           if len(s["mats"]) == 1 and s["mats"][0][1] in used and s["name"].replace("熔煉", "") + "錠" in used]
    source = f"leveling_route.py（{result['prices']}" + (f"、背包 {bags_saved}" if bags_saved else "") + "）"
    if result.get("notes"):
        source += "。" + "；".join(result["notes"])
    return {"name": f"{zh}路線（{result['from']}→{result['to']}：{'→'.join(order)}）",
            "list": f"我的路線-{zh}{result['to']}", "updated": updated, "products": result["products"],
            "source": source, "buy": [r for r in buy.values() if r["qty"] > 0], "make": list(make.values()),
            "hold": list(hold.values()), "ore": ore}


def save_route(result, path, updated, bags_saved=None):
    """Write route_file() to path for auction_brief.py; an existing file is kept as <stem>-<time>.json."""
    path = Path(path).expanduser()
    backup = None
    if path.exists():
        backup = path.with_name(f"{path.stem}-{datetime.datetime.now():%Y%m%d-%H%M%S}.json")
        backup.write_bytes(path.read_bytes())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(route_file(result, updated, bags_saved), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    print(f"路線存到 {path}" + (f"，舊檔備份為 {backup.name}" if backup else ""), file=sys.stderr)


def print_report(result, product_note=""):
    """Print the plan: settings, character and notes, segments, each phase's shopping list,
    the routes --goal cash compared, and plans nobody sells that would beat the route.

    product_note says how disenchant values were priced (Pricer.product_note)."""
    g = lambda c: f"{c / 10000:.2f}g"
    products, gate, segments = result["products"], result["gate"], result["segments"]
    mode = {"vendor": "成品賣給商人", "disenchant": f"成品分解（{product_note}）", "keep": "成品保留"}[products]
    if result["goal"] == "cash":
        mode += "・最省現金（已有的材料先用、不算錢）"
    if result["use"]:
        mode += "・只用 " + "、".join(result["use"])
    if result["avoid"]:
        mode += "・不用 " + "、".join(result["avoid"])
    print(f"{result['profession']} {result['from']}→{result['to']}・價格：{result['prices']}・掛單價，非成交價・{mode}")
    c = result.get("character")
    if c:
        import auction_brief
        bags_saved = result.get("bags_saved")
        print(f"角色：{c['level']} 級・技能 {c['skill'][0]}/{c['skill'][1]}・採礦 {c['mining'] or '—'}"
              f"（API 角色資料 {auction_brief.taiwan_time(c['api_modified'])}）" + (f"・背包存檔 {bags_saved}" if bags_saved else ""))
    for note in result["notes"]:
        print(f"注意：{note}")
    for seg in segments:
        print(f"{seg['from']}→{seg['to']} {seg['recipe']} 約 {seg['crafts']:.0f} 次（多備 {seg['spare']} 次）｜"
              f"每次材料 {g(seg['cost'])}、{seg['recover']} {g(seg['sell'])}｜"
              f"{seg['plan'] + ' ' + g(seg['plan_price']) + '（' + seg['learn'] + '）' if seg['plan'] else seg['learn']}｜"
              + "、".join(f"{n}×{q}" for n, q in seg["mats"]))
    for ph in result["phases"]:
        label = f"到 {gate}" if ph["phase"] == 1 else f"{gate} 以後（要先學下一階）"
        cash = f"、扣掉已有要花 {g(ph['cash'])}" if "cash" in ph else ""
        back = {"vendor": "賣店收回", "disenchant": "成品回收（能分解的算分解）", "keep": "成品回收"}[products]
        fees = sum(s["fee"] for s in segments if s["phase"] == ph["phase"])
        fee_text = f"、學費 {g(fees)}" if fees else ""
        print(f"\n階段 {ph['phase']}（{label}）：材料 {g(ph['gross'])}、{back} {g(ph['vendor'])}、淨 {g(ph['net'])}{fee_text}{cash}")
        for m in ph["materials"]:
            listed = f"，掛單 {m['listed']} 件" if m["listed"] is not None else ""
            short = f"，缺 {m['short']} 件" if m["short"] else ""
            held = ""
            if m.get("have") or m.get("covered"):
                got = "、".join(x for x in (f"已有的半成品抵掉 {m['covered']}" if m.get("covered") else "",
                                            f"已有 {m['have']}" if m.get("have") else "") if x)
                held = f"｜{got}，" + (f"還要買 {m['buy']}（{g(m['cash'])}）" if m["buy"] else "不用買")
            print(f"  {m['name']} ×{m['qty']}（{g(m['unit'])}，{'、'.join(m['from'])}{listed}{short}）= {g(m['subtotal'])}{held}")
        for m in ph["made"]:
            held = f"，已有 {m['have']} 個可少做" if m.get("have") else ""
            print(f"  （{m['name']} ×{m['qty']} {m['how']}，材料已算在上面{held}）")
    compared = result.get("compared", [])
    if len(compared) > 1:
        print("\n比較過的走法（要花＝材料＋設計圖與學費；已有＝用掉的已有材料照買價；淨＝照市值、扣掉成品回收）：")
        for i, c in enumerate(compared[:4]):
            way = "、".join(f"{n} {a}→{b}" for n, a, b in c["route"])
            back = f"・賣店收回 {g(c['gold_back'])}" if c["gold_back"] else ""
            print(f"  {'選用' if i == 0 else '　　'} 要花 {g(c['cash'])}{back}・已有 {g(c['held'])}・淨 {g(c['net'])}｜{way}")
    if result["missing_plans"]:
        print("\n目前買不到、但比路線便宜的配方：")
        for m in result["missing_plans"]:
            print(f"  {m['plan']} 可用在 {m['from']}–{m['to']}，每次淨 {g(m['net'])}；{m['last_seen'] or '阿莫比沒紀錄'}")
