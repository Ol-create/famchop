from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import DB
from app.models import Family, Role, User
from app.schemas import AuthResponse, LoginRequest, SignupRequest, UserOut
from app.security import create_access_token, generate_invite_code, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


def _unique_invite_code(db: DB, family_name: str) -> str:
    for _ in range(20):
        code = generate_invite_code(family_name)
        if db.scalar(select(Family.id).where(Family.invite_code == code)) is None:
            return code
    raise HTTPException(status_code=500, detail="Could not generate an invite code, please retry")


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: DB) -> AuthResponse:
    if db.scalar(select(User.id).where(User.email == body.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    if body.invite_code:
        family = db.scalar(select(Family).where(Family.invite_code == body.invite_code))
        if family is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite code not found")
        role = Role.member
    else:
        family = Family(name=body.family_name, invite_code=_unique_invite_code(db, body.family_name))
        db.add(family)
        role = Role.admin  # whoever creates the family runs it

    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        family=family,
        role=role,
        age_group=body.age_group,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race on email or invite code uniqueness
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    db.refresh(user)
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: DB) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong email or password")
    return _auth_response(user)
