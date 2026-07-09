from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db

router = APIRouter()


@router.get("/", response_model=List[dict])
async def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return []


@router.get("/{project_id}", response_model=dict)
async def read_project(project_id: int, db: Session = Depends(get_db)):
    return {"id": project_id, "name": f"Project {project_id}"}


@router.post("/", response_model=dict)
async def create_project(project: dict, db: Session = Depends(get_db)):
    return {**project, "id": 1}


@router.put("/{project_id}", response_model=dict)
async def update_project(project_id: int, project: dict, db: Session = Depends(get_db)):
    return {**project, "id": project_id}


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    return None