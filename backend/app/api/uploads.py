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
import gzip
import base64
import pandas as pd

router = APIRouter()
logger = logging.getLogger(__name__)

def compress_string(s: str) -> str:
    """Compresses a string to a base64 gzipped string to reduce Neon Postgres payload write sizes by 90%"""
    try:
        compressed = gzip.compress(s.encode('utf-8'))
        return "gz:" + base64.b64encode(compressed).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to compress file content payload: {str(e)}")
        return s

def decompress_string(s: str) -> str:
    """Decompresses a base64 gzipped string if it starts with 'gz:', otherwise returns original"""
    if s and s.startswith("gz:"):
        try:
            compressed_bytes = base64.b64decode(s[3:].encode('utf-8'))
            return gzip.decompress(compressed_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decompress file content payload: {str(e)}")
            return s
    return s

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB limit for MVP
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
            
        # Save file content to database for stateless persistence (Render Free Tier)
        try:
            raw_content = file_bytes.decode('utf-8', errors='ignore')
            upload.file_content = compress_string(raw_content)
            db.commit()
        except Exception as db_err:
            logger.error(f"Failed to save file content to database for upload {upload_id}: {str(db_err)}")

        
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
    # 1. Strict File Extension check
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file extension. Only .csv files are allowed.")
        
    if file.content_type not in ALLOWED_MIME_TYPES and file.content_type != "application/octet-stream":
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV files are allowed.")
    
    # Read file to check size
    file_bytes = await file.read()
    file_size = len(file_bytes)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the 100MB limit.")
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        
    # 2. Prevent Zip Bombs and Binary Exploit Injections
    # Check first 1KB for null bytes
    if b"\x00" in file_bytes[:1024]:
        raise HTTPException(status_code=400, detail="Invalid file format. Binary files/archives are strictly prohibited.")

    
    # Deduplicate: reuse existing upload with same filename for this user, resetting its status and clearing old reports.
    existing_upload = db.query(Upload).filter(
        Upload.user_id == current_user.id,
        Upload.filename == file.filename
    ).first()

    if existing_upload:
        # Clear child reports
        db.query(DataQualityReport).filter(DataQualityReport.upload_id == existing_upload.id).delete()
        db.query(StatisticalFinding).filter(StatisticalFinding.upload_id == existing_upload.id).delete()
        db.query(AIInsightReport).filter(AIInsightReport.upload_id == existing_upload.id).delete()
        
        existing_upload.file_size_bytes = file_size
        existing_upload.mime_type = file.content_type
        existing_upload.status = "UPLOADED"
        existing_upload.error_message = None
        db.commit()
        db.refresh(existing_upload)
        upload = existing_upload
    else:
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

@router.post("/{upload_id}/regenerate", response_model=UploadResponse)
def regenerate_dataset(
    upload_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    upload = db.query(Upload).filter(
        Upload.id == upload_id,
        Upload.user_id == current_user.id
    ).first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Dataset not found.")
        
    # Retrieve file content from disk or database
    file_bytes = None
    file_path = f"data/uploads/{upload_id}.csv"
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
        except Exception as e:
            logger.error(f"Failed to read file from disk for regenerate: {str(e)}")
            
    if not file_bytes and upload.file_content:
        decompressed_content = decompress_string(upload.file_content)
        file_bytes = decompressed_content.encode('utf-8')
        # Re-save to disk for any other processes expecting it
        try:
            os.makedirs("data/uploads", exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(file_bytes)
        except Exception as disk_err:
            logger.error(f"Failed to restore file to disk: {str(disk_err)}")
        
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Dataset content is missing or unavailable.")
        
    # Clear child reports
    db.query(DataQualityReport).filter(DataQualityReport.upload_id == upload.id).delete()
    db.query(StatisticalFinding).filter(StatisticalFinding.upload_id == upload.id).delete()
    db.query(AIInsightReport).filter(AIInsightReport.upload_id == upload.id).delete()
    
    # Reset status
    upload.status = "UPLOADED"
    upload.error_message = None
    db.commit()
    db.refresh(upload)
    
    # Start background processing
    background_tasks.add_task(process_upload_background, upload.id, file_bytes, db)
    
    return upload

@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    upload_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    upload = db.query(Upload).filter(
        Upload.id == upload_id,
        Upload.user_id == current_user.id
    ).first()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Dataset not found.")
        
    # Delete child reports
    db.query(DataQualityReport).filter(DataQualityReport.upload_id == upload.id).delete()
    db.query(StatisticalFinding).filter(StatisticalFinding.upload_id == upload.id).delete()
    db.query(AIInsightReport).filter(AIInsightReport.upload_id == upload.id).delete()
    
    # Delete file from disk
    file_path = f"data/uploads/{upload_id}.csv"
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Failed to delete file from disk: {str(e)}")
            
    db.delete(upload)
    db.commit()
    return
