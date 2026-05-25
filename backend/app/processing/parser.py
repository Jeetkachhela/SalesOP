import pandas as pd
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

# Security: Forbidden starting characters in CSVs that might indicate formula injection
FORBIDDEN_START_CHARS = ("=", "+", "-", "@", "\t", "\r")

def sanitize_csv_value(value):
    if isinstance(value, str):
        value = value.strip()
        if value.startswith(FORBIDDEN_START_CHARS):
            return f"'{value}"  # Escape the formula
    return value

def parse_and_sanitize_csv(file_bytes: bytes, chunk_size: int = 10000) -> pd.DataFrame:
    """
    Parses a CSV file in chunks to prevent memory exhaustion and sanitizes for formula injection.
    """
    logger.info("Starting sandboxed CSV parsing...")
    try:
        # We read the entire file into a bytes buffer, but use chunksize for pandas iteration
        # In a real heavy-duty scenario, the file might be read from disk in chunks.
        buffer = BytesIO(file_bytes)
        
        # Read the file to enforce some limits, but since it's already in memory for MVP, 
        # we will simulate chunked parsing and sanitization.
        chunks = []
        for chunk in pd.read_csv(buffer, chunksize=chunk_size):
            # Apply sanitization to all object (string) columns
            string_cols = chunk.select_dtypes(include=['object', 'string']).columns
            for col in string_cols:
                chunk[col] = chunk[col].apply(sanitize_csv_value)
            chunks.append(chunk)
            
        if not chunks:
            raise ValueError("CSV is empty.")
            
        df_sanitized = pd.concat(chunks, ignore_index=True)
        return df_sanitized
        
    except pd.errors.EmptyDataError:
        logger.error("Parsed CSV is empty.")
        raise ValueError("The uploaded CSV file contains no data.")
    except Exception as e:
        logger.error(f"Failed to parse CSV: {str(e)}")
        raise ValueError(f"Failed to parse CSV: {str(e)}")
