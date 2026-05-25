import os
import uuid
import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings

# Initialize logger
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Operational Intelligence & Data Reliability Platform API",
    version="0.1.0",
)

# 1. CORS Hardening
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://sales-op-68o2.vercel.app",
]
env_origins = os.getenv("BACKEND_CORS_ORIGINS")
if env_origins:
    allowed_origins.extend([orig.strip() for orig in env_origins.split(",") if orig.strip()])

# Enforce clean deduplicated list
allowed_origins = list(set(allowed_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Request-ID", "accept", "origin"],
)

# 2. Request Tracing Middleware
class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(RequestTracingMiddleware)

# 2b. Rate Limiter Middleware Throttling (Redis with In-Memory Fallback)
from app.security.rate_limiter import DualRateLimiterMiddleware
redis_url = os.getenv("REDIS_URL")
app.add_middleware(DualRateLimiterMiddleware, redis_url=redis_url)


# 3. OWASP Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # SSL Enforcement (HSTS) - Only activated in production environments
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
            
        # Strict CSP rules
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' https://sales-op-68o2.vercel.app http://localhost:3000 http://localhost:8000 http://127.0.0.1:8000; "
            "frame-ancestors 'none';"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)

# 4. Centralized Exception Handling (Prevent stack trace leakages)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "N/A")
    logger.error(f"Unhandled exception [ID: {request_id}]: {str(exc)}\n{traceback.format_exc()}")
    status_code = exc.status_code if hasattr(exc, "status_code") else 500
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": getattr(exc, "detail", "An unexpected server error occurred. Please contact system support."),
            "request_id": request_id
        }
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


