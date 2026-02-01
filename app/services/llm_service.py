from openai import OpenAI
from app.core.config import settings
from app.schemas.meal import AIAnalysisResult
import json
from datetime import datetime

# Initialize OpenAI
client = OpenAI(api_key=settings.openai_api_key)

def analyze_meal_text(text: str, current_time: datetime) -> AIAnalysisResult:
    """
    Analyzes the meal text using OpenAI GPT and returns structured data.
    """
    system_prompt = f"""
    You are an expert nutritionist AI. Your goal is to extract food information from the user's input text.
    
    Current Time (User's Local Time): {current_time.isoformat()}

    Tasks:
    1. Identify the 'meal_type' based on the time or keywords (breakfast, lunch, dinner, snack).
    2. Extract a list of 'food_items'. For each item, estimate the Calories (kcal) roughly.
    3. Calculate 'total_kcal'.
    4. Write a short, friendly 'message' (in Korean) commenting on the meal (encouraging or informative).
    
    Output JSON format ONLY:
    {{
        "meal_type": "lunch",
        "food_items": [
            {{"name": "Kimchi Stew", "qty": "1 bowl", "kcal": 450}},
            {{"name": "Rice", "qty": "1 bowl", "kcal": 300}}
        ],
        "total_kcal": 750,
        "message": "김치찌개 맛있겠네요! 나트륨 섭취에 조금만 주의해주세요."
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106", # Supports JSON mode well
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        response_text = response.choices[0].message.content
        data = json.loads(response_text)
        
        # Return as Pydantic model
        return AIAnalysisResult(
            meal_type=data.get("meal_type", "snack"),
            food_items=data.get("food_items", []),
            total_kcal=data.get("total_kcal", 0),
            message=data.get("message", "기록되었습니다."),
            confidence=0.9
        )
        
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        raise e # Propagate error to endpoint
