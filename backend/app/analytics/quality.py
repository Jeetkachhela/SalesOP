import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def evaluate_data_quality(df: pd.DataFrame) -> dict:
    """
    Evaluates schema intelligence, data quality, and computes the Data Trust Score™.
    Returns a dictionary of findings including trust score metrics.
    """
    logger.info("Starting deterministic data quality analysis...")
    
    findings = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns": {}
    }
    
    total_cells = findings["total_rows"] * findings["total_columns"]
    total_missing = 0
    consistent_columns_count = 0
    anomaly_mask = pd.Series(False, index=df.index)
    
    for col in df.columns:
        col_series = df[col]
        missing_count = int(col_series.isnull().sum())
        total_missing += missing_count
        missing_pct = missing_count / findings["total_rows"] if findings["total_rows"] > 0 else 0
        
        # Determine inferred data type
        dtype = str(col_series.dtype)
        inferred_type = "string"
        if pd.api.types.is_numeric_dtype(col_series):
            inferred_type = "numeric"
            
            # Fast vectorized Z-score anomaly detection to flag rows for Trust Score
            mean = col_series.mean()
            std = col_series.std()
            if pd.notnull(std) and std > 0:
                col_anomalies = np.abs((col_series - mean) / std) > 3
                anomaly_mask |= col_anomalies
                    
        elif pd.api.types.is_datetime64_any_dtype(col_series):
            inferred_type = "datetime"
        elif pd.api.types.is_bool_dtype(col_series):
            inferred_type = "boolean"
            
        # Determine consistency (mixed types check)
        # Non-object dtypes (numeric, datetime, bool) are guaranteed to be consistent
        if str(col_series.dtype) != "object":
            is_consistent = True
        else:
            non_null_series = col_series.dropna()
            if len(non_null_series) == 0:
                is_consistent = False
            else:
                inferred = pd.api.types.infer_dtype(non_null_series)
                is_consistent = not inferred.startswith("mixed")
            
        if is_consistent:
            consistent_columns_count += 1
            
        col_data = {
            "dtype": dtype,
            "inferred_type": inferred_type,
            "missing_count": missing_count,
            "missing_percentage": round(missing_pct * 100, 2),
            "unique_count": int(col_series.nunique()),
            "is_consistent": is_consistent
        }
        
        findings["columns"][col] = col_data
        
    # Calculate Data Trust Score™ components
    completeness = 1.0 - (total_missing / total_cells) if total_cells > 0 else 1.0
    consistency = consistent_columns_count / findings["total_columns"] if findings["total_columns"] > 0 else 1.0
    
    anomaly_rows_count = int(anomaly_mask.sum())
    anomaly_health = 1.0 - (anomaly_rows_count / findings["total_rows"]) if findings["total_rows"] > 0 else 1.0
    
    # Trust Score™ = weighted average: 40% Completeness, 30% Consistency, 30% Anomaly Health
    raw_trust_score = (0.4 * completeness + 0.3 * consistency + 0.3 * anomaly_health) * 100
    trust_score = max(0.0, min(100.0, raw_trust_score))
    
    findings["trust_score"] = {
        "score": round(float(trust_score), 2),
        "breakdown": {
            "completeness": round(float(completeness * 100), 2),
            "consistency": round(float(consistency * 100), 2),
            "anomaly_health": round(float(anomaly_health * 100), 2)
        }
    }
    
    return findings
