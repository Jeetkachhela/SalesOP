from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.interactions import UserAnnotation, ChatHistory
from app.models.session import AnalysisSession
from app.models.upload import Upload
from app.models.analysis import AIInsightReport
from app.api.deps import get_current_user
from app.ai.interpreter import chat_with_insights
import logging
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

class AnnotationRequest(BaseModel):
    session_id: str
    reference_key: str
    note: str

class ChatRequest(BaseModel):
    session_id: str
    upload_id: str # The active upload/merged dataset being queried
    message: str

@router.post("/annotations", status_code=status.HTTP_201_CREATED)
def add_annotation(
    request: AnnotationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify session ownership to prevent IDOR
    session = db.query(AnalysisSession).filter(AnalysisSession.id == request.session_id).first()
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")

    annotation = UserAnnotation(
        user_id=current_user.id,
        session_id=request.session_id,
        reference_key=request.reference_key,
        note=request.note
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return {"message": "Annotation added", "annotation_id": annotation.id}

@router.get("/annotations/{session_id}")
def get_annotations(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify session ownership to prevent IDOR
    session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")

    annotations = db.query(UserAnnotation).filter(
        UserAnnotation.session_id == session_id,
        UserAnnotation.user_id == current_user.id
    ).all()
    return annotations

@router.post("/chat")
def interact_with_ai(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Verify session ownership to prevent IDOR
    session = db.query(AnalysisSession).filter(AnalysisSession.id == request.session_id).first()
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")

    # 2. Verify dataset ownership to prevent BOLA
    upload = db.query(Upload).filter(Upload.id == request.upload_id).first()
    if not upload or upload.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")

    # Save user message
    user_msg = ChatHistory(
        session_id=request.session_id,
        user_id=current_user.id,
        role="user",
        content=request.message
    )
    db.add(user_msg)
    db.commit()
    
    # Get current insights for the upload/merged dataset
    insight_report = db.query(AIInsightReport).filter(AIInsightReport.upload_id == request.upload_id).first()
    insights = insight_report.interpretation if insight_report else {}
    
    # Get annotations
    annotations_db = db.query(UserAnnotation).filter(UserAnnotation.session_id == request.session_id).all()
    annotations = [{"reference": a.reference_key, "note": a.note} for a in annotations_db]
    
    # Get recent chat
    recent_chat_db = db.query(ChatHistory).filter(
        ChatHistory.session_id == request.session_id
    ).order_by(ChatHistory.created_at.asc()).all()
    past_chat = [{"role": c.role, "content": c.content} for c in recent_chat_db]
    
    # Call AI
    assistant_reply = chat_with_insights(
        question=request.message,
        past_chat=past_chat,
        annotations=annotations,
        current_insights=insights
    )
    
    # Save assistant message
    ai_msg = ChatHistory(
        session_id=request.session_id,
        user_id=current_user.id,
        role="assistant",
        content=assistant_reply
    )
    db.add(ai_msg)
    db.commit()
    
    return {"reply": assistant_reply}
