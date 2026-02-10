import google.generativeai as genai
from app.core.config import settings
from app.schemas.meal import AIAnalysisResult
import json
from datetime import datetime

# Initialize Gemini
genai.configure(api_key=settings.gemini_api_key)

def analyze_meal_text(text: str, current_time: datetime, meal_type_hint: str = None, persona: str = 'friendly') -> AIAnalysisResult:
    """
    Analyzes the meal text using Google Gemini and returns structured data.
    """
    hint_text = f"User explicitly suggests this is '{meal_type_hint}'. Prioritize this type." if meal_type_hint else ""

    # Persona Logic
    if persona == 'strict':
        persona_prompt = """
        You are a strict, professional nutritionist AI.
        Your tone should be formal, factual, and direct. NO emojis.
        Speak in Korean (formal/polite, e.g., '섭취하십시오.', '주의가 필요합니다.').
        Focus heavily on nutritional balance and potential health risks.
        """
    elif persona == 'humorous':
        persona_prompt = """
        You are a funny, witty AI friend.
        Your tone should be playful, maybe slightly sarcastic/teasing but friendly. Use funny emojis.
        Speak in Korean (casual, e.g., '또 먹었어? ㅋㅋ', '대박이네').
        Make jokes about their food choice if unhealthy, but praise good choices enthusiastically.
        """
    else: # friendly (default)
        persona_prompt = """
        You are a friendly and supportive AI friend who helps users track their meals. 
        Your tone should be casual, encouraging, and use emojis (😊, 😋, 💪) naturally.
        Speak in Korean (informal but polite, e.g., '맛있었겠다!', '잘했어!').
        Do not sound like a strict doctor.
        """

    system_prompt = f"""
    {persona_prompt}
    
    Current Time (User's Local Time): {current_time.strftime('%A, %Y-%m-%d %H:%M:%S')}
    (ISO: {current_time.isoformat()})
    {hint_text}

    Tasks:
    1. Identify the 'meal_type' (breakfast, lunch, dinner, snack). Use user hint if available.
    2. Extract a list of 'food_items'. 
       - Estimate Calories (kcal).
       - Estimate Macros (Carbs, Protein, Fat in grams).
       - IMPORTANT: The 'name' of each food item must be in KOREAN (e.g., "Apple" -> "사과").
    3. Calculate 'total_kcal' and total 'macros'.
    4. Write a short, friendly 'message' (in Korean) commenting on the meal.
       - Include specific, ACTIONABLE advice or tips based on the food (e.g., "Sodium is high, drink water!", "Great protein!", "Add veggies next time?").
       - Keep it supportive and casual (using emojis).
    5. Determine the 'eaten_at' time if the user specifies a date or time (e.g., "Yesterday", "Last Friday", "2024-05-05", "This morning").
       - If "Yesterday", assume {current_time.date()} minus 1 day, keeping similar time or defaulting to meal time.
       - Calculate the exact ISO 8601 datetime based on the 'Current Time'.
       - If no date is mentioned and user implies NOW, return null (it will default to current time).
    6. Suggest 'suggestions' (List[FoodItem]):
        - MANDATORY: Identify 2-4 common side dishes or drinks that usually accompany this meal but were NOT mentioned.
        - Examples: If 'Rice', suggest 'Kimchi', 'Soup'. If 'Burger', suggest 'Fries', 'Coke'. If just 'Sandwich', suggest 'Coffee'.
        - Even if meal is complete, suggest 'Water' or 'Dessert'.
        - Provide name, qty, estimated kcal, and macros for each suggestion.

    Output JSON format ONLY:
    {{
        "meal_type": "lunch",
        "food_items": [
            {{"name": "김치찌개", "qty": "1 bowl", "kcal": 450, "macros": {{"carbs": 20, "protein": 15, "fat": 10}}}},
            {{"name": "밥", "qty": "1 bowl", "kcal": 300, "macros": {{"carbs": 65, "protein": 5, "fat": 1}}}}
        ],
        "total_kcal": 750,
        "macros": {{"carbs": 85, "protein": 20, "fat": 11}},
        "eaten_at": "2024-05-02T12:30:00",
        "suggestions": [
            {{"name": "계란말이", "qty": "1 serving", "kcal": 150, "macros": {{"carbs": 2, "protein": 10, "fat": 10}}}},
            {{"name": "김", "qty": "1 pack", "kcal": 30, "macros": {{"carbs": 1, "protein": 1, "fat": 2}}}}
        ],
        "message": "김치찌개와 쌀밥은 훌륭한 조합이죠! 나트륨 조절을 위해 국물은 적게 드시는 게 좋아요."
    }}
    """

    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        
        chat = model.start_chat(history=[
            {"role": "user", "parts": [system_prompt]}
        ])
        
        response = chat.send_message(text, generation_config={"response_mime_type": "application/json"})
        

        response_text = response.text
        data = json.loads(response_text)
        
        # Suggestions Logic
        suggestions_data = data.get("suggestions", [])
        
        # Default Items to Consider: Rice, Kimchi, Gim (Seaweed)
        defaults = [
            {"name": "밥", "qty": "1 bowl", "kcal": 300, "macros": {"carbs": 65, "protein": 5, "fat": 1}},
            {"name": "김치", "qty": "1 small plate", "kcal": 30, "macros": {"carbs": 2, "protein": 1, "fat": 0}},
            {"name": "김", "qty": "1 pack", "kcal": 30, "macros": {"carbs": 1, "protein": 1, "fat": 2}}
        ]

        # Filter out if already in food_items or suggestions
        existing_names = {item.get("name") for item in data.get("food_items", [])}
        existing_suggestions = {item.get("name") for item in suggestions_data}
        
        # Also remove 'Water' if AI suggested it (user request)
        suggestions_data = [s for s in suggestions_data if s.get("name") != "물"]
        
        for default in defaults:
            if default["name"] not in existing_names and default["name"] not in existing_suggestions:
                # Add to suggestions if not present
                suggestions_data.append(default)

        # Cap suggestions to reasonable number? (Frontend wraps anyway)
        
        # Return as Pydantic model
        return AIAnalysisResult(
            meal_type=data.get("meal_type", "snack"),
            food_items=data.get("food_items", []),
            total_kcal=data.get("total_kcal", 0),
            macros=data.get("macros", None),
            suggestions=suggestions_data,
            message=data.get("message", "기록되었습니다."),
            confidence=0.9,
            eaten_at=datetime.fromisoformat(data["eaten_at"]) if data.get("eaten_at") else None
        )
        
    except Exception as e:
        print(f"Gemini API Error: {e}")
        # Fallback or re-raise
        raise e 
