import google.generativeai as genai
from app.core.config import settings
from app.schemas.meal import AIAnalysisResult, RecipeRecommendRequest, RecipeRecommendResponse
import json
from datetime import datetime
from typing import Optional

# Initialize Gemini
genai.configure(api_key=settings.gemini_api_key)


def _clean_json_text(response_text: str) -> str:
    text = (response_text or "").strip()
    if text.startswith("```json"):
        text = text[7:]
        if text.strip().endswith("```"):
            text = text.strip()[:-3]
    elif text.startswith("```"):
        text = text[3:]
        if text.strip().endswith("```"):
            text = text.strip()[:-3]
    return text.strip()


def _generate_content(prompt: str, preferred_model: str) -> str:
    """
    Support both modern google-generativeai (GenerativeModel) and legacy 0.1.0rc1 API.
    """
    if hasattr(genai, "GenerativeModel"):
        model = genai.GenerativeModel(preferred_model)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        return response.text

    # python3.8 fallback: legacy API does not provide GenerativeModel/chat interfaces
    response = genai.generate_text(
        model="models/text-bison-001",
        prompt=prompt,
        temperature=0.2,
        max_output_tokens=2048,
    )
    return getattr(response, "result", "")


def recommend_recipes(request: RecipeRecommendRequest) -> RecipeRecommendResponse:
    """
    Recommends recipes based on available ingredients and diet type using Gemini.
    """
    ingredients_str = ", ".join(request.ingredients)
    
    diet_guidelines = {
        "regular": "특별한 제한 없이 균형 잡힌 가정식",
        "diet": "1끼 400~500kcal 이하, 저지방 조리법 우선 (찜, 삶기, 그릴). 튀김/볶음 지양",
        "high_protein": "단백질 30g 이상 포함. 닭가슴살, 계란, 두부 등 고단백 재료 우선",
        "keto": "탄수화물 20g 이하, 고지방 식재료 활용. 밥/면/빵 제외",
        "low_carb": "탄수화물 50g 이하. 밥 대신 채소 위주",
        "vegan": "동물성 재료 완전 제외 (고기, 생선, 계란, 유제품 모두 제외)"
    }
    
    diet_guide = diet_guidelines.get(request.diet_type, diet_guidelines["regular"])
    
    roulette_instruction = ""
    if request.is_roulette:
        roulette_instruction = """
        ⚠️ ROULETTE MODE: 딱 1개의 요리만 recommendations에 추천하세요. 
        bonus_recommendations는 빈 배열로 반환하세요.
        가장 재미있고 의외의 조합을 추천해주세요!
        """

    prompt = f"""당신은 한국 가정요리 전문 셰프 AI입니다.

사용자가 보유한 재료: {ingredients_str}
식단 유형: {request.diet_type} ({diet_guide})
인원수: {request.servings}명
{roulette_instruction}

다음 규칙에 따라 식단을 추천하세요:

[recommendations - 메인 추천]
1. 보유 재료만으로 바로 만들 수 있는 요리를 추천 (소금, 후추, 간장, 식용유 등 기본 양념은 보유한 것으로 간주)
2. 2~5개 추천 (룰렛 모드가 아닌 경우)
3. 반드시 선택된 식단 유형의 영양 가이드라인을 준수

[bonus_recommendations - 서브 추천]
4. 보유 재료 + 1~2개 재료만 추가하면 만들 수 있는 요리 추천
5. 부족한 재료를 missing_ingredients에 명확히 표시 (available: false)
6. 최대 3개까지 추천

[공통 규칙]
7. 각 요리에 대해 필요 재료, 영양 정보(칼로리, 탄단지), 레시피 단계, 조리 팁을 제공
8. 한국인 기준 적절한 1인분 양 기준
9. 난이도는 easy, medium, hard 중 하나
10. 모든 텍스트는 한국어로 작성

Output JSON format ONLY:
{{
  "recommendations": [
    {{
      "name": "김치볶음밥",
      "description": "매콤하고 고소한 한 그릇 요리",
      "cooking_time_min": 15,
      "difficulty": "easy",
      "servings": 1,
      "ingredients": [
        {{"name": "김치", "qty": "1컵", "available": true}},
        {{"name": "계란", "qty": "1개", "available": true}},
        {{"name": "밥", "qty": "1공기", "available": true}}
      ],
      "nutrition": {{
        "total_kcal": 450,
        "macros": {{"carbs": 55, "protein": 15, "fat": 12}}
      }},
      "recipe_steps": [
        "김치를 잘게 썰어주세요.",
        "팬에 기름을 두르고 김치를 볶아주세요.",
        "밥을 넣고 잘 섞어 볶아주세요.",
        "계란 프라이를 올려 완성합니다."
      ],
      "tips": "김치 국물을 조금 넣으면 더 맛있어요!"
    }}
  ],
  "bonus_recommendations": [
    {{
      "name": "김치찌개",
      "description": "뜨끈하고 얼큰한 대표 찌개",
      "cooking_time_min": 20,
      "difficulty": "easy",
      "servings": 1,
      "ingredients": [
        {{"name": "김치", "qty": "1컵", "available": true}},
        {{"name": "두부", "qty": "1/2모", "available": false}}
      ],
      "nutrition": {{
        "total_kcal": 280,
        "macros": {{"carbs": 15, "protein": 18, "fat": 12}}
      }},
      "recipe_steps": ["김치를 썰어 끓입니다.", "두부를 넣고 간을 맞춥니다."],
      "tips": "참치캔을 넣으면 더 풍성해져요!",
      "missing_ingredients": [{{"name": "두부", "qty": "1/2모", "available": false}}]
    }}
  ],
  "message": "보유 재료로 바로 만들 수 있는 요리를 추천해요! 🍳"
}}
"""

    try:
        response_text = _generate_content(prompt, "gemini-2.0-flash")
        data = json.loads(_clean_json_text(response_text))
        
        return RecipeRecommendResponse(
            recommendations=data.get("recommendations", []),
            bonus_recommendations=data.get("bonus_recommendations", []),
            message=data.get("message", "추천 완료!")
        )
        
    except Exception as e:
        print(f"Gemini Recipe Recommend Error: {e}")
        raise e

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
        prompt = f"{system_prompt}\n\nUser Input:\n{text}"
        response_text = _generate_content(prompt, "gemini-2.5-flash")
        data = json.loads(_clean_json_text(response_text))
        
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
