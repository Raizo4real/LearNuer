import bcrypt
from datetime import datetime, timedelta
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256") # الـ HS256

ACCESS_TOKEN_EXPIRE_MINUTES = 259200

# دالة لتشفيير الباسورد (وقت الـ Register)
def get_password_hash(password: str) -> str:
    # بنحول النص لـ bytes الأول لأن bcrypt بيتعامل مع الـ bytes
    password_bytes = password.encode('utf-8')
    # بنولد الـ salt ونشفر
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # بنرجعها كـ string عشان تتخزن في الداتابيز عادي
    return hashed.decode('utf-8')

# دالة للتأكد من صحة الباسورد (وقت الـ Login)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

# دالة توليد التوكن (زي ما هي مفيهاش تغيير)
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt

# استدعاء الـ Database والـ Model
from database import get_db
from models import User  # بفترض إن اسم الكلاس في ملف models.py هو User

# مسار اللوجين اللي بيطلع منه التوكن (لو مسار اللوجين عندك مختلف، غير "login" لاسم المسار)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # بنفك التوكن بنفس الـ SECRET_KEY و الـ ALGORITHM اللي فوق في نفس الملف
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # بنستخرج الإيميل (بافتراض إنك بتخزنه في الـ sub وقت إنشاء التوكن)
        email: str = payload.get("sub")
        role: str = payload.get("role") 

        if email is None:
            raise credentials_exception
       
        if role == "OWNER" and email is not None and email.lower() == "learnuer.owner@gmail.com":
            class MockOwner:
                id = "owner-super-id"
                email = "learnuer.owner@gmail.com"
                role = "OWNER"
                token_role = "OWNER"
            return MockOwner()
        # =================================================
    except Exception:
        raise credentials_exception
    
    # بنبحث عن المستخدم في قاعدة البيانات
    user = db.query(User).filter(User.email == email).first()
    
    if user is None:
        raise credentials_exception
        
    return user
