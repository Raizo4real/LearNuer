from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# 1. بنجيب الرابط من ملف الـ .env أو من Railway
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 2. التريكة: لو الرابط بيبدأ بـ postgres بنخليه postgresql عشان SQLAlchemy ميزعلش
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. شلنا الـ connect_args الخاصة بـ SQLite
engine = create_engine(SQLALCHEMY_DATABASE_URL) 

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
