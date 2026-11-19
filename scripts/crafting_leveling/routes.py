"""Compile and quote the guide's fixed candidate routes."""

from collections import Counter
from dataclasses import dataclass, field
from fractions import Fraction
import math

from .sources import series


MILESTONES = (150, 225, 300)
STARTS = (1, 150, 225)
RODS = (6218, 6339, 11130, 11145, 16207)


@dataclass
class Phase:
    start: int
    end: int
    demands: Counter = field(default_factory=Counter)
    formulas: set = field(default_factory=set)
    training: int = 0
    estimated_training: bool = False
    missing_fees: set = field(default_factory=set)
    steps: list = field(default_factory=list)
    carried: Counter = field(default_factory=Counter)
    recovery: int = 0
    requirements: set = field(default_factory=set)


def expected_crafts(recipe, start, end):
    def probability(skill):
        if skill < recipe.yellow:
            return 1
        if skill < recipe.green:
            return 1 - 0.5 * (skill - recipe.yellow) / (recipe.green - recipe.yellow)
        return max(0.05, 0.5 - 0.45 * (skill - recipe.green) / max(1, recipe.grey - recipe.green))

    return math.ceil(sum(1 / probability(skill) for skill in range(start, end)))


def compile_route(slug, steps, recipes, facts):
    """Expand only materials with a verified same-profession producer."""
    phases = [Phase(a, b) for a, b in zip(STARTS, MILESTONES)]
    rank_fees = facts["rankFees"][slug]
    for phase, fees in zip(phases, (rank_fees[:2], rank_fees[2:3], rank_fees[3:])):
        phase.training = sum(fees)
    known, unlocked, inventory = set(), set(), Counter()
    carry_stock = Counter()
    producers = {recipes[spell].product: spell for spell in facts["components"].get(slug, [])}
    tools = {int(item): spell for item, spell in facts["tools"].items()}
    phase = phases[0]

    def craft(spell, count, start, end, visiting=frozenset()):
        recipe = recipes[spell]
        if (start < recipe.learn or (end > start and end > recipe.grey) or spell in visiting
                or (end > start and count < end - start)):
            raise ValueError(f"{slug} {start}→{end} 的配方或材料前置不符（法術 {spell}，學習 {recipe.learn}）")
        if start == end and recipe.product in tools and inventory[recipe.product]:
            return
        for tool in recipe.tools:
            upgraded = RODS[RODS.index(tool):] if tool in RODS else (tool,)
            owned = next((item for item in upgraded if inventory[item]), None)
            if owned and carry_stock[owned]:
                phase.carried[owned] = 1
            elif not owned and tool in tools:
                craft(tools[tool], 1, start, start, visiting | {spell})
            elif not owned:
                inventory[tool] = 1
                phase.demands[tool] += 1
        if spell not in known:
            known.add(spell)
            if recipe.requirement:
                phase.requirements.add(recipe.requirement)
                if recipe.requirement not in unlocked:
                    unlocked.add(recipe.requirement)
                    phase.demands.update(dict(recipe.unlock_materials))
            if recipe.formula:
                phase.formulas.add(recipe.formula)
            elif recipe.fee is None:
                phase.missing_fees.add(recipe.name)
            else:
                phase.training += recipe.fee
                phase.estimated_training |= recipe.estimated_fee
        for item, unit in recipe.reagents:
            need = count * unit
            if need > inventory[item] and item in producers:
                component = recipes[producers[item]]
                if start >= component.learn and producers[item] != spell:
                    batches = math.ceil((need - inventory[item]) / component.output)
                    craft(producers[item], batches, start, start, visiting | {spell})
            used = min(need, inventory[item])
            carried = min(used, carry_stock[item])
            phase.carried[item] += carried
            carry_stock[item] -= carried
            inventory[item] -= used
            phase.demands[item] += need - used
        if recipe.product:
            inventory[recipe.product] += count * recipe.output
        phase.steps.append((start, end, recipe, count))

    end = 1
    for start, target, spell, count in steps:
        if start != end or start > target:
            raise ValueError(f"{slug} 路線中斷於 {end}")
        if start == phase.end and start != 300:
            phase = phases[phases.index(phase) + 1]
            carry_stock = inventory.copy()
        if target > phase.end:
            raise ValueError(f"{slug} 路線跨過 {phase.end}")
        craft(spell, count, start, target)
        end = target
    if end != 300 or any(not stage.steps for stage in phases):
        raise ValueError(f"{slug} 路線未涵蓋全部里程碑")
    used_items = set(producers) | set(tools)
    for stage in phases:
        for _, _, recipe, _ in stage.steps:
            used_items.update(recipe.tools)
            used_items.update(item for item, _ in recipe.reagents)
    for stage in phases:
        stage.recovery = sum(
            count * recipe.output * facts["sellPrices"].get(str(recipe.product), 0)
            for _, _, recipe, count in stage.steps if recipe.product not in used_items
        )
    return phases


@dataclass(frozen=True)
class Purchase:
    item: int
    quantity: int
    auction: int
    npc: int
    spent: int
    missing: int
    unknown: bool = False
    vendor: str = ""
    npc_spent: int = 0


def buy(item, needed, depth, offer=None):
    """Price the requested units with a shared price ladder and a public NPC offer."""
    left, spent = needed, Fraction()
    for unit, listed in depth or ():
        if offer and unit >= Fraction(offer[0], offer[1]):
            break
        quantity = min(left, listed)
        spent += unit * quantity
        left -= quantity
        if not left:
            break
    auction, npc, npc_spent, vendor = needed - left, 0, 0, ""
    if left and offer:
        price, pack, vendor = offer
        npc = math.ceil(left / pack) * pack
        npc_spent = price * (npc // pack)
        spent += npc_spent
        left = 0
    return Purchase(item, needed, auction, npc, math.ceil(spent), left, bool(left and depth is None), vendor, npc_spent)


@dataclass
class Quote:
    materials: list
    formulas: list
    training: int
    missing_fees: set
    estimated_training: bool

    @property
    def total(self):
        return self.training + sum(p.spent for p in self.materials + self.formulas)

    @property
    def missing(self):
        return [p for p in self.materials + self.formulas if p.missing]


class Market:
    def __init__(self, depth, supplies, formulas):
        self.depth, self.supplies, self.formulas = depth, supplies, formulas

    def quote(self, phases):
        demands, formulas, missing_fees = Counter(), Counter(), set()
        for phase in phases:
            demands.update(phase.demands)
            formulas.update(phase.formulas)
            missing_fees.update(phase.missing_fees)
        return Quote(
            [buy(i, n, self.depth.get(i, ()), self.supplies.get(i)) for i, n in demands.items() if n],
            [buy(i, n, self.depth.get(i, ()), self.formulas.get(i)) for i, n in formulas.items()],
            sum(p.training for p in phases), missing_fees, any(p.estimated_training for p in phases),
        )


def candidate_steps(slug, handbook, recipes, facts):
    steps = [series(row) for row in series(handbook["steps"])]
    for label, changes in facts.get("routes", {}).get(slug, {}).items():
        if any(row[2] not in recipes for section in changes for row in section):
            continue
        route = steps[:]
        for replacement in changes:
            start, end = replacement[0][0], replacement[-1][1]
            before = [row for row in route if row[0] < start and row[1] <= start]
            after = [row for row in route if row[0] >= end and row[0] != start]
            patched = []
            for left, right, spell, *count in replacement:
                bounds = [left, *(level for level in MILESTONES if left < level < right), right]
                for a, b in zip(bounds, bounds[1:]):
                    n = count[0] if count and len(bounds) == 2 else max(1, expected_crafts(recipes[spell], a, b))
                    patched.append((a, b, spell, n))
            route = before + patched + after
        yield label, route
    yield "無限副本手冊", steps


def select_route(slug, handbook, recipes, facts, market):
    candidates = []
    errors = []
    for label, steps in candidate_steps(slug, handbook, recipes, facts):
        try:
            phases = compile_route(slug, steps, recipes, facts)
        except (KeyError, ValueError) as error:
            errors.append(f"{label}：{error}")
            continue
        stages = [market.quote([phase]) for phase in phases]
        cumulative = [market.quote(phases[:index]) for index in range(1, 4)]
        # Secure the first point first, then compare the remaining reachable stages and their spend.
        score = (
            bool(stages[0].missing),
            sum(bool(q.missing) for q in stages),
            bool(cumulative[-1].missing),
            sum(p.missing for p in stages[0].missing),
            sum(p.missing for q in stages[1:] for p in q.missing),
            stages[0].total, cumulative[-1].total,
        )
        candidates.append((score, label, phases, stages, cumulative))
    if not candidates:
        raise ValueError(f"{slug} 找不到可執行的路線（{'；'.join(errors)}）")
    _, label, phases, stages, cumulative = min(candidates, key=lambda result: result[0])
    return label, phases, stages, cumulative
