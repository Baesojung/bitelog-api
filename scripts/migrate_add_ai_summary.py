import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import engine

def add_column():
    print("Migrating database schema...")
    from sqlalchemy.exc import ProgrammingError
    
    with engine.connect() as conn:
        try:
            # Using standard SQL for PostgreSQL
            conn.execute(text("ALTER TABLE meal_logs ADD COLUMN ai_summary TEXT"))
            conn.commit()
            print("Successfully added 'ai_summary' column.")
        except ProgrammingError as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("Column 'ai_summary' already exists. Skipping.")
            else:
                print(f"Migration failed checking: {e}")
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    add_column()
