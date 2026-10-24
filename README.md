# 🍲 FamChop

**Feed your family well, within budget.**

FamChop plans a week of Nigerian home-cooked meals from the prices *your* market charges, turns it into a shopping list that fits your budget, and lets you send any family member to market with money from a shared family wallet. When they're back, it tallies the change and learns the real prices for next week.

> "Chop" is Nigerian slang for *eat*. FamChop = the whole family, eating well, together.

---

## The problem

Food is the biggest line in most Nigerian household budgets, and prices move every week. Parents juggle three questions at once:

1. **What do we cook this week** that the kids will actually eat and that's balanced?
2. **Can we afford it** at this week's market prices?
3. **Who goes to market,** with how much money, and where did the change go?

Generic meal apps don't know what garri costs at Oja Oba this week, and they don't help with the "here's ₦25,000, go to market" handoff that happens in real homes.

## What FamChop does

| | |
|---|---|
| 👨‍👩‍👧‍👦 **Family accounts** | One parent creates the family and shares an invite code (by WhatsApp). Everyone joins the same family. Up to 2 admins (Mum and Dad); everyone else is a member. |
| 🏷️ **Your own prices** | A shared price table, prefilled with common items (rice, beans, garri, yam, eggs, palm oil…). You type what you actually pay. |
| 🤖 **AI meal plan (Gemma 4)** | A 7-day breakfast/lunch/dinner menu of familiar Nigerian meals, balanced across protein, carbs, vegetables and fruit, respecting each member's dislikes and what's already in the kitchen. |
| 💰 **Budget you can trust** | The AI decides *what* to buy. **Python does all the maths** from your price list. If the list is over budget, Gemma trims it, and if it's still over, suggests cheaper swaps. |
| 🥗 **Nutrition check** | Age-aware priorities for the household ("the teen needs more protein; Ada avoids beans, so use fish and eggs") plus a weekly balance score. |
| 👛 **Family wallet** | Admins add money (simulated). Releasing money for a shopping trip, change coming back, and overspend reimbursements all show up in the history. |
| 🛒 **Market errands** | An admin assigns the approved list to a member. On their phone they tick items off and type what they actually paid. Finishing returns the change to the wallet and **feeds real prices back** into the price list. |

## How it works

```
 Next.js (React)  ──JSON/JWT──▶  FastAPI  ──SQLAlchemy──▶  PostgreSQL
   frontend/                     backend/        │
                                                 └──▶  Gemma 4 (gemma-4-26b-a4b-it) via the Gemini API
```

**The plan pipeline** (`backend/app/planner.py`):

1. Build a prompt from the family (ages, dislikes), the budget, pantry and preferences, and the family's price list.
2. Gemma returns JSON: a budget split, a grocery list (with its own cost estimates, which keep it budget-aware), the 7-day menu, and a nutrition score.
3. **Python prices every line** from the family's list (`quantity × price`), merges duplicates, and flags items with no price instead of guessing.
4. **Over budget?** One revise pass: Gemma may only *reduce* quantities or *remove* lines. Python enforces that (no new items, no increases) and keeps the result only if it's cheaper.
5. **Still over?** Gemma suggests up to 5 cheaper swaps (chicken → fish, vegetable oil → palm oil…).

### How we use Gemma 4

- **Model:** `gemma-4-26b-a4b-it` through the Gemini API (`google-genai` SDK). Every model call goes through one function, `ask_ai()` in `backend/app/ai.py`.
- **Thinking level `MINIMAL`:** by default Gemma 4 produced about 6,000 hidden "thinking" tokens and took about 2.5 minutes per plan. `MINIMAL` brings that to about 30–40 seconds with JSON of the same quality.
- **Structured output without JSON mode:** `ask_json()` strips code fences and extra text, validates the shape with Pydantic, and retries once with the validation error fed back to the model.
- **Resilience:** replies are streamed so long answers don't time out. Google 5xx errors, 429 rate limits and network drops are retried with backoff.
- **Never trusted with money:** the model's cost estimates are ignored. Every naira shown comes from the family's own prices.

Results on live Gemma 4 for a family of 4: plans for ₦12k, ₦15k, ₦18k, ₦30k, ₦32k, ₦35k, ₦45k and ₦60k all came in at or under budget.

## Running it locally

**You need:** Python 3.12+, Node 20+, PostgreSQL 16 (a local install; no Docker needed), and a free Gemini API key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

### 1. Database

Create a role and database (you'll be asked for your `postgres` password). On Windows, `psql` is in `C:\Program Files\PostgreSQL\16\bin\` if it isn't on your PATH.

```bash
psql -U postgres -h localhost -c "CREATE ROLE famchop LOGIN PASSWORD 'famchop';" -c "CREATE DATABASE famchop OWNER famchop;"
```

### 2. Backend (FastAPI)

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # macOS/Linux: .venv/bin/python
cp .env.example .env        # then set GEMINI_API_KEY and a long random JWT_SECRET
.venv/Scripts/alembic upgrade head
.venv/Scripts/python -m scripts.smoke_gemma                    # checks the Gemma connection
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs. Click **Authorize** and paste an `access_token` to try the protected routes.

### 3. Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000.

### 4. Demo data (optional)

```bash
cd backend
.venv/Scripts/python -m scripts.seed_demo              # Adeyemi Family, prices, ₦40k wallet
.venv/Scripts/python -m scripts.seed_demo --with-plan  # also pre-generates a draft plan with Gemma
```

Logins are `mum@`, `dad@`, `tunde@` or `ada@adeyemi.example.com`, all with password `famchop-demo` (test data only). Re-running the script resets just that family.

### Environment variables (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://famchop:famchop@localhost:5432/famchop` | Postgres connection |
| `JWT_SECRET` | `dev-secret-change-me` | Signs login tokens. **Set a long random value** for anything beyond local dev. |
| `JWT_EXPIRE_MINUTES` | `10080` (7 days) | Login lifetime |
| `GEMINI_API_KEY` | none, **must be set** | Gemini API key |
| `GEMMA_MODEL` | `gemma-4-26b-a4b-it` | Model ID |
| `GEMMA_THINKING_LEVEL` | `MINIMAL` | Leave empty to let Gemma think at full length (much slower) |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | Allowed by CORS |

### Tests

```bash
cd backend
.venv/Scripts/python -m pytest -q
```

There are 42 tests covering auth and roles, prices, the wallet, plan costing, the revise and swap passes, JSON repair and retries, and errand reconciliation. Gemma is replaced with scripted replies, so the tests are fast and need no API key. They use the local database and delete everything they create.

## 2-minute demo script

1. **Mum signs in** (`mum@adeyemi.example.com`). The dashboard shows the family, the invite code with a WhatsApp share button, and a ₦40,000 wallet.
2. **Prices:** change Fish to ₦3,800 and save. "These are *my* market's prices."
3. **Meal plan:** tap *Analyze our needs* to get age-aware priorities. In our runs it caught that Ada avoids beans and suggested fish and eggs. Set the budget to ₦35,000 and the pantry to "half bag of rice, palm oil", then tap *Plan my week*.
   *While it thinks (about 30–40s):* "Gemma picks the meals. Python does every naira."
4. **Show the result:** the green budget bar, a 7-day menu with no beans for Ada, rice and palm oil skipped because they're in the pantry, the nutrition bars, and the unpriced Oranges flagged instead of guessed. **Approve**, then **Send someone to market**: Tunde, Oja Oba, ₦35,000.
5. **Sign in as Tunde** on a phone. The banner says "You have shopping to do". Tick items, then type ₦8,000 for fish because it cost more today. Tap **Finish shopping**.
6. The **result** shows released, spent and change returned. Show the **wallet**: change is back in it. Show **prices**: fish updated to Tunde's real price, ready for next week's plan.

> Backup: run `seed_demo --with-plan` before presenting so a plan already exists if the network is slow.

## Responsible design

- **Money is simulated.** No real payments are made. Real payments (Paystack/Flutterwave) would need proper licensing and security, so it's on the roadmap, not in the demo.
- **Not medical advice.** Nutrition output is general guidance and every plan carries a disclaimer. Medical diets are out of scope.
- **Family data is isolated.** Every query is scoped to the signed-in user's family, and the tests check that another family can't see or change it.

## What's next

- Real wallet top-ups with Paystack / Flutterwave
- WhatsApp / SMS notifications ("Tunde finished shopping, ₦3,300 change")
- Community price board: "Rice at Oja Oba this week: ₦X", crowd-sourced from completed errands
- Share and copy budget-friendly weekly plans ("A week for 6 under ₦30k")
- Plan history, swap a single meal, cancel or split an errand
- Detailed health profiles (with professional guidance)

## Project structure

```
backend/
  app/
    main.py            FastAPI app and routers
    models.py          SQLAlchemy models (families, users, prices, wallet, plans, errands)
    ai.py              Gemma client: streaming, retries, JSON extraction
    planner.py         Prompts, costing, the revise-to-budget pass, swaps
    routers/           auth, me, family, prices, wallet, nutrition, plans, errands
  alembic/             Database migrations
  scripts/             smoke_gemma.py, seed_demo.py
  tests/               pytest suite
frontend/
  src/app/(auth)/      Sign in, sign up
  src/app/(app)/       Dashboard, plan, errands, prices, wallet, family
  src/components/      UI kit, budget bar, AI progress, assign-errand modal
  src/lib/             API client, React Query hooks, types, formatting
```

Built with Next.js 14, FastAPI, PostgreSQL and Gemma 4.
