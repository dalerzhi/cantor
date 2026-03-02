from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from db.session import get_db
from models.auth import Organization
from pydantic import BaseModel

router = APIRouter(prefix="/vlm", tags=["VLM Engine"])

class VLMRequest(BaseModel):
    image_url: str
    tenant_id: str

@router.post("/visual-fix")
async def execute_visual_fix(request: VLMRequest, db: Session = Depends(get_db)):
    """
    Call VLM slow engine for visual fix.
    """
    # Fetch tenant
    org = db.query(Organization).filter(Organization.id == request.tenant_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if org.status != "active":
        raise HTTPException(status_code=403, detail=f"Tenant is not active: {org.status}")
        
    # Check and deduct quota
    if org.vlm_quota_remaining <= 0:
        raise HTTPException(status_code=402, detail="VLM quota exhausted")
        
    # Deduct quota
    org.vlm_quota_remaining -= 1
    db.commit()
    
    # Mock VLM execution
    return {
        "status": "success",
        "message": "Visual fix executed",
        "remaining_quota": org.vlm_quota_remaining,
        "fixed_result": {"x": 100, "y": 200, "action": "click"}
    }
