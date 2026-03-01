"""
工作空间 API
工作空间的 CRUD 和成员管理
"""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from core.database import get_db
from middleware.auth import require_auth, require_permission, AuthContext
from models.auth import (
    Workspace, User, Role, UserWorkspaceRole,
    DEFAULT_WORKSPACE_QUOTAS, DEFAULT_WORKSPACE_SETTINGS
)


router = APIRouter(prefix="/workspaces", tags=["工作空间管理"])


# ===== 请求/响应模型 =====

class WorkspaceResponse(BaseModel):
    """工作空间响应"""
    id: str
    org_id: str
    name: str
    description: Optional[str]
    status: str
    quotas: dict
    settings: dict
    created_at: datetime

    class Config:
        from_attributes = True


class CreateWorkspaceRequest(BaseModel):
    """创建工作空间请求"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class UpdateWorkspaceRequest(BaseModel):
    """更新工作空间请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    settings: Optional[dict] = None


class WorkspaceMemberResponse(BaseModel):
    """工作空间成员响应"""
    id: str
    user_id: str
    email: str
    name: Optional[str]
    role: str
    role_id: str
    granted_at: datetime


class AddMemberRequest(BaseModel):
    """添加成员请求"""
    user_id: str
    role_id: str


class WorkspaceListResponse(BaseModel):
    """工作空间列表响应"""
    workspaces: List[WorkspaceResponse]
    total: int


# ===== API 路由 =====

@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(
    auth: AuthContext = Depends(require_auth()),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户可访问的工作空间列表
    """
    # 用户只能看到自己有权限的工作空间
    workspace_ids = [ws["id"] for ws in auth.workspaces]

    if not workspace_ids:
        return WorkspaceListResponse(workspaces=[], total=0)

    result = await db.execute(
        select(Workspace).where(
            and_(
                Workspace.id.in_(workspace_ids),
                Workspace.status == "active",
                Workspace.deleted_at.is_(None)
            )
        )
    )
    workspaces = result.scalars().all()

    return WorkspaceListResponse(
        workspaces=[
            WorkspaceResponse(
                id=str(ws.id),
                org_id=str(ws.org_id),
                name=ws.name,
                description=ws.description,
                status=ws.status,
                quotas=ws.quotas or {},
                settings=ws.settings or {},
                created_at=ws.created_at
            )
            for ws in workspaces
        ],
        total=len(workspaces)
    )


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: CreateWorkspaceRequest,
    auth: AuthContext = Depends(require_permission("workspace:create")),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新工作空间
    """
    # 检查名称是否已存在
    result = await db.execute(
        select(Workspace).where(
            and_(
                Workspace.org_id == auth.org_id,
                Workspace.name == request.name,
                Workspace.deleted_at.is_(None)
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="工作空间名称已存在"
        )

    # 创建工作空间
    workspace = Workspace(
        org_id=auth.org_id,
        name=request.name,
        description=request.description,
        quotas=DEFAULT_WORKSPACE_QUOTAS,
        settings=DEFAULT_WORKSPACE_SETTINGS
    )
    db.add(workspace)
    await db.flush()

    # 自动将创建者添加为 Owner
    result = await db.execute(
        select(Role).where(and_(Role.org_id.is_(None), Role.name == "Owner"))
    )
    owner_role = result.scalar_one_or_none()

    if owner_role:
        uwr = UserWorkspaceRole(
            user_id=auth.user_id,
            workspace_id=workspace.id,
            role_id=owner_role.id
        )
        db.add(uwr)

    await db.commit()
    await db.refresh(workspace)

    return WorkspaceResponse(
        id=str(workspace.id),
        org_id=str(workspace.org_id),
        name=workspace.name,
        description=workspace.description,
        status=workspace.status,
        quotas=workspace.quotas or {},
        settings=workspace.settings or {},
        created_at=workspace.created_at
    )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    auth: AuthContext = Depends(require_auth()),
    db: AsyncSession = Depends(get_db)
):
    """
    获取工作空间详情
    """
    # 检查访问权限
    if not auth.has_workspace_access(workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此工作空间"
        )

    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工作空间不存在"
        )

    return WorkspaceResponse(
        id=str(workspace.id),
        org_id=str(workspace.org_id),
        name=workspace.name,
        description=workspace.description,
        status=workspace.status,
        quotas=workspace.quotas or {},
        settings=workspace.settings or {},
        created_at=workspace.created_at
    )


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    request: UpdateWorkspaceRequest,
    auth: AuthContext = Depends(require_permission("workspace:update")),
    db: AsyncSession = Depends(get_db)
):
    """
    更新工作空间信息
    """
    # 检查访问权限
    if not auth.has_workspace_access(workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改此工作空间"
        )

    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工作空间不存在"
        )

    # 更新字段
    if request.name is not None:
        # 检查新名称是否冲突
        result = await db.execute(
            select(Workspace).where(
                and_(
                    Workspace.org_id == auth.org_id,
                    Workspace.name == request.name,
                    Workspace.id != workspace_id,
                    Workspace.deleted_at.is_(None)
                )
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="工作空间名称已存在"
            )
        workspace.name = request.name

    if request.description is not None:
        workspace.description = request.description

    if request.settings is not None:
        current_settings = workspace.settings or {}
        current_settings.update(request.settings)
        workspace.settings = current_settings

    workspace.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(workspace)

    return WorkspaceResponse(
        id=str(workspace.id),
        org_id=str(workspace.org_id),
        name=workspace.name,
        description=workspace.description,
        status=workspace.status,
        quotas=workspace.quotas or {},
        settings=workspace.settings or {},
        created_at=workspace.created_at
    )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    auth: AuthContext = Depends(require_permission("workspace:delete")),
    db: AsyncSession = Depends(get_db)
):
    """
    删除工作空间（软删除）
    """
    # 检查访问权限
    if not auth.has_workspace_access(workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此工作空间"
        )

    result = await db.execute(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工作空间不存在"
        )

    # 软删除
    workspace.status = "deleted"
    workspace.deleted_at = datetime.now(timezone.utc)
    await db.commit()


@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
async def list_workspace_members(
    workspace_id: str,
    auth: AuthContext = Depends(require_auth()),
    db: AsyncSession = Depends(get_db)
):
    """
    获取工作空间成员列表
    """
    # 检查访问权限
    if not auth.has_workspace_access(workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此工作空间"
        )

    result = await db.execute(
        select(UserWorkspaceRole, User, Role)
        .join(User, UserWorkspaceRole.user_id == User.id)
        .join(Role, UserWorkspaceRole.role_id == Role.id)
        .where(
            and_(
                UserWorkspaceRole.workspace_id == workspace_id,
                User.status == "active"
            )
        )
    )

    members = []
    for uwr, user, role in result.all():
        members.append(WorkspaceMemberResponse(
            id=str(uwr.id),
            user_id=str(user.id),
            email=user.email,
            name=user.name,
            role=role.name,
            role_id=str(role.id),
            granted_at=uwr.granted_at
        ))

    return members


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    workspace_id: str,
    request: AddMemberRequest,
    auth: AuthContext = Depends(require_permission("workspace:update")),
    db: AsyncSession = Depends(get_db)
):
    """
    添加工作空间成员
    """
    # 检查访问权限
    if not auth.has_workspace_access(workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改此工作空间"
        )

    # 检查用户是否存在且在同一组织
    result = await db.execute(
        select(User).where(
            and_(User.id == request.user_id, User.org_id == auth.org_id)
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 检查角色是否存在
    result = await db.execute(
        select(Role).where(
            and_(
                Role.id == request.role_id,
                or_(Role.org_id.is_(None), Role.org_id == auth.org_id)
            )
        )
    )
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 检查是否已存在
    result = await db.execute(
        select(UserWorkspaceRole).where(
            and_(
                UserWorkspaceRole.user_id == request.user_id,
                UserWorkspaceRole.workspace_id == workspace_id,
                UserWorkspaceRole.role_id == request.role_id
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已在此工作空间拥有此角色"
        )

    # 添加成员
    uwr = UserWorkspaceRole(
        user_id=request.user_id,
        workspace_id=workspace_id,
        role_id=request.role_id,
        granted_by=auth.user_id
    )
    db.add(uwr)
    await db.commit()
    await db.refresh(uwr)

    return WorkspaceMemberResponse(
        id=str(uwr.id),
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        role=role.name,
        role_id=str(role.id),
        granted_at=uwr.granted_at
    )


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: str,
    user_id: str,
    auth: AuthContext = Depends(require_permission("workspace:update")),
    db: AsyncSession = Depends(get_db)
):
    """
    移除工作空间成员
    """
    # 检查访问权限
    if not auth.has_workspace_access(workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改此工作空间"
        )

    # 查找并删除
    result = await db.execute(
        select(UserWorkspaceRole).where(
            and_(
                UserWorkspaceRole.user_id == user_id,
                UserWorkspaceRole.workspace_id == workspace_id
            )
        )
    )
    uwr = result.scalar_one_or_none()

    if not uwr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="成员关系不存在"
        )

    await db.delete(uwr)
    await db.commit()
