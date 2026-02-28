from typing import Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from enum import Enum

router = APIRouter(prefix="/devices", tags=["Devices"])


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"


class Device(BaseModel):
    id: str = Field(..., description="Device unique identifier")
    name: str = Field(..., description="Device name")
    status: DeviceStatus = Field(default=DeviceStatus.OFFLINE, description="Device status")
    ip_address: Optional[str] = Field(default=None, description="Device IP address")
    last_heartbeat: Optional[datetime] = Field(default=None, description="Last heartbeat timestamp")


class DeviceCreate(BaseModel):
    name: str = Field(..., description="Device name")
    ip_address: Optional[str] = Field(default=None, description="Device IP address")


class DeviceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, description="Device name")
    status: Optional[DeviceStatus] = Field(default=None, description="Device status")
    ip_address: Optional[str] = Field(default=None, description="Device IP address")


# In-memory storage for devices
devices_db: Dict[str, Device] = {}


@router.get("", response_model=List[Device])
async def list_devices():
    """Get all devices list."""
    return list(devices_db.values())


@router.get("/{device_id}", response_model=Device)
async def get_device(device_id: str):
    """Get device details by ID."""
    if device_id not in devices_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )
    return devices_db[device_id]


@router.post("", response_model=Device, status_code=status.HTTP_201_CREATED)
async def create_device(device: DeviceCreate):
    """Register a new device."""
    import uuid
    device_id = str(uuid.uuid4())[:8]
    
    new_device = Device(
        id=device_id,
        name=device.name,
        status=DeviceStatus.ONLINE,
        ip_address=device.ip_address,
        last_heartbeat=datetime.now()
    )
    
    devices_db[device_id] = new_device
    return new_device


@router.put("/{device_id}", response_model=Device)
async def update_device(device_id: str, device_update: DeviceUpdate):
    """Update device information."""
    if device_id not in devices_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )
    
    existing = devices_db[device_id]
    update_data = device_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(existing, field, value)
    
    return existing


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: str):
    """Delete a device."""
    if device_id not in devices_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )
    
    del devices_db[device_id]
    return None


@router.post("/{device_id}/heartbeat", response_model=Device)
async def device_heartbeat(device_id: str):
    """Update device heartbeat timestamp."""
    if device_id not in devices_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )
    
    device = devices_db[device_id]
    device.last_heartbeat = datetime.now()
    if device.status == DeviceStatus.OFFLINE:
        device.status = DeviceStatus.ONLINE
    
    return device