import os
import sys
sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import text
from apps.api.src.core.database import engine, Base
import apps.api.src.models

def run_migration():
    print("Running Milestone 4 database schema migration...")
    with engine.begin() as conn:
        # 1. Update creators table with monitoring columns
        alter_stmts = [
            "ALTER TABLE creators ADD COLUMN IF NOT EXISTS monitoring_interval VARCHAR(50) DEFAULT 'daily';",
            "ALTER TABLE creators ADD COLUMN IF NOT EXISTS custom_interval_hours INTEGER DEFAULT 24;",
            "ALTER TABLE creators ADD COLUMN IF NOT EXISTS last_checked_at TIMESTAMP WITH TIME ZONE;",
            "ALTER TABLE creators ADD COLUMN IF NOT EXISTS next_check_due TIMESTAMP WITH TIME ZONE;",
            "ALTER TABLE creators ADD COLUMN IF NOT EXISTS content_fingerprint VARCHAR(64);",
            "ALTER TABLE creators ADD COLUMN IF NOT EXISTS theme_summary JSONB DEFAULT '[]'::jsonb;",
            "ALTER TABLE creators ADD COLUMN IF NOT EXISTS theme_embedding JSONB;",
            "ALTER TABLE creators ADD COLUMN IF NOT EXISTS alert_preferences JSONB DEFAULT '{}'::jsonb;"
        ]
        for stmt in alter_stmts:
            conn.execute(text(stmt))
            
        # 2. Create newly registered tables
        Base.metadata.create_all(bind=conn)
        print("Schema migration complete. All tables created/updated successfully.")

if __name__ == "__main__":
    run_migration()
