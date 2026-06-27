from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, schemas, database
from dependencies import get_current_parent

router = APIRouter(prefix="/game", tags=["Telemetry Engine"])

@router.post("/telemetry", status_code=status.HTTP_201_CREATED)
def save_telemetry(
    payload: schemas.TelemetryCreate, 
    db: Session = Depends(database.get_db), 
    current_parent: models.Parent = Depends(get_current_parent)
):
    child = db.query(models.Child).filter(
        models.Child.id == payload.child_id, 
        models.Child.parent_id == current_parent.id
    ).first()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Unauthorized. This child profile does not belong to your account."
        )

    new_session = models.GameSession(
        child_id=payload.child_id,
        game_name=payload.game_name,
        time_taken_seconds=payload.time_taken_seconds,
        total_clicks=payload.total_clicks,
        frantic_clicks=payload.frantic_clicks,
        is_completed=payload.is_completed
    )
    
    db.add(new_session)
    db.commit()
    
    return {"status": "success", "message": "Telemetry data securely logged."}

@router.get("/telemetry", response_model=list[schemas.TelemetryResponse], status_code=status.HTTP_200_OK)
def get_telemetry(
    child_id: int, 
    db: Session = Depends(database.get_db), 
    current_parent: models.Parent = Depends(get_current_parent)
):
    """
    Retrieves all historical game sessions and neuro-telemetry metrics for a specific child,
    strictly restricted to the authenticated parent's context scope.
    """
    # 1. التحقق من صلاحية وصول الأب للطفل المطلوب لمنع التلاعب
    child = db.query(models.Child).filter(
        models.Child.id == child_id, 
        models.Child.parent_id == current_parent.id
    ).first()
    
    if not child:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access Denied. The requested child profile is not linked to your parent account."
        )

    # 2. سحب البيانات وتصنيفها ترتيبياً من الأقدم للأحدث
    telemetry_records = db.query(models.GameSession).filter(
        models.GameSession.child_id == child_id
    ).order_by(models.GameSession.id.asc()).all()
    
    return telemetry_records
