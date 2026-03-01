"""
组织 API
组织的 CRUD 操作
"""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from core.database import get_db
from middleware.auth import require_auth, require_permission, AuthContext
from models.auth import Organization, User, DEFAULT_ORG_QUOTAS, DEFAULT_ORG_SETTINGS


router = APIRouter(prefix="/orgs", tags=["组织管理"])


# ===== 请求/响应模型 =====

class OrganizationResponse(BaseModel):
    """组织响应"""
    id: str
    name: str
    slug: str
    tier: str
    status: str
    quotas: dict
    settings: dict
    created_at: datetime

    class Config:
        from_attributes = True


class CreateOrganizationRequest(BaseModel):
    """创建组织请求"""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    tier: str = Field(default="b2b", pattern=r"^(b2b|b2c)$")


class UpdateOrganizationRequest(BaseModel):
    """更新组织请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    settings: Optional[dict] = None
    quotas: Optional[dict] = None


class OrganizationMemberResponse(BaseModel):
    """组织成员响应"""
    id: str
    email: str
    name: Optional[str]
    status: str
    created_at: datetime


class OrganizationListResponse(BaseModel):
    """组织列表响应"""
    organizations: List[OrganizationResponse]
    total: int


# ===== API 路由 =====

@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    auth: AuthContext = Depends(require_auth()),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的组织列表

    注：当前设计一个用户只属于一个组织
    """
    result = await db.execute(
        select(Organization).where(
            and_(
                Organization.id == auth.org_id,
                Organization.deleted_at.is_(None)
            )
        )
    )
    org = result.scalar_one_or_none()

    if not org:
        return OrganizationListResponse(organizations=[], total=0)

    return OrganizationListResponse(
        organizations=[
            OrganizationResponse(
                id=str(org.id),
                name=org.name,
                slug=org.slug,
                tier=org.tier,
                status=org.status,
                quotas=org.quotas or {},
                settings=org.settings or {},
                created_at=org.created_at
            )
        ],
        total=1
    )


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    request: CreateOrganizationRequest,
    auth: AuthContext = Depends(require_auth()),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新组织

    注：当前用户会从原组织移动到新组织
    """
    # 检查 slug 是否已存在
    result = await db.execute(
        select(Organization).where(Organization.slug == request.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="组织标识已存在"
        )

    # 创建组织
    org = Organization(
        name=request.name,
        slug=request.slug,
        tier=request.tier,
        quotas=DEFAULT_ORG_QUOTAS,
        settings=DEFAULT_ORG_SETTINGS
    )
    db.add(org)
    await db.flush()

    # 更新用户所属组织
    result = await db.execute(select(User).where(User.id == auth.user_id))
    user = result.scalar_one_or_none()
    if user:
        user.org_id = org.id

    await db.commit()
    await db.refresh(org)

    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        tier=org.tier,
        status=org.status,
        quotas=org.quotas or {},
        settings=org.settings or {},
        created_at=org.created_at
    )


@router.get("/current", response_model=OrganizationResponse)
async def get_current_organization(
    auth: AuthContext = Depends(require_auth()),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前组织详情
    """
    result = await db.execute(
        select(Organization).where(Organization.id == auth.org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在"
        )

    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        tier=org.tier,
        status=org.status,
        quotas=org.quotas or {},
        settings=org.settings or {},
        created_at=org.created_at
    )


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    request: UpdateOrganizationRequest,
    auth: AuthContext = Depends(require_permission("org:update")),
    db: AsyncSession = Depends(get_db)
):
    """
    更新组织信息
    """
    # 检查是否是当前用户的组织
    if org_id != auth.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改此组织"
        )

    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在"
        )

    # 更新字段
    if request.name is not None:
        org.name = request.name

    if request.settings is not None:
        # 合并设置
        current_settings = org.settings or {}
        current_settings.update(request.settings)
        org.settings = current_settings

    if request.quotas is not None:
        # 需要 admin 权限才能修改配额
        if not auth.has_permission("org:admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权修改配额"
            )
        current_quotas = org.quotas or {}
        current_quotas.update(request.quotas)
        org.quotas = current_quotas

    org.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(org)

    return OrganizationResponse(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        tier=org.tier,
        status=org.status,
        quotas=org.quotas or {},
        settings=org.settings or {},
        created_at=org.created_at
    )


@router.get("/{org_id}/members", response_model=List[OrganizationMemberResponse])
async def list_organization_members(
    org_id: str,
    auth: AuthContext = Depends(require_permission("user:read")),
    db: AsyncSession = Depends(get_db)
):
    """
    获取组织成员列表
    """
    if org_id != auth.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此组织成员"
        )

    result = await db.execute(
        select(User)
        .where(and_(User.org_id == org_id, User.status != "deleted"))
        .order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    return [
        OrganizationMemberResponse(
            id=str(u.id),
            email=u.email,
            name=u.name,
            status=u.status,
            created_at=u.created_at
        )
        for u in users
    ]
