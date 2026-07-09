from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db

router = APIRouter()


@router.get("/", response_model=List[dict])
async def read_heat_data(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return []


@router.get("/{heat_id}", response_model=dict)
async def read_heat_data_item(heat_id: int, db: Session = Depends(get_db)):
    return {"id": heat_id, "temperature": 25.0, "timestamp": "2024-01-01T00:00:00Z"}


@router.post("/", response_model=dict)
async def create_heat_data(heat_data: dict, db: Session = Depends(get_db)):
    return {**heat_data, "id": 1}


@router.put("/{heat_id}", response_model=dict)
async def update_heat_data(heat_id: int, heat_data: dict, db: Session = Depends(get_db)):
    return {**heat_data, "id": heat_id}


@router.delete("/{heat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_heat_data(heat_id: int, db: Session = Depends(get_db)):
    return None