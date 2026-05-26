import pandas as pd
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def merge_datasets(
    df1: pd.DataFrame, 
    df2: pd.DataFrame, 
    join_type: str = "inner", 
    left_on: Optional[str] = None, 
    right_on: Optional[str] = None
) -> pd.DataFrame:
    """
    Safely merges two pandas DataFrames.
    If left_on and right_on are not provided, it attempts to find common columns.
    """
    logger.info(f"Attempting to merge datasets. df1 shape: {df1.shape}, df2 shape: {df2.shape}")
    
    # Edge Case: Handle empty DataFrames safely
    if df1.empty or df2.empty:
        logger.warning("One or both DataFrames are empty. Returning empty merged DataFrame.")
        # Return empty dataframe with merged columns schema
        empty_cols = list(set(df1.columns).union(set(df2.columns)))
        return pd.DataFrame(columns=empty_cols)
        
    if not left_on or not right_on:
        common_cols = list(set(df1.columns).intersection(set(df2.columns)))
        if not common_cols:
            raise ValueError("No common columns found for automatic merge, and no join keys provided.")
        # Just use the first common column as a simple auto-merge strategy
        left_on = common_cols[0]
        right_on = common_cols[0]
        logger.info(f"Auto-detected merge keys: {left_on}")
        
    try:
        # Avoid full deep copies which duplicate the entire dataset in memory.
        # Only copy if we need to modify the join keys to resolve type mismatch or strip strings.
        if left_on in df1.columns and right_on in df2.columns:
            type1 = df1[left_on].dtype
            type2 = df2[right_on].dtype
            
            is_num1 = pd.api.types.is_numeric_dtype(type1)
            is_num2 = pd.api.types.is_numeric_dtype(type2)
            
            # Smart check: If they have the exact same dtype or are both numeric,
            # they are compatible for native high-speed C-level joins without string casting.
            if type1 == type2 or (is_num1 and is_num2):
                logger.info(f"Join keys are highly compatible ({type1} and {type2}). Direct join enabled.")
            else:
                logger.info(f"Converting join keys to stripped strings due to type difference ({type1} vs {type2})")
                df1 = df1.copy(deep=False)
                df2 = df2.copy(deep=False)
                df1[left_on] = df1[left_on].astype(str).str.strip()
                df2[right_on] = df2[right_on].astype(str).str.strip()
            
        merged_df = pd.merge(
            df1, 
            df2, 
            how=join_type, 
            left_on=left_on, 
            right_on=right_on,
            suffixes=('_ds1', '_ds2')
        )
        logger.info(f"Successfully merged. New shape: {merged_df.shape}")
        return merged_df
    except Exception as e:
        logger.error(f"Merge failed: {str(e)}")
        raise ValueError(f"Failed to merge datasets: {str(e)}")
