"""
用户认证 API
注册、登录、登出、Token 刷新
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.config import settings
from services.auth import AuthService, validate_password_strength
from middleware.auth import get_current_user, AuthContext, require_auth


router = APIRouter(prefix="/auth", tags=["认证"])


# ===== 请求/响应模型 =====

class RegisterRequest(BaseModel):
    """注册请求"""
    email: EmailStr
    password: str = Field(..., min_length=12)
    name: str = Field(..., min_length=1, max_length=100)
    org_name: str = Field(..., min_length=1, max_length=255)
    org_slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr
    password: str
    org_slug: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求"""
    refresh_token: str


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """用户信息响应"""
    id: str
    email: str
    name: Optional[str]
    org_id: str
    org_name: Optional[str]
    status: str
    mfa_enabled: bool
    created_at: datetime


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12)


# ===== API 路由 =====

@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用户注册

    创建新用户和组织，返回登录凭证
    """
    # 验证密码强度
    valid, msg = validate_password_strength(request.password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    auth_service = AuthService(db)
    user, error = await auth_service.register_user(
        email=request.email,
        password=request.password,
        name=request.name,
        org_name=request.org_name,
        org_slug=request.org_slug
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    # 自动登录
    token_data, error = await auth_service.login(request.email, request.password)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册成功但自动登录失败"
        )

    return LoginResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_in=token_data["expires_in"],
        user=UserResponse(
            id=token_data["user"]["id"],
            email=token_data["user"]["email"],
            name=token_data["user"]["name"],
            org_id=token_data["user"]["org_id"],
            org_name=token_data["user"]["org_name"],
            status=user.status,
            mfa_enabled=user.mfa_enabled,
            created_at=user.created_at
        )
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录

    返回 JWT token 对
    """
    auth_service = AuthService(db)
    token_data, error = await auth_service.login(
        email=request.email,
        password=request.password,
        org_slug=request.org_slug
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 获取用户详情
    user = await auth_service.get_current_user(token_data["user"]["id"])

    return LoginResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_in=token_data["expires_in"],
        user=UserResponse(
            id=token_data["user"]["id"],
            email=token_data["user"]["email"],
            name=token_data["user"]["name"],
            org_id=token_data["user"]["org_id"],
            org_name=token_data["user"]["org_name"],
            status=user.status,
            mfa_enabled=user.mfa_enabled,
            created_at=user.created_at
        )
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    刷新 Token

    使用 refresh_token 获取新的 token 对
    """
    redis_client = getattr(req.app.state, "redis", None)
    auth_service = AuthService(db, redis_client)

    result = await auth_service.refresh_access_token(
        db,
        request.refresh_token,
        redis_client
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的 refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    access_token, refresh_token = result

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    req: Request,
    auth: AuthContext = Depends(require_auth()),
    db: AsyncSession = Depends(get_db)
):
    """
    登出

    将当前 token 加入黑名单
    """
    redis_client = getattr(req.app.state, "redis", None)
    auth_service = AuthService(db, redis_client)

    await auth_service.logout(auth.jti, auth.exp)

    return MessageResponse(message="登出成功")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    auth: AuthContext = Depends(require_auth()),
    db: AsyncSession = Depends(get_db)
):
    """
    登出所有设备

    通过递增 token_version 使所有 refresh_token 失效
    """
    from services.auth import revoke_all_tokens

    await revoke_all_tokens(db, auth.user_id)

    return MessageResponse(message="已登出所有设备")


@router.get("/me", response_model=UserResponse)
async def get_me(
    auth: AuthContext = Depends(require_auth()),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户信息
    """
    auth_service = AuthService(db)
    user = await auth_service.get_current_user(auth.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        org_id=str(user.org_id),
        org_name=user.organization.name if user.organization else None,
        status=user.status,
        mfa_enabled=user.mfa_enabled,
        created_at=user.created_at
    )


@router.post("/me/password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    auth: AuthContext = Depends(require_auth()),
    db: AsyncSession = Depends(get_db)
):
    """
    修改密码
    """
    from services.auth import hash_password, verify_password
    from models.auth import User
    from sqlalchemy import select

    # 验证密码强度
    valid, msg = validate_password_strength(request.new_password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )

    # 获取用户
    result = await db.execute(select(User).where(User.id == auth.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 验证当前密码
    if not verify_password(request.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误"
        )

    # 更新密码
    user.password_hash = hash_password(request.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    user.token_version += 1  # 使所有 token 失效

    await db.commit()

    return MessageResponse(message="密码修改成功，请重新登录")
