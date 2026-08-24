from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from src.infrastructure.database import get_db
from src.domain.models.user import User
from src.infrastructure.security.auth_service import AuthService
import random
import time
import jwt
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_otp_email(to_email: str, otp: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    if not (smtp_host and smtp_port and smtp_user and smtp_password):
        print(f"--- SMTP NOT CONFIGURED ---")
        print(f"To: {to_email}")
        print(f"OTP: {otp}")
        print(f"---------------------------")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = "ResumeRank Pro - Password Reset OTP"
        
        body = f"""Hello,

You have requested to reset your password on ResumeRank Pro.
Your 6-digit verification code is:

{otp}

This code is valid for 10 minutes. If you did not request this, please ignore this email.

Best regards,
ResumeRank Pro Team"""
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to server
        server = smtplib.SMTP(smtp_host, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.close()
        print(f"OTP Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return False

router = APIRouter(prefix="/auth", tags=["auth"])

class GoogleLoginRequest(BaseModel):
    id_token: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None

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
    user_email = user_in.email.lower()
    db_user = db.query(User).filter(User.email == user_email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=user_email,
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
    user_email = user_in.email.lower()
    user = db.query(User).filter(User.email == user_email).first()
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

@router.post("/google", response_model=Token)
def google_login(req: GoogleLoginRequest, db: Session = Depends(get_db)):
    # Verify Google token or use development sandbox mode fallback
    email = None
    full_name = None
    
    if req.id_token.startswith("mock_google_"):
        email = req.email or f"{req.id_token.replace('mock_google_', '')}@gmail.com"
        full_name = req.full_name or "Google Sandbox User"
    else:
        try:
            # Attempt to decode the JWT (soft signature check for dev robustness)
            payload = jwt.decode(req.id_token, options={"verify_signature": False})
            email = payload.get("email")
            full_name = payload.get("name")
        except Exception:
            # Fallback to requested credentials if decode fails (useful in local dev/testing)
            if req.email:
                email = req.email
                full_name = req.full_name or "Google User"
            else:
                raise HTTPException(status_code=400, detail="Invalid Google token payload")

    if not email:
        raise HTTPException(status_code=400, detail="Google token does not contain email")
        
    email = email.lower()
    
    # Register user if they do not exist
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password=AuthService.get_password_hash(f"google_{random.randint(1000000, 9999999)}"),
            full_name=full_name or email.split("@")[0].capitalize(),
            experience=[],
            education=[]
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
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
    """Generates a 6-digit OTP valid for 10 minutes. Sends it via SMTP if configured, or falls back to returning it for development."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        # Return success anyway to prevent email enumeration
        return {"message": "If this email exists, an OTP has been sent."}
    
    otp = str(random.randint(100000, 999999))
    expiry = time.time() + 600  # 10 minutes
    _otp_store[req.email] = (otp, expiry)
    
    # Try to send real email
    email_sent = send_otp_email(req.email, otp)
    
    res = {"message": "OTP generated. Check your email."}
    if not email_sent:
        res["dev_otp"] = otp
        res["message"] = "SMTP unconfigured. OTP returned in payload for local dev."
    else:
        res["message"] = "OTP sent to your email address."
        
    return res

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
