"""Route search for leveling_route.py: which recipe to craft at each skill point.

Skill points are walked in order; each goes to the recipe with the lowest expected net cost
at the stock still listed, (reagents - product value) / chance. --goal value then drops
plans that save less than their price over the route. --goal cash walks with held units at
several weights, with and without the product value, drops recipes while that saves gold
(prune_route) and keeps the route that costs least out of pocket.
"""

from functools import partial
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import amobi_recipe_value as av  # noqa: E402
from leveling_pricing import HELD_WEIGHT, SHORT_PENALTY  # noqa: E402

CASH_WEIGHTS = (HELD_WEIGHT, 0.5, 1.0)  # --goal cash: held-unit weights the skill-by-skill walk is tried with


def chance(r, s):
    """Chance that one craft at skill s gives a point: 1 below yellow, falling to 0 at grey."""
    if r["orange"] is None or s < r["orange"] or s >= r["grey"]:
        return 0
    return 1 if s < r["yellow"] else (r["grey"] - s) / (r["grey"] - r["yellow"])


def candidate_pool(recipes, pricer, start, end, stock, use=(), avoid=(), state=None, holdings=None):
    """(recipes a route from start to end can use, recipes whose plan nobody sells now).

    Each usable recipe gets cost (reagents for one craft), sell and recover (product value),
    net, and acquire / acquire_from: what learning it costs and where. state is the
    character from the API (learned recipes, trainer fees); holdings are the bags, whose
    plans cost nothing."""
    pool, missing_plans = [], []
    for r in recipes:
        if r["blocked"] or r["grey"] <= start or (r["orange"] or 999) >= end:
            continue
        if (use and r["name"] not in use) or r["name"] in avoid:
            continue
        priced = pricer.quote_recipe(r, 1, max(start, r["orange"] or start), stock)
        if priced is None:
            continue
        r["cost"] = sum(take * unit for _, _, _, take, unit, _ in priced[1])
        r["sell"], r["recover"] = pricer.product_value(r)
        r["net"] = r["cost"] - r["sell"]
        owned = (holdings or {}).get(r["recipe_id"]) if r["recipe_id"] else None
        if r["learn"] == "trainer" and state and r["name"] not in state["learned"]:
            fee = state["fees"].get(r["name"], 0)
            r["acquire"] = fee
            r["acquire_from"] = "訓練師（未學" + (f"，學費 {fee / 10000:.2f}g" if fee else "") + "）"
        elif r["learn"] in ("trainer", "auto"):
            r["acquire"], r["acquire_from"] = 0, "訓練師"
        elif state and r["name"] in state["learned"]:
            r["acquire"], r["acquire_from"] = 0, "已學"
        elif owned:
            r["acquire"], r["acquire_from"] = 0, f"已有設計圖（{'、'.join(owned['where'][:2])}）"
        else:
            plan = next(iter(pricer.sources(r["recipe_id"])), None)
            if plan is None:
                missing_plans.append(r)
                continue
            r["acquire"], r["acquire_from"] = plan[0], plan[2]
        pool.append(r)
    return pool, missing_plans


def walk(pricer, start, end, stock, candidates, weight=HELD_WEIGHT, recover=True):
    """Walk the skill points in order; each takes the recipe with the lowest expected net
    cost at the stock still listed, then uses that stock up. weight is what a held unit
    weighs against its buy price (--goal cash); recover=False ignores the product value.

    stock is {item id: listed count, ("held", item id): held count}; the walk uses a copy.
    Returns steps {skill, score, recipe, chance, parts}, or None when a point has no recipe."""
    pricer.held_weight = weight
    stock = dict(stock)
    steps = []
    for s in range(start, end):
        best = None
        for r in candidates:
            p = chance(r, s)
            if p <= 0:
                continue
            got = pricer.quote_recipe(r, 1 / p, s, stock)
            if got is None:
                continue
            score = got[0] - (r["sell"] / p if recover else 0)
            if best is None or score < best[0]:
                best = (score, r, p, got[1])
        if best is None:
            return None
        for item_id, _, kind, take, _, short in best[3]:
            if kind == "held":
                stock[("held", item_id)] = max(0, stock[("held", item_id)] - take)
            if kind == "ah" and item_id in stock:
                stock[item_id] = max(0, stock[item_id] - (take - short))
        steps.append({"skill": s, "score": best[0], "recipe": best[1], "chance": best[2], "parts": best[3]})
    return steps


def route_cash(steps, held_price):
    """Gold and materials a walked route uses, for --goal cash.

    steps carry "recipe" (with "acquire", "sell", "recover"), "chance" and "parts"
    (item id, label, kind, quantity, copper per unit, quantity beyond the listings).
    held_price(item id) is what one held unit would cost to buy now. Returns spent
    (materials bought), fees (plans and trainer fees of the recipes used), short_extra
    (what units beyond the listings add at SHORT_PENALTY), held (buy value of the held
    materials used), back (product value) and gold_back (the part that comes back as
    gold: products sold to a vendor)."""
    out = dict(spent=0, fees=0, short_extra=0, held=0, back=0, gold_back=0)
    used = {}
    for st in steps:
        r = st["recipe"]
        used[r["name"]] = r
        out["back"] += r["sell"] / st["chance"]
        if r["recover"] == "賣店":
            out["gold_back"] += r["sell"] / st["chance"]
        for item_id, _, kind, take, unit, short in st["parts"]:
            if kind == "held":
                out["held"] += take * held_price(item_id)
            elif kind != "made":
                out["spent"] += take * unit
                out["short_extra"] += short * unit * (SHORT_PENALTY - 1)
    out["fees"] = sum(r["acquire"] for r in used.values())
    return out


def cash_cost(tally):
    """What --goal cash minimises: gold out of pocket, with held materials at HELD_WEIGHT
    of their price so a route does not burn a pile of them to save a few copper."""
    return (tally["spent"] + tally["fees"] + tally["short_extra"] - tally["gold_back"]
            + HELD_WEIGHT * tally["held"])


def prune_route(pool, run, cost, rounds=10):
    """Drop recipes while that lowers cost(run(recipes)); returns (cost, steps, dropped) or None.

    The skill-by-skill walk is greedy: it can spend a scarce held material on an early
    recipe that a later stretch needed, then buy it back. Each round tries the route
    without each recipe it used and keeps the best drop that lowers the cost by more
    than a copper."""
    active = list(pool)
    steps = run(active)
    if steps is None:
        return None
    best, dropped = cost(steps), []
    for _ in range(rounds):
        used = {st["recipe"]["name"] for st in steps}
        trial = None
        for r in active:
            if r["name"] not in used:
                continue
            alt = run([x for x in active if x is not r])
            if alt is None:
                continue
            c = cost(alt)
            if c < best - 1 and (trial is None or c < trial[0]):
                trial = (c, r, alt)
        if trial is None:
            break
        best, steps = trial[0], trial[2]
        active.remove(trial[1])
        dropped.append(trial[1]["name"])
    return best, steps, dropped


def value_route(pool, run):
    """Steps of the walk once every plan it uses saves more than its price, or None.

    run(candidates) walks the skill points. While a used recipe with a price (plan or
    trainer fee) saves less than that price, the one furthest under is dropped."""
    active = list(pool)
    while True:
        steps = run(active)
        if steps is None:
            return None
        used = {st["recipe"]["name"] for st in steps}
        total = sum(st["score"] for st in steps)
        worst = None
        for r in active:
            if r["acquire"] <= 0 or r["name"] not in used:
                continue
            alt = run([x for x in active if x is not r])
            if alt is None:
                continue
            saving = sum(st["score"] for st in alt) - total
            if saving < r["acquire"] and (worst is None or r["acquire"] - saving > worst[0]):
                worst = (r["acquire"] - saving, r)
        if not worst:
            return steps
        active.remove(worst[1])


def cheapest_cash_route(pool, run, buy_price):
    """(steps, compared) of the route that costs least out of pocket, or (None, []).

    One greedy walk can burn held materials early and buy them back later. Walk with held
    units at several weights, with and without the product value, drop recipes while that
    saves gold, and keep the cheapest. run(candidates, weight, recover) walks the skill
    points; buy_price(item id) is what one held unit would cost now. compared lists every
    distinct route found, cheapest first: route [[recipe, from, to]], cash, gold_back, held,
    net, cost and dropped."""
    found = {}
    for weight in CASH_WEIGHTS:
        for recover in (True, False):
            got = prune_route(pool, partial(run, weight=weight, recover=recover),
                              lambda st: cash_cost(route_cash(st, buy_price)))
            if got is None:
                continue
            key = tuple(st["recipe"]["name"] for st in got[1])
            if key not in found or got[0] < found[key][0]:
                found[key] = got
    if not found:
        return None, []
    ranked = sorted(found.values(), key=lambda g: g[0])
    compared = []
    for cost, steps, dropped in ranked:
        t = route_cash(steps, buy_price)
        order = []
        for st in steps:
            if not order or order[-1][0] != st["recipe"]["name"]:
                order.append([st["recipe"]["name"], st["skill"], st["skill"] + 1])
            order[-1][2] = st["skill"] + 1
        compared.append({"route": order, "cash": round(t["spent"] + t["fees"]), "gold_back": round(t["gold_back"]),
                         "held": round(t["held"]),
                         "net": round(t["spent"] + t["fees"] + t["held"] - t["back"]),
                         "cost": round(cost), "dropped": dropped})
    return ranked[0][1], compared


def find_route(pool, pricer, start, end, stock, goal="value"):
    """(steps, compared) for the goal, or (None, []) when no route covers every skill point.

    compared is empty for --goal value; see cheapest_cash_route for --goal cash."""
    run = partial(walk, pricer, start, end, stock)
    if goal == "cash":
        return cheapest_cash_route(pool, run, pricer.buy_price)
    return value_route(pool, run), []


def cheaper_missing_plans(missing_plans, steps, page):
    """Plans nobody sells now that would beat the route on at least three skill points.

    page(item id) is the plan's wowamobi page, for when each faction last listed it."""
    out = []
    for r in missing_plans:
        points = [st["skill"] for st in steps
                  if chance(r, st["skill"]) > 0 and r["net"] / chance(r, st["skill"]) < 0.8 * st["score"]]
        if len(points) >= 3:  # one or two points near a colour change are noise
            info = page(r["recipe_id"])
            seen = "；".join(f"{k} {av.gold(v)}（{info['faction_seen'].get(k, '')}）" for k, v in info["faction_min"].items())
            out.append({"plan": r["recipe"], "plan_id": r["recipe_id"], "from": min(points),
                        "to": max(points) + 1, "net": r["net"], "last_seen": seen})
    return out
