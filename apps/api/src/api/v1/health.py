from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from apps.api.src.core.database import get_db
from apps.api.src.core.config import settings

router = APIRouter(tags=["System Health"])

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint validating API, PostgreSQL connectivity, and pgvector extension status."""
    db_status = "connected"
    pgvector_status = "unknown"
    db_version = "unknown"

    try:
        # Check basic query execution
        version_res = db.execute(text("SELECT version();")).scalar()
        if version_res:
            db_version = version_res
        
        # Check pgvector extension
        ext_res = db.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector';")).scalar()
        if ext_res:
            pgvector_status = f"active (v{ext_res})"
        else:
            pgvector_status = "not installed"
    except Exception as e:
        db_status = f"degraded: {str(e)}"

    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": {
            "status": db_status,
            "version": db_version,
            "pgvector": pgvector_status
        }
    }
