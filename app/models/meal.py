from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, func, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class MealLog(Base):
    __tablename__ = "meal_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), default=1, index=True)
    user = relationship("User", back_populates="meals")
    
    # Original Input
    raw_text = Column(Text, nullable=False)
    
    # AI Parsed Data
    meal_type = Column(String(20)) # breakfast, lunch, dinner, snack
    eaten_at = Column(DateTime(timezone=True)) # Time of meal
    items_json = Column(JSON) # List of food items
    
    # Estimated Nutrition
    total_kcal = Column(Integer, default=0)
    macros = Column(JSON) # {protein: 10, carbs: 20, fat: 5}
    
    # Store AI's natural language summary/message separately
    ai_summary = Column(Text, nullable=True)
    
    # AI Metadata
    confidence = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    items = relationship("MealItem", back_populates="meal", cascade="all, delete-orphan")
