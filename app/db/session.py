from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Create Database Engine
# pool_pre_ping=True: DB 연결 끊김 방지 (자동 재연결)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True
)

# Create SessionLocal Class
# autocommit=False: 트랜잭션 관리 명시적 수행
# autoflush=False: 명시적 flush 전까지 DB 전송 지연
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base Class for Models
Base = declarative_base()

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
