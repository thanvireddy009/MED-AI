import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env locally if it exists (ignored on Railway — env vars set in dashboard)
env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

def get_connection():
    conn_str = os.getenv("NEON_CONNECTION_STRING")
    if not conn_str:
        raise RuntimeError("NEON_CONNECTION_STRING environment variable is not set")
    return psycopg2.connect(conn_str, cursor_factory=psycopg2.extras.RealDictCursor)

def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT NOW(),
            status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'approved', 'rejected')),
            extracted_data JSONB,
            validated_data JSONB,
            review_notes TEXT
        );

        CREATE TABLE IF NOT EXISTS review_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID REFERENCES documents(id),
            action TEXT NOT NULL,
            previous_data JSONB,
            updated_data JSONB,
            reviewer TEXT DEFAULT 'reviewer',
            reviewed_at TIMESTAMP DEFAULT NOW(),
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            timestamp TIMESTAMP DEFAULT NOW(),
            user_id TEXT,
            action TEXT NOT NULL,
            resource TEXT,
            resource_id TEXT,
            details JSONB,
            ip_address TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
