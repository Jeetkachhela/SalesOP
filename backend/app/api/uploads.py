from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.upload import Upload
from app.models.analysis import DataQualityReport, StatisticalFinding, AIInsightReport
from app.schemas.upload import UploadResponse
from app.api.deps import get_current_user
from app.processing.parser import parse_and_sanitize_csv
from app.analytics.quality import evaluate_data_quality
from app.analytics.statistics import evaluate_statistics_and_anomalies
from app.analytics.correlation import evaluate_correlations
from app.analytics.distribution import evaluate_distributions
from app.analytics.trends import evaluate_trends
from app.ai.interpreter import generate_ai_insights
import logging
import time
import os
import io
import pandas as pd

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB limit for MVP
ALLOWED_MIME_TYPES = ["text/csv", "application/vnd.ms-excel"]

def process_upload_background(upload_id: str, file_bytes: bytes, db: Session):
    logger.info(f"Background task started for upload {upload_id}")
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        return
    
    try:
        upload.status = "PARSING"
        db.commit()
        
        # Save file to disk for merging later
        os.makedirs("data/uploads", exist_ok=True)
        file_path = f"data/uploads/{upload_id}.csv"
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        
        # Simulate heavy parsing + chunked sanitization
        df = parse_and_sanitize_csv(file_bytes)
        
        # In a full MVP, we would now pass this df to Schema detection and Quality detection
        # Schema & Quality Analysis
        upload.status = "SCHEMA_ANALYSIS"
        db.commit()
        quality_findings = evaluate_data_quality(df)
        quality_report = DataQualityReport(upload_id=upload.id, findings=quality_findings)
        db.add(quality_report)
        db.commit()
        
        # Statistical & Advanced Analysis
        upload.status = "STATISTICAL_ANALYSIS"
        db.commit()
        
        stat_findings = evaluate_statistics_and_anomalies(df)
        correlation_findings = evaluate_correlations(df)
        distribution_findings = evaluate_distributions(df)
        trend_findings = evaluate_trends(df)
        
        stat_report = StatisticalFinding(
            upload_id=upload.id, 
            anomalies=stat_findings["anomalies"], 
            metrics=stat_findings["metrics"],
            correlations=correlation_findings,
            distributions=distribution_findings,
            trends=trend_findings
        )
        db.add(stat_report)
        db.commit()
        
        # AI Interpretation
        upload.status = "AI_INTERPRETATION"
        db.commit()
        ai_insights = generate_ai_insights(quality_findings, stat_findings)
        
        # We assume the AI returns a summary field as per prompt format.
        summary_text = ai_insights.get("summary", "AI interpretation completed.") if isinstance(ai_insights, dict) else "Error generating summary."
        
        ai_report = AIInsightReport(
            upload_id=upload.id,
            summary=summary_text,
            interpretation=ai_insights
        )
        db.add(ai_report)
        db.commit()
        
        upload.status = "VISUALIZATION_READY"
        db.commit()
        
        logger.info(f"Upload {upload_id} successfully parsed, analyzed, stats generated, and AI interpreted.")
        
    except ValueError as e:
        upload.status = "FAILED"
        upload.error_message = str(e)
        db.commit()
    except Exception as e:
        upload.status = "FAILED"
        upload.error_message = "An unexpected error occurred during processing."
        db.commit()
        logger.error(f"Unexpected error for upload {upload_id}: {str(e)}")


@router.post("/", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV files are allowed.")
    
    # Read file to check size
    file_bytes = await file.read()
    file_size = len(file_bytes)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the 50MB limit.")
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    
    upload = Upload(
        user_id=current_user.id,
        filename=file.filename,
        file_size_bytes=file_size,
        mime_type=file.content_type,
        status="UPLOADED"
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    
    # Start background processing
    background_tasks.add_task(process_upload_background, upload.id, file_bytes, db)
    
    return upload

@router.get("/", response_model=list[UploadResponse])
def list_uploads(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    uploads = db.query(Upload).filter(Upload.user_id == current_user.id).order_by(Upload.created_at.desc()).all()
    return uploads
