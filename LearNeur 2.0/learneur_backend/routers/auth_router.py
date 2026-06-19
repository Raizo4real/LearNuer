from fastapi import APIRouter, Depends, HTTPException, status ,Response
from fastapi.responses import HTMLResponse 
from sqlalchemy.orm import Session
from datetime import timedelta
from database import get_db
import schemas, models, auth, database
from utils.email_tokens import create_email_verification_token , verify_email_token
from utils.smtp_service import send_verification_email
from fastapi import BackgroundTasks , File, Form, UploadFile
import models
import os
import shutil
import uuid
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login")
def login(credentials: schemas.UserLogin, response: Response, db: Session = Depends(database.get_db)):
    # === 👑 Owner Login Override ===
    if credentials.email.lower() == "learnuer.owner@gmail.com" and credentials.password == "707070@LearNeur.com":
        access_token = auth.create_access_token(data={"sub": credentials.email.lower(), "role": "OWNER"})
        
        # 🍪 زراعة الكوكي للأونر (لمدة 6 شهور)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=6 * 30 * 24 * 60 * 60
        )
        
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "redirect_url": "/owner_dashboard.html",
            "role": "OWNER",
            "message": "Welcome back, Owner!"
        }
    # ===============================
    
    # 1. Find user by email
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    
    if not user or not auth.verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # === 🔒 قفل التحقق من الإيميل (للآباء فقط) ===
    if user.role == models.RoleEnum.PARENT:
        if not user.parent_profile.is_email_verified:
            raise HTTPException(
                status_code=403, 
                detail="Email not verified. Please check your inbox for the verification link."
            )
        
    # 2. HIDDEN ADMIN OVERRIDE LOGIC
    if user.role == models.RoleEnum.ADMIN:
        access_token = auth.create_access_token(data={"sub": user.email, "role": "ADMIN"})
        
        # 🍪 زراعة الكوكي للأدمن (لمدة 6 شهور)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=6 * 30 * 24 * 60 * 60
        )
        
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "redirect_url": "admin-dashboard",
            "role": "ADMIN",
            "message": "Welcome back, Admin!."
        }

    # 3. DOCTOR APPROVAL GATE
    if user.role == models.RoleEnum.DOCTOR:
        doctor_profile = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        if not doctor_profile.is_approved:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Your doctor account is pending Admin approval. Please check your email."
            )
        redirect_url = "/doctor-dashboard"

    # 4. PARENT LOGIN
    elif user.role == models.RoleEnum.PARENT:
        parent_profile = db.query(models.Parent).filter(models.Parent.user_id == user.id).first()
        redirect_url = "/parent-dashboard"

    # Generate JWT (كودك الأصلي اللي بيحفظ الـ email مش الـ id)
    access_token = auth.create_access_token(data={"sub": user.email, "role": user.role.name})
    
    # 🍪 زراعة الكوكي لولي الأمر أو الدكتور (لمدة 6 شهور)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=6 * 30 * 24 * 60 * 60
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "redirect_url": redirect_url,
        "user_id": str(user.id),
        "role": user.role.name
    }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        samesite="lax",
        secure=False
    )
    return {"message": "Logged out successfully"}
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    # 👇 حولنا البيانات لـ Form Data بدل Schema عشان نقدر نرفع معاها ملف
    email: str = Form(...),
    password: str = Form(...),
    role: models.RoleEnum = Form(...),
    name: str = Form(...),
    specialty: str = Form(None), # اختياري عشان ولي الأمر مش بيبعته
    document: UploadFile = File(None) # اختياري لنفس السبب
):
    """
    Registers a new user (Parent or Doctor) and handles real file uploads.
    """
    # 1. Check if a user with this email already exists
    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # 2. Hash the plaintext password
    hashed_password = auth.get_password_hash(password)

    # 3. Create the Base User record
    new_user = models.User(
        email=email,
        password_hash=hashed_password,
        role=role,
        is_active=True
    )
    
    db.add(new_user)
    db.flush()  # عشان نولد الـ UUID بتاع اليوزر

    # 4. Handle Role-Specific Profile Creation
    if role == models.RoleEnum.PARENT:
        new_parent = models.Parent(
            user_id=new_user.id,
            full_name=name,
            is_email_verified=False  
        )
        db.add(new_parent)
        db.commit()
        
        # اللينك السحري والإيميل
        verification_token = create_email_verification_token(new_user.email)
        background_tasks.add_task(send_verification_email, new_user.email, verification_token)
        
        return {"message": "Registration successful! Please check your email to verify your account."}

    elif role == models.RoleEnum.DOCTOR:
        # Validate that Doctor-specific fields were provided
        if not specialty or not document:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Medical specialty and verification document are required for Doctor registration."
            )
            
        # ==========================================
        # 🔥 الرفع الحقيقي للملف (Real File Upload)
        # ==========================================
        upload_dir = "uploads/verification"
        os.makedirs(upload_dir, exist_ok=True) # بيكريت الفولدر لو مش موجود على جهازك أوتوماتيك
        
        # بنعمل اسم مميز للملف عشان مايحصلش تداخل (مثلاً: 1234-anime.jpg)
        file_extension = document.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4().hex[:8]}_{document.filename}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # بنحفظ الملف الحقيقي على الهارد ديسك
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(document.file, buffer)
        # ==========================================
            
        new_doctor = models.Doctor(
            user_id=new_user.id,
            full_name=name,
            specialty=specialty,
            verification_document_url=file_path, # 👈 بنخزن المسار الحقيقي في الداتا بيس
            is_approved=False,  
            rating=0
        )
        db.add(new_doctor)
        redirect_url = "/login"
        message = "Registration successful! Your credentials have been sent to administration for review."

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role specified."
        )

    # 5. Commit both the user and profile atomic transaction safely
    db.commit()

    return {
        "status": "success",
        "message": message,
        "redirect_url": redirect_url
    }

@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email(token: str, db: Session = Depends(get_db)):
    # 1. فك التوكن والتأكد إنه سليم
    email = verify_email_token(token)
    if not email:
        return _get_verification_html("Invalid or Expired Link", "Please request a new verification link.", success=False)
    
    # 2. البحث عن اليوزر في الداتا بيس
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return _get_verification_html("User Not Found", "We couldn't find an account associated with this email.", success=False)
    
    # 3. التأكد إنه ولي أمر (Parent)
    parent = db.query(models.Parent).filter(models.Parent.user_id == user.id).first()
    if not parent:
        return _get_verification_html("Not a Parent Account", "Only parent accounts require email verification.", success=False)
    
    # 4. التحديث في الداتا بيس
    if parent.is_email_verified:
        return _get_verification_html("Already Verified", "Your account is already verified! You can log in now.", success=True)

    parent.is_email_verified = True
    db.commit()

    return _get_verification_html("Verification Successful!", "Your account is now fully active. Welcome to LearNeur.", success=True)

# دالة مساعدة بترجع صفحة الـ HTML الشيك للمستخدم
def _get_verification_html(title: str, message: str, success: bool):
    # تحديد الأيقونة ولون العلامة بناءً على النجاح أو الفشل
    icon = "✨" if success else "⚠️"
    icon_color = "var(--primary)" if success else "var(--danger)"
    
    return f"""
    <!DOCTYPE html>
    <html lang="en" dir="ltr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>LearNeur - {title}</title>
        
        <link href="https://fonts.googleapis.com/css2?family=Fredoka+One&family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
        
        <style>
            /* === THEME VARIABLES === */
            :root {{
                /* Light Mode */
                --bg-gradient: linear-gradient(135deg, #E2E8F0 0%, #EDF2F7 100%);
                --glass-bg: rgba(255, 255, 255, 0.4);
                --glass-border: rgba(255, 255, 255, 0.5);
                --text-main: #2D3748;
                --text-muted: #718096;
                --primary: #4FD1C5;
                --danger: #F56565;
                --shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
            }}

            /* Dark Mode (بيدعم طريقتك في الـ dashboard والـ owner_dashboard) */
            body.dark-mode, body[data-theme="dark"] {{
                /* 👇 دي الخلفية الغامقة اللي هتشتغل كـ افتراضي دلوقتي */
                --bg-gradient: linear-gradient(135deg, #0F2027 0%, #203A43 50%, #2C5364 100%);
                --glass-bg: rgba(15, 23, 42, 0.45);
                --glass-border: rgba(255, 255, 255, 0.08);
                --text-main: #EDF2F7;
                --text-muted: #A0AEC0;
                --primary: #4FD1C5;
                --danger: #FC8181;
                --shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
            }}

            /* === GLOBAL RESET === */
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: 'Nunito', sans-serif;
                transition: background 0.3s ease, color 0.3s ease;
            }}

            body {{
                background: var(--bg-gradient);
                color: var(--text-main);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
            }}

            /* === الخلفية المتحركة (Ambient Background) === */
            body::before {{
                content: '';
                position: fixed;
                top: -50%; left: -50%; width: 200%; height: 200%;
                background: radial-gradient(circle at 50% 50%, rgba(79, 209, 197, 0.08), transparent 40%),
                            radial-gradient(circle at 80% 20%, rgba(99, 179, 237, 0.05), transparent 30%);
                z-index: -1;
                animation: backgroundDrift 20s infinite alternate linear;
                pointer-events: none;
            }}

            @keyframes backgroundDrift {{
                0% {{ transform: translate(0, 0); }}
                100% {{ transform: translate(5%, 5%); }}
            }}

            /* === كارت الإزاز (Glassmorphism Card) === */
            .glass-card {{
                background: var(--glass-bg);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid var(--glass-border);
                box-shadow: var(--shadow);
                border-radius: 24px;
                padding: 3rem 2rem;
                width: 90%;
                max-width: 450px;
                text-align: center;
                animation: fadeIn 0.5s ease-out;
            }}

            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(20px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}

            /* === العناصر الداخلية === */
            .brand-logo {{
                font-family: 'Fredoka One', cursive;
                font-size: 2.2rem;
                color: var(--text-main);
                margin-bottom: 2rem;
                letter-spacing: 1px;
            }}

            .brand-logo span {{
                color: var(--primary);
            }}

            .icon-wrapper {{
                font-size: 4.5rem;
                margin-bottom: 1rem;
                color: {icon_color};
            }}

            h1 {{
                font-size: 1.8rem;
                font-weight: 800;
                margin-bottom: 1rem;
                background: linear-gradient(to right, var(--text-main), #63B3ED);
                -webkit-background-clip: text;
                background-clip: text;
                -webkit-text-fill-color: transparent;
            }}

            p {{
                font-size: 1.05rem;
                color: var(--text-muted);
                font-weight: 600;
                margin-bottom: 2.5rem;
                line-height: 1.6;
            }}

            /* === الزرار الأساسي === */
            .btn-primary {{
                background: linear-gradient(135deg, var(--primary) 0%, #63B3ED 100%);
                color: #0F2027;
                border: none;
                padding: 1rem 2rem;
                border-radius: 12px;
                font-size: 1.1rem;
                font-weight: 800;
                cursor: pointer;
                display: inline-block;
                width: 100%;
                text-decoration: none;
                transition: opacity 0.2s ease, transform 0.2s ease;
                box-shadow: 0 4px 15px rgba(79, 209, 197, 0.3);
            }}

            .btn-primary:hover {{
                opacity: 0.9;
                transform: translateY(-2px);
            }}
        </style>
    </head>
    
    <body class="dark-mode">

        <div class="glass-card">
            <div class="brand-logo">Lear<span>Neur</span></div>
            
            <div class="icon-wrapper">{icon}</div>
            <h1>{title}</h1>
            <p>{message}</p>
            
            <a href="http://127.0.0.1:5500/login.html" class="btn-primary">Continue to Login</a>
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', () => {{
                const currentTheme = localStorage.getItem('theme');
                if (currentTheme === 'light') {{
                    document.body.classList.remove('dark-mode');
                    document.body.removeAttribute('data-theme');
                }}
            }});
        </script>
    </body>
    </html>
    """