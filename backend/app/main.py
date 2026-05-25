from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Operational Intelligence & Data Reliability Platform API",
    version="0.1.0",
)

# CORS configuration
# Strict CORS origin restrictions will be enforced in production
import os
allowed_origins = ["http://localhost:3000"]
env_origins = os.getenv("BACKEND_CORS_ORIGINS")
if env_origins:
    allowed_origins = [orig.strip() for orig in env_origins.split(",") if orig.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.auth import router as auth_router
from app.api.uploads import router as uploads_router
from app.api.datasets import router as datasets_router
from app.api.interactions import router as interactions_router
from app.api.analytics_api import router as analytics_router

app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(uploads_router, prefix=f"{settings.API_V1_STR}/uploads", tags=["uploads"])
app.include_router(datasets_router, prefix=f"{settings.API_V1_STR}/datasets", tags=["datasets"])
app.include_router(interactions_router, prefix=f"{settings.API_V1_STR}/interactions", tags=["interactions"])
app.include_router(analytics_router, prefix=f"{settings.API_V1_STR}/analytics", tags=["analytics"])

@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"message": "Operational Intelligence Platform API is running."}

@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return {"status": "ok"}

