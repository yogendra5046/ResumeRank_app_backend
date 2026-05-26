from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from src.infrastructure.database import get_db
from src.domain.models.user import User
from src.infrastructure.security.auth_service import AuthService
import random
import time

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory OTP store: {email: (otp_code, expiry_timestamp)}
_otp_store: dict = {}

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

from src.presentation.api.dependencies import get_current_user

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    target_salary: Optional[str] = None
    work_preference: Optional[str] = None
    experience: Optional[List[dict]] = None
    education: Optional[List[dict]] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

@router.post("/register", response_model=dict)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=user_in.email,
        hashed_password=AuthService.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        experience=[],
        education=[]
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not AuthService.verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token = AuthService.create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "bio": user.bio,
            "target_salary": user.target_salary,
            "work_preference": user.work_preference,
            "experience": user.experience,
            "education": user.education
        }
    }

@router.get("/me", response_model=dict)
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "bio": current_user.bio,
        "target_salary": current_user.target_salary,
        "work_preference": current_user.work_preference,
        "experience": current_user.experience,
        "education": current_user.education
    }

@router.put("/profile", response_model=dict)
def update_profile(
    profile_in: UserProfileUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if profile_in.full_name is not None:
        current_user.full_name = profile_in.full_name
    if profile_in.bio is not None:
        current_user.bio = profile_in.bio
    if profile_in.target_salary is not None:
        current_user.target_salary = profile_in.target_salary
    if profile_in.work_preference is not None:
        current_user.work_preference = profile_in.work_preference
    if profile_in.experience is not None:
        current_user.experience = profile_in.experience
    if profile_in.education is not None:
        current_user.education = profile_in.education
    
    db.commit()
    db.refresh(current_user)
    return {"message": "Profile updated successfully"}

@router.post("/forgot-password", response_model=dict)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Generates a 6-digit OTP valid for 10 minutes. In production, email this to the user."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        # Return success anyway to prevent email enumeration
        return {"message": "If this email exists, an OTP has been sent."}
    
    otp = str(random.randint(100000, 999999))
    expiry = time.time() + 600  # 10 minutes
    _otp_store[req.email] = (otp, expiry)
    
    # In production: send via SendGrid/SMTP. For now, return OTP in response (dev mode).
    return {
        "message": "OTP generated. Check your email.",
        "dev_otp": otp  # REMOVE THIS IN PRODUCTION
    }

@router.post("/reset-password", response_model=dict)
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Verifies the OTP and sets a new password."""
    stored = _otp_store.get(req.email)
    if not stored:
        raise HTTPException(status_code=400, detail="No OTP found. Request a new one.")
    
    otp_code, expiry = stored
    if time.time() > expiry:
        _otp_store.pop(req.email, None)
        raise HTTPException(status_code=400, detail="OTP has expired. Request a new one.")
    
    if req.otp != otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP. Please check and retry.")
    
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    user.hashed_password = AuthService.get_password_hash(req.new_password)
    db.commit()
    _otp_store.pop(req.email, None)
    return {"message": "Password updated successfully. Please log in."}
