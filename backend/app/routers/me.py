from fastapi import APIRouter

from app.deps import DB, CurrentUser
from app.schemas import ProfileUpdate, UserOut

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=UserOut)
def get_me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/profile", response_model=UserOut)
def update_profile(body: ProfileUpdate, user: CurrentUser, db: DB) -> UserOut:
    changes = body.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is None:
        changes.pop("name")  # name can't be cleared
    if "age_group" in changes and changes["age_group"] is None:
        changes.pop("age_group")
    if "dislikes" in changes:
        changes["dislikes"] = (changes["dislikes"] or "").strip() or None
    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
