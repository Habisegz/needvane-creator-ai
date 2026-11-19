from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from apps.api.src.core.database import get_db
from apps.api.src.api.deps import get_current_user
from apps.api.src.models.user import User
from apps.api.src.models.library_resource import LibraryResource
from apps.api.src.services.library.library_service import LibraryService

router = APIRouter(prefix="/library", tags=["Library Intelligence Centre"])


class ComplianceCheckRequest(BaseModel):
    resource_ids: List[str] = Field(..., min_length=1, description="List of library resource IDs to verify")


class ConnectorQueryRequest(BaseModel):
    query: Optional[str] = "*"
    parameters: Optional[Dict[str, Any]] = None


class ReverifyRequest(BaseModel):
    evidence_url: Optional[str] = None


@router.get("/resources")
def search_resources(
    query: Optional[str] = Query(None, description="Search term for name, description, application"),
    category: Optional[str] = Query(None, description="Filter by category domain"),
    tier: Optional[str] = Query(None, description="Filter by tier classification"),
    commercial_use: Optional[bool] = Query(None, description="Filter by commercial use permission"),
    api_available: Optional[bool] = Query(None, description="Filter by API availability"),
    verification_status: Optional[str] = Query(None, description="Filter by verification status (Verified, Stale)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search and filter genuine assessed resources across all domains and tiers.
    """
    result = LibraryService.search_resources(
        db=db,
        query=query,
        category=category,
        tier=tier,
        commercial_use=commercial_use,
        api_available=api_available,
        verification_status=verification_status,
        limit=limit,
        offset=offset
    )
    return result


@router.get("/resources/{resource_id}")
def get_resource(
    resource_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve full 23-point metadata for a specific library resource.
    """
    resource = LibraryService.get_resource_by_id(db, resource_id)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library resource not found")
    return resource


@router.post("/compliance/verify")
def verify_compliance(
    payload: ComplianceCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mandatory compliance engine: Verifies commercial and redistribution rights 
    before any external material is included in a digital product.
    """
    assessment = LibraryService.validate_compliance_for_product(db, payload.resource_ids)
    return assessment


@router.post("/maintenance/stale-check")
def run_stale_records_check(
    max_age_days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Scheduled verification task: Flags records older than max_age_days as 'Stale'.
    """
    stale_items = LibraryService.flag_stale_records(db, max_age_days=max_age_days)
    return {
        "status": "success",
        "stale_count": len(stale_items),
        "stale_resources": [{"id": str(r.id), "name": r.name, "verification_date": r.verification_date.isoformat()} for r in stale_items]
    }


@router.post("/resources/{resource_id}/reverify")
def reverify_resource(
    resource_id: str,
    payload: Optional[ReverifyRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Re-verifies an external resource, resetting its status to 'Verified' and updating verification_date.
    """
    evidence_url = payload.evidence_url if payload else None
    resource = LibraryService.reverify_resource(db, resource_id, evidence_url=evidence_url)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library resource not found")
    return {
        "status": "success",
        "id": str(resource.id),
        "name": resource.name,
        "verification_status": resource.verification_status,
        "verification_date": resource.verification_date.isoformat()
    }


@router.post("/connectors/{resource_id}/query")
def execute_connector(
    resource_id: str,
    payload: Optional[ConnectorQueryRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Execute modular connector query with rate limit checking, usage tracking, and licensing metadata.
    """
    params = {}
    if payload:
        params["query"] = payload.query
        if payload.parameters:
            params.update(payload.parameters)

    result = LibraryService.execute_connector(db, resource_id, params)
    if "error" in result and result.get("status") == "failed":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.get("/export/json")
def export_json(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export full assessed library registry as JSON.
    """
    json_data = LibraryService.export_catalog_json(db)
    return Response(content=json_data, media_type="application/json", headers={"Content-Disposition": "attachment; filename=needvane_library_registry.json"})


@router.get("/export/csv")
def export_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export full assessed library registry as CSV.
    """
    csv_data = LibraryService.export_catalog_csv(db)
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=needvane_library_registry.csv"})


@router.get("/export/pdf")
def export_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export executive registry report as PDF.
    """
    pdf_bytes = LibraryService.export_catalog_pdf(db)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=needvane_library_registry.pdf"})
