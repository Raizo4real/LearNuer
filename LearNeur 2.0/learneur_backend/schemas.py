from pydantic import BaseModel, EmailStr, Field
from typing import Optional , List
from models import RoleEnum
from datetime import datetime

# -----------------
# Login Schemas
# -----------------
class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

# -----------------
# Registration Schemas
# -----------------
class UserRegister(BaseModel):
    role: RoleEnum
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    
    # Optional fields depending on the role
    specialty: Optional[str] = None
    documentName: Optional[str] = None 

# -----------------
# Response Schemas 
# (Used to structure the data sent back to the frontend)
# -----------------
class Token(BaseModel):
    access_token: str
    token_type: str
    redirect_url: str
    message: Optional[str] = None

# -----------------
# Child Schemas (Phase 3)
# -----------------
class ChildCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    age: int = Field(..., gt=0, lt=100)
    communication_level: str
    sensory_sensitivities: Optional[str] = None
    special_interests: Optional[str] = None

class ChildUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    age: Optional[int] = Field(None, gt=0, lt=100)
    communication_level: Optional[str] = None
    sensory_sensitivities: Optional[str] = None
    special_interests: Optional[str] = None

class AutismProfileResponse(BaseModel):
    id: int
    child_id: int
    communication_level: str
    sensory_sensitivities: Optional[str] = None
    special_interests: Optional[str] = None

    class Config:
        from_attributes = True

class ChildResponse(BaseModel):
    id: int
    parent_id: int
    first_name: str
    age: int
    avatar_url: str
    autism_profile: Optional[AutismProfileResponse] = None # السطر ده هو السر!

    class Config:
        from_attributes = True

# -----------------
# Game Schemas (Phase 4)
# -----------------
class TelemetryCreate(BaseModel):
    child_id: int
    game_name: str
    time_taken_seconds: float
    total_clicks: int
    frantic_clicks: int
    is_completed: bool

# 👇 الكلاس الجديد اللي هيرجع الداتا للفرونت إند ومعاها التاريخ
class TelemetryResponse(TelemetryCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# -----------------
# Pin Schemas (Phase 9)
# -----------------
class PinVerifyRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6, description="The Parent PIN to unlock the kiosk")

class ForgotPasswordPINRequest(BaseModel):
    email: EmailStr

class ResetPINWithOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code sent via email")
    new_pin: str = Field(..., min_length=4, max_length=6, description="The new 4-to-6 digit PIN")

# -----------------
# Doctor Profile Schema
# -----------------
class DoctorProfileUpdate(BaseModel):
    full_name: str
    specialty: Optional[str] = None
    bio: Optional[str] = None
