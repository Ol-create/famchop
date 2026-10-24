from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.deps import DB, AdminUser, CurrentUser
from app.models import Family, Role, User
from app.schemas import FamilyOut, MemberOut, RoleUpdate

router = APIRouter(prefix="/family", tags=["family"])

MAX_ADMINS = 2


@router.get("", response_model=FamilyOut)
def get_family(user: CurrentUser, db: DB) -> FamilyOut:
    family = db.get(Family, user.family_id)
    members = db.scalars(
        select(User)
        .where(User.family_id == user.family_id)
        # Admins first, then in the order people joined
        .order_by(User.role != Role.admin, User.created_at)
    ).all()
    return FamilyOut(
        id=family.id,
        name=family.name,
        invite_code=family.invite_code,
        wallet_balance=family.wallet_balance,
        members=[MemberOut.model_validate(m) for m in members],
    )


@router.patch("/members/{member_id}", response_model=MemberOut)
def set_member_role(member_id: int, body: RoleUpdate, admin: AdminUser, db: DB) -> MemberOut:
    # Lock the family row so two admins changing roles at once can't exceed the limit
    db.scalar(select(Family).where(Family.id == admin.family_id).with_for_update())

    member = db.get(User, member_id)
    if member is None or member.family_id != admin.family_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in your family")

    if member.role != body.role:
        admin_count = db.scalar(
            select(func.count()).where(User.family_id == admin.family_id, User.role == Role.admin)
        )
        if body.role == Role.admin and admin_count >= MAX_ADMINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A family can have at most {MAX_ADMINS} admins",
            )
        if body.role == Role.member and admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A family needs at least one admin",
            )
        member.role = body.role

    db.commit()
    db.refresh(member)
    return MemberOut.model_validate(member)
