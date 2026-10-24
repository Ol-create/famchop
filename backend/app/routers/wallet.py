"""Family food wallet. The money is simulated for the hackathon: no real payments are made."""

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import DB, AdminUser, CurrentUser
from app.models import Family, TransactionType, User, WalletTransaction
from app.schemas import FundRequest, TransactionOut, WalletOut

router = APIRouter(prefix="/wallet", tags=["wallet"])

HISTORY_LIMIT = 50


def _wallet(db: Session, family_id: int) -> WalletOut:
    family = db.get(Family, family_id)
    rows = db.execute(
        select(WalletTransaction, User.name)
        .outerjoin(User, User.id == WalletTransaction.user_id)
        .where(WalletTransaction.family_id == family_id)
        .order_by(WalletTransaction.created_at.desc(), WalletTransaction.id.desc())
        .limit(HISTORY_LIMIT)
    ).all()
    return WalletOut(
        balance=family.wallet_balance,
        transactions=[
            TransactionOut(
                id=t.id,
                type=t.type,
                amount=t.amount,
                note=t.note,
                user_name=name,
                errand_id=t.errand_id,
                created_at=t.created_at,
            )
            for t, name in rows
        ],
    )


@router.get("", response_model=WalletOut)
def get_wallet(user: CurrentUser, db: DB) -> WalletOut:
    return _wallet(db, user.family_id)


@router.post("/fund", response_model=WalletOut, status_code=status.HTTP_201_CREATED)
def fund_wallet(body: FundRequest, admin: AdminUser, db: DB) -> WalletOut:
    # Lock the row so concurrent top-ups/releases can't overwrite each other's balance
    family = db.scalar(select(Family).where(Family.id == admin.family_id).with_for_update())
    family.wallet_balance += body.amount
    db.add(
        WalletTransaction(
            family_id=family.id,
            user_id=admin.id,
            type=TransactionType.fund,
            amount=body.amount,
            note=(body.note or "").strip() or None,
        )
    )
    db.commit()
    return _wallet(db, family.id)
