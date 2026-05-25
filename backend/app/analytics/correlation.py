import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def evaluate_correlations(df: pd.DataFrame) -> dict:
    """
    Computes the Pearson correlation matrix for all numeric columns in a DataFrame.
    Flags pairs with strong correlation (|r| > 0.7).
    Returns findings as a JSON-serializable dictionary.
    """
    logger.info("Starting deterministic correlation analysis...")
    
    findings = {
        "matrix": {},
        "strong_correlations": []
    }
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # We need at least two numeric columns to compute correlations
    if len(numeric_cols) < 2:
        return findings
        
    corr_matrix = df[numeric_cols].corr(method='pearson')
    
    # Fill diagonal and convert NaNs to None for JSON serialization
    for col1 in numeric_cols:
        findings["matrix"][col1] = {}
        for col2 in numeric_cols:
            val = corr_matrix.loc[col1, col2]
            if pd.isnull(val):
                findings["matrix"][col1][col2] = None
            else:
                findings["matrix"][col1][col2] = round(float(val), 4)
                
    # Detect strong correlations (exclude self-correlation and duplicates)
    for i, col1 in enumerate(numeric_cols):
        for col2 in numeric_cols[i+1:]:
            val = corr_matrix.loc[col1, col2]
            if pd.notnull(val) and abs(val) > 0.7:
                direction = "positive" if val > 0 else "negative"
                findings["strong_correlations"].append({
                    "col_a": col1,
                    "col_b": col2,
                    "coefficient": round(float(val), 4),
                    "direction": direction
                })
                
    return findings
