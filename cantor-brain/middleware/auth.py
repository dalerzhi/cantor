"""
认证中间件
JWT 验证和权限检查
"""
from typing import Optional, List, Callable
from functools import wraps
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.config import settings
from services.auth import validate_access_token, check_permission

security = HTTPBearer(auto_error=False)


class AuthContext:
    """认证上下文"""

    def __init__(
        self,
        user_id: str,
        email: str,
        org_id: str,
        permissions: List[str],
        workspaces: List[dict],
        jti: str,
        exp: int
    ):
        self.user_id = user_id
        self.email = email
        self.org_id = org_id
        self.permissions = permissions
        self.workspaces = workspaces
        self.jti = jti
        self.exp = exp

    def has_permission(self, required: str) -> bool:
        """检查是否拥有指定权限"""
        return check_permission(self.permissions, required)

    def has_workspace_access(self, workspace_id: str) -> bool:
        """检查是否有工作空间访问权限"""
        for ws in self.workspaces:
            if ws.get("id") == workspace_id:
                return True
        return False

    def get_workspace_permissions(self, workspace_id: str) -> List[str]:
        """获取指定工作空间的权限"""
        for ws in self.workspaces:
            if ws.get("id") == workspace_id:
                return ws.get("permissions", [])
        return []


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> AuthContext:
    """
    获取当前用户的认证上下文

    Raises:
        HTTPException: 未认证或 token 无效
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials

    # 验证 token
    claims = validate_access_token(token)
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 检查黑名单（如果有 Redis）
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client:
        jti = claims.get("jti")
        blacklisted = await redis_client.get(f"jwt:blacklist:{jti}")
        if blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="token 已被撤销",
                headers={"WWW-Authenticate": "Bearer"}
            )

    # 构建上下文
    return AuthContext(
        user_id=claims.get("sub"),
        email=claims.get("email"),
        org_id=claims.get("org", {}).get("id"),
        permissions=claims.get("permissions", []),
        workspaces=claims.get("workspaces", []),
        jti=claims.get("jti"),
        exp=claims.get("exp")
    )


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[AuthContext]:
    """
    可选的用户认证（不强制要求）

    Returns:
        AuthContext 或 None
    """
    if not credentials:
        return None

    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None


def require_auth():
    """
    要求认证的依赖

    用法:
        @router.get("/protected")
        async def protected_route(auth: AuthContext = Depends(require_auth())):
            return {"user_id": auth.user_id}
    """
    # 返回 get_current_user 函数本身，而不是 Depends 对象
    # 这样 Depends(require_auth()) 就等于 Depends(get_current_user)
    return get_current_user


def require_permission(permission: str):
    """
    要求特定权限的依赖

    用法:
        @router.post("/users")
        async def create_user(
            auth: AuthContext = Depends(require_permission("user:create"))
        ):
            ...
    """
    async def permission_checker(
        auth: AuthContext = Depends(get_current_user)
    ) -> AuthContext:
        if not auth.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足: 需要 {permission}"
            )
        return auth

    # 返回函数本身，而不是 Depends 对象
    return permission_checker


def require_workspace_access(workspace_id_param: str = "workspace_id"):
    """
    要求工作空间访问权限的依赖

    用法:
        @router.get("/workspaces/{workspace_id}/devices")
        async def list_devices(
            workspace_id: str,
            auth: AuthContext = Depends(require_workspace_access())
        ):
            ...
    """
    async def workspace_checker(
        request: Request,
        auth: AuthContext = Depends(get_current_user)
    ) -> AuthContext:
        workspace_id = request.path_params.get(workspace_id_param)

        if workspace_id and not auth.has_workspace_access(workspace_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此工作空间"
            )

        return auth

    # 返回函数本身，而不是 Depends 对象
    return workspace_checker


class APIKeyAuth:
    """API Key 认证中间件"""

    def __init__(self):
        self.api_key_header = "X-API-Key"
        self.api_key_query = "api_key"

    async def __call__(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db)
    ) -> Optional[dict]:
        """
        从请求中提取并验证 API Key

        Returns:
            API Key 信息或 None
        """
        # 从 Header 或 Query 参数获取
        api_key = request.headers.get(self.api_key_header)
        if not api_key:
            api_key = request.query_params.get(self.api_key_query)

        if not api_key:
            return None

        # 验证
        from services.api_key import APIKeyService

        redis_client = getattr(request.app.state, "redis", None)
        service = APIKeyService(db, redis_client)

        client_ip = self._get_client_ip(request)
        api_key_info = await service.validate_api_key(api_key, client_ip)

        return api_key_info

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        return request.client.host if request.client else "unknown"


async def get_api_key_or_jwt(
    request: Request,
    api_key_auth: APIKeyAuth = Depends(),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    支持 API Key 或 JWT 认证

    优先级：API Key > JWT

    Returns:
        认证信息字典
    """
    # 先尝试 API Key
    if api_key_auth:
        return {
            "type": "api_key",
            **api_key_auth
        }

    # 再尝试 JWT
    if credentials:
        auth_ctx = await get_current_user(request, credentials, db)
        return {
            "type": "jwt",
            "user_id": auth_ctx.user_id,
            "org_id": auth_ctx.org_id,
            "permissions": auth_ctx.permissions,
            "workspaces": auth_ctx.workspaces
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="需要 API Key 或 JWT 认证"
    )
