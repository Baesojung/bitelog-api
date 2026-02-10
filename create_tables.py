from app.db.session import engine, Base
from app.models.meal import MealLog
from app.models.meal_item import MealItem

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Done!")

if __name__ == "__main__":
    init_db()
