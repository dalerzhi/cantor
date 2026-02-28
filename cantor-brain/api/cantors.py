from typing import Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from enum import Enum

router = APIRouter(prefix="/cantors", tags=["Cantors"])


class CantorStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class CantorInstance(BaseModel):
    id: str = Field(..., description="Cantor instance unique identifier")
    name: str = Field(..., description="Cantor instance name")
    persona_prompt: Optional[str] = Field(default=None, description="Persona prompt for this Cantor")
    llm_config: Dict = Field(default_factory=dict, description="LLM model configuration")
    device_ids: List[str] = Field(default_factory=list, description="List of bound device IDs")
    status: CantorStatus = Field(default=CantorStatus.INACTIVE, description="Cantor status")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    model_config = {"populate_by_name": True}


class CantorInstanceCreate(BaseModel):
    name: str = Field(..., description="Cantor instance name")
    persona_prompt: Optional[str] = Field(default=None, description="Persona prompt")
    llm_config: Optional[Dict] = Field(default_factory=dict, description="LLM model configuration")


class CantorInstanceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, description="Cantor instance name")
    persona_prompt: Optional[str] = Field(default=None, description="Persona prompt")
    llm_config: Optional[Dict] = Field(default=None, description="LLM model configuration")
    status: Optional[CantorStatus] = Field(default=None, description="Cantor status")


class BindDeviceRequest(BaseModel):
    device_id: str = Field(..., description="Device ID to bind")


class UnbindDeviceRequest(BaseModel):
    device_id: str = Field(..., description="Device ID to unbind")


# In-memory storage for Cantor instances
cantors_db: Dict[str, CantorInstance] = {}


@router.get("", response_model=List[CantorInstance])
async def list_cantors():
    """Get all Cantor instances list."""
    return list(cantors_db.values())


@router.get("/{cantor_id}", response_model=CantorInstance)
async def get_cantor(cantor_id: str):
    """Get Cantor instance details by ID."""
    if cantor_id not in cantors_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cantor instance {cantor_id} not found"
        )
    return cantors_db[cantor_id]


@router.post("", response_model=CantorInstance, status_code=status.HTTP_201_CREATED)
async def create_cantor(cantor: CantorInstanceCreate):
    """Create a new Cantor instance."""
    import uuid
    cantor_id = str(uuid.uuid4())[:8]
    
    new_cantor = CantorInstance(
        id=cantor_id,
        name=cantor.name,
        persona_prompt=cantor.persona_prompt,
        llm_config=cantor.llm_config or {},
        status=CantorStatus.INACTIVE
    )
    
    cantors_db[cantor_id] = new_cantor
    return new_cantor


@router.put("/{cantor_id}", response_model=CantorInstance)
async def update_cantor(cantor_id: str, cantor_update: CantorInstanceUpdate):
    """Update Cantor instance information."""
    if cantor_id not in cantors_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cantor instance {cantor_id} not found"
        )
    
    existing = cantors_db[cantor_id]
    update_data = cantor_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(existing, field, value)
    
    existing.updated_at = datetime.now()
    return existing


@router.delete("/{cantor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cantor(cantor_id: str):
    """Delete a Cantor instance."""
    if cantor_id not in cantors_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cantor instance {cantor_id} not found"
        )
    
    del cantors_db[cantor_id]
    return None


@router.post("/{cantor_id}/bind-device", response_model=CantorInstance)
async def bind_device(cantor_id: str, request: BindDeviceRequest):
    """Bind a device to a Cantor instance."""
    if cantor_id not in cantors_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cantor instance {cantor_id} not found"
        )
    
    cantor = cantors_db[cantor_id]
    
    # Check if device already bound
    if request.device_id in cantor.device_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Device {request.device_id} is already bound to this Cantor"
        )
    
    cantor.device_ids.append(request.device_id)
    cantor.updated_at = datetime.now()
    
    return cantor


@router.post("/{cantor_id}/unbind-device", response_model=CantorInstance)
async def unbind_device(cantor_id: str, request: UnbindDeviceRequest):
    """Unbind a device from a Cantor instance."""
    if cantor_id not in cantors_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cantor instance {cantor_id} not found"
        )
    
    cantor = cantors_db[cantor_id]
    
    if request.device_id not in cantor.device_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Device {request.device_id} is not bound to this Cantor"
        )
    
    cantor.device_ids.remove(request.device_id)
    cantor.updated_at = datetime.now()
    
    return cantor