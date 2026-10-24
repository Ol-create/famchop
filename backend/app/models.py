"""Database tables. Everything a family shares (prices, wallet, plans, errands) hangs off family_id."""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# Naira amounts: up to 9,999,999,999.99
Money = Numeric(12, 2)
Quantity = Numeric(10, 2)


def _enum(cls: type[enum.Enum], name: str) -> Enum:
    # Store the lowercase value ("admin"), not the member name ("ADMIN")
    return Enum(cls, name=name, values_callable=lambda e: [m.value for m in e])


class Role(str, enum.Enum):
    admin = "admin"
    member = "member"


class AgeGroup(str, enum.Enum):
    child = "child"
    teen = "teen"
    adult = "adult"
    elderly = "elderly"


class TransactionType(str, enum.Enum):
    fund = "fund"  # admin adds money to the wallet
    release = "release"  # money handed to a member for an errand
    spend = "spend"  # what the member actually spent
    refund = "refund"  # change the member returns to the wallet


class PlanStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"


class ErrandStatus(str, enum.Enum):
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Family(TimestampMixin, Base):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    invite_code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    wallet_balance: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), server_default="0")

    members: Mapped[list["User"]] = relationship(back_populates="family")
    prices: Mapped[list["Price"]] = relationship(back_populates="family", cascade="all, delete-orphan")

    __table_args__ = (CheckConstraint("wallet_balance >= 0", name="wallet_balance_non_negative"),)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), index=True)
    role: Mapped[Role] = mapped_column(_enum(Role, "user_role"), default=Role.member)
    age_group: Mapped[AgeGroup] = mapped_column(_enum(AgeGroup, "age_group"), default=AgeGroup.adult)
    dislikes: Mapped[str | None] = mapped_column(Text)

    family: Mapped[Family] = relationship(back_populates="members")


class Price(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), index=True)
    item: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(40))
    price: Mapped[Decimal] = mapped_column(Money)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    family: Mapped[Family] = relationship(back_populates="prices")

    __table_args__ = (
        UniqueConstraint("family_id", "item", "unit", name="uq_price_family_item_unit"),
        CheckConstraint("price >= 0", name="price_non_negative"),
    )


class WalletTransaction(TimestampMixin, Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    errand_id: Mapped[int | None] = mapped_column(ForeignKey("errands.id", ondelete="SET NULL"))
    type: Mapped[TransactionType] = mapped_column(_enum(TransactionType, "transaction_type"))
    amount: Mapped[Decimal] = mapped_column(Money)
    note: Mapped[str | None] = mapped_column(String(255))

    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)


class Plan(TimestampMixin, Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    budget: Mapped[Decimal] = mapped_column(Money)
    status: Mapped[PlanStatus] = mapped_column(_enum(PlanStatus, "plan_status"), default=PlanStatus.draft)
    menu_json: Mapped[dict] = mapped_column(JSON, default=dict)
    nutrition_json: Mapped[dict | None] = mapped_column(JSON)
    swaps_json: Mapped[list | None] = mapped_column(JSON)
    total_cost: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))

    items: Mapped[list["PlanItem"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="PlanItem.id"
    )


class PlanItem(Base):
    __tablename__ = "plan_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    item: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(40))
    quantity: Mapped[Decimal] = mapped_column(Quantity)
    # Null when the family has no price for this item yet; the UI flags it
    unit_price: Mapped[Decimal | None] = mapped_column(Money)
    subtotal: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))

    plan: Mapped[Plan] = relationship(back_populates="items")


class Errand(TimestampMixin, Base):
    __tablename__ = "errands"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    assigned_to: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    market: Mapped[str | None] = mapped_column(String(120))
    released_amount: Mapped[Decimal] = mapped_column(Money)
    actual_spent: Mapped[Decimal | None] = mapped_column(Money)
    status: Mapped[ErrandStatus] = mapped_column(
        _enum(ErrandStatus, "errand_status"), default=ErrandStatus.assigned
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["ErrandItem"]] = relationship(
        back_populates="errand", cascade="all, delete-orphan", order_by="ErrandItem.id"
    )

    __table_args__ = (CheckConstraint("released_amount > 0", name="released_amount_positive"),)


class ErrandItem(Base):
    __tablename__ = "errand_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    errand_id: Mapped[int] = mapped_column(ForeignKey("errands.id", ondelete="CASCADE"), index=True)
    plan_item_id: Mapped[int] = mapped_column(ForeignKey("plan_items.id", ondelete="CASCADE"))
    bought: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Total paid for this line at the market (not per unit); null until bought
    actual_price: Mapped[Decimal | None] = mapped_column(Money)

    errand: Mapped[Errand] = relationship(back_populates="items")
    plan_item: Mapped[PlanItem] = relationship()

    __table_args__ = (UniqueConstraint("errand_id", "plan_item_id", name="uq_errand_plan_item"),)
