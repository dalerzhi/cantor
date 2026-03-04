from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.deps import get_db
from models.auth import Organization
from pydantic import BaseModel

router = APIRouter(prefix="/vlm", tags=["VLM Engine"])

class VLMRequest(BaseModel):
    image_url: str
    tenant_id: str

@router.post("/visual-fix")
async def execute_visual_fix(request: VLMRequest, db: AsyncSession = Depends(get_db)):
    """
    Call VLM slow engine for visual fix.
    """
    # Fetch tenant
    result = await db.execute(select(Organization).where(Organization.id == request.tenant_id))
    org = result.scalar_one_or_none()
    
    if not org:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if org.status != "active":
        raise HTTPException(status_code=403, detail=f"Tenant is not active: {org.status}")
        
    # Check and deduct quota
    if org.vlm_quota_remaining <= 0:
        raise HTTPException(status_code=402, detail="VLM quota exhausted")
        
    # Deduct quota
    org.vlm_quota_remaining -= 1
    await db.commit()
    
    # Mock VLM execution
    return {
        "status": "success",
        "message": "Visual fix executed",
        "remaining_quota": org.vlm_quota_remaining,
        "fixed_result": {"x": 100, "y": 200, "action": "click"}
    }