"""
云手机实例管理 API
从 IaaS 平台同步和管理云手机实例
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_db, get_current_user
from models.user import User
from services.iaas_client import IaaSClient
from core.config import settings

router = APIRouter(prefix="/cloud-phones", tags=["Cloud Phones"])


# ==================== Schemas ====================

class CloudPhoneResponse(BaseModel):
    """云手机实例响应"""
    id: str
    name: str
    ip: Optional[str] = None
    project_name: str
    project_id: str
    node_name: Optional[str] = None
    card_sn: Optional[str] = None
    status: int
    status_text: str
    resolution: Optional[str] = None
    os: Optional[str] = None
    os_version: Optional[str] = None
    synced_at: datetime

    class Config:
        from_attributes = True


class CloudPhoneSummary(BaseModel):
    """云手机统计摘要"""
    total: int
    running: int
    stopped: int
    creating: int
    error: int


class CloudPhoneSyncResult(BaseModel):
    """同步结果"""
    success: bool
    total: int
    created: int
    updated: int
    message: str
    synced_at: datetime


class NodeDistribution(BaseModel):
    """节点分布"""
    node_name: str
    total: int
    running: int
    stopped: int
    cards: int


class ProjectDistribution(BaseModel):
    """项目分布"""
    project_name: str
    project_id: str
    total: int
    running: int
    stopped: int
    cards: int


class CloudPhoneDashboard(BaseModel):
    """云手机仪表盘"""
    summary: CloudPhoneSummary
    nodes: List[NodeDistribution]
    projects: List[ProjectDistribution]
    last_synced: Optional[datetime] = None


# ==================== Helper Functions ====================

def get_status_text(status: int) -> str:
    """获取状态文本"""
    status_map = {
        0: "创建中",
        1: "运行中",
        2: "已关机",
        3: "异常",
        4: "运行中"
    }
    return status_map.get(status, f"未知({status})")


def get_iaas_client() -> IaaSClient:
    """获取 IaaS 客户端"""
    return IaaSClient(
        base_url=settings.IAAS_BASE_URL,
        access_key=settings.IAAS_ACCESS_KEY,
        secret_key=settings.IAAS_SECRET_KEY
    )


# 存储同步数据 (简单实现，生产环境应使用数据库)
_synced_data = {
    "instances": [],
    "last_synced": None
}


# ==================== API Endpoints ====================

@router.post("/sync", response_model=CloudPhoneSyncResult)
async def sync_cloud_phones(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    从 IaaS 平台同步云手机实例
    
    需要 Owner 或 Admin 权限
    """
    # 权限检查
    if current_user.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    client = get_iaas_client()
    
    try:
        # 1. 获取项目列表
        projects_data = client.list_projects()
        projects = projects_data.get('body', {}).get('result', [])
        
        # 2. 遍历项目获取实例
        all_instances = []
        for project in projects:
            project_id = project.get('uuid')
            project_name = project.get('name')
            
            instances_data = client.list_instances(
                page_num=1,
                page_size=100,
                project_uuid=project_id
            )
            
            result = instances_data.get('body', {}).get('result', {})
            records = result.get('records', [])
            
            for rec in records:
                all_instances.append({
                    'id': rec.get('uuid'),
                    'name': rec.get('name'),
                    'ip': rec.get('ip'),
                    'project_name': project_name,
                    'project_id': project_id,
                    'node_name': rec.get('nodeName', rec.get('nodeUuid')),
                    'card_sn': rec.get('armCardSn'),
                    'status': rec.get('status'),
                    'resolution': rec.get('resolution'),
                    'os': rec.get('os'),
                    'os_version': rec.get('osVersion'),
                    'synced_at': datetime.utcnow()
                })
        
        # 3. 更新缓存
        _synced_data['instances'] = all_instances
        _synced_data['last_synced'] = datetime.utcnow()
        
        return CloudPhoneSyncResult(
            success=True,
            total=len(all_instances),
            created=len(all_instances),  # 简化实现
            updated=0,
            message=f"成功同步 {len(all_instances)} 个云手机实例",
            synced_at=_synced_data['last_synced']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")
    finally:
        client.close()


@router.get("/dashboard", response_model=CloudPhoneDashboard)
async def get_cloud_phones_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取云手机仪表盘数据
    
    包括统计摘要、节点分布、项目分布
    """
    instances = _synced_data.get('instances', [])
    last_synced = _synced_data.get('last_synced')
    
    # 统计摘要
    summary = CloudPhoneSummary(
        total=len(instances),
        running=len([i for i in instances if i['status'] in [1, 4]]),
        stopped=len([i for i in instances if i['status'] == 2]),
        creating=len([i for i in instances if i['status'] == 0]),
        error=len([i for i in instances if i['status'] == 3])
    )
    
    # 节点分布
    nodes_map = {}
    for inst in instances:
        node = inst.get('node_name') or 'Unknown'
        if node not in nodes_map:
            nodes_map[node] = {
                'instances': [],
                'cards': set()
            }
        nodes_map[node]['instances'].append(inst)
        nodes_map[node]['cards'].add(inst.get('card_sn'))
    
    nodes = [
        NodeDistribution(
            node_name=node,
            total=len(data['instances']),
            running=len([i for i in data['instances'] if i['status'] in [1, 4]]),
            stopped=len([i for i in data['instances'] if i['status'] == 2]),
            cards=len(data['cards'])
        )
        for node, data in nodes_map.items()
    ]
    
    # 项目分布
    projects_map = {}
    for inst in instances:
        pid = inst.get('project_id')
        if pid not in projects_map:
            projects_map[pid] = {
                'project_name': inst.get('project_name'),
                'instances': [],
                'cards': set()
            }
        projects_map[pid]['instances'].append(inst)
        projects_map[pid]['cards'].add(inst.get('card_sn'))
    
    projects = [
        ProjectDistribution(
            project_name=data['project_name'],
            project_id=pid,
            total=len(data['instances']),
            running=len([i for i in data['instances'] if i['status'] in [1, 4]]),
            stopped=len([i for i in data['instances'] if i['status'] == 2]),
            cards=len(data['cards'])
        )
        for pid, data in projects_map.items()
    ]
    
    return CloudPhoneDashboard(
        summary=summary,
        nodes=nodes,
        projects=projects,
        last_synced=last_synced
    )


@router.get("", response_model=List[CloudPhoneResponse])
async def list_cloud_phones(
    project_id: Optional[str] = Query(None, description="项目 ID 过滤"),
    node_name: Optional[str] = Query(None, description="节点名称过滤"),
    status: Optional[int] = Query(None, description="状态过滤"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取云手机实例列表
    
    支持按项目、节点、状态过滤
    """
    instances = _synced_data.get('instances', [])
    
    # 过滤
    if project_id:
        instances = [i for i in instances if i['project_id'] == project_id]
    if node_name:
        instances = [i for i in instances if i['node_name'] == node_name]
    if status is not None:
        instances = [i for i in instances if i['status'] == status]
    
    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    paginated = instances[start:end]
    
    return [
        CloudPhoneResponse(
            id=i['id'],
            name=i['name'],
            ip=i['ip'],
            project_name=i['project_name'],
            project_id=i['project_id'],
            node_name=i['node_name'],
            card_sn=i['card_sn'],
            status=i['status'],
            status_text=get_status_text(i['status']),
            resolution=i['resolution'],
            os=i['os'],
            os_version=i['os_version'],
            synced_at=i['synced_at']
        )
        for i in paginated
    ]


@router.get("/{instance_id}", response_model=CloudPhoneResponse)
async def get_cloud_phone(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单个云手机实例详情"""
    instances = _synced_data.get('instances', [])
    
    for i in instances:
        if i['id'] == instance_id:
            return CloudPhoneResponse(
                id=i['id'],
                name=i['name'],
                ip=i['ip'],
                project_name=i['project_name'],
                project_id=i['project_id'],
                node_name=i['node_name'],
                card_sn=i['card_sn'],
                status=i['status'],
                status_text=get_status_text(i['status']),
                resolution=i['resolution'],
                os=i['os'],
                os_version=i['os_version'],
                synced_at=i['synced_at']
            )
    
    raise HTTPException(status_code=404, detail="实例不存在")


@router.post("/{instance_id}/start")
async def start_cloud_phone(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """启动云手机实例"""
    if current_user.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    client = get_iaas_client()
    try:
        result = client.start_instances([instance_id])
        return {"success": True, "message": "启动命令已发送", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")
    finally:
        client.close()


@router.post("/{instance_id}/stop")
async def stop_cloud_phone(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """停止云手机实例"""
    if current_user.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    client = get_iaas_client()
    try:
        result = client.stop_instances([instance_id])
        return {"success": True, "message": "停止命令已发送", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止失败: {str(e)}")
    finally:
        client.close()


@router.post("/{instance_id}/restart")
async def restart_cloud_phone(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """重启云手机实例"""
    if current_user.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    client = get_iaas_client()
    try:
        result = client.restart_instances([instance_id])
        return {"success": True, "message": "重启命令已发送", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重启失败: {str(e)}")
    finally:
        client.close()
