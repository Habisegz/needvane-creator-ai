from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from apps.api.src.core.config import settings

def get_engine():
    raw_url = settings.DATABASE_URL
    if not raw_url:
        return create_engine("sqlite:///./needvane_dev.db", connect_args={"check_same_thread": False})
    
    # Format for SQLAlchemy with psycopg v3
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
        raw_url = raw_url.replace("postgresql://", "postgresql+psycopg://", 1)

    return create_engine(
        raw_url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10
    )

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Dependency providing a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def set_tenant_session(db: Session, tenant_id: str) -> None:
    """Sets the PostgreSQL session variable for Row Level Security (RLS)."""
    try:
        db.execute(text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"), {"tenant_id": str(tenant_id)})
    except Exception:
        pass
