from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.meal import MealIngestRequest, MealLogResponse, AIAnalysisResult, MealLogCreate, Macros
from app.services.llm_service import analyze_meal_text
from app.models.meal import MealLog
from app.models.meal_item import MealItem
from app.models.failed_log import FailedLog
import json
from datetime import datetime

router = APIRouter()

@router.post("/analyze", response_model=AIAnalysisResult)
async def analyze_meal_endpoint(request: MealIngestRequest, db: Session = Depends(get_db)):
    """
    Step 1: Analyze meal text without saving.
    """
    try:
        ai_result = analyze_meal_text(request.text, request.client_local_time, request.meal_type_hint, request.persona)
        # If eaten_at is not parsed by AI, use request client time
        if not ai_result.eaten_at:
            ai_result.eaten_at = request.client_local_time
        return ai_result
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/create", response_model=MealLogResponse)
async def create_meal_log(meal_data: MealLogCreate, db: Session = Depends(get_db)):
    """
    Step 2: Save confirmed meal log.
    """
    # Create MealItems
    meal_items = []
    items_json_list = []
    
    for item in meal_data.items:
        meal_item = MealItem(
            name=item.name,
            qty=item.qty,
            kcal=item.kcal,
            carbs=item.macros.carbs if item.macros else 0,
            protein=item.macros.protein if item.macros else 0,
            fat=item.macros.fat if item.macros else 0
        )
        meal_items.append(meal_item)
        
        # Determine macros dict safely
        item_macros = item.macros.model_dump() if item.macros else None
        
        items_json_list.append({
            "name": item.name,
            "qty": item.qty,
            "kcal": item.kcal,
            "macros": item_macros
        })

    macros_dict = meal_data.macros.model_dump() if meal_data.macros else None

    # Determine confidence (default if not provided, though schema has it)
    confidence = meal_data.confidence if meal_data.confidence else 0.9

    db_log = MealLog(
        user_id=meal_data.user_id,
        raw_text=meal_data.raw_text,
        meal_type=meal_data.meal_type,
        eaten_at=meal_data.eaten_at,
        items_json=items_json_list, # Still keeping for now
        total_kcal=meal_data.total_kcal,
        macros=macros_dict,
        ai_summary=meal_data.ai_summary,
        confidence=confidence,
        items=meal_items
    )
    
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    
    return db_log

@router.post("/ingest", response_model=MealLogResponse)
async def ingest_meal(request: MealIngestRequest, db: Session = Depends(get_db)):
    """
    Ingest natural language meal log, analyze with AI, and save to DB.
    """
    # 1. AI Analysis
    try:
        ai_result = analyze_meal_text(request.text, request.client_local_time, request.meal_type_hint)
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

    # 2. Check for empty food items
    if not ai_result.food_items:
        failed_log = FailedLog(
            user_id=1,
            raw_text=request.text,
            error_message="No food items identified by AI"
        )
        db.add(failed_log)
        db.commit()
        db.refresh(failed_log)
        
        return MealLogResponse(
            id=failed_log.id,
            user_id=failed_log.user_id,
            raw_text=failed_log.raw_text,
            created_at=failed_log.created_at,
            message="음식 정보를 찾을 수 없습니다.",
            success=False,
            error_message="No food items identified",
            total_kcal=0
        )

    # 3. Convert to DB Model
    # Since items_json is a JSON column in DB but List[FoodItem] in Pydantic,
    # we need to serialize it to list of dicts.
    food_items_dict = [item.model_dump() for item in ai_result.food_items]
    macros_dict = ai_result.macros.model_dump() if ai_result.macros else None
    
    # Create MealItems
    meal_items = []
    for item in ai_result.food_items:
        meal_item = MealItem(
            name=item.name,
            qty=item.qty,
            kcal=item.kcal,
            carbs=item.macros.carbs if item.macros else 0,
            protein=item.macros.protein if item.macros else 0,
            fat=item.macros.fat if item.macros else 0
        )
        meal_items.append(meal_item)

    db_log = MealLog(
        user_id=1, # Fixed for MVP
        raw_text=request.text,
        meal_type=ai_result.meal_type,
        eaten_at=ai_result.eaten_at or request.client_local_time, # Use AI parsed time or client time
        items_json=food_items_dict, # Keeping JSON for redundancy/ease
        total_kcal=ai_result.total_kcal,
        macros=macros_dict,
        ai_summary=ai_result.message,
        confidence=ai_result.confidence,
        items=meal_items # Relationship
    )
    
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    
    # 4. Construct Response
    # Merge DB fields with the transient AI message
    response = MealLogResponse.model_validate(db_log)
    response.message = ai_result.message
    
    return response

@router.get("/", response_model=list[MealLogResponse])
async def read_meals(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve meal logs.
    """
    meals = db.query(MealLog).order_by(MealLog.eaten_at.desc()).offset(skip).limit(limit).all()
    return meals

@router.delete("/{meal_id}")
async def delete_meal(meal_id: int, db: Session = Depends(get_db)):
    """
    Delete a meal log.
    """
    meal = db.query(MealLog).filter(MealLog.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    
    db.delete(meal)
    db.commit()
    return {"message": "Meal deleted"}

from app.schemas.meal import DuplicateMealRequest
@router.post("/{meal_id}/duplicate", response_model=MealLogResponse)
async def duplicate_meal(meal_id: int, request: DuplicateMealRequest, db: Session = Depends(get_db)):
    """
    Duplicate a meal log with optional new date.
    """
    original_meal = db.query(MealLog).filter(MealLog.id == meal_id).first()
    if not original_meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    
    new_meal = MealLog(
        user_id=original_meal.user_id,
        raw_text=original_meal.raw_text,
        meal_type=original_meal.meal_type,
        eaten_at=request.new_eaten_at or original_meal.eaten_at,
        items_json=original_meal.items_json,
        total_kcal=original_meal.total_kcal,
        ai_summary=original_meal.ai_summary,
        confidence=original_meal.confidence
    )
    
    db.add(new_meal)
    db.commit()
    db.refresh(new_meal)
    
    return new_meal
