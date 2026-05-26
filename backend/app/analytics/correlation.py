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
    
    # Vectorized rounding and conversion of NaNs to None for clean JSON serialization
    corr_matrix_rounded = corr_matrix.round(4)
    corr_matrix_cleaned = corr_matrix_rounded.where(pd.notnull(corr_matrix_rounded), None)
    findings["matrix"] = corr_matrix_cleaned.to_dict()
                
    # Detect strong correlations using vectorized upper triangle stack
    try:
        # Create a mask for the upper triangle (excluding the diagonal)
        mask = np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        # Stack the masked correlation matrix to get non-redundant pairs
        stacked = corr_matrix.where(mask).stack()
        # Filter for strong correlation coefficients (|r| > 0.7)
        strong_pairs = stacked[stacked.abs() > 0.7]
        
        for (col_a, col_b), val in strong_pairs.items():
            direction = "positive" if val > 0 else "negative"
            findings["strong_correlations"].append({
                "col_a": col_a,
                "col_b": col_b,
                "coefficient": round(float(val), 4),
                "direction": direction
            })
    except Exception as e:
        logger.error(f"Vectorized strong correlation extraction failed: {str(e)}. Using safe fallback.")
        # Safe fallback loop in case of unusual multi-index or empty shapes
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
