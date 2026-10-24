from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.routers import auth, family, me, nutrition, plans, prices, wallet

app = FastAPI(title="FamChop API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(family.router)
app.include_router(prices.router)
app.include_router(wallet.router)
app.include_router(nutrition.router)
app.include_router(plans.router)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception as exc:  # surface the reason during setup instead of a bare 500
        database = f"error: {exc.__class__.__name__}"
    return {"status": "ok", "database": database}
