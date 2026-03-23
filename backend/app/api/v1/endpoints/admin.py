from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter()

def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user

@router.get("/users", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    current_superuser: User = Depends(get_current_superuser),
) -> Any:
    """
    Retrieve all users. Only for superusers.
    """
    users = db.query(User).all()
    return users

@router.patch("/users/{user_id}/toggle-active", response_model=UserResponse)
def toggle_user_active(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_superuser: User = Depends(get_current_superuser),
) -> Any:
    """
    Block or unblock a user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_superuser.id:
        raise HTTPException(status_code=400, detail="Superuser cannot block themselves")

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_superuser: User = Depends(get_current_superuser),
) -> None:
    """
    Delete a user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_superuser.id:
        raise HTTPException(status_code=400, detail="Superuser cannot delete themselves")

    db.delete(user)
    db.commit()
    return None
