from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import models, schemas, database , random
from dependencies import get_current_parent
from datetime import datetime, timedelta
from utils.email_utils import send_otp_email
from pydantic import BaseModel
from database import get_db
from models import Child, DoctorChildConnection, User  , DoctorRating, Doctor
from auth import get_current_user
router = APIRouter(prefix="/parent", tags=["Parent Dashboard"])

@router.post("/add-child", response_model=schemas.ChildResponse, status_code=status.HTTP_201_CREATED)

def add_child(payload: schemas.ChildCreate, db: Session = Depends(database.get_db), current_parent: models.Parent = Depends(get_current_parent)):
    new_child = models.Child(
        parent_id=current_parent.id, # Extracted securely from JWT
        first_name=payload.first_name,
        age=payload.age,
        avatar_url=f"https://api.dicebear.com/7.x/bottts/svg?seed={payload.first_name}"
    )
    db.add(new_child)
    db.flush() 

    new_profile = models.AutismProfile(
        child_id=new_child.id,
        communication_level=payload.communication_level,
        sensory_sensitivities=payload.sensory_sensitivities,
        special_interests=payload.special_interests
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_child)

    return new_child

@router.get("/children", response_model=List[schemas.ChildResponse])
def get_children(db: Session = Depends(database.get_db), current_parent: models.Parent = Depends(get_current_parent)):
    # Automatically scopes the query to only the logged-in parent's children
    return db.query(models.Child).filter(models.Child.parent_id == current_parent.id).all()

@router.delete("/delete-child/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_child(child_id: int, db: Session = Depends(database.get_db), current_parent: models.Parent = Depends(get_current_parent)):
    child = db.query(models.Child).filter(models.Child.id == child_id, models.Child.parent_id == current_parent.id).first()
    
    if not child:
        raise HTTPException(status_code=404, detail="Child profile not found or unauthorized.")
        
    db.delete(child)
    db.commit()
    return {"message": "Child deleted successfully"}

@router.put("/edit-child/{child_id}", response_model=schemas.ChildResponse)
def edit_child(child_id: int, payload: schemas.ChildUpdate, db: Session = Depends(database.get_db), current_parent: models.Parent = Depends(get_current_parent)):
    child = db.query(models.Child).filter(models.Child.id == child_id, models.Child.parent_id == current_parent.id).first()
    
    if not child:
        raise HTTPException(status_code=404, detail="Child profile not found or unauthorized.")
        
    # Update Child fields
    if payload.first_name: child.first_name = payload.first_name
    if payload.age: child.age = payload.age
    
    # Update AutismProfile fields
    if any([payload.communication_level, payload.sensory_sensitivities, payload.special_interests]):
        profile = child.autism_profile
        if payload.communication_level: profile.communication_level = payload.communication_level
        if payload.sensory_sensitivities is not None: profile.sensory_sensitivities = payload.sensory_sensitivities
        if payload.special_interests is not None: profile.special_interests = payload.special_interests

    db.commit()
    db.refresh(child)
    return child

# ==========================================
# 1. VERIFY PIN (Protected Endpoint)
# ==========================================
@router.post("/verify-pin", status_code=status.HTTP_200_OK)
def verify_parent_pin(
    payload: schemas.PinVerifyRequest, 
    db: Session = Depends(database.get_db), 
    current_parent: models.Parent = Depends(get_current_parent)
):
    """
    Verifies the PIN to allow the parent to exit the Child Kiosk Mode.
    """
    if current_parent.pin != payload.pin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect PIN."
        )
    
    return {"status": "success", "message": "PIN verified successfully."}


# ==========================================
# 2. FORGOT PIN (Public Endpoint)
# ==========================================
@router.post("/forgot-pin", status_code=status.HTTP_200_OK)
def forgot_pin(payload: schemas.ForgotPasswordPINRequest, db: Session = Depends(database.get_db)):
    """
    Generates an OTP and emails it to the parent if the account exists.
    """
    # Find base User by email
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or user.role != models.RoleEnum.PARENT:
        # Standard security practice: Do not reveal if email exists or not
        return {"status": "success", "message": "If that email exists, an OTP has been sent."}

    # Get corresponding Parent profile
    parent = db.query(models.Parent).filter(models.Parent.user_id == user.id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent profile not found.")

    # Generate 6-digit OTP and set expiration (15 minutes from now)
    otp_code = str(random.randint(100000, 999999))
    parent.reset_pin_token = otp_code
    parent.reset_pin_expires = datetime.utcnow() + timedelta(minutes=15)
    
    db.commit()

    # Send the email
    email_sent = send_otp_email(payload.email, otp_code)
    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send the recovery email. Please try again later.")

    return {"status": "success", "message": "If that email exists, an OTP has been sent."}

# ==========================================
# 3. CHECK PIN STATUS (Protected Endpoint)
# ==========================================
@router.get("/check-pin-status")
def check_pin_status(current_parent: models.Parent = Depends(get_current_parent)):
    """
    بيفحص هل ولي الأمر الحالي مسجل PIN في الداتابيز ولا خانته فاضية
    """
    # لو الـ pin مش null ومش فاضي، هيرجع true غير كده false
    has_pin = current_parent.pin is not None and str(current_parent.pin).strip() != ""
    return {"has_pin": has_pin}

# ==========================================
# 4. RESET PIN WITH OTP (Public Endpoint)
# ==========================================
@router.post("/reset-pin-otp", status_code=status.HTTP_200_OK)
def reset_pin_with_otp(payload: schemas.ResetPINWithOTPRequest, db: Session = Depends(database.get_db)):
    """
    Verifies the OTP and applies the new PIN.
    """
    # 1. Find user by email
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid email or OTP.")

    # 2. Find parent profile
    parent = db.query(models.Parent).filter(models.Parent.user_id == user.id).first()
    if not parent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid email or OTP.")

    # 3. Verify OTP & Expiration
    if parent.reset_pin_token != payload.otp_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP code.")
    
    if parent.reset_pin_expires is None or datetime.utcnow() > parent.reset_pin_expires:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP code has expired. Please request a new one.")

    # 4. Apply new PIN & Clear temporary tokens
    parent.pin = payload.new_pin
    parent.reset_pin_token = None
    parent.reset_pin_expires = None
    
    db.commit()

    return {"status": "success", "message": "Your PIN has been successfully reset. You can now unlock the dashboard."}

# ==========================================
# 5. DOCTOR CONNECTION ENDPOINTS
# ==========================================

# --- SCHEMA ---
class DoctorConnectionRequest(BaseModel):
    doctor_id: str
    child_id: int

# --- ENDPOINT ---
@router.post("/connect-doctor")
def connect_doctor(
    req: DoctorConnectionRequest, 
    db: Session = Depends(database.get_db), 
    current_parent: models.Parent = Depends(get_current_parent) # 👈 التعديل السحري هنا
):
    # 🔒 الحماية الجذرية: التأكد إن الطفل ده أصلاً بتاع ولي الأمر اللي فاتح الحساب
    child = db.query(models.Child).filter(
        models.Child.id == req.child_id, 
        models.Child.parent_id == current_parent.id # 👈 المقارنة بقت مظبوطة
    ).first()
    
    if not child:
        raise HTTPException(status_code=404, detail="Child not found or doesn't belong to you.")

    # 1. التأكد إن مفيش طلب مبعوت قبل كده عشان نمنع التكرار (Spam)
    existing_conn = db.query(models.DoctorChildConnection).filter(
        models.DoctorChildConnection.doctor_id == req.doctor_id,
        models.DoctorChildConnection.child_id == req.child_id
    ).first()

    if existing_conn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"A connection request already exists with status: {existing_conn.status}"
        )

    # 2. إنشاء الطلب الجديد وربطه
    new_conn = models.DoctorChildConnection(
        doctor_id=req.doctor_id,
        child_id=req.child_id,
        status="pending"
    )
    db.add(new_conn)
    db.commit()

    return {"message": "Connection request sent to the doctor successfully."}
# ==========================================
# 🌟 DOCTOR DIRECTORY & CHILDREN APIs
# ==========================================

@router.get("/doctors-directory")
def get_doctors_directory(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    بيجيب كل الدكاترة المعتمدين في المنصة عشان نعرضهم لولي الأمر مع تقييمهم الحقيقي
    """
    doctors = db.query(User).filter(User.role == "DOCTOR").all()
    
    result = []
    for doc in doctors:
        # 1. بنحاول نجيب الاسم من جدول اليوزر مباشرة (name أو full_name)
        doc_name = getattr(doc, "full_name", getattr(doc, "name", None))
        doc_specialty = getattr(doc, "specialty", None)

       # 1. الدخول لبروفايل الدكتور عشان نجيب الصورة
        doc_profile = getattr(doc, "doctor_profile", None)
        doc_avatar = getattr(doc_profile, "avatar_url", "default_doctor.png") if doc_profile else "default_doctor.png"
        # 2. لو مش موجود في اليوزر، بنجيبه من الـ DoctorProfile لو معمول له Relationship
        doc_profile = getattr(doc, "doctor_profile", None)
        if doc_profile:
            if not doc_name:
                doc_name = getattr(doc_profile, "full_name", "Unknown Doctor")
            if not doc_specialty:
                doc_specialty = getattr(doc_profile, "specialty", "Clinical Specialist")
        
        # لو كل المحاولات فشلت، بنحط قيم افتراضية شيك
        if not doc_name:
            doc_name = "Specialist"
        if not doc_specialty:
            doc_specialty = "Clinical Specialist"

        # 🌟 السحر هنا: بنحسب التقييم الحقيقي اللايف من جدول التقييمات
        avg_rating = db.query(func.avg(DoctorRating.rating_value)).filter(DoctorRating.doctor_id == str(doc.id)).scalar()
        
        # لو ملوش تقييم هيبقى 0.0، ولو ليه هيتقرب لأقرب رقم عشري (زي 4.0 أو 4.5)
        live_rating = round(avg_rating, 1) if avg_rating else 0.0

        result.append({
            "doctor_id": str(doc.id), # أو حسب الكود بتاعك
            "full_name": doc_name,
            "specialty": doc_specialty,
            "rating": live_rating,
            "avatar_url": doc_avatar  # 👈 بنمررها هنا
        })
        
    return result


@router.get("/children")
def get_parent_children(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    بيجيب قائمة الأطفال الخاصة بولي الأمر اللي فاتح الحساب دلوقتي
    عشان تظهر في الـ Dropdown لما ييجي يربط طفل بدكتور
    """
    children = db.query(Child).filter(Child.parent_id == current_user.id).all()
    
    result = []
    for child in children:
        result.append({
            "id": child.id,
            "first_name": getattr(child, "first_name", "Unknown Child")
        })
        
    return result

@router.get("/my-approved-connections")
def get_my_approved_connections(
    db: Session = Depends(database.get_db), 
    current_parent: models.Parent = Depends(get_current_parent)
):
    approved_conns = db.query(models.DoctorChildConnection).join(models.Child).filter(
        models.Child.parent_id == current_parent.id,
        models.DoctorChildConnection.status == "approved"
    ).all()

    result = []
    for conn in approved_conns:
        doc_user = db.query(models.User).filter(models.User.id == conn.doctor_id).first()
        # 2. الدخول لبروفايل الدكتور في الـ Connections
        doc_profile = getattr(doc_user, "doctor_profile", None) if doc_user else None
        doc_avatar = getattr(doc_profile, "avatar_url", "default_doctor.png") if doc_profile else "default_doctor.png"
        
        # 🧠 البحث الذكي عن اسم الدكتور
        doc_name = None
        if doc_user:
            doc_name = getattr(doc_user, "full_name", getattr(doc_user, "name", None))
            doc_profile = getattr(doc_user, "doctor_profile", None)
            if not doc_name and doc_profile:
                doc_name = getattr(doc_profile, "full_name", None)
        
        if not doc_name:
            doc_name = "Specialist"

        result.append({
            "connection_id": conn.id,
            "doctor_name": f"Dr. {doc_name}",
            "child_name": conn.child.first_name,
            "avatar_url": doc_avatar 
        })
        
    return result

class RateRequest(BaseModel):
    rating: int

@router.post("/rate-doctor/{connection_id}")
def rate_doctor(connection_id: int, req: RateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. التأكد إن الـ Connection ده يخص ولي الأمر وإنه Approved
    parent_profile = current_user.parent_profile
    if not parent_profile:
        raise HTTPException(status_code=403, detail="Parent profile not found.")
    
    child_ids = [child.id for child in parent_profile.children]
    
    conn = db.query(DoctorChildConnection).filter(
        DoctorChildConnection.id == connection_id,
        DoctorChildConnection.child_id.in_(child_ids),
        DoctorChildConnection.status == "approved"
    ).first()

    if not conn:
        raise HTTPException(status_code=403, detail="Invalid connection or unauthorized access.")

    # 2. استخراج بيانات الدكتور من الـ Connection بذكاء
    doctor_identifier = conn.doctor_id
    try:
        doc_id_int = int(doctor_identifier)
        doctor_profile = db.query(Doctor).filter((Doctor.user_id == str(doctor_identifier)) | (Doctor.id == doc_id_int)).first()
    except ValueError:
        doctor_profile = db.query(Doctor).filter(Doctor.user_id == doctor_identifier).first()

    if not doctor_profile:
        raise HTTPException(status_code=404, detail="Doctor profile not found in database.")

    # 3. تسجيل أو تحديث التقييم
    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5.")

    existing_rating = db.query(DoctorRating).filter_by(doctor_id=doctor_profile.user_id, parent_id=str(current_user.id)).first()
    if existing_rating:
        existing_rating.rating_value = req.rating
    else:
        new_rating = DoctorRating(doctor_id=doctor_profile.user_id, parent_id=str(current_user.id), rating_value=req.rating)
        db.add(new_rating)
    db.commit()

    # 4. حساب المتوسط وتحديث نجوم الدكتور
    avg_rating = db.query(func.avg(DoctorRating.rating_value)).filter_by(doctor_id=doctor_profile.user_id).scalar()
    doctor_profile.rating = round(avg_rating, 1) if avg_rating else 0
    db.commit()

    return {"message": "Rating submitted successfully!", "new_rating": doctor_profile.rating}
