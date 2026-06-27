from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, database
from dependencies import get_current_parent

router = APIRouter(prefix="/analytics", tags=["Analytics Dashboard"])

@router.get("/{child_id}")
def get_child_analytics(
    child_id: int, 
    db: Session = Depends(database.get_db), 
    current_parent: models.Parent = Depends(get_current_parent)
):
    # 1. Security check
    child = db.query(models.Child).filter(
        models.Child.id == child_id, 
        models.Child.parent_id == current_parent.id
    ).first()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Unauthorized access to this profile."
        )
    
    # 2. Fetch all telemetry history ordered chronologically
    sessions = db.query(models.GameSession).filter(
        models.GameSession.child_id == child_id
    ).order_by(models.GameSession.id.asc()).all()
    
    # Handle case where child hasn't played any games yet
    if not sessions:
        return {
            "child_name": child.first_name,
            "summary": {"total_sessions": 0, "avg_time_seconds": 0, "total_frantic_clicks": 0},
            "history": []
        }
    
    # 3. Aggregate Data 
    total_sessions = len(sessions)
    total_time = sum(s.time_taken_seconds for s in sessions)
    avg_time = round(total_time / total_sessions, 2)
    total_frantic = sum(s.frantic_clicks for s in sessions)
    
    # 4. Format timeseries data for the frontend charts
    history = [
        {
            "session_id": f"Session {i + 1}",
            "time_taken": s.time_taken_seconds,
            "frantic_clicks": s.frantic_clicks,
            "created_at": s.created_at.isoformat() if getattr(s, 'created_at', None) else None
        }
        for i, s in enumerate(sessions)
    ]
    
    return {
        "child_name": child.first_name,
        "summary": {
            "total_sessions": total_sessions,
            "avg_time_seconds": avg_time,
            "total_frantic_clicks": total_frantic
        },
        "history": history
    }
