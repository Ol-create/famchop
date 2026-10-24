from decimal import Decimal

from app.planner import _AIGroceryLine, cost_plan_items
from app.models import Price

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MENU = [{"day": d, "breakfast": "Pap and akara", "lunch": "Jollof rice", "dinner": "Beans and plantain"} for d in DAYS]
NUTRITION = {"score": {"protein": 7, "carbs": 8.6, "vegetables": "5", "fruit": 3}, "note": "Fairly balanced.", "tips": ["Add fruit"]}


def plan_reply(grocery):
    return {"menu": MENU, "grocery_list": grocery, "nutrition": NUTRITION}


# ---------- costing (pure Python) ----------


def test_costing_uses_family_prices_merges_and_flags_unpriced():
    prices = [
        Price(item="Rice", unit="kg", price=Decimal("1500")),
        Price(item="Palm oil", unit="litre", price=Decimal("2200.50")),
        Price(item="Tomatoes", unit="kg", price=None),
    ]
    lines = [
        _AIGroceryLine(item="rice", unit="KG", quantity=Decimal("3")),
        _AIGroceryLine(item="Rice ", unit="kg", quantity=Decimal("2")),  # duplicate, merged
        _AIGroceryLine(item="Palm oil", unit="litre", quantity=Decimal("1.333")),  # rounds to 1.33
        _AIGroceryLine(item="Tomatoes", unit="kg", quantity=Decimal("2")),  # listed but unpriced
        _AIGroceryLine(item="Maggi  cubes", unit="pack", quantity=Decimal("1")),  # not on list
    ]
    items = {i.item: i for i in cost_plan_items(lines, prices)}
    assert items["Rice"].quantity == Decimal("5.00") and items["Rice"].subtotal == Decimal("7500.00")
    assert items["Palm oil"].quantity == Decimal("1.33") and items["Palm oil"].subtotal == Decimal("2926.67")
    assert items["Tomatoes"].unit_price is None and items["Tomatoes"].subtotal == 0
    assert items["Maggi cubes"].unit_price is None
    assert len(items) == 4


# ---------- API ----------


def test_admin_creates_plan_under_budget(client, gemma, family):
    gemma.queue(
        plan_reply([
            {"item": "Rice", "unit": "kg", "quantity": 5},
            {"item": "beans", "unit": "kg", "quantity": 3},
            {"item": "Eggs", "unit": "crate", "quantity": 1},
            {"item": "Tomatoes", "unit": "kg", "quantity": 2},
        ])
    )
    r = client.post("/plans", headers=family["mum"], json={"budget": 30000, "notes": "no pork", "pantry": "palm oil"})
    assert r.status_code == 201, r.text
    plan = r.json()
    # 5*1500 + 3*1800 + 1*5500 = 18,400 (tomatoes unpriced, excluded)
    assert plan["total_cost"] == "18400.00"
    assert plan["remaining"] == "11600.00" and plan["over_budget"] is False
    assert plan["unpriced_items"] == ["Tomatoes"]
    assert plan["swaps"] == [] and plan["status"] == "draft"
    assert len(plan["menu"]) == 7
    assert plan["nutrition"]["score"] == {"protein": 7, "carbs": 9, "vegetables": 5, "fruit": 3}
    assert "not medical advice" in plan["disclaimer"]
    assert len(gemma.prompts) == 1  # no swaps call when under budget

    prompt = gemma.prompts[0]
    for expected in ("Rice | kg | NGN 1500.00", "Tomatoes | kg | price unknown", "no pork", "palm oil",
                     "1 adult, 1 teen", "dislikes/avoids: okra", "NGN 30000"):
        assert expected in prompt, expected


def test_over_budget_plan_gets_swaps(client, gemma, family):
    gemma.queue(
        plan_reply([{"item": "Chicken", "unit": "kg", "quantity": 4}, {"item": "Rice", "unit": "kg", "quantity": 5}]),
        "```json\n" + '{"swaps": [{"from_item": "Chicken", "to_item": "Fish (frozen)", "reason": "Cheaper protein"}]}' + "\n```",
    )
    plan = client.post("/plans", headers=family["mum"], json={"budget": 20000}).json()
    assert plan["total_cost"] == "31500.00"
    assert plan["over_budget"] is True and plan["remaining"] == "-11500.00"
    assert plan["swaps"] == [{"from_item": "Chicken", "to_item": "Fish (frozen)", "reason": "Cheaper protein"}]
    assert "NGN 11500.00 over" in gemma.prompts[1]


def test_swaps_failure_does_not_lose_the_plan(client, gemma, family):
    gemma.queue(plan_reply([{"item": "Chicken", "unit": "kg", "quantity": 10}]), "nope", "still nope")
    r = client.post("/plans", headers=family["mum"], json={"budget": 1000})
    assert r.status_code == 201 and r.json()["swaps"] == []


def test_broken_json_is_retried(client, gemma, family):
    gemma.queue('{"menu": [', plan_reply([{"item": "Rice", "unit": "kg", "quantity": 1}]))
    assert client.post("/plans", headers=family["mum"], json={"budget": 5000}).status_code == 201


def test_wrong_shape_twice_is_502_and_nothing_saved(client, gemma, family):
    short_menu = {"menu": MENU[:3], "grocery_list": [{"item": "Rice", "unit": "kg", "quantity": 1}], "nutrition": NUTRITION}
    gemma.queue(short_menu, short_menu)
    r = client.post("/plans", headers=family["mum"], json={"budget": 5000})
    assert r.status_code == 502
    assert client.get("/plans/latest", headers=family["mum"]).status_code == 404


def test_member_cannot_create_plan(client, gemma, family):
    assert client.post("/plans", headers=family["tunde"], json={"budget": 5000}).status_code == 403


def test_invalid_budget(client, gemma, family):
    for bad in (0, -1, "12.345"):
        assert client.post("/plans", headers=family["mum"], json={"budget": bad}).status_code == 422


def test_latest_get_regenerate_approve(client, gemma, family):
    mum, tunde = family["mum"], family["tunde"]
    assert client.get("/plans/latest", headers=tunde).status_code == 404

    gemma.queue(plan_reply([{"item": "Rice", "unit": "kg", "quantity": 2}]))
    first = client.post("/plans", headers=mum, json={"budget": 10000, "notes": "no pork"}).json()

    latest = client.get("/plans/latest", headers=tunde).json()
    assert latest["id"] == first["id"] and latest["total_cost"] == "3000.00"
    assert client.get(f"/plans/{first['id']}", headers=tunde).json()["id"] == first["id"]

    # Regenerate without a body keeps the inputs
    gemma.queue(plan_reply([{"item": "Beans", "unit": "kg", "quantity": 2}]))
    regen = client.post(f"/plans/{first['id']}/regenerate", headers=mum).json()
    assert regen["id"] == first["id"] and regen["notes"] == "no pork"
    assert [i["item"] for i in regen["items"]] == ["Beans"] and regen["total_cost"] == "3600.00"

    # Regenerate with new inputs
    gemma.queue(plan_reply([{"item": "Eggs", "unit": "crate", "quantity": 1}]))
    regen = client.post(f"/plans/{first['id']}/regenerate", headers=mum, json={"budget": 8000}).json()
    assert regen["budget"] == "8000.00" and regen["notes"] is None and regen["total_cost"] == "5500.00"

    assert client.post(f"/plans/{first['id']}/approve", headers=tunde).status_code == 403
    approved = client.post(f"/plans/{first['id']}/approve", headers=mum).json()
    assert approved["status"] == "approved"
    assert client.post(f"/plans/{first['id']}/regenerate", headers=mum).status_code == 400


def test_other_family_cannot_see_plan(client, gemma, family):
    from tests.conftest import signup

    gemma.queue(plan_reply([{"item": "Rice", "unit": "kg", "quantity": 1}]))
    plan_id = client.post("/plans", headers=family["mum"], json={"budget": 5000}).json()["id"]
    other, _ = signup(client, "Other", family_name="Okafor")
    assert client.get(f"/plans/{plan_id}", headers=other).status_code == 404
    # Other is an admin, but of a different family
    assert client.post(f"/plans/{plan_id}/approve", headers=other).status_code == 404
    assert client.post(f"/plans/{plan_id}/regenerate", headers=other).status_code == 404


def test_nutrition_analysis(client, gemma, family):
    gemma.queue({
        "priorities": ["Teen needs more protein and iron", "  "],
        "focus_foods": ["Eggs", "Beans", "Fish"],
        "tips": ["Add fruit to breakfast"],
    })
    r = client.post("/nutrition/analyze", headers=family["tunde"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["priorities"] == ["Teen needs more protein and iron"]
    assert body["focus_foods"] == ["Eggs", "Beans", "Fish"]
    assert "not medical advice" in body["disclaimer"]
    assert "1 adult, 1 teen" in gemma.prompts[0] and "Eggs | crate | NGN 5500.00" in gemma.prompts[0]


def test_missing_api_key_returns_503(client, family, monkeypatch):
    from app import ai

    monkeypatch.setattr(ai, "_client", None)
    monkeypatch.setattr(ai.get_settings(), "gemini_api_key", "")
    r = client.post("/plans", headers=family["mum"], json={"budget": 5000})
    assert r.status_code == 503 and "GEMINI_API_KEY" in r.json()["detail"]
