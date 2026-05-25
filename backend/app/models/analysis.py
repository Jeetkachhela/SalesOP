from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class DataQualityReport(Base):
    __tablename__ = "data_quality_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    upload_id = Column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=False)
    findings = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StatisticalFinding(Base):
    __tablename__ = "statistical_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    upload_id = Column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=False)
    anomalies = Column(JSONB, nullable=False)
    metrics = Column(JSONB, nullable=False)
    correlations = Column(JSONB, nullable=True)
    distributions = Column(JSONB, nullable=True)
    trends = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AIInsightReport(Base):
    __tablename__ = "ai_insight_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    upload_id = Column(UUID(as_uuid=True), ForeignKey("uploads.id"), nullable=False)
    summary = Column(String, nullable=False)
    interpretation = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
