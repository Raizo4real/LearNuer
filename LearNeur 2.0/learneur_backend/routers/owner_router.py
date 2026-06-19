from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, EmailHistory , Doctor , Parent , Admin# Add Parent, Doctor, Admin models if separated
from auth import get_current_user, get_password_hash
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/admin", tags=["Admin & Owner Dashboard"])

# دي الـ Schema اللي هتستقبل بيانات الإضافة والتعديل من الفرونت إند
class UpdateProfileSchema(BaseModel):
    full_name: str
    email: str
    password: Optional[str] = None
    specialty: Optional[str] = None

# --- DEPENDENCY: Role Checker ---
def require_admin_or_owner(current_user: User = Depends(get_current_user)):
    """Dependency to restrict access to ADMIN and OWNER roles."""
    # If the user is the hardcoded owner, their token decoding might yield a mock User object 
    # or just a dict depending on how your get_current_user is written.
    # Assuming get_current_user returns a User object with a 'role' property:
    if current_user.role not in ["ADMIN", "OWNER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Insufficient clearance. Admin or Owner required."
        )
    return current_user

# Apply the dependency to ALL routes in this router
deps = [Depends(require_admin_or_owner)]

# --- حارس رقم 1: للموظفين والأونر (عشان يشوفوا الدكاترة والأهالي) ---
def require_admin_or_owner(current_user: User = Depends(get_current_user)):
    # 💡 التريكة: بنستخرج الكلمة كنص (String) سواء كانت Enum أو String جاهز
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    
    if user_role not in ["ADMIN", "OWNER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Insufficient clearance. Admin or Owner required."
        )
    return current_user

# --- حارس رقم 2: للأونر بس (عشان يدير الآدمنز) ---
def require_owner_only(current_user: User = Depends(get_current_user)):
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    
    if user_role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Super-admin (Owner) clearance required for this action."
        )
    return current_user

# المتغيرين دول بنركبهم على مسارات الـ APIs
deps = [Depends(require_admin_or_owner)]
owner_deps = [Depends(require_owner_only)]

# ==========================================
# 1. DOCTORS ENDPOINTS
# ==========================================

@router.get("/doctors/pending", dependencies=deps)
def get_pending_doctors(db: Session = Depends(get_db)):
    doctors = db.query(Doctor).filter(Doctor.is_approved == False).all()
    result = []
    for doc in doctors:
        result.append({
            "id": doc.id,
            "full_name": doc.full_name, 
            "specialty": getattr(doc, "specialty", "N/A"),
            "email": doc.user.email if doc.user else "No Email",
            "document_url": getattr(doc, "verification_document_url", "#")
        })
    return result

@router.get("/doctors/approved", dependencies=deps)
def get_approved_doctors(db: Session = Depends(get_db)):
    doctors = db.query(Doctor).filter(Doctor.is_approved == True).all()
    result = []
    for doc in doctors:
        result.append({
            "id": doc.id,
            "full_name": doc.full_name,
            "specialty": getattr(doc, "specialty", "N/A"),
            "email": doc.user.email if doc.user else "No Email",
            "document_url": getattr(doc, "verification_document_url", "#")
        })
    return result

# 👈 دالة الموافقة اللي كانت ممسوحة
@router.put("/doctors/{doctor_id}/approve", dependencies=deps)
def approve_doctor(doctor_id: str, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == str(doctor_id)).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    doctor.is_approved = True
    db.commit()
    return {"message": "Doctor approved successfully."}

# 👈 دالة الرفض/المسح متعدلة لـ str وبتكلم جدول Doctor
@router.delete("/doctors/{doctor_id}", dependencies=deps)
def delete_doctor(doctor_id: str, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == str(doctor_id)).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # بنحفظ الـ ID بتاع اليوزر قبل ما نمسح الدكتور
    user_to_delete = doctor.user 
    
    # 1. بنمسح الدكتور
    db.delete(doctor)
    
    # 2. بنمسح اليوزر (عشان نفضي الإيميل)
    if user_to_delete:
        db.delete(user_to_delete)
        
    db.commit()
    return {"message": "Doctor and associated account deleted successfully."}
# ==========================================
# 2. PARENTS ENDPOINTS
# ==========================================

@router.get("/parents", dependencies=deps)
def get_all_parents(db: Session = Depends(get_db)):
    # بنجيب الداتا من جدول الـ Parent
    parents = db.query(Parent).all()
    
    # بنجهز الداتا زي ما الفرونت إند طالبها بالظبط
    result = []
    for parent in parents:
        result.append({
            "id": parent.id,
            "full_name": getattr(parent, "full_name", "N/A"), # استخدمنا getattr تحسباً لو مفيش اسم
            "email": parent.user.email if parent.user else "No Email", # بنجيب الإيميل من جدول الـ User المرتبط
            "user_id": parent.user_id # محتاجينه عشان الـ Email History
        })
    return result

@router.delete("/parents/{parent_id}", dependencies=deps)
def delete_parent(parent_id: str, db: Session = Depends(get_db)):
    parent = db.query(Parent).filter(Parent.id == str(parent_id)).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    
    # بنحفظ الـ ID بتاع اليوزر 
    user_to_delete = parent.user
    
    # 1. بنمسح ولي الأمر
    db.delete(parent)
    
    # 2. بنمسح اليوزر المرتبط بيه
    if user_to_delete:
        db.delete(user_to_delete)
        
    db.commit()
    return {"message": "Parent and associated account deleted successfully."}

# ==========================================
# 3. ADMINS ENDPOINTS
# ==========================================

@router.get("/admins", dependencies=owner_deps)
async def get_all_admins(db: Session = Depends(get_db)):
    admins = db.query(User).filter(User.role == "ADMIN").all()
    return admins

@router.post("/admins", dependencies=owner_deps)
async def create_admin(email: str, password: str, name: str, db: Session = Depends(get_db)):
    # 1. نتأكد إن الإيميل مش متسجل قبل كده
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. ننشئ حساب اليوزر الجديد
    new_user = User(
        email=email,
        password_hash=get_password_hash(password),
        role="ADMIN",
        is_active=True
        
    )
    db.add(new_user)
    db.flush() # 

    # 3. ننشئ بروفايل للآدمن ونربطه باليوزر
    new_admin = Admin(
        user_id=new_user.id,
        admin_level=1 
    )
    db.add(new_admin)
    db.commit()

    return {"message": f"Admin {name} created successfully!"}

@router.delete("/admins/{admin_id}", dependencies=owner_deps)
async def delete_admin(admin_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin_or_owner)):
    admin_to_delete = db.query(User).filter(User.id == admin_id, User.role == "ADMIN").first()
    if not admin_to_delete:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    # Prevent admin from deleting themselves or the owner
    if admin_to_delete.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")
        
    db.delete(admin_to_delete)
    db.commit()
    return {"message": "Admin deleted successfully."}


# ==========================================
# 4. EMAIL HISTORY ENDPOINTS
# ==========================================

@router.get("/users/{user_id}/email-history", dependencies=deps)
async def get_user_email_history(user_id: int, db: Session = Depends(get_db)):
    history = db.query(EmailHistory).filter(EmailHistory.user_id == user_id).order_by(EmailHistory.changed_at.desc()).all()
    if not history:
        return []
    
    return [
        {
            "id": record.id,
            "old_email": record.old_email,
            "new_email": record.new_email,
            "changed_at": record.changed_at
        }
        for record in history
    ]


# ==========================================
# 5. DIRECT ADD & EDIT ENDPOINTS
# ==========================================

# 1. إضافة ولي أمر مباشر (بدون تفعيل إيميل)
@router.post("/parents/direct", dependencies=deps)
def add_parent_direct(data: UpdateProfileSchema, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user: 
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # بنعمل يوزر جديد وبنشفّر الباسورد
    new_user = User(
        email=data.email, 
        password_hash=get_password_hash(data.password), # تأكد إن اسم العمود password_hash أو hashed_password حسب الموديل بتاعك
        role="PARENT", 
        is_active=True
    )
    db.add(new_user)
    db.flush()
    
    # بنعمل البروفايل وبنخليه Verified أوتوماتيك
    new_parent = Parent(
        user_id=new_user.id, 
        full_name=data.full_name, 
        is_email_verified=True # 👈 السر هنا
    )
    db.add(new_parent)
    db.commit()
    return {"message": "Parent added and verified instantly."}

# 2. تعديل بيانات ولي الأمر
@router.put("/parents/{parent_id}", dependencies=deps)
def update_parent(parent_id: str, data: UpdateProfileSchema, db: Session = Depends(get_db)):
    parent = db.query(Parent).filter(Parent.id == str(parent_id)).first()
    if not parent: 
        raise HTTPException(status_code=404, detail="Parent not found")
    
    parent.full_name = data.full_name
    parent.user.email = data.email
    if data.password: # لو كتب باسورد جديد هنشفره ونحدثه
        parent.user.password_hash = get_password_hash(data.password)
    
    db.commit()
    return {"message": "Parent updated successfully"}

# 3. تعديل بيانات الدكتور
@router.put("/doctors/{doctor_id}", dependencies=deps)
def update_doctor(doctor_id: str, data: UpdateProfileSchema, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == str(doctor_id)).first()
    if not doctor: 
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    doctor.full_name = data.full_name
    if data.specialty:
        doctor.specialty = data.specialty
    doctor.user.email = data.email
    if data.password:
        doctor.user.password_hash = get_password_hash(data.password)
    
    db.commit()
    return {"message": "Doctor updated successfully"}


# 4. إضافة دكتور مباشر (وموافق عليه أوتوماتيك)
@router.post("/doctors/direct", dependencies=deps)
def add_doctor_direct(data: UpdateProfileSchema, db: Session = Depends(get_db)):
    if not data.specialty:
        raise HTTPException(status_code=400, detail="Specialty is required for doctors.")
        
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user: 
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # يوزر جديد بصلاحية دكتور
    new_user = User(
        email=data.email, 
        password_hash=get_password_hash(data.password), 
        role="DOCTOR", 
        is_active=True
    )
    db.add(new_user)
    db.flush()
    
    # بروفايل دكتور متوافق عليه جاهز
    new_doctor = Doctor(
        user_id=new_user.id, 
        full_name=data.full_name,
        specialty=data.specialty,
        verification_document_url="Added Directly by Owner", # رسالة وهمية لأن الـ Owner هو اللي ضافه
        is_approved=True, # 👈 متوافق عليه أوتوماتيك
        rating=0
    )
    db.add(new_doctor)
    db.commit()
    return {"message": "Doctor added and approved instantly."}

