from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import get_db
from models import User, Child, DoctorChildConnection , Doctor, DoctorRating
from auth import get_current_user # Adjust based on your auth file location
from schemas import DoctorProfileUpdate

import os
import shutil
import uuid
from fastapi import UploadFile, File

router = APIRouter(prefix="/doctor", tags=["Doctor Dashboard"])

# --- DEPENDENCY: Ensure user is a Doctor ---
def require_doctor(current_user: User = Depends(get_current_user)):
    if current_user.role.value != "DOCTOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access denied. Clinical Doctor clearance required."
        )
    return current_user
# --- ENDPOINT: Get Current Doctor Profile (With Live Rating & Avatar) ---
@router.get("/my-profile")
def get_my_profile(db: Session = Depends(get_db), current_user: User = Depends(require_doctor)):
    profile = db.query(Doctor).filter(Doctor.user_id == str(current_user.id)).first()
    
    avg_rating = db.query(func.avg(DoctorRating.rating_value)).filter(DoctorRating.doctor_id == str(current_user.id)).scalar()
    live_rating = round(avg_rating, 1) if avg_rating else 0.0

    return {
        "full_name": profile.full_name if profile else current_user.name if hasattr(current_user, 'name') else "Doctor",
        "specialty": profile.specialty if profile else "Clinical Specialist",
        "bio": profile.bio if profile else "", 
        "is_verified": profile.is_approved if profile else False,
        "rating": live_rating,
        "avatar_url": getattr(profile, "avatar_url", "default_doctor.png") if profile else "default_doctor.png" # 👈 إضافة الصورة
    }

# --- ENDPOINT: Upload Doctor Avatar ---
@router.post("/upload-avatar")
def upload_doctor_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor)
):
    profile = db.query(Doctor).filter(Doctor.user_id == str(current_user.id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Doctor profile not found")

    upload_dir = "uploads/avatars"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"doctor_{current_user.id[:8]}_{uuid.uuid4().hex[:8]}.{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    profile.avatar_url = file_path
    db.commit()
    
    return {"message": "Avatar updated successfully", "avatar_url": file_path}

# --- ENDPOINT: Update Doctor Profile ---
@router.put("/update-profile")
def update_my_profile(
    payload: DoctorProfileUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_doctor)
):
    # بندور على البروفايل
    profile = db.query(Doctor).filter(Doctor.user_id == str(current_user.id)).first()
    
    if not profile:
        # لو ملوش بروفايل، ننشئ واحد جديد
        profile = Doctor(
            user_id=str(current_user.id),
            full_name=payload.full_name,
            specialty=payload.specialty,
            bio=payload.bio,
            is_approved=False
        )
        db.add(profile)
    else:
        # لو ليه بروفايل، نحدث بياناته
        profile.full_name = payload.full_name
        profile.specialty = payload.specialty
        profile.bio = payload.bio
        
    db.commit()
    return {"message": "Profile updated successfully!"}
# --- ENDPOINT 1: Get Pending Requests ---
@router.get("/requests/pending")
def get_pending_requests(db: Session = Depends(get_db), current_doctor: User = Depends(require_doctor)):
    # Fetch pending connections for this specific doctor
    pending_conns = db.query(DoctorChildConnection).filter(
        DoctorChildConnection.doctor_id == str(current_doctor.id), 
        DoctorChildConnection.status == "pending"
    ).all()

    results = []
    for conn in pending_conns:
        child = conn.child
        
        # 1. بنجيب الإيميل من جدول الـ User المرتبط بـ Parent
        parent_email = "Unknown"
        if child and child.parent and getattr(child.parent, "user", None):
            parent_email = child.parent.user.email
            
        # 2. بنجيب مستوى التواصل من جدول الـ AutismProfile لو موجود
        comm_level = "Unknown"
        if child and getattr(child, "autism_profile", None):
            comm_level = child.autism_profile.communication_level

        results.append({
            "connection_id": conn.id,
            "child_name": getattr(child, "first_name", "Unknown"),
            "child_age": getattr(child, "age", "Unknown"),
            "parent_email": parent_email,
            "communication_level": comm_level
        })
        
    return results

# --- ENDPOINT 2: Approve or Reject Request ---
@router.put("/requests/{connection_id}/{action}")
def respond_to_request(connection_id: int, action: str, db: Session = Depends(get_db), current_doctor: User = Depends(require_doctor)):
    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be exactly 'approve' or 'reject'.")

    # Find the specific connection securely (ensuring it belongs to this doctor)
    conn = db.query(DoctorChildConnection).filter(
        DoctorChildConnection.id == connection_id,
        DoctorChildConnection.doctor_id == str(current_doctor.id)
    ).first()

    if not conn:
        raise HTTPException(status_code=404, detail="Connection request not found.")

    # Update status ("approve" -> "approved", "reject" -> "rejected")
    conn.status = f"{action}d" 
    db.commit()

    return {"message": f"Connection request {conn.status} successfully."}

# --- ENDPOINT 3: Get Approved Patients ---
@router.get("/my-patients")
def get_my_patients(db: Session = Depends(get_db), current_doctor: User = Depends(require_doctor)):
    approved_conns = db.query(DoctorChildConnection).filter(
        DoctorChildConnection.doctor_id == str(current_doctor.id),
        DoctorChildConnection.status == "approved"
    ).all()

    patients = []
    for conn in approved_conns:
        child = conn.child
        
        # بنجيب فئة التواصل من بروفايل الطفل
        comm_level = "Not Specified"
        if child and getattr(child, "autism_profile", None):
            comm_level = child.autism_profile.communication_level

        patients.append({
            "connection_id": conn.id, # 👈 ده اللي هنفتح بيه غرفة الشات
            "child_id": child.id,
            "name": getattr(child, "first_name", "Unknown"),
            "age": getattr(child, "age", "Unknown"),
            "communication_level": comm_level # 👈 الداتا الجديدة
        })
        
    return patients

# --- ENDPOINT 4: Get REAL Patient Telemetry & Full Report ---
@router.get("/patient-telemetry/{child_id}")
def get_patient_telemetry(child_id: int, db: Session = Depends(get_db), current_doctor: User = Depends(require_doctor)):
    # 🔒 Security: Check if Doctor is approved for this specific child
    conn = db.query(DoctorChildConnection).filter(
        DoctorChildConnection.doctor_id == str(current_doctor.id),
        DoctorChildConnection.child_id == child_id,
        DoctorChildConnection.status == "approved"
    ).first()

    if not conn:
        raise HTTPException(status_code=403, detail="Unauthorized access to this patient's telemetry.")

    child = conn.child
    profile = getattr(child, "autism_profile", None)
    sessions = getattr(child, "game_sessions", [])

    # 1. حساب الإحصائيات العامة
    total_sessions = len(sessions)
    tasks_completed = sum(1 for s in sessions if s.is_completed)
    total_time_seconds = sum(s.time_taken_seconds for s in sessions)
    total_clicks = sum(s.total_clicks for s in sessions)
    total_frantic = sum(s.frantic_clicks for s in sessions)

    focus_score = 0
    if total_sessions > 0:
        completion_rate = (tasks_completed / total_sessions) * 100
        frantic_penalty = (total_frantic / max(total_clicks, 1)) * 100
        focus_score = max(0, min(100, round(completion_rate - frantic_penalty)))
    
    # 2. تجهيز الداتا الخام للرسومات البيانية (Charts)
    raw_sessions = []
    for s in sessions:
        raw_sessions.append({
            "game_name": s.game_name,
            "time_taken_seconds": s.time_taken_seconds,
            "total_clicks": s.total_clicks,
            "frantic_clicks": s.frantic_clicks,
            "is_completed": s.is_completed
        })

    # 3. معالجة الـ Nulls بذكاء
    sensory = getattr(profile, "sensory_sensitivities", None)
    interests = getattr(profile, "special_interests", None)

    return {
        "child_id": child.id,
        "name": getattr(child, "first_name", "Unknown"),
        "communication_level": getattr(profile, "communication_level", "Not Specified") if profile else "Not Specified",
        "sensory_sensitivities": sensory if sensory else "None Reported",
        "special_interests": interests if interests else "None Reported",
        "focus_score": focus_score, 
        "tasks_completed": tasks_completed,
        "total_sessions": total_sessions,
        "total_time_minutes": round(total_time_seconds / 60, 1),
        "raw_sessions": raw_sessions # 👈 دي اللي هترسم الـ Charts والجداول للدكتور
    }

