import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def evaluate_distributions(df: pd.DataFrame) -> dict:
    """
    Computes skewness, kurtosis, shape classification, and histogram bins (10 bins)
    for each numeric column in a DataFrame.
    Returns findings as a JSON-serializable dictionary.
    """
    logger.info("Starting deterministic distribution analysis...")
    
    findings = {}
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    for col in numeric_cols:
        col_series = df[col].dropna()
        if len(col_series) < 2:
            continue
            
        skew = col_series.skew()
        kurt = col_series.kurt() # pandas kurt() returns excess kurtosis (kurtosis - 3)
        
        # Determine skewness classification
        if pd.isnull(skew):
            skew_class = "unknown"
        elif skew > 0.5:
            skew_class = "right-skewed"
        elif skew < -0.5:
            skew_class = "left-skewed"
        else:
            skew_class = "symmetric"
            
        # Determine tail-shape (kurtosis) classification
        if pd.isnull(kurt):
            kurt_class = "unknown"
        elif kurt > 1:
            kurt_class = "heavy-tailed (leptokurtic)"
        elif kurt < -1:
            kurt_class = "light-tailed (platykurtic)"
        else:
            kurt_class = "normal-tailed (mesokurtic)"
            
        # Compute 10 histogram bins
        counts, bin_edges = np.histogram(col_series, bins=10)
        histogram = []
        for i in range(len(counts)):
            histogram.append({
                "bin_start": round(float(bin_edges[i]), 4),
                "bin_end": round(float(bin_edges[i+1]), 4),
                "count": int(counts[i])
            })
            
        findings[col] = {
            "skewness": round(float(skew), 4) if pd.notnull(skew) else None,
            "skewness_classification": skew_class,
            "kurtosis": round(float(kurt), 4) if pd.notnull(kurt) else None,
            "kurtosis_classification": kurt_class,
            "histogram": histogram
        }
        
    return findings
