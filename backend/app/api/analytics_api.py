from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from uuid import UUID

from app.core.database import get_db
from app.models.user import User
from app.models.upload import Upload, MergedDataset
from app.models.session import AnalysisSession
from app.models.analysis import DataQualityReport, StatisticalFinding, AIInsightReport
from app.api.deps import get_current_user
from app.ai.interpreter import nl_query_to_chart

import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class ExploreRequest(BaseModel):
    question: str

def get_authorized_upload(upload_id: UUID, db: Session, current_user: User):
    # Check if it's a regular Upload
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if upload:
        if upload.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this dataset")
        return upload
        
    # Check if it's a MergedDataset
    merged = db.query(MergedDataset).filter(MergedDataset.id == upload_id).first()
    if merged:
        session = db.query(AnalysisSession).filter(AnalysisSession.id == merged.session_id).first()
        if not session or session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this dataset")
        return merged
        
    raise HTTPException(status_code=404, detail="Dataset not found")

@router.get("/{upload_id}/trust-score")
def get_trust_score(upload_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns the Data Trust Score™ and its breakdown for a dataset.
    """
    get_authorized_upload(upload_id, db, current_user)
    
    quality_report = db.query(DataQualityReport).filter(DataQualityReport.upload_id == upload_id).first()
    if not quality_report:
        raise HTTPException(status_code=404, detail="Quality report not found for this dataset")
        
    findings = quality_report.findings
    trust_score_info = findings.get("trust_score")
    
    if not trust_score_info:
        raise HTTPException(status_code=400, detail="Trust score has not been calculated for this dataset yet")
        
    return trust_score_info

@router.get("/{upload_id}/correlations")
def get_correlations(upload_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns the Pearson correlation matrix and flagged strong correlations.
    """
    get_authorized_upload(upload_id, db, current_user)
    
    stat_report = db.query(StatisticalFinding).filter(StatisticalFinding.upload_id == upload_id).first()
    if not stat_report:
        raise HTTPException(status_code=404, detail="Statistical report not found for this dataset")
        
    # Standardize return object in case correlation isn't computed (e.g. fewer than 2 numeric columns)
    correlations = stat_report.correlations if stat_report.correlations is not None else {"matrix": {}, "strong_correlations": []}
    return correlations

@router.get("/{upload_id}/distributions")
def get_distributions(upload_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns histogram bins and distribution shape metrics per column.
    """
    get_authorized_upload(upload_id, db, current_user)
    
    stat_report = db.query(StatisticalFinding).filter(StatisticalFinding.upload_id == upload_id).first()
    if not stat_report:
        raise HTTPException(status_code=404, detail="Statistical report not found for this dataset")
        
    distributions = stat_report.distributions if stat_report.distributions is not None else {}
    return distributions

@router.get("/{upload_id}/trends")
def get_trends(upload_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns aggregated time-series data and moving averages for trend visualization.
    """
    get_authorized_upload(upload_id, db, current_user)
    
    stat_report = db.query(StatisticalFinding).filter(StatisticalFinding.upload_id == upload_id).first()
    if not stat_report:
        raise HTTPException(status_code=404, detail="Statistical report not found for this dataset")
        
    trends = stat_report.trends if stat_report.trends is not None else {"primary_datetime_column": None, "resample_period": None, "series": [], "metrics": {}}
    return trends

@router.get("/{upload_id}/summary")
def get_ai_summary(upload_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Returns the AI interpretation report.
    """
    get_authorized_upload(upload_id, db, current_user)
    
    ai_report = db.query(AIInsightReport).filter(AIInsightReport.upload_id == upload_id).first()
    if not ai_report:
        raise HTTPException(status_code=404, detail="AI insight report not found for this dataset")
        
    return {
        "summary": ai_report.summary,
        "interpretation": ai_report.interpretation
    }

@router.post("/{upload_id}/explore")
def explore_dataset_nl(
    upload_id: UUID, 
    request: ExploreRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Accepts a natural language question about the dataset and returns a textual answer + Recharts config.
    """
    get_authorized_upload(upload_id, db, current_user)
    
    # 1. Fetch all deterministic findings to provide as strict context to the AI
    quality_report = db.query(DataQualityReport).filter(DataQualityReport.upload_id == upload_id).first()
    stat_report = db.query(StatisticalFinding).filter(StatisticalFinding.upload_id == upload_id).first()
    
    if not quality_report or not stat_report:
        raise HTTPException(status_code=400, detail="Dataset deterministic analyses must be completed first.")
        
    # Get the findings or fallback to empty structures
    quality_findings = quality_report.findings
    
    stat_findings = {
        "metrics": stat_report.metrics,
        "anomalies": stat_report.anomalies
    }
    
    correlation_findings = stat_report.correlations if stat_report.correlations is not None else {}
    trend_findings = stat_report.trends if stat_report.trends is not None else {}
    
    # 2. Run NL translation service
    result = nl_query_to_chart(
        question=request.question,
        quality_findings=quality_findings,
        stat_findings=stat_findings,
        correlation_findings=correlation_findings,
        trend_findings=trend_findings
    )
    
    return result
