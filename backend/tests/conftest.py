"""Tests run against the local famchop database. Each test's families use @pytest.example.com
emails and are deleted afterwards, so real data is never touched."""

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import ai
from app.db import engine
from app.main import app

TEST_EMAIL_DOMAIN = "pytest.example.com"


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM families WHERE id IN (SELECT family_id FROM users WHERE email LIKE :pattern)"),
            {"pattern": f"%@{TEST_EMAIL_DOMAIN}"},
        )


class FakeGemma:
    """Stands in for ask_ai: returns queued replies in order and records every prompt."""

    def __init__(self):
        self.replies: list[str] = []
        self.prompts: list[str] = []

    def queue(self, *replies):
        self.replies += [r if isinstance(r, str) else json.dumps(r) for r in replies]

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.replies:
            raise AssertionError("FakeGemma got an unexpected call")
        return self.replies.pop(0)


@pytest.fixture
def gemma(monkeypatch):
    fake = FakeGemma()
    monkeypatch.setattr(ai, "ask_ai", fake)
    return fake


def signup(client, name, **extra):
    email = f"{name.lower()}-{uuid.uuid4().hex[:8]}@{TEST_EMAIL_DOMAIN}"
    r = client.post("/auth/signup", json={"name": name, "email": email, "password": "secret123", **extra})
    assert r.status_code == 201, r.text
    body = r.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]


@pytest.fixture
def family(client):
    """Mum (admin) + Tunde (teen member), with a few prices set."""
    mum, _ = signup(client, "Mum", family_name="Adeyemi")
    code = client.get("/family", headers=mum).json()["invite_code"]
    tunde, _ = signup(client, "Tunde", invite_code=code, age_group="teen")
    client.patch("/me/profile", headers=tunde, json={"dislikes": "okra"})
    prices = [
        {"item": "Rice", "unit": "kg", "price": "1500"},
        {"item": "Beans", "unit": "kg", "price": "1800"},
        {"item": "Eggs", "unit": "crate", "price": "5500"},
        {"item": "Chicken", "unit": "kg", "price": "6000"},
        {"item": "Fish (frozen)", "unit": "kg", "price": "3500"},
        {"item": "Palm oil", "unit": "litre", "price": "2200.50"},
        {"item": "Tomatoes", "unit": "kg", "price": None},
    ]
    assert client.put("/prices", headers=mum, json={"items": prices}).status_code == 200
    return {"mum": mum, "tunde": tunde}
