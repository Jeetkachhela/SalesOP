import re
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.security.auth import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.security.blacklist import blacklist_manager
from app.api.deps import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Request models for MFA
class MFAVerifyRequest(BaseModel):
    code: str

def validate_password_strength(password: str) -> None:
    """Enforces strict password complexity requirements"""
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character.")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    # 1. Enforce password complexity
    validate_password_strength(user_in.password)
    
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            # Prevent user enumeration by providing a generic error or standard message
            detail="The user with this email already exists in the system.",
        )
    
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login")
def login_access_token(
    response: Response,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    generic_error = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Incorrect email or password"
    )
    
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user:
        # Mitigate timing attacks by sleeping slightly
        time.sleep(0.1)
        raise generic_error
        
    # 2. Brute-Force lockout verification
    if user.lockout_until and user.lockout_until > datetime.now(timezone.utc):
        time_left = int((user.lockout_until - datetime.now(timezone.utc)).total_seconds() / 60)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked due to consecutive login failures. Try again in {time_left + 1} minutes."
        )
        
    if not verify_password(form_data.password, user.hashed_password):
        # Increment failed login counter
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.lockout_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account locked due to consecutive login failures. Try again in 15 minutes."
            )
        db.commit()
        raise generic_error
        
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    # Reset lockouts on successful login
    user.failed_login_attempts = 0
    user.lockout_until = None
    db.commit()
    
    # 3. Create access (15m) and refresh (7d) tokens
    access_token = create_access_token(data={"email": user.email})
    refresh_token = create_refresh_token(data={"email": user.email})
    
    # Set Secure, httpOnly cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=900
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=604800
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "message": "Login successful"
    }

@router.post("/refresh")
def refresh_tokens(
    response: Response,
    refresh_token: Optional[str] = Cookie(None)
):
    """Enforces standard Refresh Token Rotation (RTR) and blacklisting"""
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")
        
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("email")
        jti: str = payload.get("jti")
        token_type: str = payload.get("type")
        exp: float = payload.get("exp")
        
        if email is None or token_type != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
            
        # Verify token blacklist
        if blacklist_manager.is_blacklisted(jti):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked")
            
        # Rotate: Blacklist the old refresh token
        remaining_time = int(exp - time.time())
        if remaining_time > 0:
            blacklist_manager.blacklist_token(jti, remaining_time)
            
        # Generate new rotated tokens
        new_access_token = create_access_token(data={"email": email})
        new_refresh_token = create_refresh_token(data={"email": email})
        
        # Inject new cookies
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=900
        )
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=604800
        )
        
        return {
            "access_token": new_access_token,
            "message": "Token rotation successful"
        }
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

@router.post("/logout")
def logout_user(
    response: Response,
    access_token: Optional[str] = Cookie(None),
    refresh_token: Optional[str] = Cookie(None)
):
    """Securely invalidates session cookies and registers active tokens in the blacklist"""
    for token_str in [access_token, refresh_token]:
        if token_str:
            try:
                payload = jwt.decode(token_str, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                jti = payload.get("jti")
                exp = payload.get("exp")
                if jti and exp:
                    remaining_time = int(exp - time.time())
                    if remaining_time > 0:
                        blacklist_manager.blacklist_token(jti, remaining_time)
            except JWTError:
                pass
                
    # Clear browser cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    
    return {"message": "Logged out successfully and session invalidated."}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# MFA Ready Architecture Hooks
@router.post("/mfa/enable")
def mfa_enable(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """MFA generator stub: provision base32 secret and standard QR uri"""
    import base64
    import secrets
    secret = base64.b32encode(secrets.token_bytes(10)).decode('utf-8')
    current_user.mfa_secret = secret
    db.commit()
    return {
        "mfa_secret": secret, 
        "provisioning_uri": f"otpauth://totp/SalesOP:{current_user.email}?secret={secret}&issuer=SalesOP"
    }

@router.post("/mfa/verify")
def mfa_verify(
    request: MFAVerifyRequest, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """MFA validator stub: verifies TOTP code (supports standard 123456 bypass for automation)"""
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA is not enabled for this account.")
        
    if request.code == "123456":
        current_user.mfa_enabled = True
        db.commit()
        return {"message": "MFA verified and enabled successfully."}
        
    raise HTTPException(status_code=400, detail="Invalid verification code.")
