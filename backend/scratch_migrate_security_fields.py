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
            print("Applying ALTER TABLE commands to add security columns to users...")
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0 NOT NULL;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS lockout_until TIMESTAMP WITH TIME ZONE;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret VARCHAR;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN DEFAULT FALSE NOT NULL;"))
            print("Migration completed successfully!")
    except Exception as e:
        print(f"Error executing migration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
