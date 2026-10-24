from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import AgeGroup, ErrandStatus, PlanStatus, Role, TransactionType


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6)
    age_group: AgeGroup = AgeGroup.adult
    # Exactly one of these: create a new family, or join an existing one
    family_name: str | None = Field(default=None, max_length=120)
    invite_code: str | None = Field(default=None, max_length=12)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        return v

    @field_validator("family_name", "invite_code")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v is not None else None

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def bcrypt_limit(cls, v: str) -> str:
        if len(v.encode()) > 72:
            raise ValueError("Password must be at most 72 bytes")
        return v

    @model_validator(mode="after")
    def create_xor_join(self) -> "SignupRequest":
        if bool(self.family_name) == bool(self.invite_code):
            raise ValueError("Provide either family_name (to create a family) or invite_code (to join one)")
        if self.invite_code:
            self.invite_code = self.invite_code.upper()
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower()


# ---------- Users & family ----------


class UserOut(ORMModel):
    id: int
    name: str
    email: str
    role: Role
    age_group: AgeGroup
    dislikes: str | None
    family_id: int


class MemberOut(ORMModel):
    id: int
    name: str
    email: str
    role: Role
    age_group: AgeGroup
    dislikes: str | None


class FamilyOut(ORMModel):
    id: int
    name: str
    invite_code: str
    wallet_balance: Decimal
    members: list[MemberOut]


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    age_group: AgeGroup | None = None
    dislikes: str | None = Field(default=None, max_length=500)


class RoleUpdate(BaseModel):
    role: Role


# ---------- Prices ----------

MAX_MONEY = Decimal("9999999999.99")


class PriceIn(BaseModel):
    item: str = Field(min_length=1, max_length=120)
    unit: str = Field(min_length=1, max_length=40)
    price: Decimal | None = Field(default=None, ge=0, le=MAX_MONEY, decimal_places=2)

    @field_validator("item", "unit")
    @classmethod
    def strip_required(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Required")
        return v


class PriceListUpdate(BaseModel):
    items: list[PriceIn] = Field(max_length=200)

    @model_validator(mode="after")
    def no_duplicates(self) -> "PriceListUpdate":
        seen: set[tuple[str, str]] = set()
        for p in self.items:
            key = (p.item.lower(), p.unit.lower())
            if key in seen:
                raise ValueError(f"'{p.item}' per {p.unit} is listed twice")
            seen.add(key)
        return self


class PriceOut(ORMModel):
    id: int
    item: str
    unit: str
    price: Decimal | None
    updated_at: datetime


# ---------- Wallet ----------


class FundRequest(BaseModel):
    # Simulated money for the hackathon; cap a single top-up at ₦10m
    amount: Decimal = Field(gt=0, le=Decimal("10000000"), decimal_places=2)
    note: str | None = Field(default=None, max_length=255)


class TransactionOut(BaseModel):
    id: int
    type: TransactionType
    amount: Decimal
    note: str | None
    user_name: str | None
    errand_id: int | None
    created_at: datetime


class WalletOut(BaseModel):
    balance: Decimal
    transactions: list[TransactionOut]


# ---------- AI: nutrition & plans ----------

DISCLAIMER = (
    "General guidance only, not medical advice. For medical conditions or special diets, "
    "talk to a doctor or dietitian."
)


class NutritionAnalysis(BaseModel):
    priorities: list[str]
    focus_foods: list[str]
    tips: list[str]
    disclaimer: str = DISCLAIMER


class PlanRequest(BaseModel):
    budget: Decimal = Field(gt=0, le=MAX_MONEY, decimal_places=2)
    notes: str | None = Field(default=None, max_length=500)
    pantry: str | None = Field(default=None, max_length=500)

    @field_validator("notes", "pantry")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v is not None else None


class MenuDay(BaseModel):
    day: str
    breakfast: str
    lunch: str
    dinner: str


class NutritionScore(BaseModel):
    """0-10 per food group for the week."""

    protein: int = Field(ge=0, le=10)
    carbs: int = Field(ge=0, le=10)
    vegetables: int = Field(ge=0, le=10)
    fruit: int = Field(ge=0, le=10)


class PlanNutrition(BaseModel):
    score: NutritionScore
    note: str
    tips: list[str] = []


class Swap(BaseModel):
    from_item: str
    to_item: str
    reason: str


class PlanItemOut(ORMModel):
    id: int
    item: str
    unit: str
    quantity: Decimal
    unit_price: Decimal | None
    subtotal: Decimal


class PlanOut(BaseModel):
    id: int
    status: PlanStatus
    budget: Decimal
    total_cost: Decimal
    remaining: Decimal  # negative when over budget
    over_budget: bool
    unpriced_items: list[str]  # items the family has no price for, so they're not in total_cost
    notes: str | None
    pantry: str | None
    menu: list[MenuDay]
    nutrition: PlanNutrition | None
    swaps: list[Swap]
    items: list[PlanItemOut]
    created_at: datetime
    disclaimer: str = DISCLAIMER


# ---------- Errands ----------


class ErrandCreate(BaseModel):
    plan_id: int
    assigned_to: int
    # Cash handed over from the wallet; defaults to the plan's total cost
    released_amount: Decimal | None = Field(default=None, gt=0, le=MAX_MONEY, decimal_places=2)
    market: str | None = Field(default=None, max_length=120)

    @field_validator("market")
    @classmethod
    def strip_optional(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v is not None else None


class ErrandItemUpdate(BaseModel):
    bought: bool | None = None
    # What was actually paid for this whole line (not per unit). Null clears it.
    actual_price: Decimal | None = Field(default=None, ge=0, le=MAX_MONEY, decimal_places=2)


class PersonOut(BaseModel):
    id: int
    name: str


class ErrandItemOut(BaseModel):
    id: int
    item: str
    unit: str
    quantity: Decimal
    unit_price: Decimal | None
    planned_cost: Decimal
    bought: bool
    actual_price: Decimal | None


class ErrandOut(BaseModel):
    id: int
    plan_id: int
    status: ErrandStatus
    assigned_to: PersonOut
    assigned_by: PersonOut | None
    market: str | None
    released_amount: Decimal
    planned_total: Decimal
    bought_count: int
    item_count: int
    # Running total of actual prices so far; final once completed
    spent_so_far: Decimal
    actual_spent: Decimal | None
    # released - spent: positive = change returned to the wallet, negative = wallet reimbursed the shopper
    change: Decimal | None
    items: list[ErrandItemOut]
    created_at: datetime
    completed_at: datetime | None
