from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import AgeGroup, Role


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
