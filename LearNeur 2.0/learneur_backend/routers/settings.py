from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import random
import os
import shutil
import uuid
from fastapi import UploadFile, File

# --- CRITICAL IMPORTS (Uncommented & accurately mapped to your structure) ---
from database import get_db
from models import User, Child , EmailHistory
from auth import get_current_user, verify_password, get_password_hash
from utils.smtp_service import send_otp_email, send_email_changed_alerts
from utils.email_masker import mask_email

router = APIRouter(prefix="/settings", tags=["Settings"])

# --- SCHEMAS ---
class OTPRequest(BaseModel):
    action: str  # e.g., "password", "email", "delete"

class ChangePinRequest(BaseModel):
    current_pin: str
    new_pin: str

class ChangePasswordRequest(BaseModel):
    otp_code: str
    new_password: str

class ChangeEmailRequest(BaseModel):
    otp_code: str
    new_email: str

class DeleteAccountRequest(BaseModel):
    otp_code: str

# --- MOCK OTP STORE ---
# Note: In production, replace this with Redis + TTL expiration
otp_store = {}

# --- ENDPOINTS ---

@router.post("/request-otp")
async def request_action_otp(req: OTPRequest, current_user: User = Depends(get_current_user)):
    otp_code = str(random.randint(100000, 999999))
    
    # Store OTP bound to the specific action to prevent cross-action exploits
    otp_store[current_user.id] = {"code": otp_code, "action": req.action}
    
    # Trigger SMTP email sending
    await send_otp_email(current_user.email, otp_code, req.action)
    return {"message": "OTP sent successfully."}


@router.put("/change-pin")
async def change_pin(req: ChangePinRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # التأكد إن المستخدم ده ولي أمر وعنده بروفايل في جدول الـ parents
    if not current_user.parent_profile:
        raise HTTPException(status_code=403, detail="Only parents can have a PIN.")
    
    # مقارنة الـ PIN القديم (مقارنة نصية عادية لأن الديفولت 0000)
    if current_user.parent_profile.pin != req.current_pin:
        raise HTTPException(status_code=400, detail="Invalid current PIN.")
    
    # تحديث الـ PIN الجديد
    current_user.parent_profile.pin = req.new_pin
    db.commit()
    
    return {"message": "PIN updated successfully."}


@router.put("/change-password")
async def change_password(req: ChangePasswordRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    stored_otp_data = otp_store.get(current_user.id)
    if not stored_otp_data or stored_otp_data["code"] != req.otp_code or stored_otp_data["action"] != "password":
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")
    
    # التعديل السحري هنا: غيرنا اسم العمود لـ password_hash عشان يطابق الداتا بيس
    current_user.password_hash = get_password_hash(req.new_password)
    db.commit()
    del otp_store[current_user.id] # مسح الـ OTP بعد الاستخدام عشان الأمان
    
    return {"message": "Password updated successfully."}


@router.put("/change-email")
async def change_email(req: ChangeEmailRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    stored_otp_data = otp_store.get(current_user.id)
    if not stored_otp_data or stored_otp_data["code"] != req.otp_code or stored_otp_data["action"] != "email":
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")
    
    # التأكد إن الإيميل الجديد مش متسجل في الداتا بيس قبل كده
    existing_user = db.query(User).filter(User.email == req.new_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already in use.")

    old_email = current_user.email
    masked_new = mask_email(req.new_email)
    
    # التعديل هنا: هنجيب اسم المستخدم من البروفايل بتاعه الصح (ولي أمر أو دكتور)
    user_name = "User"
    if current_user.role.value == "PARENT" and current_user.parent_profile:
        user_name = current_user.parent_profile.full_name
    elif current_user.role.value == "DOCTOR" and current_user.doctor_profile:
        user_name = current_user.doctor_profile.full_name

    # تسجيل التغيير في جدول الـ EmailHistory
    history_record = EmailHistory(
        user_id=current_user.id,
        old_email=old_email,
        new_email=req.new_email
    )
    db.add(history_record)
    
    # تحديث الإيميل في الداتا بيس
    current_user.email = req.new_email
    db.commit()
    del otp_store[current_user.id]

    # إرسال رسائل التنبيه بالاسم المظبوط
    await send_email_changed_alerts(old_email, req.new_email, user_name, masked_new)
    
    return {"message": "Email updated successfully."}


@router.delete("/delete-account")
async def delete_account(req: DeleteAccountRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    stored_otp_data = otp_store.get(current_user.id)
    
    # Ensure they used a 'delete' specific OTP before wiping data
    if not stored_otp_data or stored_otp_data["code"] != req.otp_code or stored_otp_data["action"] != "delete":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP.")
    
    # Delete the user (SQLAlchemy Cascade handles associated Child profiles if configured)
    db.delete(current_user)
    db.commit()
    
    # Clean up OTP store
    del otp_store[current_user.id]
    
    return {"message": "Account securely deleted."}

# --- AVATAR ENDPOINTS ---

@router.post("/upload-avatar")
async def upload_parent_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # التأكد إن المستخدم ولي أمر
    if not current_user.parent_profile:
        raise HTTPException(status_code=403, detail="Only parents can upload avatars.")

    # إنشاء فولدر الصور لو مش موجود
    upload_dir = "uploads/avatars"
    os.makedirs(upload_dir, exist_ok=True)
    
    # عمل اسم مميز للصورة عشان الصور متدخلش في بعض
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"parent_{current_user.id[:8]}_{uuid.uuid4().hex[:8]}.{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    # حفظ الصورة على الهارد
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # تحديث مسار الصورة في الداتا بيس
    current_user.parent_profile.avatar_url = file_path
    db.commit()
    
    return {"message": "Avatar updated successfully", "avatar_url": file_path}


@router.get("/my-avatar")
async def get_my_avatar(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.parent_profile:
        return {"avatar_url": "default_parent.png"}
    
    # جلب مسار الصورة، ولو مفيش نرجع الصورة الافتراضية
    avatar = getattr(current_user.parent_profile, "avatar_url", "default_parent.png")
    if not avatar:
        avatar = "default_parent.png"
        
    return {"avatar_url": avatar}