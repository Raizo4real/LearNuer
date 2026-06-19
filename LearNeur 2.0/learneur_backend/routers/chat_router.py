from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime

# Adjust your imports based on your project structure
from database import get_db
from models import User, DoctorChildConnection, Message
from auth import get_current_user

router = APIRouter(prefix="/chat", tags=["Secure Chat"])

# --- SCHEMAS ---
class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: int
    connection_id: int
    sender_id: str
    content: str
    timestamp: datetime

    class Config:
        from_attributes = True

# --- ENDPOINTS ---
@router.get("/{connection_id}", response_model=List[MessageResponse])
async def get_messages(
    connection_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Verify connection exists
    conn = db.query(DoctorChildConnection).filter(DoctorChildConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")
    
    # Security: Ensure current user is either the assigned doctor or the child's parent
    is_authorized = False
    if current_user.role.value == "DOCTOR" and str(conn.doctor_id) == str(current_user.id):
        is_authorized = True
    elif current_user.role.value == "PARENT" and str(conn.child.parent.user_id) == str(current_user.id):
        is_authorized = True

    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized to view this chat.")

    messages = db.query(Message).filter(Message.connection_id == connection_id).order_by(Message.timestamp.asc()).all()
    return messages


@router.post("/{connection_id}", response_model=MessageResponse)
async def send_message(
    connection_id: int, 
    message_data: MessageCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    conn = db.query(DoctorChildConnection).filter(DoctorChildConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")
    
    # Security check for sending messages
    is_authorized = False
    if current_user.role.value == "DOCTOR" and str(conn.doctor_id) == str(current_user.id):
        is_authorized = True
    elif current_user.role.value == "PARENT" and str(conn.child.parent.user_id) == str(current_user.id):
        is_authorized = True

    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized to send messages here.")

    new_message = Message(
        connection_id=connection_id,
        sender_id=str(current_user.id),
        content=message_data.content
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    return new_message