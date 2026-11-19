import os
import sys
sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import text
from apps.api.src.core.database import engine, Base
import apps.api.src.models

def run_migration():
    print("Running Milestone 5 database schema migration...")
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)
        print("Milestone 5 tables (audience_signals, unmet_demands, product_briefs) created successfully!")

if __name__ == "__main__":
    run_migration()
