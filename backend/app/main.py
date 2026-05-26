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

# Automatically initialize and synchronize database tables on application boot
try:
    from app.core.database import engine, Base
    # Import all models to ensure they are registered on Base.metadata
    from app.models.user import User
    from app.models.upload import Upload
    from app.models.analysis import DataQualityReport, StatisticalFinding, AIInsightReport
    from app.models.session import AnalysisSession
    from app.models.interactions import UserAnnotation, ChatHistory
    
    logger.info("Automatically checking and synchronizing database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully.")
except Exception as db_init_err:
    logger.error(f"Critical error during database schema auto-initialization: {str(db_init_err)}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Operational Intelligence & Data Reliability Platform API",
    version="0.1.0",
)

# 1. CORS Hardening (Dynamic Vercel Namespace Whitelisting)
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://sales-op-five.vercel.app",
    "https://sales-op-68o2.vercel.app",
    "https://sales-op-6802.vercel.app",
    "https://sales-op-6802-3uuzfff4u-jeetkachhelas-projects.vercel.app",
]
env_origins = os.getenv("BACKEND_CORS_ORIGINS")
if env_origins:
    allowed_origins.extend([orig.strip() for orig in env_origins.split(",") if orig.strip()])

# Enforce clean deduplicated list
allowed_origins = list(set(allowed_origins))

class DynamicCORSMiddleware(CORSMiddleware):
    def is_allowed_origin(self, origin: str) -> bool:
        if super().is_allowed_origin(origin):
            return True
        # Allow any Vercel preview or production deployments containing "sales-op" or "salesop" and ending with .vercel.app
        origin_lower = origin.lower()
        if (
            origin_lower.endswith("-jeetkachhelas-projects.vercel.app") 
            or (origin_lower.endswith(".vercel.app") and ("sales-op" in origin_lower or "salesop" in origin_lower))
            or "sales-op-6802" in origin_lower 
            or "sales-op-68o2" in origin_lower
        ):
            return True
        return False

app.add_middleware(
    DynamicCORSMiddleware,
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
            
        # Strict CSP rules - Dynamically whitelist allowed origins
        connect_src_origins = " ".join(allowed_origins)
        req_origin = request.headers.get("origin")
        if req_origin:
            req_origin_lower = req_origin.lower()
            if (
                req_origin in allowed_origins 
                or req_origin_lower.endswith("-jeetkachhelas-projects.vercel.app") 
                or "sales-op-6802" in req_origin_lower 
                or "sales-op-68o2" in req_origin_lower
            ):
                connect_src_origins += f" {req_origin}"
                
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            f"connect-src 'self' {connect_src_origins} https://*.onrender.com; "
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
    
    response = JSONResponse(
        status_code=status_code,
        content={
            "detail": getattr(exc, "detail", "An unexpected server error occurred. Please contact system support."),
            "request_id": request_id
        }
    )
    
    # Manually append CORS headers to avoid masking exceptions under CORS errors
    origin = request.headers.get("origin")
    if origin:
        origin_lower = origin.lower()
        is_valid = False
        if origin in allowed_origins:
            is_valid = True
        elif (
            origin_lower.endswith("-jeetkachhelas-projects.vercel.app") 
            or (origin_lower.endswith(".vercel.app") and ("sales-op" in origin_lower or "salesop" in origin_lower))
            or "sales-op-6802" in origin_lower 
            or "sales-op-68o2" in origin_lower
        ):
            is_valid = True
            
        if is_valid:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, X-Request-ID, accept, origin"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD"
            
    return response

from app.api.auth import router as auth_router
from app.api.uploads import router as uploads_router
from app.api.interactions import router as interactions_router
from app.api.analytics_api import router as analytics_router

app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(uploads_router, prefix=f"{settings.API_V1_STR}/uploads", tags=["uploads"])
app.include_router(interactions_router, prefix=f"{settings.API_V1_STR}/interactions", tags=["interactions"])
app.include_router(analytics_router, prefix=f"{settings.API_V1_STR}/analytics", tags=["analytics"])

@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"message": "Operational Intelligence Platform API is running."}

@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return {"status": "ok"}


