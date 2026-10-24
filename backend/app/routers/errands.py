"""Shopping errands: an admin hands an approved plan's list (and cash from the wallet) to a family member,
who ticks items off at the market. Completing the errand reconciles the wallet and feeds real prices back."""

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import DB, AdminUser, CurrentUser
from app.models import (
    Errand,
    ErrandItem,
    ErrandStatus,
    Family,
    Plan,
    PlanStatus,
    Price,
    Role,
    TransactionType,
    User,
    WalletTransaction,
)
from app.schemas import ErrandCreate, ErrandItemOut, ErrandItemUpdate, ErrandOut, PersonOut

router = APIRouter(prefix="/errands", tags=["errands"])

CENTS = Decimal("0.01")


def _naira(amount: Decimal) -> str:
    return f"₦{amount:,.2f}"


def _line_cost(ei: ErrandItem) -> Decimal:
    """What a bought line cost: the price paid if entered, otherwise what was planned."""
    return ei.actual_price if ei.actual_price is not None else ei.plan_item.subtotal


def _spent(errand: Errand) -> Decimal:
    return sum((_line_cost(ei) for ei in errand.items if ei.bought), Decimal("0.00"))


def _person(db: Session, user_id: int | None) -> PersonOut | None:
    user = db.get(User, user_id) if user_id is not None else None
    return PersonOut(id=user.id, name=user.name) if user else None


def errand_out(db: Session, errand: Errand) -> ErrandOut:
    completed = errand.status == ErrandStatus.completed
    return ErrandOut(
        id=errand.id,
        plan_id=errand.plan_id,
        status=errand.status,
        assigned_to=_person(db, errand.assigned_to),
        assigned_by=_person(db, errand.assigned_by),
        market=errand.market,
        released_amount=errand.released_amount,
        planned_total=sum((ei.plan_item.subtotal for ei in errand.items), Decimal("0.00")),
        bought_count=sum(1 for ei in errand.items if ei.bought),
        item_count=len(errand.items),
        spent_so_far=_spent(errand),
        actual_spent=errand.actual_spent,
        change=errand.released_amount - errand.actual_spent if completed else None,
        items=[
            ErrandItemOut(
                id=ei.id,
                item=ei.plan_item.item,
                unit=ei.plan_item.unit,
                quantity=ei.plan_item.quantity,
                unit_price=ei.plan_item.unit_price,
                planned_cost=ei.plan_item.subtotal,
                bought=ei.bought,
                actual_price=ei.actual_price,
            )
            for ei in errand.items
        ],
        created_at=errand.created_at,
        completed_at=errand.completed_at,
    )


def _lock_family(db: Session, family_id: int) -> Family:
    return db.scalar(select(Family).where(Family.id == family_id).with_for_update())


def _get_errand(db: Session, errand_id: int, family_id: int, lock: bool = False) -> Errand:
    query = select(Errand).where(Errand.id == errand_id, Errand.family_id == family_id)
    errand = db.scalar(query.with_for_update() if lock else query)
    if errand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Errand not found")
    return errand


# ---------- Admin: assign ----------


@router.post("", response_model=ErrandOut, status_code=status.HTTP_201_CREATED)
def assign_errand(body: ErrandCreate, admin: AdminUser, db: DB) -> ErrandOut:
    # The lock also serialises assignments, so the "already assigned" check below can't race
    family = _lock_family(db, admin.family_id)

    plan = db.get(Plan, body.plan_id)
    if plan is None or plan.family_id != family.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    if plan.status != PlanStatus.approved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approve the plan before assigning it")
    if db.scalar(select(Errand.id).where(Errand.plan_id == plan.id)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This plan has already been assigned")

    shopper = db.get(User, body.assigned_to)
    if shopper is None or shopper.family_id != family.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in your family")

    released = body.released_amount if body.released_amount is not None else plan.total_cost
    if released <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter how much money to release")
    if released > family.wallet_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Wallet has {_naira(family.wallet_balance)}, not enough to release {_naira(released)}",
        )

    errand = Errand(
        family_id=family.id,
        plan_id=plan.id,
        assigned_to=shopper.id,
        assigned_by=admin.id,
        market=body.market,
        released_amount=released,
        items=[ErrandItem(plan_item=pi) for pi in plan.items],
    )
    db.add(errand)
    db.flush()  # get errand.id for the transaction

    family.wallet_balance -= released
    db.add(
        WalletTransaction(
            family_id=family.id,
            user_id=shopper.id,
            errand_id=errand.id,
            type=TransactionType.release,
            amount=released,
            note=f"Shopping money for {shopper.name}" + (f" at {body.market}" if body.market else ""),
        )
    )
    db.commit()
    db.refresh(errand)
    return errand_out(db, errand)


# ---------- Views ----------


@router.get("", response_model=list[ErrandOut])
def list_errands(user: CurrentUser, db: DB) -> list[ErrandOut]:
    errands = db.scalars(
        select(Errand).where(Errand.family_id == user.family_id).order_by(Errand.created_at.desc(), Errand.id.desc())
    ).all()
    return [errand_out(db, e) for e in errands]


@router.get("/mine", response_model=list[ErrandOut])
def my_errands(user: CurrentUser, db: DB) -> list[ErrandOut]:
    errands = db.scalars(
        select(Errand)
        .where(Errand.assigned_to == user.id)
        # Open errands first, then newest
        .order_by(Errand.status == ErrandStatus.completed, Errand.created_at.desc(), Errand.id.desc())
    ).all()
    return [errand_out(db, e) for e in errands]


@router.get("/{errand_id}", response_model=ErrandOut)
def get_errand(errand_id: int, user: CurrentUser, db: DB) -> ErrandOut:
    return errand_out(db, _get_errand(db, errand_id, user.family_id))


# ---------- Shopper: tick items ----------


@router.patch("/{errand_id}/items/{item_id}", response_model=ErrandOut)
def update_item(errand_id: int, item_id: int, body: ErrandItemUpdate, user: CurrentUser, db: DB) -> ErrandOut:
    errand = _get_errand(db, errand_id, user.family_id, lock=True)
    if errand.assigned_to != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the person shopping can tick items")
    if errand.status == ErrandStatus.completed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This errand is already completed")

    item = next((ei for ei in errand.items if ei.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not on this list")

    if "bought" in body.model_fields_set and body.bought is not None:
        item.bought = body.bought
    if "actual_price" in body.model_fields_set:
        item.actual_price = body.actual_price
        if body.actual_price is not None:
            item.bought = True  # entering a price means it was bought
    errand.status = ErrandStatus.in_progress

    db.commit()
    db.refresh(errand)
    return errand_out(db, errand)


# ---------- Complete & reconcile ----------


def _feed_back_prices(db: Session, errand: Errand) -> None:
    """Use what was actually paid to update the family's price list, so the next plan is more accurate."""
    prices = {
        (p.item.lower(), p.unit.lower()): p
        for p in db.scalars(select(Price).where(Price.family_id == errand.family_id))
    }
    for ei in errand.items:
        pi = ei.plan_item
        if not ei.bought or ei.actual_price is None or pi.quantity <= 0:
            continue
        unit_price = (ei.actual_price / pi.quantity).quantize(CENTS, ROUND_HALF_UP)
        price = prices.get((pi.item.lower(), pi.unit.lower()))
        if price is None:
            db.add(Price(family_id=errand.family_id, item=pi.item, unit=pi.unit, price=unit_price))
        elif price.price != unit_price:
            price.price = unit_price


@router.post("/{errand_id}/complete", response_model=ErrandOut)
def complete_errand(errand_id: int, user: CurrentUser, db: DB) -> ErrandOut:
    family = _lock_family(db, user.family_id)
    errand = _get_errand(db, errand_id, family.id, lock=True)
    if errand.assigned_to != user.id and user.role != Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the shopper or an admin can complete this")
    if errand.status == ErrandStatus.completed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This errand is already completed")

    missing = [ei.plan_item.item for ei in errand.items if ei.bought and ei.actual_price is None and ei.plan_item.unit_price is None]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Enter what you paid for: {', '.join(missing)}",
        )

    spent = _spent(errand)
    change = errand.released_amount - spent
    shopper = db.get(User, errand.assigned_to)

    if change > 0:
        family.wallet_balance += change
        db.add(
            WalletTransaction(
                family_id=family.id, user_id=shopper.id, errand_id=errand.id,
                type=TransactionType.refund, amount=change, note=f"Change returned by {shopper.name}",
            )
        )
    elif change < 0:
        overspend = -change
        if overspend > family.wallet_balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"{shopper.name} spent {_naira(overspend)} more than released, but the wallet only has "
                    f"{_naira(family.wallet_balance)}. An admin needs to fund the wallet first."
                ),
            )
        family.wallet_balance -= overspend
        db.add(
            WalletTransaction(
                family_id=family.id, user_id=shopper.id, errand_id=errand.id,
                type=TransactionType.spend, amount=overspend, note=f"Reimbursed {shopper.name} for overspending",
            )
        )

    errand.actual_spent = spent
    errand.status = ErrandStatus.completed
    errand.completed_at = datetime.now(timezone.utc)
    _feed_back_prices(db, errand)

    db.commit()
    db.refresh(errand)
    return errand_out(db, errand)
