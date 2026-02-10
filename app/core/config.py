from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:qothwjd123!@db.kraghiweoqidsotphmcf.supabase.co:5432/postgres"
    gemini_api_key: str = "placeholder"
    cors_origins: str = "http://localhost:3000"
    debug: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings()
