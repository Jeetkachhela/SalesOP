from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.upload import Upload, MergedDataset
from app.models.analysis import DataQualityReport, StatisticalFinding
from app.models.session import AnalysisSession
from app.api.deps import get_current_user
from app.processing.merge import merge_datasets
from app.analytics.quality import evaluate_data_quality
from app.analytics.statistics import evaluate_statistics_and_anomalies
from app.analytics.correlation import evaluate_correlations
from app.analytics.distribution import evaluate_distributions
from app.analytics.trends import evaluate_trends
from app.ai.interpreter import generate_ai_insights
import logging
import os
import pandas as pd
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
logger = logging.getLogger(__name__)

from typing import List, Optional

class MergeRequest(BaseModel):
    session_id: Optional[str] = None
    upload_id_1: Optional[str] = None
    upload_id_2: Optional[str] = None
    upload_ids: Optional[List[str]] = None
    join_type: str = "inner"
    left_on: Optional[str] = None
    right_on: Optional[str] = None
    merged_name: str = "Merged Dataset"

def process_merge_background(merged_dataset_id: str, df: pd.DataFrame, db: Session):
    logger.info(f"Background task started for merged dataset {merged_dataset_id}")
    merged_ds = db.query(MergedDataset).filter(MergedDataset.id == merged_dataset_id).first()
    upload_entry = db.query(Upload).filter(Upload.id == merged_dataset_id).first()
    if not merged_ds:
        return
        
    try:
        # Schema & Quality Analysis
        merged_ds.status = "SCHEMA_ANALYSIS"
        if upload_entry:
            upload_entry.status = "SCHEMA_ANALYSIS"
        db.commit()
        quality_findings = evaluate_data_quality(df)
        quality_report = DataQualityReport(upload_id=merged_ds.id, findings=quality_findings)
        db.add(quality_report)
        db.commit()
        
        # Statistical Analysis
        merged_ds.status = "STATISTICAL_ANALYSIS"
        if upload_entry:
            upload_entry.status = "STATISTICAL_ANALYSIS"
        db.commit()
        stat_findings = evaluate_statistics_and_anomalies(df)
        correlation_findings = evaluate_correlations(df)
        distribution_findings = evaluate_distributions(df)
        trend_findings = evaluate_trends(df)
        
        stat_report = StatisticalFinding(
            upload_id=merged_ds.id, 
            anomalies=stat_findings["anomalies"], 
            metrics=stat_findings["metrics"],
            correlations=correlation_findings,
            distributions=distribution_findings,
            trends=trend_findings
        )
        db.add(stat_report)
        db.commit()
        
        # AI Interpretation
        merged_ds.status = "AI_INTERPRETATION"
        if upload_entry:
            upload_entry.status = "AI_INTERPRETATION"
        db.commit()
        ai_insights = generate_ai_insights(quality_findings, stat_findings)
        
        summary_text = ai_insights.get("summary", "AI interpretation completed.") if isinstance(ai_insights, dict) else "Error generating summary."
        
        from app.models.analysis import AIInsightReport
        ai_report = AIInsightReport(
            upload_id=merged_ds.id,
            summary=summary_text,
            interpretation=ai_insights
        )
        db.add(ai_report)
        db.commit()
        
        merged_ds.status = "READY"
        if upload_entry:
            upload_entry.status = "VISUALIZATION_READY"
        db.commit()
        
        logger.info(f"Merged Dataset {merged_dataset_id} fully analyzed.")
        
    except Exception as e:
        merged_ds.status = "FAILED"
        if upload_entry:
            upload_entry.status = "FAILED"
            upload_entry.error_message = str(e)
        merged_ds.error_message = str(e)
        db.commit()
        logger.error(f"Merge processing failed: {str(e)}")


@router.post("/merge", status_code=status.HTTP_202_ACCEPTED)
async def merge_datasets_endpoint(
    request: MergeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    import uuid
    
    # 1. Resolve uploads
    u1_id = request.upload_id_1
    u2_id = request.upload_id_2
    
    if request.upload_ids and len(request.upload_ids) >= 2:
        u1_id = request.upload_ids[0]
        u2_id = request.upload_ids[1]
        
    if not u1_id or not u2_id:
        raise HTTPException(status_code=400, detail="Must provide at least two dataset IDs to merge.")
        
    upload1 = db.query(Upload).filter(Upload.id == u1_id, Upload.user_id == current_user.id).first()
    upload2 = db.query(Upload).filter(Upload.id == u2_id, Upload.user_id == current_user.id).first()
    
    if not upload1 or not upload2:
        raise HTTPException(status_code=404, detail="One or both uploads not found.")
        
    # 2. Resolve and auto-create session if it does not exist
    sess_id = request.session_id
    if not sess_id:
        sess_id = str(uuid.uuid4())
        
    session = db.query(AnalysisSession).filter(AnalysisSession.id == sess_id).first()
    if not session:
        session = AnalysisSession(id=sess_id, user_id=current_user.id, name=f"Session for {current_user.email}")
        db.add(session)
        db.commit()
        db.refresh(session)
        
    path1 = f"data/uploads/{upload1.id}.csv"
    path2 = f"data/uploads/{upload2.id}.csv"
    
    # Restore file1 from database if missing on disk (Render free tier ephemeral restart)
    if not os.path.exists(path1):
        if upload1.file_content:
            os.makedirs("data/uploads", exist_ok=True)
            with open(path1, "w", encoding="utf-8") as f:
                f.write(upload1.file_content)
        else:
            raise HTTPException(status_code=400, detail=f"Dataset {upload1.filename} is missing from both disk and database.")
            
    # Restore file2 from database if missing on disk (Render free tier ephemeral restart)
    if not os.path.exists(path2):
        if upload2.file_content:
            os.makedirs("data/uploads", exist_ok=True)
            with open(path2, "w", encoding="utf-8") as f:
                f.write(upload2.file_content)
        else:
            raise HTTPException(status_code=400, detail=f"Dataset {upload2.filename} is missing from both disk and database.")
        
    try:
        df1 = pd.read_csv(path1)
        df2 = pd.read_csv(path2)
        
        merged_df = merge_datasets(
            df1, 
            df2, 
            join_type=request.join_type, 
            left_on=request.left_on, 
            right_on=request.right_on
        )
        
        merged_csv_str = merged_df.to_csv(index=False)
        merged_uuid = uuid.uuid4()
        
        # 1. Create twin Upload entry with same UUID to allow standard uploads UI listing
        upload_entry = Upload(
            id=merged_uuid,
            user_id=current_user.id,
            filename=request.merged_name if request.merged_name.lower().endswith(".csv") else f"{request.merged_name}.csv",
            file_size_bytes=len(merged_csv_str.encode('utf-8')),
            mime_type="text/csv",
            status="PROCESSING",
            file_content=merged_csv_str
        )
        db.add(upload_entry)
        
        # 2. Create MergedDataset row with the same UUID
        merged_dataset = MergedDataset(
            id=merged_uuid,
            session_id=sess_id,
            name=request.merged_name,
            status="PROCESSING",
            file_content=merged_csv_str
        )
        db.add(merged_dataset)
        db.commit()
        db.refresh(merged_dataset)
        
        merged_path = f"data/uploads/{merged_uuid}.csv"
        merged_df.to_csv(merged_path, index=False)
        
        background_tasks.add_task(process_merge_background, merged_dataset.id, merged_df, db)
        
        return {
            "message": "Merge started in background", 
            "id": merged_dataset.id,
            "merged_dataset_id": merged_dataset.id
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error during merge endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error during merge.")
