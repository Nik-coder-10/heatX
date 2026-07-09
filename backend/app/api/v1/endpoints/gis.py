from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db

router = APIRouter()


@router.get("/", response_model=List[dict])
async def read_gis_data(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return []


@router.get("/{gis_id}", response_model=dict)
async def read_gis_data_item(gis_id: int, db: Session = Depends(get_db)):
    return {"id": gis_id, "name": f"GIS Data {gis_id}"}


@router.post("/", response_model=dict)
async def create_gis_data(gis_data: dict, db: Session = Depends(get_db)):
    return {**gis_data, "id": 1}


@router.put("/{gis_id}", response_model=dict)
async def update_gis_data(gis_id: int, gis_data: dict, db: Session = Depends(get_db)):
    return {**gis_data, "id": gis_id}


@router.delete("/{gis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gis_data(gis_id: int, db: Session = Depends(get_db)):
    return None