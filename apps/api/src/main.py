import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from apps.api.src.core.config import settings
from apps.api.src.core.database import Base, engine
from apps.api.src.api.v1.auth import router as auth_router
from apps.api.src.api.v1.tenants import router as tenants_router
from apps.api.src.api.v1.health import router as health_router
from apps.api.src.api.v1.products import router as products_router
from apps.api.src.api.v1.creators import router as creators_router
from apps.api.src.api.v1.monitoring import router as monitoring_router
from apps.api.src.api.v1.audience import router as audience_router
from apps.api.src.api.v1.library import router as library_router
from apps.api.src.api.v1.emails import router as emails_router
from apps.api.src.api.v1.partnerships import router as partnerships_router
from apps.api.src.api.v1.commerce import router as commerce_router
from apps.api.src.api.v1.billing import router as billing_router

# Ensure tables are created on startup
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Database initialization notice: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API engine for NeedVane Creator AI - Creator Intelligence & Digital Product Studio",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Timing & Diagnostic Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response

# Register API v1 Endpoints
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(tenants_router, prefix=settings.API_V1_STR)
app.include_router(products_router, prefix=settings.API_V1_STR)
app.include_router(creators_router, prefix=settings.API_V1_STR)
app.include_router(monitoring_router, prefix=settings.API_V1_STR)
app.include_router(audience_router, prefix=settings.API_V1_STR)
app.include_router(library_router, prefix=settings.API_V1_STR)
app.include_router(emails_router, prefix=settings.API_V1_STR)
app.include_router(partnerships_router, prefix=settings.API_V1_STR)
app.include_router(commerce_router, prefix=settings.API_V1_STR)
app.include_router(billing_router, prefix=settings.API_V1_STR)
app.include_router(commerce_router)  # Also expose /p/{slug} at root level for clean blog URLs

@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API Engine",
        "documentation": "/docs",
        "health": f"{settings.API_V1_STR}/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.src.main:app", host="0.0.0.0", port=8000, reload=True)
