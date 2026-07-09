from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db

router = APIRouter()


@router.get("/", response_model=List[dict])
async def read_reports(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return []


@router.get("/{report_id}", response_model=dict)
async def read_report(report_id: int, db: Session = Depends(get_db)):
    return {"id": report_id, "title": f"Report {report_id}", "format": "PDF", "generated_at": "2024-01-01T00:00:00Z"}


@router.post("/", response_model=dict)
async def create_report(report: dict, db: Session = Depends(get_db)):
    return {**report, "id": 1}


@router.put("/{report_id}", response_model=dict)
async def update_report(report_id: int, report: dict, db: Session = Depends(get_db)):
    return {**report, "id": report_id}


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: int, db: Session = Depends(get_db)):
    return None