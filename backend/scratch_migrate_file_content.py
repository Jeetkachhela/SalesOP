import sys
import os
from sqlalchemy import text

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine

def migrate():
    print("Connecting to Neon PostgreSQL database...")
    try:
        with engine.begin() as conn:
            print("Applying ALTER TABLE commands to add file_content column to uploads and merged_datasets...")
            conn.execute(text("ALTER TABLE uploads ADD COLUMN IF NOT EXISTS file_content TEXT;"))
            conn.execute(text("ALTER TABLE merged_datasets ADD COLUMN IF NOT EXISTS file_content TEXT;"))
            print("Migration completed successfully!")
    except Exception as e:
        print(f"Error executing migration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
