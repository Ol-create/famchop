from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import DB, AdminUser, CurrentUser
from app.models import Plan, PlanStatus
from app.planner import fill_plan
from app.routers.ai_errors import ai_http_errors
from app.schemas import MenuDay, PlanItemOut, PlanNutrition, PlanOut, PlanRequest, Swap

router = APIRouter(prefix="/plans", tags=["plans"])


def plan_out(plan: Plan) -> PlanOut:
    return PlanOut(
        id=plan.id,
        status=plan.status,
        budget=plan.budget,
        total_cost=plan.total_cost,
        remaining=plan.budget - plan.total_cost,
        over_budget=plan.total_cost > plan.budget,
        unpriced_items=[i.item for i in plan.items if i.unit_price is None],
        notes=plan.notes,
        pantry=plan.pantry,
        menu=[MenuDay.model_validate(d) for d in plan.menu_json or []],
        nutrition=PlanNutrition.model_validate(plan.nutrition_json) if plan.nutrition_json else None,
        swaps=[Swap.model_validate(s) for s in plan.swaps_json or []],
        items=[PlanItemOut.model_validate(i) for i in plan.items],
        created_at=plan.created_at,
    )


def _get_family_plan(db: DB, plan_id: int, family_id: int) -> Plan:
    plan = db.get(Plan, plan_id)
    if plan is None or plan.family_id != family_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


@router.post("", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(body: PlanRequest, admin: AdminUser, db: DB) -> PlanOut:
    plan = Plan(
        family_id=admin.family_id,
        created_by=admin.id,
        budget=body.budget,
        notes=body.notes,
        pantry=body.pantry,
    )
    with ai_http_errors():
        fill_plan(db, plan)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan_out(plan)


@router.get("/latest", response_model=PlanOut)
def latest_plan(user: CurrentUser, db: DB) -> PlanOut:
    plan = db.scalar(
        select(Plan).where(Plan.family_id == user.family_id).order_by(Plan.created_at.desc(), Plan.id.desc()).limit(1)
    )
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No plan yet")
    return plan_out(plan)


@router.get("/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: int, user: CurrentUser, db: DB) -> PlanOut:
    return plan_out(_get_family_plan(db, plan_id, user.family_id))


@router.post("/{plan_id}/regenerate", response_model=PlanOut)
def regenerate_plan(plan_id: int, admin: AdminUser, db: DB, body: PlanRequest | None = None) -> PlanOut:
    """Re-run the planner on a draft. Pass a body to change the budget, notes or pantry first."""
    plan = _get_family_plan(db, plan_id, admin.family_id)
    if plan.status != PlanStatus.draft:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only draft plans can be regenerated")
    if body is not None:
        plan.budget, plan.notes, plan.pantry = body.budget, body.notes, body.pantry
    with ai_http_errors():
        fill_plan(db, plan)
    db.commit()
    db.refresh(plan)
    return plan_out(plan)


@router.post("/{plan_id}/approve", response_model=PlanOut)
def approve_plan(plan_id: int, admin: AdminUser, db: DB) -> PlanOut:
    plan = _get_family_plan(db, plan_id, admin.family_id)
    plan.status = PlanStatus.approved
    db.commit()
    db.refresh(plan)
    return plan_out(plan)
