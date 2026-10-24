import pytest

from tests.conftest import signup
from tests.test_plans import plan_reply

# Rice 5kg = 7,500 | Eggs 1 crate = 5,500 | Palm oil 1L = 2,200.50 | Tomatoes 2kg = unpriced -> total 15,200.50
GROCERY = [
    {"item": "Rice", "unit": "kg", "quantity": 5},
    {"item": "Eggs", "unit": "crate", "quantity": 1},
    {"item": "Palm oil", "unit": "litre", "quantity": 1},
    {"item": "Tomatoes", "unit": "kg", "quantity": 2},
]


@pytest.fixture
def setup(client, gemma, family):
    """Family with ₦40k in the wallet and an approved ₦15,200.50 plan."""
    mum, tunde = family["mum"], family["tunde"]
    client.post("/wallet/fund", headers=mum, json={"amount": 40000})
    gemma.queue(plan_reply(GROCERY))
    plan = client.post("/plans", headers=mum, json={"budget": 20000}).json()
    assert plan["total_cost"] == "15200.50"
    client.post(f"/plans/{plan['id']}/approve", headers=mum)
    tunde_id = client.get("/me", headers=tunde).json()["id"]
    return {**family, "plan_id": plan["id"], "tunde_id": tunde_id}


def assign(client, s, **extra):
    return client.post("/errands", headers=s["mum"], json={"plan_id": s["plan_id"], "assigned_to": s["tunde_id"], **extra})


def items_by_name(errand):
    return {i["item"]: i for i in errand["items"]}


def balance(client, headers):
    return client.get("/wallet", headers=headers).json()["balance"]


# ---------- assigning ----------


def test_assign_releases_plan_total_from_wallet(client, setup):
    r = assign(client, setup, market="Oja Oba")
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["status"] == "assigned" and e["assigned_to"]["name"] == "Tunde" and e["assigned_by"]["name"] == "Mum"
    assert e["released_amount"] == "15200.50" and e["planned_total"] == "15200.50"
    assert (e["item_count"], e["bought_count"], e["spent_so_far"], e["change"]) == (4, 0, "0.00", None)

    wallet = client.get("/wallet", headers=setup["mum"]).json()
    assert wallet["balance"] == "24799.50"
    release = wallet["transactions"][0]
    assert (release["type"], release["amount"], release["errand_id"]) == ("release", "15200.50", e["id"])
    assert release["note"] == "Shopping money for Tunde at Oja Oba"


def test_assign_custom_amount(client, setup):
    assert assign(client, setup, released_amount=20000).json()["released_amount"] == "20000.00"
    assert balance(client, setup["mum"]) == "20000.00"


def test_assign_rules(client, gemma, setup):
    mum, tunde = setup["mum"], setup["tunde"]
    assert client.post("/errands", headers=tunde, json={"plan_id": setup["plan_id"], "assigned_to": setup["tunde_id"]}).status_code == 403
    assert assign(client, setup, released_amount=50000).json()["detail"].startswith("Wallet has ₦40,000.00")

    other, other_user = signup(client, "Other", family_name="Okafor")
    assert client.post("/errands", headers=mum, json={"plan_id": setup["plan_id"], "assigned_to": other_user["id"]}).status_code == 404
    assert client.post("/errands", headers=other, json={"plan_id": setup["plan_id"], "assigned_to": other_user["id"]}).status_code == 404

    gemma.queue(plan_reply(GROCERY))
    draft = client.post("/plans", headers=mum, json={"budget": 20000}).json()
    r = client.post("/errands", headers=mum, json={"plan_id": draft["id"], "assigned_to": setup["tunde_id"]})
    assert r.status_code == 400 and "Approve" in r.json()["detail"]

    assert assign(client, setup).status_code == 201
    assert assign(client, setup).status_code == 409
    assert balance(client, mum) == "24799.50"  # only released once


# ---------- shopping ----------


def test_shopper_ticks_items(client, setup):
    e = assign(client, setup).json()
    items = items_by_name(e)
    url = f"/errands/{e['id']}/items"

    assert client.patch(f"{url}/{items['Rice']['id']}", headers=setup["mum"], json={"bought": True}).status_code == 403
    assert client.patch(f"{url}/999999", headers=setup["tunde"], json={"bought": True}).status_code == 404

    # Entering a price ticks the item
    e = client.patch(f"{url}/{items['Rice']['id']}", headers=setup["tunde"], json={"actual_price": 8000}).json()
    assert e["status"] == "in_progress" and items_by_name(e)["Rice"]["bought"] is True
    # Ticking without a price counts the planned cost
    e = client.patch(f"{url}/{items['Eggs']['id']}", headers=setup["tunde"], json={"bought": True}).json()
    assert (e["bought_count"], e["spent_so_far"]) == (2, "13500.00")
    # Untick keeps the price but stops counting it
    e = client.patch(f"{url}/{items['Rice']['id']}", headers=setup["tunde"], json={"bought": False}).json()
    assert items_by_name(e)["Rice"]["actual_price"] == "8000.00" and e["spent_so_far"] == "5500.00"
    assert client.patch(f"{url}/{items['Rice']['id']}", headers=setup["tunde"], json={"actual_price": -1}).status_code == 422


def test_views(client, setup):
    e = assign(client, setup).json()
    assert [x["id"] for x in client.get("/errands/mine", headers=setup["tunde"]).json()] == [e["id"]]
    assert client.get("/errands/mine", headers=setup["mum"]).json() == []
    assert [x["id"] for x in client.get("/errands", headers=setup["tunde"]).json()] == [e["id"]]
    assert client.get(f"/errands/{e['id']}", headers=setup["mum"]).json()["id"] == e["id"]
    other, _ = signup(client, "Other", family_name="Okafor")
    assert client.get(f"/errands/{e['id']}", headers=other).status_code == 404
    assert client.get("/errands", headers=other).json() == []


# ---------- completing ----------


def test_complete_returns_change_and_updates_prices(client, setup):
    mum, tunde = setup["mum"], setup["tunde"]
    e = assign(client, setup, released_amount=20000).json()
    items = items_by_name(e)
    url = f"/errands/{e['id']}"
    client.patch(f"{url}/items/{items['Rice']['id']}", headers=tunde, json={"actual_price": 8000})
    client.patch(f"{url}/items/{items['Eggs']['id']}", headers=tunde, json={"bought": True})
    client.patch(f"{url}/items/{items['Tomatoes']['id']}", headers=tunde, json={"bought": True})

    # Tomatoes had no planned price, so Tunde must say what he paid
    r = client.post(f"{url}/complete", headers=tunde)
    assert r.status_code == 400 and r.json()["detail"] == "Enter what you paid for: Tomatoes"
    client.patch(f"{url}/items/{items['Tomatoes']['id']}", headers=tunde, json={"actual_price": 3000})

    r = client.post(f"{url}/complete", headers=tunde)
    assert r.status_code == 200, r.text
    done = r.json()
    # 8,000 rice + 5,500 eggs (planned) + 3,000 tomatoes; palm oil not bought
    assert (done["status"], done["actual_spent"], done["change"]) == ("completed", "16500.00", "3500.00")
    assert done["completed_at"] is not None

    wallet = client.get("/wallet", headers=mum).json()
    assert wallet["balance"] == "23500.00"  # 40,000 - 20,000 + 3,500
    refund = wallet["transactions"][0]
    assert (refund["type"], refund["amount"], refund["note"]) == ("refund", "3500.00", "Change returned by Tunde")

    prices = {p["item"]: p["price"] for p in client.get("/prices", headers=mum).json()}
    assert prices["Rice"] == "1600.00"  # 8,000 / 5kg
    assert prices["Tomatoes"] == "1500.00"  # was unpriced; 3,000 / 2kg
    assert prices["Eggs"] == "5500.00" and prices["Palm oil"] == "2200.50"  # no actual price entered / not bought

    assert client.post(f"{url}/complete", headers=tunde).status_code == 400
    assert client.patch(f"{url}/items/{items['Rice']['id']}", headers=tunde, json={"bought": False}).status_code == 400


def test_overspend_is_reimbursed_from_wallet(client, setup):
    e = assign(client, setup, released_amount=10000).json()
    rice = items_by_name(e)["Rice"]
    client.patch(f"/errands/{e['id']}/items/{rice['id']}", headers=setup["tunde"], json={"actual_price": 12500})
    done = client.post(f"/errands/{e['id']}/complete", headers=setup["tunde"]).json()
    assert (done["actual_spent"], done["change"]) == ("12500.00", "-2500.00")
    wallet = client.get("/wallet", headers=setup["mum"]).json()
    assert wallet["balance"] == "27500.00"  # 40,000 - 10,000 - 2,500
    assert (wallet["transactions"][0]["type"], wallet["transactions"][0]["amount"]) == ("spend", "2500.00")


def test_overspend_blocked_when_wallet_too_low(client, setup):
    e = assign(client, setup, released_amount=40000).json()  # empties the wallet
    rice = items_by_name(e)["Rice"]
    client.patch(f"/errands/{e['id']}/items/{rice['id']}", headers=setup["tunde"], json={"actual_price": 41000})
    r = client.post(f"/errands/{e['id']}/complete", headers=setup["tunde"])
    assert r.status_code == 400 and "fund the wallet first" in r.json()["detail"]
    assert client.get(f"/errands/{e['id']}", headers=setup["mum"]).json()["status"] == "in_progress"

    client.post("/wallet/fund", headers=setup["mum"], json={"amount": 1000})
    assert client.post(f"/errands/{e['id']}/complete", headers=setup["tunde"]).json()["change"] == "-1000.00"
    assert balance(client, setup["mum"]) == "0.00"


def test_who_can_complete(client, setup):
    e = assign(client, setup).json()
    code = client.get("/family", headers=setup["mum"]).json()["invite_code"]
    dad, _ = signup(client, "Dad", invite_code=code)
    assert client.post(f"/errands/{e['id']}/complete", headers=dad).status_code == 403
    # An admin can close it on the shopper's behalf; nothing bought means all cash comes back
    done = client.post(f"/errands/{e['id']}/complete", headers=setup["mum"]).json()
    assert (done["actual_spent"], done["change"]) == ("0.00", "15200.50")
    assert balance(client, setup["mum"]) == "40000.00"
