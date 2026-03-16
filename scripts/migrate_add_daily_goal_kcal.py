from sqlalchemy import inspect, text

from app.db.session import engine


def migrate() -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "daily_goal_kcal" in columns:
        print("daily_goal_kcal already exists")
        return

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN daily_goal_kcal INTEGER NOT NULL DEFAULT 2000"))

    print("Added daily_goal_kcal to users")


if __name__ == "__main__":
    migrate()
