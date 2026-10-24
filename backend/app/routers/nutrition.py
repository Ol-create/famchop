from fastapi import APIRouter

from app.deps import DB, CurrentUser
from app.planner import analyze_nutrition
from app.routers.ai_errors import ai_http_errors
from app.schemas import NutritionAnalysis

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.post("/analyze", response_model=NutritionAnalysis)
def analyze(user: CurrentUser, db: DB) -> NutritionAnalysis:
    with ai_http_errors():
        return analyze_nutrition(db, user.family_id)
