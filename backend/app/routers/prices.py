from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB, AdminUser, CurrentUser
from app.models import Price
from app.planner import reprice_open_plans
from app.schemas import PriceListUpdate, PriceOut

router = APIRouter(prefix="/prices", tags=["prices"])


def _family_prices(db: DB, family_id: int) -> list[Price]:
    return list(db.scalars(select(Price).where(Price.family_id == family_id).order_by(Price.id)))


@router.get("", response_model=list[PriceOut])
def list_prices(user: CurrentUser, db: DB) -> list[Price]:
    return _family_prices(db, user.family_id)


@router.put("", response_model=list[PriceOut])
def replace_prices(body: PriceListUpdate, admin: AdminUser, db: DB) -> list[Price]:
    """Save the whole table at once. Rows are matched by item + unit (case-insensitive),
    so unchanged rows keep their updated_at and the UI can show when a price last changed."""
    existing = {(p.item.lower(), p.unit.lower()): p for p in _family_prices(db, admin.family_id)}

    for row in body.items:
        price = existing.pop((row.item.lower(), row.unit.lower()), None)
        if price is None:
            db.add(Price(family_id=admin.family_id, item=row.item, unit=row.unit, price=row.price))
        else:
            price.item, price.unit, price.price = row.item, row.unit, row.price

    for removed in existing.values():
        db.delete(removed)

    db.flush()
    reprice_open_plans(db, admin.family_id)
    db.commit()
    return _family_prices(db, admin.family_id)
