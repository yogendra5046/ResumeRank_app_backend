from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from src.infrastructure.database import get_db
from src.domain.models.history import HistoryItem
from src.domain.models.user import User
from src.presentation.api.dependencies import get_current_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/history", tags=["history"])

class HistoryItemCreate(BaseModel):
    id: str
    file_name: str
    date: datetime
    score: int
    percentile: int
    missing_keywords: list = []
    suggestions: list = []
    full_result_json: str = None

@router.get("/", response_model=List[Dict[str, Any]])
def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(HistoryItem).filter(HistoryItem.user_id == current_user.id).order_by(HistoryItem.date.desc()).all()
    return [
        {
            "id": item.id,
            "file_name": item.file_name,
            "date": item.date.isoformat(),
            "score": item.score,
            "percentile": item.percentile,
            "missing_keywords": item.missing_keywords,
            "suggestions": item.suggestions,
            "full_result_json": item.full_result_json
        } for item in items
    ]

@router.post("/", response_model=dict)
def save_history(item: HistoryItemCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(HistoryItem).filter(HistoryItem.id == item.id).first()
    if existing:
        return {"message": "History item already exists"}
    
    new_item = HistoryItem(
        id=item.id,
        user_id=current_user.id,
        file_name=item.file_name,
        date=item.date,
        score=item.score,
        percentile=item.percentile,
        missing_keywords=item.missing_keywords,
        suggestions=item.suggestions,
        full_result_json=item.full_result_json
    )
    db.add(new_item)
    db.commit()
    return {"message": "History saved successfully"}

@router.delete("/{item_id}", response_model=dict)
def delete_history_item(item_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(HistoryItem).filter(HistoryItem.id == item_id, HistoryItem.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(item)
    db.commit()
    return {"message": "Item deleted"}

@router.delete("/", response_model=dict)
def clear_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(HistoryItem).filter(HistoryItem.user_id == current_user.id).delete()
    db.commit()
    return {"message": "History cleared"}
