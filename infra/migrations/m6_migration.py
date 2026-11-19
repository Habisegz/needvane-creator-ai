import os
import sys
sys.path.insert(0, os.path.abspath("."))

from datetime import datetime, timezone
from sqlalchemy import select, func
from apps.api.src.core.database import engine, Base, SessionLocal
from apps.api.src.models.library_resource import LibraryResource
from apps.api.src.services.library.catalog_data import GENUINE_RESOURCES_100

def run_migration():
    print("Running Milestone 6 database schema migration...")
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)
        print("Milestone 6 table (library_resources) created successfully!")

    print(f"Seeding genuine resources into database ({len(GENUINE_RESOURCES_100)} total)...")
    db = SessionLocal()
    try:
        existing_count = db.query(func.count(LibraryResource.id)).scalar()
        print(f"Currently existing resources in database: {existing_count}")
        
        seeded = 0
        for item in GENUINE_RESOURCES_100:
            existing = db.query(LibraryResource).filter(LibraryResource.name == item["name"]).first()
            if not existing:
                res = LibraryResource(
                    name=item["name"],
                    official_website=item["official_website"],
                    category=item["category"],
                    description=item["description"],
                    available_content=item["available_content"],
                    api_available=item["api_available"],
                    api_documentation_url=item.get("api_documentation_url"),
                    authentication_type=item.get("authentication_type", "none"),
                    search_capability=item.get("search_capability", "keyword"),
                    download_export_options=item.get("download_export_options", "JSON, CSV"),
                    bulk_access_restrictions=item.get("bulk_access_restrictions", "Standard limits"),
                    rate_limits=item.get("rate_limits", "Standard public limits"),
                    is_free=item.get("is_free", True),
                    pricing_model=item.get("pricing_model", "Free"),
                    published_pricing=item.get("published_pricing", "$0"),
                    commercial_use_allowed=item.get("commercial_use_allowed", True),
                    attribution_required=item.get("attribution_required", True),
                    attribution_format=item.get("attribution_format"),
                    redistribution_restrictions=item.get("redistribution_restrictions", "Permitted with attribution"),
                    geographic_restrictions=item.get("geographic_restrictions", "Global"),
                    integration_complexity=item.get("integration_complexity", "Low"),
                    recommended_application=item.get("recommended_application", "Reference"),
                    evidence_url=item["evidence_url"],
                    verification_date=item.get("verification_date") or datetime.now(timezone.utc),
                    verification_status=item.get("verification_status", "Verified"),
                    tier_classification=item.get("tier_classification", "Tier 1: Direct API"),
                    integration_status=item.get("integration_status", "available"),
                    usage_count=0
                )
                db.add(res)
                seeded += 1
        
        db.commit()
        total_now = db.query(func.count(LibraryResource.id)).scalar()
        print(f"Seeding completed: {seeded} added. Total resources now in database: {total_now}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
