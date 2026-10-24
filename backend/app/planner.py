"""Gemma prompts plus the Python side of planning.

The model only decides *what* to eat and *how much* to buy. Every naira figure is computed here from
the family's own price list, because LLMs are unreliable at arithmetic and prices must be trustworthy.
"""

import logging
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import AIError, ask_json
from app.models import Plan, PlanItem, Price, User
from app.schemas import MenuDay, NutritionAnalysis, PlanNutrition, Swap

log = logging.getLogger(__name__)

CENTS = Decimal("0.01")
MAX_SWAPS = 5


# ---------- What we accept back from the model ----------


class _AIGroceryLine(BaseModel):
    item: str = Field(min_length=1, max_length=120)
    unit: str = Field(min_length=1, max_length=40)
    # 0 is allowed (the model uses it to mean "drop this line"); cost_plan_items skips those
    quantity: Decimal = Field(ge=0, le=10_000)


class _AIScore(BaseModel):
    protein: int = Field(ge=0, le=10)
    carbs: int = Field(ge=0, le=10)
    vegetables: int = Field(ge=0, le=10)
    fruit: int = Field(ge=0, le=10)

    @field_validator("*", mode="before")
    @classmethod
    def round_number(cls, v):
        return round(float(v)) if isinstance(v, (int, float, str)) else v


class _AINutrition(BaseModel):
    score: _AIScore
    note: str
    tips: list[str] = []

    @field_validator("tips")
    @classmethod
    def trim(cls, v: list[str]) -> list[str]:
        return [s.strip() for s in v if s.strip()][:5]


class _AIPlan(BaseModel):
    menu: list[MenuDay] = Field(min_length=7, max_length=7)
    grocery_list: list[_AIGroceryLine] = Field(min_length=1, max_length=80)
    nutrition: _AINutrition

    @field_validator("grocery_list")
    @classmethod
    def something_to_buy(cls, v: list[_AIGroceryLine]) -> list[_AIGroceryLine]:
        if not any(line.quantity > 0 for line in v):
            raise ValueError("grocery_list has no items with quantity above 0")
        return v


class _AISwaps(BaseModel):
    swaps: list[Swap]

    @field_validator("swaps")
    @classmethod
    def at_most(cls, v: list[Swap]) -> list[Swap]:
        return v[:MAX_SWAPS]


class _AINutritionAnalysis(BaseModel):
    priorities: list[str] = Field(min_length=1)
    focus_foods: list[str] = []
    tips: list[str] = []

    @field_validator("priorities", "focus_foods", "tips")
    @classmethod
    def trim(cls, v: list[str]) -> list[str]:
        # Keep the response readable even if the model over-delivers
        return [s.strip() for s in v if s.strip()][:8]


# ---------- Family context for prompts ----------


def _key(item: str, unit: str) -> tuple[str, str]:
    return (" ".join(item.lower().split()), " ".join(unit.lower().split()))


def _family_profile(db: Session, family_id: int) -> str:
    members = db.scalars(select(User).where(User.family_id == family_id).order_by(User.id)).all()
    counts = Counter(m.age_group.value for m in members)
    lines = [f"Household of {len(members)}: " + ", ".join(f"{n} {group}" for group, n in sorted(counts.items()))]
    for m in members:
        if m.dislikes:
            lines.append(f"- {m.name} ({m.age_group.value}) dislikes/avoids: {m.dislikes}")
    return "\n".join(lines)


def _family_prices(db: Session, family_id: int) -> list[Price]:
    return list(db.scalars(select(Price).where(Price.family_id == family_id).order_by(Price.id)))


def _price_table(prices: list[Price]) -> str:
    rows = [f"- {p.item} | {p.unit} | {'NGN ' + str(p.price) if p.price is not None else 'price unknown'}" for p in prices]
    return "\n".join(rows) or "(no items listed)"


# ---------- Nutrition analysis ----------


def analyze_nutrition(db: Session, family_id: int) -> NutritionAnalysis:
    prompt = f"""You are a friendly Nigerian family nutrition assistant.

FAMILY
{_family_profile(db, family_id)}

FOODS THIS FAMILY BUYS
{_price_table(_family_prices(db, family_id))}

Based on the ages in this household, give general (not medical) nutrition priorities for the week.
Prefer affordable Nigerian foods, ideally ones from the list above.

JSON shape:
{{
  "priorities": ["short sentence, e.g. 'Kids need more protein and calcium: add eggs, milk, fish'"],
  "focus_foods": ["food name"],
  "tips": ["short practical tip"]
}}
Give 3-5 priorities, up to 8 focus_foods and 3-5 tips."""
    result = ask_json(prompt, validate=_AINutritionAnalysis.model_validate)
    return NutritionAnalysis(**result.model_dump())


# ---------- Meal plan ----------


def _plan_prompt(db: Session, plan: Plan, prices: list[Price]) -> str:
    extras = ""
    if plan.notes:
        extras += f"\nFAMILY PREFERENCES: {plan.notes}"
    if plan.pantry:
        extras += f"\nALREADY IN THE KITCHEN (don't buy these again unless more is needed): {plan.pantry}"
    return f"""You are a Nigerian family meal planner. Plan one week of home-cooked meals.

FAMILY
{_family_profile(db, plan.family_id)}
WEEKLY FOOD BUDGET: NGN {plan.budget}{extras}

MARKET PRICE LIST (item | unit | price per unit)
{_price_table(prices)}

RULES
- THE BUDGET IS A HARD LIMIT. The grocery list must cost at most NGN {plan.budget}; aim for 85-95% of it.
- Work in this order: first split the budget across food groups, then build the grocery list inside that split,
  then write the menu using only what is on the grocery list (plus what is already in the kitchen).
- For each grocery line, est_cost = quantity x price per unit, and running_total adds up the est_cost so far.
  If running_total would pass the budget, buy less or choose a cheaper item instead.
- Cheap staples (garri, rice, beans, yam, bread) should fill most meals; use costly protein (chicken, fish, eggs)
  in modest amounts. Leftovers and repeated meals are fine and realistic.
- 7 days, Monday to Sunday, with breakfast, lunch and dinner. Use familiar Nigerian meals.
- Balance protein, carbohydrates, vegetables and fruit across the week. Respect every dislike.
- For grocery_list "item" and "unit", copy the EXACT text from the price list whenever the item is listed there.
  Only add items that are not on the list if truly necessary (e.g. seasoning), with a sensible unit.
- "quantity" is how many of that unit to buy for the week (a number, decimals allowed).

JSON shape (keys in this order):
{{
  "budget_split": {{"carbs": 0, "protein": 0, "vegetables_fruit": 0, "oils_seasoning": 0}},
  "grocery_list": [{{"item": "Rice", "unit": "kg", "quantity": 5, "est_cost": 7500, "running_total": 7500}}],
  "estimated_total": 0,
  "menu": [{{"day": "Monday", "breakfast": "...", "lunch": "...", "dinner": "..."}}],
  "nutrition": {{
    "score": {{"protein": 0-10, "carbs": 0-10, "vegetables": 0-10, "fruit": 0-10}},
    "note": "one or two sentences on how balanced the week is",
    "tips": ["short tip"]
  }}
}}"""


def cost_plan_items(lines: list[_AIGroceryLine], prices: list[Price]) -> list[PlanItem]:
    """Merge duplicate lines and price each one from the family's list. Unknown prices stay None."""
    by_key = {_key(p.item, p.unit): p for p in prices}
    merged: dict[tuple[str, str], PlanItem] = {}
    for line in lines:
        key = _key(line.item, line.unit)
        qty = line.quantity.quantize(CENTS, ROUND_HALF_UP)
        if qty <= 0:
            continue
        if key in merged:
            merged[key].quantity += qty
            continue
        price = by_key.get(key)
        merged[key] = PlanItem(
            # Use the family's spelling so the list matches their price table
            item=price.item if price else " ".join(line.item.split()),
            unit=price.unit if price else " ".join(line.unit.split()),
            quantity=qty,
            unit_price=price.price if price else None,
        )
    for pi in merged.values():
        pi.subtotal = (pi.quantity * pi.unit_price).quantize(CENTS, ROUND_HALF_UP) if pi.unit_price is not None else Decimal("0")
    return list(merged.values())


def _suggest_swaps(plan: Plan, prices: list[Price]) -> list[Swap]:
    over = plan.total_cost - plan.budget
    lines = "\n".join(
        f"- {i.item}: {i.quantity} {i.unit} = NGN {i.subtotal}" for i in sorted(plan.items, key=lambda i: -i.subtotal)
    )
    prompt = f"""This Nigerian family's weekly grocery list costs NGN {plan.total_cost}, which is NGN {over} over their NGN {plan.budget} budget.

GROCERY LIST (most expensive first)
{lines}

MARKET PRICE LIST (item | unit | price per unit)
{_price_table(prices)}

Suggest up to {MAX_SWAPS} swaps to cheaper, still nutritious alternatives (e.g. chicken -> fish, or reduce a costly item).
Prefer items from the price list. Do not do any arithmetic.

JSON shape:
{{"swaps": [{{"from_item": "Chicken", "to_item": "Fish (frozen)", "reason": "short reason"}}]}}"""
    try:
        return ask_json(prompt, validate=_AISwaps.model_validate).swaps
    except AIError:
        # Swaps are a nice-to-have; don't fail the whole plan over them
        log.warning("Could not get swap suggestions", exc_info=True)
        return []


class _AIRevision(BaseModel):
    grocery_list: list[_AIGroceryLine] = Field(min_length=1, max_length=80)


def _total(items: list[PlanItem]) -> Decimal:
    return sum((i.subtotal for i in items), Decimal("0"))


def _revise_to_budget(items: list[PlanItem], budget: Decimal, prices: list[Price]) -> list[PlanItem] | None:
    """One extra Gemma pass that trims an over-budget list. Python enforces that it can only shrink:
    new items are dropped and quantities are capped at the original, so the menu stays cookable."""
    total = _total(items)
    lines = "\n".join(
        f"- {i.item} | {i.unit} | qty {i.quantity} | "
        + (f"NGN {i.unit_price} each = NGN {i.subtotal}" if i.unit_price is not None else "price unknown")
        for i in sorted(items, key=lambda i: -i.subtotal)
    )
    prompt = f"""This weekly grocery list for a Nigerian family costs NGN {total}, but the budget is NGN {budget}.
It is NGN {total - budget} over. Trim it so it costs at most NGN {budget} (aim for about 95% of it).

CURRENT LIST (item | unit | quantity | cost; most expensive first)
{lines}

RULES
- You may ONLY reduce quantities or remove lines. Do not add new items or increase any quantity.
- Cut expensive items (meat, fish, eggs, oil) before cheap staples, but keep some protein for the children.
- Keep "item" and "unit" text exactly as above.
- For each line, est_cost = quantity x price each, and running_total adds them up. Stop cutting once
  running_total is within the budget.

JSON shape:
{{"grocery_list": [{{"item": "Rice", "unit": "kg", "quantity": 4, "est_cost": 6000, "running_total": 6000}}]}}"""
    try:
        revision: _AIRevision = ask_json(prompt, validate=_AIRevision.model_validate)
    except AIError:
        log.warning("Budget revise pass failed; keeping the original list", exc_info=True)
        return None

    original = {_key(i.item, i.unit): i.quantity for i in items}
    allowed = [
        line.model_copy(update={"quantity": min(line.quantity, original[_key(line.item, line.unit)])})
        for line in revision.grocery_list
        if _key(line.item, line.unit) in original
    ]
    if not allowed:
        return None
    revised = cost_plan_items(allowed, prices)
    return revised if _total(revised) < total else None


def fill_plan(db: Session, plan: Plan) -> None:
    """Ask Gemma for a menu + grocery list, then price it. Replaces any existing content on `plan`."""
    prices = _family_prices(db, plan.family_id)
    result: _AIPlan = ask_json(_plan_prompt(db, plan, prices), validate=_AIPlan.model_validate)

    items = cost_plan_items(result.grocery_list, prices)
    if _total(items) > plan.budget:
        items = _revise_to_budget(items, plan.budget, prices) or items
    plan.items = items
    plan.total_cost = _total(items)
    plan.menu_json = [d.model_dump() for d in result.menu]
    plan.nutrition_json = PlanNutrition.model_validate(result.nutrition.model_dump()).model_dump()
    plan.swaps_json = (
        [s.model_dump() for s in _suggest_swaps(plan, prices)] if plan.total_cost > plan.budget else []
    )
