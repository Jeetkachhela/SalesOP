import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def evaluate_statistics_and_anomalies(df: pd.DataFrame) -> dict:
    """
    Evaluates basic statistics and identifies anomalies using z-score or IQR.
    Returns findings as a dictionary suitable for JSONB storage.
    """
    logger.info("Starting deterministic statistical anomaly analysis...")
    
    findings = {
        "metrics": {},
        "anomalies": {}
    }
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        col_series = df[col].dropna()
        if len(col_series) == 0:
            continue
            
        mean = col_series.mean()
        std = col_series.std()
        
        findings["metrics"][col] = {
            "mean": float(mean) if pd.notnull(mean) else None,
            "std": float(std) if pd.notnull(std) else None,
            "min": float(col_series.min()),
            "max": float(col_series.max()),
            "median": float(col_series.median()),
        }
        
        # Simple Z-score anomaly detection (|z| > 3)
        if pd.notnull(std) and std > 0:
            z_scores = np.abs((col_series - mean) / std)
            anomalies = col_series[z_scores > 3]
            
            findings["anomalies"][col] = {
                "anomaly_count": len(anomalies),
                "anomaly_values": anomalies.head(10).tolist(), # store up to 10 for AI context
            }
        else:
            findings["anomalies"][col] = {
                "anomaly_count": 0,
                "anomaly_values": []
            }
            
    return findings
