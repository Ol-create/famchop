"""Create (or reset) the demo family used in the FamChop pitch.

Run from backend/:
    python -m scripts.seed_demo              # family, prices, ₦40k wallet; plan the week live in the demo
    python -m scripts.seed_demo --with-plan  # also generate a draft plan with Gemma now (~40s), as a backup

It goes through the real API (in-process), so it exercises the same code as the app. Re-running deletes
only the previous demo family (found by the demo emails below) and starts fresh.

Demo logins (test data only, all share DEMO_PASSWORD):
    mum@adeyemi.example.com    admin  (creates the family)
    dad@adeyemi.example.com    admin
    tunde@adeyemi.example.com  member, teen  (does the shopping)
    ada@adeyemi.example.com    member, child, avoids beans and okra
"""

import argparse
import sys

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.main import app

DEMO_PASSWORD = "famchop-demo"
DOMAIN = "adeyemi.example.com"

MEMBERS = [
    # name, email user, age group, dislikes
    ("Mum", "mum", "adult", None),
    ("Dad", "dad", "adult", "no pork"),
    ("Tunde", "tunde", "teen", None),
    ("Ada", "ada", "child", "beans, okra"),
]

# Rough Lagos/Ibadan market prices; edit them on the Prices page during the demo
PRICES = [
    ("Rice", "kg", 1500),
    ("Beans", "kg", 1800),
    ("Garri", "kg", 1000),
    ("Yam", "tuber", 3000),
    ("Plantain", "bunch", 4000),
    ("Bread", "loaf", 1500),
    ("Spaghetti", "pack", 1200),
    ("Eggs", "crate", 5500),
    ("Chicken", "kg", 6000),
    ("Fish (frozen)", "kg", 3500),
    ("Tomatoes", "kg", 2000),
    ("Onions", "kg", 1200),
    ("Pepper", "kg", 2500),
    ("Ugu (pumpkin leaves)", "bunch", 500),
    ("Palm oil", "litre", 2500),
    ("Vegetable oil", "litre", 3000),
    ("Bananas", "bunch", 1500),
    ("Oranges", "dozen", None),  # left blank on purpose to show "no price yet"
]


def _ok(r, what):
    if r.status_code >= 400:
        sys.exit(f"Failed to {what}: HTTP {r.status_code} {r.text}")
    return r.json()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--with-plan", action="store_true", help="also generate a draft meal plan with Gemma")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which has no ₦

    with engine.begin() as conn:
        removed = conn.execute(
            text("DELETE FROM families WHERE id IN (SELECT family_id FROM users WHERE email LIKE :p)"),
            {"p": f"%@{DOMAIN}"},
        ).rowcount
    if removed:
        print(f"Removed the previous demo family ({removed}).")

    with TestClient(app) as c:
        tokens: dict[str, dict] = {}
        code = None
        for name, user, age, dislikes in MEMBERS:
            body = {"name": name, "email": f"{user}@{DOMAIN}", "password": DEMO_PASSWORD, "age_group": age}
            body |= {"family_name": "Adeyemi Family"} if code is None else {"invite_code": code}
            res = _ok(c.post("/auth/signup", json=body), f"sign up {name}")
            tokens[name] = {"Authorization": f"Bearer {res['access_token']}", "id": res["user"]["id"]}
            if code is None:
                code = _ok(c.get("/family", headers=_auth(tokens[name])), "read family")["invite_code"]
            if dislikes:
                _ok(c.patch("/me/profile", headers=_auth(tokens[name]), json={"dislikes": dislikes}), f"set {name}'s dislikes")

        mum = _auth(tokens["Mum"])
        _ok(c.patch(f"/family/members/{tokens['Dad']['id']}", headers=mum, json={"role": "admin"}), "make Dad an admin")
        _ok(
            c.put("/prices", headers=mum, json={"items": [{"item": i, "unit": u, "price": p} for i, u, p in PRICES]}),
            "save prices",
        )
        _ok(c.post("/wallet/fund", headers=mum, json={"amount": 40000, "note": "This week's food money"}), "fund wallet")

        plan_note = "none yet (generate it live in the demo)"
        if args.with_plan:
            print("Asking Gemma 4 for a meal plan (about 30-60s)...")
            plan = _ok(
                c.post("/plans", headers=mum, json={"budget": 35000, "pantry": "half bag of rice, palm oil"}),
                "generate a plan",
            )
            plan_note = f"draft, ₦{float(plan['total_cost']):,.0f} of ₦{float(plan['budget']):,.0f}"

    print(
        f"""
Demo family ready: Adeyemi Family  (invite code {code})
  Members : Mum (admin), Dad (admin, no pork), Tunde (teen), Ada (child, avoids beans and okra)
  Prices  : {len(PRICES)} items, Oranges left unpriced
  Wallet  : ₦40,000
  Plan    : {plan_note}
  Logins  : <name>@{DOMAIN}  /  password: {DEMO_PASSWORD}"""
    )


def _auth(token: dict) -> dict:
    return {"Authorization": token["Authorization"]}


if __name__ == "__main__":
    main()
