import os
import sys
sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import text
from apps.api.src.core.database import engine, Base, SessionLocal
from apps.api.src.models.commerce import Order, PaymentTransaction, CommissionLedger, DownloadToken

def run_migration():
    print("Running Milestone 9 database schema migration...")
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)
        print("Milestone 9 tables (orders, payment_transactions, commission_ledgers, download_tokens) created successfully!")

if __name__ == "__main__":
    run_migration()
