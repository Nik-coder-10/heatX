from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db

router = APIRouter()


@router.get("/", response_model=List[dict])
async def read_notifications(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return []


@router.get("/{notification_id}", response_model=dict)
async def read_notification(notification_id: int, db: Session = Depends(get_db)):
    return {"id": notification_id, "message": f"Notification {notification_id}", "is_read": False, "created_at": "2024-01-01T00:00:00Z"}


@router.post("/", response_model=dict)
async def create_notification(notification: dict, db: Session = Depends(get_db)):
    return {**notification, "id": 1}


@router.put("/{notification_id}", response_model=dict)
async def update_notification(notification_id: int, notification: dict, db: Session = Depends(get_db)):
    return {**notification, "id": notification_id}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(notification_id: int, db: Session = Depends(get_db)):
    return None