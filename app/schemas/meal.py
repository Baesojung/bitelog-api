from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

# Request Model
class MealIngestRequest(BaseModel):
    text: str
    client_local_time: datetime

# Internal Data Structure (Gemini Output)
class FoodItem(BaseModel):
    name: str
    qty: str = "1 serving"
    kcal: int = 0

class AIAnalysisResult(BaseModel):
    meal_type: str  # breakfast, lunch, dinner, snack
    food_items: List[FoodItem]
    total_kcal: int
    message: str # AI's comment
    confidence: float = 0.0

# Response Model (DB Model + Extra)
class MealLogResponse(BaseModel):
    id: int
    user_id: int
    raw_text: str
    meal_type: Optional[str] = None
    eaten_at: Optional[datetime] = None
    items_json: Optional[List[dict]] = None
    total_kcal: int = 0
    created_at: datetime
    message: Optional[str] = None # Include AI message in response

    class Config:
        from_attributes = True
