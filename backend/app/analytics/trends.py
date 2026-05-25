import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def evaluate_trends(df: pd.DataFrame) -> dict:
    """
    Auto-detects datetime columns, performs resampling of numerical columns,
    computes moving averages, and fits a linear regression line to classify the trend.
    Returns findings as a JSON-serializable dictionary.
    """
    logger.info("Starting deterministic trend and time-series analysis...")
    
    findings = {
        "primary_datetime_column": None,
        "resample_period": None,
        "series": [],
        "metrics": {}
    }
    
    # 1. Auto-detect datetime columns
    datetime_cols = []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            datetime_cols.append(col)
            continue
            
        # Try parsing strings that look like dates (only if they are object/string type)
        if df[col].dtype == 'object' or str(df[col].dtype) == 'string':
            # Check a sample of the first 100 non-null values to verify
            sample = df[col].dropna().head(100)
            if len(sample) > 0:
                try:
                    parsed = pd.to_datetime(sample, errors='coerce')
                    # If more than 80% of non-nulls parse successfully, count as date
                    if parsed.notnull().sum() / len(sample) > 0.8:
                        datetime_cols.append(col)
                except Exception:
                    pass
                    
    if not datetime_cols:
        logger.info("No datetime columns detected. Skipping trend analysis.")
        return findings
        
    # Pick the datetime column with the most unique values (or first one)
    primary_dt_col = max(datetime_cols, key=lambda c: df[c].nunique())
    findings["primary_datetime_column"] = primary_dt_col
    
    # 2. Prepare temp DataFrame
    df_temp = pd.DataFrame()
    df_temp[primary_dt_col] = pd.to_datetime(df[primary_dt_col], errors='coerce')
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        logger.info("No numeric columns found for trend analysis.")
        return findings
        
    for col in numeric_cols:
        df_temp[col] = df[col]
        
    df_temp = df_temp.dropna(subset=[primary_dt_col]).sort_values(by=primary_dt_col)
    if len(df_temp) < 5:
        logger.info("Too few rows with valid datetime values. Skipping trend analysis.")
        return findings
        
    # Determine span of time to decide resampling rule
    min_date = df_temp[primary_dt_col].min()
    max_date = df_temp[primary_dt_col].max()
    span_days = (max_date - min_date).days
    
    if span_days <= 7:
        resample_rule = 'D'
        findings["resample_period"] = "day"
        date_format = "%Y-%m-%d"
    elif span_days <= 180:
        resample_rule = 'W'
        findings["resample_period"] = "week"
        date_format = "%Y-%m-%d"
    else:
        resample_rule = 'ME'
        findings["resample_period"] = "month"
        date_format = "%Y-%m"
        
    # Perform resampling
    df_temp.set_index(primary_dt_col, inplace=True)
    
    try:
        resampled = df_temp[numeric_cols].resample(resample_rule).mean()
    except Exception:
        # Fallback for older pandas versions where 'ME' might not be supported (or vice versa)
        fallback_rule = 'M' if resample_rule == 'ME' else resample_rule
        resampled = df_temp[numeric_cols].resample(fallback_rule).mean()
        
    # Interpolate missing values in time series to prevent breakages in visualization lines
    resampled = resampled.ffill().bfill().fillna(0)
    
    if len(resampled) < 2:
        logger.info("Resampled series has less than 2 data points. Skipping trend regression.")
        return findings
        
    # 3. Format time series data for Recharts
    # Recharts expects an array of dicts, e.g. [{"date": "2023-01", "sales": 100, "freight": 20}]
    series_data = []
    for idx, row in resampled.iterrows():
        point = {"date": idx.strftime(date_format)}
        for col in numeric_cols:
            point[col] = round(float(row[col]), 4) if pd.notnull(row[col]) else 0.0
        series_data.append(point)
        
    findings["series"] = series_data
    
    # 4. Calculate trend metrics (slope, direction, moving average)
    for col in numeric_cols:
        y = resampled[col].values
        x = np.arange(len(y))
        
        # Fit linear regression: y = ax + b
        try:
            slope, intercept = np.polyfit(x, y, 1)
            mean_val = y.mean()
            # Normalize slope by mean value to get a relative percentage change per period
            slope_pct = (slope / mean_val) if mean_val != 0 else slope
            
            if slope_pct > 0.01:
                direction = "upward"
            elif slope_pct < -0.01:
                direction = "downward"
            else:
                direction = "stable"
        except Exception:
            slope = 0.0
            direction = "stable"
            
        # Compute 3-period moving average
        ma_series = pd.Series(y).rolling(window=3, min_periods=1).mean().tolist()
        ma_series = [round(float(v), 4) for v in ma_series]
        
        findings["metrics"][col] = {
            "slope": round(float(slope), 4),
            "direction": direction,
            "moving_average": ma_series
        }
        
    return findings
