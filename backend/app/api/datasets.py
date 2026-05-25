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
    if not merged_ds:
        return
        
    try:
        # Schema & Quality Analysis
        merged_ds.status = "SCHEMA_ANALYSIS"
        db.commit()
        quality_findings = evaluate_data_quality(df)
        quality_report = DataQualityReport(upload_id=merged_ds.id, findings=quality_findings)
        db.add(quality_report)
        db.commit()
        
        # Statistical Analysis
        merged_ds.status = "STATISTICAL_ANALYSIS"
        db.commit()
        stat_findings = evaluate_statistics_and_anomalies(df)
        stat_report = StatisticalFinding(
            upload_id=merged_ds.id, 
            anomalies=stat_findings["anomalies"], 
            metrics=stat_findings["metrics"]
        )
        db.add(stat_report)
        db.commit()
        
        # AI Interpretation
        merged_ds.status = "AI_INTERPRETATION"
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
        db.commit()
        
        logger.info(f"Merged Dataset {merged_dataset_id} fully analyzed.")
        
    except Exception as e:
        merged_ds.status = "FAILED"
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
    
    if not os.path.exists(path1) or not os.path.exists(path2):
        raise HTTPException(status_code=400, detail="Data files not found on disk.")
        
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
        
        # Save merged file
        merged_dataset = MergedDataset(
            session_id=sess_id,
            name=request.merged_name,
            status="PROCESSING"
        )
        db.add(merged_dataset)
        db.commit()
        db.refresh(merged_dataset)
        
        merged_path = f"data/uploads/{merged_dataset.id}.csv"
        merged_df.to_csv(merged_path, index=False)
        
        background_tasks.add_task(process_merge_background, merged_dataset.id, merged_df, db)
        
        return {"message": "Merge started in background", "merged_dataset_id": merged_dataset.id}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error during merge endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error during merge.")
