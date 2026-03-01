"""
API Key 服务
处理 API Key 的创建、验证和撤销
"""
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.auth import APIKey, User, Organization, Workspace
from services.auth import check_permission


def generate_api_key() -> Tuple[str, str]:
    """
    生成 API Key

    Returns:
        (raw_key, key_hash) - 原始 key（只显示一次）和 hash
    """
    raw_key = settings.API_KEY_PREFIX + secrets.token_urlsafe(settings.API_KEY_LENGTH)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash


def hash_api_key(key: str) -> str:
    """计算 API Key 的 hash"""
    return hashlib.sha256(key.encode()).hexdigest()


class APIKeyService:
    """API Key 服务"""

    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client

    async def create_api_key(
        self,
        user: User,
        name: str,
        permissions: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
        description: Optional[str] = None,
        allowed_ips: Optional[List[str]] = None,
        rate_limit: int = 1000,
        expires_at: Optional[datetime] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        创建 API Key

        Args:
            user: 创建者
            name: Key 名称
            permissions: 权限列表（可选，不指定则继承创建者权限）
            workspace_id: 工作空间 ID（可选，不指定则为组织级 Key）
            description: 描述
            allowed_ips: IP 白名单
            rate_limit: 速率限制（每分钟请求数）
            expires_at: 过期时间

        Returns:
            (api_key_data, error_message)
        """
        # 验证权限：API Key 权限不能超过创建者权限
        if permissions:
            # 获取用户权限
            user_perms = await self._get_user_permissions(user, workspace_id)

            for perm in permissions:
                if not any(check_permission([p], perm) for p in user_perms):
                    return None, f"无权授予权限: {perm}"

        # 生成 Key
        raw_key, key_hash = generate_api_key()

        # 创建记录
        api_key = APIKey(
            org_id=user.org_id,
            workspace_id=workspace_id,
            name=name,
            description=description,
            key_hash=key_hash,
            key_preview=raw_key[:10] + "...",
            permissions=permissions,
            allowed_ips=allowed_ips,
            rate_limit=rate_limit,
            expires_at=expires_at,
            status="active",
            created_by=user.id
        )

        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)

        # 缓存到 Redis
        if self.redis:
            await self._cache_api_key(key_hash, api_key)

        return {
            "id": str(api_key.id),
            "name": api_key.name,
            "key": raw_key,  # ⚠️ 仅返回这一次
            "key_preview": api_key.key_preview,
            "permissions": api_key.permissions,
            "workspace_id": str(api_key.workspace_id) if api_key.workspace_id else None,
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "created_at": api_key.created_at.isoformat()
        }, None

    async def validate_api_key(
        self,
        key: str,
        client_ip: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        验证 API Key

        Args:
            key: 原始 API Key
            client_ip: 客户端 IP（用于 IP 白名单检查）

        Returns:
            API Key 信息，无效时返回 None
        """
        key_hash = hash_api_key(key)

        # 先查缓存
        if self.redis:
            cached = await self.redis.get(f"apikey:{key_hash}")
            if cached:
                import json
                api_key_info = json.loads(cached)
                # 检查状态和过期
                if api_key_info.get("status") != "active":
                    return None
                if api_key_info.get("expires_at"):
                    if datetime.fromisoformat(api_key_info["expires_at"]) < datetime.utcnow():
                        return None
                return api_key_info

        # 查数据库
        result = await self.db.execute(
            select(APIKey).where(APIKey.key_hash == key_hash)
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            return None

        # 检查状态
        if api_key.status != "active":
            return None

        # 检查过期
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None

        # 检查 IP 白名单
        if api_key.allowed_ips and client_ip:
            if client_ip not in api_key.allowed_ips:
                return None

        # 更新最后使用时间
        api_key.last_used_at = datetime.utcnow()
        api_key.last_used_ip = client_ip
        await self.db.commit()

        # 构建返回信息
        api_key_info = {
            "id": str(api_key.id),
            "org_id": str(api_key.org_id),
            "workspace_id": str(api_key.workspace_id) if api_key.workspace_id else None,
            "permissions": api_key.permissions or [],
            "rate_limit": api_key.rate_limit
        }

        # 缓存
        if self.redis:
            await self._cache_api_key(key_hash, api_key)

        return api_key_info

    async def revoke_api_key(
        self,
        api_key_id: str,
        user: User,
        reason: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        撤销 API Key

        Args:
            api_key_id: API Key ID
            user: 操作者
            reason: 撤销原因

        Returns:
            (success, error_message)
        """
        result = await self.db.execute(
            select(APIKey).where(APIKey.id == api_key_id)
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            return False, "API Key 不存在"

        # 检查权限
        if api_key.org_id != user.org_id:
            return False, "无权操作此 API Key"

        # 撤销
        api_key.status = "revoked"
        api_key.revoked_at = datetime.utcnow()
        api_key.revoked_reason = reason

        await self.db.commit()

        # 清除缓存
        if self.redis:
            await self.redis.delete(f"apikey:{api_key.key_hash}")

        return True, None

    async def list_api_keys(
        self,
        user: User,
        workspace_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出 API Keys

        Args:
            user: 当前用户
            workspace_id: 工作空间 ID（可选）

        Returns:
            API Key 列表（不包含实际 key）
        """
        query = select(APIKey).where(
            and_(
                APIKey.org_id == user.org_id,
                APIKey.status != "deleted"
            )
        )

        if workspace_id:
            query = query.where(APIKey.workspace_id == workspace_id)

        query = query.order_by(APIKey.created_at.desc())

        result = await self.db.execute(query)
        api_keys = result.scalars().all()

        return [
            {
                "id": str(k.id),
                "name": k.name,
                "description": k.description,
                "key_preview": k.key_preview,
                "workspace_id": str(k.workspace_id) if k.workspace_id else None,
                "permissions": k.permissions,
                "status": k.status,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "created_at": k.created_at.isoformat()
            }
            for k in api_keys
        ]

    async def _get_user_permissions(
        self,
        user: User,
        workspace_id: Optional[str] = None
    ) -> List[str]:
        """获取用户在指定工作空间的权限"""
        from models.auth import UserWorkspaceRole, Role

        query = select(UserWorkspaceRole, Role).join(
            Role, UserWorkspaceRole.role_id == Role.id
        ).where(UserWorkspaceRole.user_id == user.id)

        if workspace_id:
            query = query.where(UserWorkspaceRole.workspace_id == workspace_id)

        result = await self.db.execute(query)

        permissions = set()
        for uwr, role in result.all():
            permissions.update(role.permissions or [])

        return list(permissions)

    async def _cache_api_key(self, key_hash: str, api_key: APIKey):
        """缓存 API Key 到 Redis"""
        import json

        data = {
            "id": str(api_key.id),
            "org_id": str(api_key.org_id),
            "workspace_id": str(api_key.workspace_id) if api_key.workspace_id else None,
            "permissions": api_key.permissions or [],
            "status": api_key.status,
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "rate_limit": api_key.rate_limit,
            "allowed_ips": api_key.allowed_ips
        }

        await self.redis.setex(
            f"apikey:{key_hash}",
            3600,  # 1 hour
            json.dumps(data)
        )
