from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

# Request Model
class MealIngestRequest(BaseModel):
    text: str
    client_local_time: datetime
    meal_type_hint: Optional[str] = None
    persona: Optional[str] = 'friendly' # friendly, strict, humorous

class DuplicateMealRequest(BaseModel):
    new_eaten_at: Optional[datetime] = None

# Internal Data Structure (Gemini Output)
class Macros(BaseModel):
    carbs: int # grams
    protein: int # grams
    fat: int # grams

class FoodItem(BaseModel):
    name: str
    qty: str = "1 serving"
    kcal: int = 0
    macros: Optional[Macros] = None

class AIAnalysisResult(BaseModel):
    meal_type: str  # breakfast, lunch, dinner, snack
    food_items: List[FoodItem]
    total_kcal: int
    macros: Optional[Macros] = None
    suggestions: List[FoodItem] = [] # Side dish suggestions
    message: str # AI's comment
    confidence: float = 0.0
    eaten_at: Optional[datetime] = None # Parsed date from user input (if any)

# Creation Models (Manual or Confirmed AI Result)
class MealItemCreate(BaseModel):
    name: str
    qty: str = "1 serving"
    kcal: int = 0
    macros: Optional[Macros] = None 

class MealLogCreate(BaseModel):
    user_id: int = 1 # MVP default
    raw_text: str
    meal_type: Optional[str] = None
    eaten_at: datetime
    items: List[MealItemCreate]
    total_kcal: int
    macros: Optional[Macros] = None
    ai_summary: Optional[str] = None
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
    macros: Optional[dict] = None # Using dict to be flexible with DB JSON
    created_at: datetime
    message: Optional[str] = None # Include AI message in response
    ai_summary: Optional[str] = None # Persisted AI summary
    success: bool = True
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

# ============================================================
# Recipe Recommendation Models (Meal Planner Feature)
# ============================================================

class RecipeRecommendRequest(BaseModel):
    ingredients: List[str]  # e.g. ["계란", "김치", "양파"]
    diet_type: str = "regular"  # regular, diet, high_protein, keto, low_carb, vegan
    meal_type: Optional[str] = None  # breakfast, lunch, dinner, snack
    servings: int = 1
    is_roulette: bool = False  # True if random roulette mode

class RecipeIngredient(BaseModel):
    name: str
    qty: str
    available: bool = True

class RecipeNutrition(BaseModel):
    total_kcal: int
    macros: Macros

class RecipeItem(BaseModel):
    name: str
    description: str
    cooking_time_min: int
    difficulty: str  # easy, medium, hard
    servings: int = 1
    ingredients: List[RecipeIngredient]
    nutrition: RecipeNutrition
    recipe_steps: List[str]
    tips: str = ""
    missing_ingredients: Optional[List[RecipeIngredient]] = None

class RecipeRecommendResponse(BaseModel):
    recommendations: List[RecipeItem]
    bonus_recommendations: List[RecipeItem] = []
    message: str
