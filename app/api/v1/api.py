from fastapi import APIRouter
from app.api.v1.endpoints import meals

api_router = APIRouter()
api_router.include_router(meals.router, prefix="/meals", tags=["meals"])
