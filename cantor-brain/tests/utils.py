"""
测试辅助函数
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import uuid


def generate_test_uuid() -> str:
    """生成测试用 UUID"""
    return str(uuid.uuid4())


class MockRedis:
    """模拟 Redis 客户端"""

    def __init__(self):
        self._data = {}

    async def get(self, key: str) -> Optional[str]:
        return self._data.get(key)

    async def set(self, key: str, value: str) -> bool:
        self._data[key] = value
        return True

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        self._data[key] = value
        return True

    async def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        return key in self._data


class MockUser:
    """模拟用户对象"""

    def __init__(
        self,
        user_id: str = None,
        email: str = "test@example.com",
        name: str = "Test User",
        org_id: str = None,
        status: str = "active",
        password_hash: str = None,
        token_version: int = 1,
        mfa_enabled: bool = False
    ):
        self.id = user_id or generate_test_uuid()
        self.email = email
        self.name = name
        self.org_id = org_id or generate_test_uuid()
        self.status = status
        self.password_hash = password_hash
        self.token_version = token_version
        self.mfa_enabled = mfa_enabled
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = None
        self.organization = None


class MockOrganization:
    """模拟组织对象"""

    def __init__(
        self,
        org_id: str = None,
        name: str = "Test Org",
        slug: str = "test-org",
        tier: str = "b2b",
        status: str = "active"
    ):
        self.id = org_id or generate_test_uuid()
        self.name = name
        self.slug = slug
        self.tier = tier
        self.status = status
        self.quotas = {}
        self.settings = {}


class MockWorkspace:
    """模拟工作空间对象"""

    def __init__(
        self,
        workspace_id: str = None,
        org_id: str = None,
        name: str = "Test Workspace",
        status: str = "active"
    ):
        self.id = workspace_id or generate_test_uuid()
        self.org_id = org_id or generate_test_uuid()
        self.name = name
        self.status = status
        self.description = None
        self.quotas = {}
        self.settings = {}
        self.deleted_at = None


class MockRole:
    """模拟角色对象"""

    def __init__(
        self,
        role_id: str = None,
        name: str = "Operator",
        permissions: list = None
    ):
        self.id = role_id or generate_test_uuid()
        self.name = name
        self.permissions = permissions or ["cantor:*", "device:control"]
        self.is_system = True


class MockAPIKey:
    """模拟 API Key 对象"""

    def __init__(
        self,
        key_id: str = None,
        org_id: str = None,
        workspace_id: str = None,
        name: str = "Test Key",
        key_hash: str = None,
        status: str = "active",
        permissions: list = None,
        allowed_ips: list = None
    ):
        self.id = key_id or generate_test_uuid()
        self.org_id = org_id or generate_test_uuid()
        self.workspace_id = workspace_id
        self.name = name
        self.key_hash = key_hash or "test_hash"
        self.key_preview = "cantor_abcd..."
        self.status = status
        self.permissions = permissions or []
        self.allowed_ips = allowed_ips
        self.rate_limit = 1000
        self.expires_at = None
        self.last_used_at = None
        self.last_used_ip = None
        self.created_at = datetime.utcnow()


def create_test_token_payload(
    user_id: str = None,
    email: str = "test@example.com",
    org_id: str = None,
    permissions: list = None,
    workspaces: list = None,
    jti: str = None,
    exp: int = None
) -> Dict[str, Any]:
    """创建测试用 token payload"""
    now = datetime.utcnow()
    return {
        "sub": user_id or generate_test_uuid(),
        "email": email,
        "org": {"id": org_id or generate_test_uuid(), "name": "Test Org"},
        "permissions": permissions or ["cantor:*"],
        "workspaces": workspaces or [],
        "jti": jti or generate_test_uuid(),
        "iat": now,
        "exp": exp or int((now + timedelta(hours=1)).timestamp()),
        "type": "access"
    }


def create_test_refresh_token_payload(
    user_id: str = None,
    token_version: int = 1,
    jti: str = None
) -> Dict[str, Any]:
    """创建测试用 refresh token payload"""
    now = datetime.utcnow()
    return {
        "sub": user_id or generate_test_uuid(),
        "jti": jti or generate_test_uuid(),
        "token_version": token_version,
        "iat": now,
        "exp": int((now + timedelta(days=7)).timestamp()),
        "type": "refresh"
    }
