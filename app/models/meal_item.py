from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class MealItem(Base):
    __tablename__ = "meal_items"

    id = Column(Integer, primary_key=True, index=True)
    meal_id = Column(Integer, ForeignKey("meal_logs.id"))
    
    name = Column(String, index=True)
    qty = Column(String, default="1 serving")
    kcal = Column(Integer, default=0)
    
    # Macros in grams
    carbs = Column(Float, default=0.0)
    protein = Column(Float, default=0.0)
    fat = Column(Float, default=0.0)

    meal = relationship("MealLog", back_populates="items")
