"""
Admin API - 系统管理接口
租户管理、设备分配等管理员功能
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.deps import get_db, get_current_user
from models.auth import User, Organization
from models.device import Device
from services.iaas_client import IaaSClient
from core.config import settings

router = APIRouter(prefix="/admin", tags=["Admin"])


# ==================== Schemas ====================

class TenantCreate(BaseModel):
    """创建租户"""
    name: str
    contact_name: str
    contact_email: EmailStr
    plan: str = "trial"
    max_devices: int = 10


class TenantResponse(BaseModel):
    """租户响应"""
    id: str
    name: str
    contact_name: str
    contact_email: str
    plan: str
    device_count: int
    max_devices: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceListResponse(BaseModel):
    """设备列表响应"""
    items: List[dict]
    total: int


class DeviceAllocateRequest(BaseModel):
    """设备分配请求"""
    tenant_id: str
    device_ids: List[str]


class DeviceAllocateResponse(BaseModel):
    """设备分配响应"""
    success: bool
    allocated_count: int
    message: str


# ==================== Helper Functions ====================

def get_iaas_client() -> IaaSClient:
    """获取 IaaS 客户端"""
    return IaaSClient(
        base_url=settings.IAAS_BASE_URL,
        access_key=settings.IAAS_ACCESS_KEY,
        secret_key=settings.IAAS_SECRET_KEY
    )


def check_admin_permission(current_user: User):
    """检查管理员权限"""
    if current_user.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )


# ==================== Tenant Management ====================

@router.get("/tenants", response_model=List[TenantResponse])
async def list_tenants(
    status: Optional[str] = Query(None, description="按状态筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取租户列表
    
    需要管理员权限
    """
    check_admin_permission(current_user)
    
    query = db.query(Organization)
    
    if status:
        query = query.filter(Organization.status == status)
    
    orgs = query.all()
    
    # 转换组织为租户格式
    tenants = []
    for org in orgs:
        # 统计该组织的设备数
        device_count = db.query(Device).filter(
            Device.organization_id == org.id
        ).count()
        
        tenants.append({
            "id": str(org.id),
            "name": org.name,
            "contact_name": org.contact_name or "-",
            "contact_email": org.contact_email or "-",
            "plan": getattr(org, 'plan', 'trial'),
            "device_count": device_count,
            "max_devices": getattr(org, 'max_devices', 10),
            "status": org.status or "active",
            "created_at": org.created_at
        })
    
    return tenants


@router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    data: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新租户
    
    需要管理员权限
    """
    check_admin_permission(current_user)
    
    # 检查组织名是否已存在
    existing = db.query(Organization).filter(
        Organization.name == data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="租户名称已存在"
        )
    
    # 创建新组织（作为租户）
    org = Organization(
        name=data.name,
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        status="active",
        plan=data.plan,
        max_devices=data.max_devices
    )
    
    db.add(org)
    db.commit()
    db.refresh(org)
    
    return {
        "id": str(org.id),
        "name": org.name,
        "contact_name": org.contact_name,
        "contact_email": org.contact_email,
        "plan": data.plan,
        "device_count": 0,
        "max_devices": data.max_devices,
        "status": "active",
        "created_at": org.created_at
    }


# ==================== Device Management ====================

@router.get("/devices", response_model=DeviceListResponse)
async def list_admin_devices(
    status: Optional[str] = Query(None, description="设备状态筛选: available, allocated, offline"),
    tenant_id: Optional[str] = Query(None, description="按租户筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取设备列表（管理员视角）
    
    需要管理员权限
    """
    check_admin_permission(current_user)
    
    query = db.query(Device)
    
    if status == "available":
        # 未分配的设备
        query = query.filter(Device.organization_id.is_(None))
    elif status == "allocated":
        # 已分配的设备
        query = query.filter(Device.organization_id.isnot(None))
    
    if tenant_id:
        query = query.filter(Device.organization_id == tenant_id)
    
    devices = query.all()
    
    # 转换为响应格式
    items = []
    for device in devices:
        org_name = None
        if device.organization_id:
            org = db.query(Organization).filter(
                Organization.id == device.organization_id
            ).first()
            org_name = org.name if org else None
        
        items.append({
            "id": str(device.id),
            "name": device.name,
            "serial_number": device.serial_number or device.id,
            "status": device.status or "available",
            "tenant_id": str(device.organization_id) if device.organization_id else None,
            "tenant_name": org_name,
            "specs": {
                "androidVersion": getattr(device, 'os_version', 'Unknown'),
                "memory": getattr(device, 'memory', '4GB'),
                "storage": getattr(device, 'storage', '64GB')
            },
            "created_at": device.created_at.isoformat() if device.created_at else None
        })
    
    return {
        "items": items,
        "total": len(items)
    }


@router.post("/devices/allocate", response_model=DeviceAllocateResponse)
async def allocate_devices(
    data: DeviceAllocateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    分配设备给租户
    
    需要管理员权限
    """
    check_admin_permission(current_user)
    
    # 验证租户存在
    tenant = db.query(Organization).filter(
        Organization.id == data.tenant_id
    ).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="租户不存在"
        )
    
    # 检查配额
    current_device_count = db.query(Device).filter(
        Device.organization_id == data.tenant_id
    ).count()
    
    max_devices = getattr(tenant, 'max_devices', 10)
    
    if current_device_count + len(data.device_ids) > max_devices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"超出设备配额限制 (当前: {current_device_count}, 最大: {max_devices})"
        )
    
    # 分配设备
    allocated_count = 0
    for device_id in data.device_ids:
        device = db.query(Device).filter(
            Device.id == device_id,
            Device.organization_id.is_(None)  # 只能分配未分配的设备
        ).first()
        
        if device:
            device.organization_id = data.tenant_id
            device.status = "allocated"
            allocated_count += 1
    
    db.commit()
    
    return DeviceAllocateResponse(
        success=allocated_count > 0,
        allocated_count=allocated_count,
        message=f"成功分配 {allocated_count} 台设备给租户 {tenant.name}"
    )


# ==================== IaaS Sync ====================

@router.post("/devices/sync-from-iaas")
async def sync_devices_from_iaas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    从 IaaS 平台同步设备到系统库存
    
    需要管理员权限
    """
    check_admin_permission(current_user)
    
    client = get_iaas_client()
    
    try:
        # 获取项目列表
        projects_data = client.list_projects()
        projects = projects_data.get('body', {}).get('result', [])
        
        synced_count = 0
        
        for project in projects:
            project_id = project.get('uuid')
            project_name = project.get('name')
            
            # 获取项目下的实例
            instances_data = client.list_instances(
                page_num=1,
                page_size=100,
                project_uuid=project_id
            )
            
            result = instances_data.get('body', {}).get('result', {})
            records = result.get('records', [])
            
            for rec in records:
                instance_id = rec.get('uuid')
                
                # 检查设备是否已存在
                existing = db.query(Device).filter(
                    Device.serial_number == instance_id
                ).first()
                
                if not existing:
                    # 创建新设备记录（作为库存）
                    device = Device(
                        name=rec.get('name', f'云手机-{instance_id[:8]}'),
                        serial_number=instance_id,
                        status="available",  # 未分配状态
                        os_version=rec.get('osVersion', 'Unknown'),
                        memory='4GB',  # 默认值，可从IaaS获取更多详情
                        storage='64GB',
                        metadata={
                            'iaas_project_id': project_id,
                            'iaas_project_name': project_name,
                            'ip': rec.get('ip'),
                            'resolution': rec.get('resolution'),
                            'node_name': rec.get('nodeName')
                        }
                    )
                    db.add(device)
                    synced_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "synced_count": synced_count,
            "message": f"成功从 IaaS 同步 {synced_count} 台设备到库存"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"同步失败: {str(e)}"
        )
    finally:
        client.close()
