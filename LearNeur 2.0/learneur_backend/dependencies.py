from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
import models, database, auth

# This tells FastAPI to look for the "Authorization: Bearer <token>" header
security = HTTPBearer()

def get_current_parent(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(database.get_db)):
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the JWT
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        
        if email is None or role != models.RoleEnum.PARENT.value:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    # Find the User, then find the associated Parent profile
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise credentials_exception
        
    parent = db.query(models.Parent).filter(models.Parent.user_id == user.id).first()
    if not parent:
        raise credentials_exception
        
    return parent