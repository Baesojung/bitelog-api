from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.meal import MealIngestRequest, MealLogResponse
from app.services.llm_service import analyze_meal_text
from app.models.meal import MealLog
from app.models.failed_log import FailedLog
import json

router = APIRouter()

@router.post("/ingest", response_model=MealLogResponse)
async def ingest_meal(request: MealIngestRequest, db: Session = Depends(get_db)):
    """
    Ingest natural language meal log, analyze with AI, and save to DB.
    """
    # 1. AI Analysis
    try:
        ai_result = analyze_meal_text(request.text, request.client_local_time)
    except Exception as e:
        # Save to FailedLog
        failed_log = FailedLog(
            user_id=1,
            raw_text=request.text,
            error_message=str(e)
        )
        db.add(failed_log)
        db.commit()
        
        # Return generic error or re-raise
        # For better UX, we might want to return a specific status code
        raise HTTPException(
            status_code=503, 
            detail=f"AI 분석 서버가 혼잡합니다. 잠시 후 다시 시도해주세요. (FailedLog saved)"
        )

    # 2. Convert to DB Model
    # Since items_json is a JSON column in DB but List[FoodItem] in Pydantic,
    # we need to serialize it to list of dicts.
    food_items_dict = [item.model_dump() for item in ai_result.food_items]
    
    db_log = MealLog(
        user_id=1, # Fixed for MVP
        raw_text=request.text,
        meal_type=ai_result.meal_type,
        eaten_at=request.client_local_time, # Using client time as eaten time for now
        items_json=food_items_dict,
        total_kcal=ai_result.total_kcal,
        confidence=ai_result.confidence
    )
    
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    
    # 3. Construct Response
    # Merge DB fields with the transient AI message
    response = MealLogResponse.model_validate(db_log)
    response.message = ai_result.message
    
    return response
