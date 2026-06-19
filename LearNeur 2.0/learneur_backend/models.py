import enum
from datetime import datetime , timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey , Float , Text , UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import func
import uuid

# Define the Roles
class RoleEnum(enum.Enum):
    ADMIN = "ADMIN"
    DOCTOR = "DOCTOR"
    PARENT = "PARENT"

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships (One-to-One)
    parent_profile = relationship("Parent", back_populates="user", uselist=False, cascade="all, delete-orphan")
    doctor_profile = relationship("Doctor", back_populates="user", uselist=False, cascade="all, delete-orphan")
    admin_profile = relationship("Admin", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Parent(Base):
    __tablename__ = "parents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    full_name = Column(String, nullable=False)
    is_email_verified = Column(Boolean, default=False)
    pin = Column(String, default="0000")
    reset_pin_token = Column(String, nullable=True)
    reset_pin_expires = Column(DateTime, nullable=True)
    avatar_url = Column(String, default="default_parent.png")

    children = relationship("Child", back_populates="parent", cascade="all, delete-orphan")
    user = relationship("User", back_populates="parent_profile")

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    full_name = Column(String, nullable=False)
    specialty = Column(String, nullable=True)
    bio = Column(Text, nullable=True) # 👈 الحقل الجديد اللي ضفناه
    verification_document_url = Column(String, nullable=True)
    is_approved = Column(Boolean, default=False)  # Admin must approve
    rating = Column(Integer, default=0)
    avatar_url = Column(String, default="default_doctor.png")

    user = relationship("User", back_populates="doctor_profile")
    # Note: Relationships to BlogPosts and Messages will be added here

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    admin_level = Column(Integer, default=1) # E.g., 1=Super, 2=Moderator

    user = relationship("User", back_populates="admin_profile")
class Child(Base):
    __tablename__ = "children"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id", ondelete="CASCADE"), nullable=False)
    first_name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    avatar_url = Column(String, default="default_avatar.png")

    game_sessions = relationship("GameSession", back_populates="child", cascade="all, delete-orphan")
    parent = relationship("Parent", back_populates="children")
    autism_profile = relationship("AutismProfile", back_populates="child", uselist=False, cascade="all, delete-orphan")

class AutismProfile(Base):
    __tablename__ = "autism_profiles"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id", ondelete="CASCADE"), unique=True, nullable=False)
    communication_level = Column(String, nullable=False)
    sensory_sensitivities = Column(String, nullable=True)
    special_interests = Column(String, nullable=True)

    child = relationship("Child", back_populates="autism_profile")    

class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True, index=True)
    child_id = Column(Integer, ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    game_name = Column(String, nullable=False)
    time_taken_seconds = Column(Float, nullable=False)
    total_clicks = Column(Integer, default=0)
    frantic_clicks = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)

    child = relationship("Child", back_populates="game_sessions")

class EmailHistory(Base):
    __tablename__ = "email_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    old_email = Column(String, nullable=False)
    new_email = Column(String, nullable=False)
    changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", backref="email_history")   


class DoctorChildConnection(Base):
    __tablename__ = "doctor_child_connections"

    id = Column(Integer, primary_key=True, index=True)
    # NOTE: Change "doctors.id" to "users.id" if your doctors are stored in the main Users table
    doctor_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    child_id = Column(Integer, ForeignKey("children.id", ondelete="CASCADE"), nullable=False)
    
    # Status can be: "pending", "approved", "rejected"
    status = Column(String, default="pending", nullable=False) 
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships (ensure your Doctor and Child models have back-populates if needed)
    doctor = relationship("User", foreign_keys=[doctor_id], backref="child_connections") # Change "Doctor" to "User" if using single table
    child = relationship("Child", backref="doctor_connections")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("doctor_child_connections.id", ondelete="CASCADE"), nullable=False)
    # Using String assuming users.id is a String (UUID)
    sender_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    connection = relationship("DoctorChildConnection", backref="messages")
    sender = relationship("User", backref="sent_messages")

    # ==========================================
# COMMUNITY & GENERAL INQUIRY MODELS (FORUM)
# ==========================================

class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationship
    author = relationship("User", backref="blog_posts")


class GeneralInquirySession(Base):
    __tablename__ = "general_inquiry_sessions"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    related_post_id = Column(Integer, ForeignKey("blog_posts.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    parent = relationship("User", foreign_keys=[parent_id], backref="started_inquiries")
    doctor = relationship("User", foreign_keys=[doctor_id], backref="received_inquiries")
    post = relationship("BlogPost")


class InquiryMessage(Base):
    __tablename__ = "inquiry_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("general_inquiry_sessions.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    
    # 💡 السر هنا: الحقل ده هيخزن جزء من البوست اللي ولي الأمر بيسأل عنه (زي الـ Reply بتاع الواتساب)
    quoted_text = Column(Text, nullable=True) 
    
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    session = relationship("GeneralInquirySession", backref="messages")
    sender = relationship("User", foreign_keys=[sender_id])

class PostLike(Base):
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("blog_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # عشان نمنع المستخدم يعمل لايك للبوست أكتر من مرة
    __table_args__ = (UniqueConstraint('post_id', 'user_id', name='_post_user_uc'),)

from sqlalchemy import UniqueConstraint

class DoctorRating(Base):
    __tablename__ = "doctor_ratings"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating_value = Column(Integer, nullable=False) # من 1 لـ 5

    # منع ولي الأمر من تقييم نفس الدكتور أكتر من مرة (هيعمل Update للقديم)
    __table_args__ = (UniqueConstraint('doctor_id', 'parent_id', name='_doc_parent_rating_uc'),)


