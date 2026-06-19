from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from pydantic import BaseModel
from database import get_db
from models import User, BlogPost, GeneralInquirySession, InquiryMessage, RoleEnum, Doctor, PostLike
from auth import get_current_user

router = APIRouter(prefix="/forum", tags=["Forum & Community"])

# ==================== Pydantic Models ====================
class PostCreate(BaseModel):
    title: str
    content: str

class InquiryMessageCreate(BaseModel):
    content: str
    quoted_text: Optional[str] = None

# ==========================================
# ENDPOINTS
# ==========================================

# 1. عمل لايك أو إلغاؤه (Toggle Like)
@router.post("/posts/{post_id}/like")
async def toggle_like(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing_like = db.query(PostLike).filter(PostLike.post_id == post_id, PostLike.user_id == str(current_user.id)).first()
    
    if existing_like:
        db.delete(existing_like)  # لو عامل لايك، هنشيله (Unlike)
        db.commit()
        return {"status": "unliked"}
    else:
        new_like = PostLike(post_id=post_id, user_id=str(current_user.id))
        db.add(new_like)
        db.commit()
        return {"status": "liked"}
    
# 2. الدكتور بيكتب بوست (نصيحة/مقال)
@router.post("/posts")
async def create_post(post: PostCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.DOCTOR:
        raise HTTPException(status_code=403, detail="Only doctors can write posts.")
    
    new_post = BlogPost(
        author_id=current_user.id,
        title=post.title,
        content=post.content
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return {"message": "Post published successfully!", "post_id": new_post.id}

# 2. جلب المنشورات (بالترتيب الجديد: الأحدث، التريندنج، الأعلى تقييماً)
@router.get("/posts")
async def get_all_posts(sort_by: str = "latest", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # عمل Subquery عشان نحسب عدد اللايكات لكل بوست بكفاءة
    likes_subq = db.query(PostLike.post_id, func.count(PostLike.id).label('like_count')).group_by(PostLike.post_id).subquery()
    
    query = db.query(BlogPost, func.coalesce(likes_subq.c.like_count, 0).label('total_likes'))\
              .outerjoin(likes_subq, BlogPost.id == likes_subq.c.post_id)

    if sort_by == "top_rated":
        # الأعلى لايكات على الإطلاق
        query = query.order_by(func.coalesce(likes_subq.c.like_count, 0).desc(), BlogPost.created_at.desc())
        
    elif sort_by == "popular":
        # تريندنج: الأعلى لايكات في آخر 24 ساعة فقط
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        query = query.filter(BlogPost.created_at >= yesterday)\
                     .order_by(func.coalesce(likes_subq.c.like_count, 0).desc(), BlogPost.created_at.desc())
                     
    else:
        # الأحدث (الافتراضي)
        query = query.order_by(BlogPost.created_at.desc())

    posts = query.all()
    
    feed = []
    for p, total_likes in posts:
        doc_profile = p.author.doctor_profile if p.author else None
        doctor_name = doc_profile.full_name if doc_profile else "Unknown"
        doctor_rating = doc_profile.rating if doc_profile else 0
        
        # 🌟 الاستخراج الآمن لصورة الدكتور (بدون إيرورز)
        doctor_avatar = getattr(doc_profile, "avatar_url", "default_doctor.png") if doc_profile else "default_doctor.png"
        
        # التأكد هل المستخدم الحالي عامل لايك للبوست ده ولا لأ؟
        is_liked = db.query(PostLike).filter(PostLike.post_id == p.id, PostLike.user_id == str(current_user.id)).first() is not None

        feed.append({
            "post_id": p.id,
            "doctor_id": p.author_id,
            "doctor_name": doctor_name,
            "doctor_rating": doctor_rating,
            "doctor_avatar": doctor_avatar, # 👈 السطر الجديد اتضاف هنا
            "title": p.title,
            "content": p.content,
            "created_at": p.created_at,
            "likes": total_likes,
            "is_liked": is_liked
        })
    return feed

# 3. ولي الأمر بيدوس "شات" تحت البوست (بيفتح Session استفسار جديدة أو بيجيب القديمة)
@router.get("/inquiry/session/{post_id}")
async def get_or_create_inquiry_session(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.PARENT:
        raise HTTPException(status_code=403, detail="Only parents can initiate post inquiries.")
    
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    # بندور هل ولي الأمر ده فتح شات مع الدكتور ده بخصوص البوست ده قبل كده؟
    session = db.query(GeneralInquirySession).filter(
        GeneralInquirySession.parent_id == current_user.id,
        GeneralInquirySession.related_post_id == post_id
    ).first()

    # لو مفيش شات، نكريت شات جديد
    if not session:
        session = GeneralInquirySession(
            parent_id=current_user.id,
            doctor_id=post.author_id,
            related_post_id=post_id
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    return {"session_id": session.id, "doctor_name": post.author.doctor_profile.full_name}

# 4. إرسال وجلب رسائل الاستفسار (بالاقتباس)
@router.post("/inquiry/messages/{session_id}")
async def send_inquiry_message(session_id: int, msg: InquiryMessageCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # التأكد إن الـ Session موجودة
    session = db.query(GeneralInquirySession).filter(GeneralInquirySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    new_msg = InquiryMessage(
        session_id=session_id,
        sender_id=current_user.id,
        content=msg.content,
        quoted_text=msg.quoted_text  # 👈 حفظ الاقتباس لو موجود
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    return new_msg

@router.get("/inquiry/messages/{session_id}")
async def get_inquiry_messages(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    messages = db.query(InquiryMessage).filter(InquiryMessage.session_id == session_id).order_by(InquiryMessage.timestamp.asc()).all()
    return messages

# 5. جلب قائمة الاستفسارات الخاصة بالدكتور
@router.get("/inquiry/doctor-sessions")
async def get_doctor_inquiry_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.DOCTOR:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    sessions = db.query(GeneralInquirySession).filter(GeneralInquirySession.doctor_id == str(current_user.id)).order_by(GeneralInquirySession.created_at.desc()).all()
    
    result = []
    for s in sessions:
        # بنجيب اسم ولي الأمر بأمان
        parent_profile = getattr(s.parent, "parent_profile", None)
        parent_name = getattr(parent_profile, "full_name", "Parent") if parent_profile else "Parent"
        
        post_title = s.post.title if s.post else "Deleted Post"
        result.append({
            "session_id": s.id,
            "parent_name": parent_name,
            "post_title": post_title
        })
    return result