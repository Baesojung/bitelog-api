from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.api.v1.api import api_router

app = FastAPI(
    title="Bitelog API",
    description="AI-powered meal logging and insights API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
origins = settings.cors_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/v1")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.get("/v1/health", summary="Health Check")
async def health():
    """
    Check if the API is running correctly.
    """
    return {"status": "ok"}
