from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from src.infrastructure.database import get_db
from src.domain.models.job import JobApplication
from src.domain.models.user import User
from src.presentation.api.dependencies import get_current_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/jobs", tags=["jobs"])

class JobApplicationCreate(BaseModel):
    id: str
    company_name: str
    job_title: str
    applied_date: datetime
    status: str
    notes: str = ""

@router.get("/", response_model=List[Dict[str, Any]])
def get_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(JobApplication).filter(JobApplication.user_id == current_user.id).order_by(JobApplication.applied_date.desc()).all()
    return [
        {
            "id": item.id,
            "company_name": item.company_name,
            "job_title": item.job_title,
            "applied_date": item.applied_date.isoformat(),
            "status": item.status,
            "notes": item.notes
        } for item in items
    ]

@router.post("/", response_model=dict)
def save_job(item: JobApplicationCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(JobApplication).filter(JobApplication.id == item.id).first()
    if existing:
        existing.status = item.status
        existing.notes = item.notes
    else:
        new_item = JobApplication(
            id=item.id,
            user_id=current_user.id,
            company_name=item.company_name,
            job_title=item.job_title,
            applied_date=item.applied_date,
            status=item.status,
            notes=item.notes
        )
        db.add(new_item)
    db.commit()
    return {"message": "Job saved successfully"}

@router.delete("/{item_id}", response_model=dict)
def delete_job(item_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(JobApplication).filter(JobApplication.id == item_id, JobApplication.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Job not found")
    
    db.delete(item)
    db.commit()
    return {"message": "Job deleted"}
