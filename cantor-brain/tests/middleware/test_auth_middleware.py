"""
认证中间件测试
测试 JWT 验证和权限检查
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from middleware.auth import (
    AuthContext,
    get_current_user,
    require_auth,
    require_permission
)
from services.auth import generate_token_pair, check_permission
from tests.utils import generate_test_uuid, MockRedis, create_test_token_payload


class TestAuthContext:
    """认证上下文测试"""

    def test_auth_context_creation(self):
        """测试创建认证上下文"""
        ctx = AuthContext(
            user_id="user-123",
            email="test@example.com",
            org_id="org-123",
            permissions=["cantor:*"],
            workspaces=[{"id": "ws-1", "name": "Default"}],
            jti="jti-123",
            exp=1234567890
        )

        assert ctx.user_id == "user-123"
        assert ctx.email == "test@example.com"
        assert ctx.org_id == "org-123"
        assert ctx.permissions == ["cantor:*"]

    def test_has_permission_exact_match(self):
        """测试精确权限匹配"""
        ctx = AuthContext(
            user_id="user-123",
            email="test@example.com",
            org_id="org-123",
            permissions=["user:read", "user:write"],
            workspaces=[],
            jti="jti-123",
            exp=1234567890
        )

        assert ctx.has_permission("user:read") is True
        assert ctx.has_permission("user:write") is True
        assert ctx.has_permission("user:delete") is False

    def test_has_permission_wildcard(self):
        """测试通配符权限"""
        ctx = AuthContext(
            user_id="user-123",
            email="test@example.com",
            org_id="org-123",
            permissions=["*"],
            workspaces=[],
            jti="jti-123",
            exp=1234567890
        )

        assert ctx.has_permission("any:permission") is True
        assert ctx.has_permission("admin:delete") is True

    def test_has_permission_segment_wildcard(self):
        """测试段通配符权限"""
        ctx = AuthContext(
            user_id="user-123",
            email="test@example.com",
            org_id="org-123",
            permissions=["device:*"],
            workspaces=[],
            jti="jti-123",
            exp=1234567890
        )

        assert ctx.has_permission("device:read") is True
        assert ctx.has_permission("device:control") is True
        assert ctx.has_permission("user:read") is False

    def test_has_workspace_access_true(self):
        """测试有工作空间访问权限"""
        ctx = AuthContext(
            user_id="user-123",
            email="test@example.com",
            org_id="org-123",
            permissions=[],
            workspaces=[{"id": "ws-1", "name": "Default"}],
            jti="jti-123",
            exp=1234567890
        )

        assert ctx.has_workspace_access("ws-1") is True

    def test_has_workspace_access_false(self):
        """测试无工作空间访问权限"""
        ctx = AuthContext(
            user_id="user-123",
            email="test@example.com",
            org_id="org-123",
            permissions=[],
            workspaces=[{"id": "ws-1", "name": "Default"}],
            jti="jti-123",
            exp=1234567890
        )

        assert ctx.has_workspace_access("ws-2") is False

    def test_get_workspace_permissions(self):
        """测试获取工作空间权限"""
        ctx = AuthContext(
            user_id="user-123",
            email="test@example.com",
            org_id="org-123",
            permissions=[],
            workspaces=[{
                "id": "ws-1",
                "name": "Default",
                "permissions": ["cantor:*", "device:control"]
            }],
            jti="jti-123",
            exp=1234567890
        )

        perms = ctx.get_workspace_permissions("ws-1")
        assert "cantor:*" in perms
        assert "device:control" in perms

        # 不存在的工作空间返回空列表
        assert ctx.get_workspace_permissions("ws-2") == []


class TestRequireAuthValidToken:
    """require_auth 有效 token 测试"""

    @pytest.mark.asyncio
    async def test_require_auth_valid_token(self, db_session, test_user):
        """测试有效 token 通过认证"""
        # 准备 token
        workspaces = [{
            "id": "ws-1",
            "name": "Default",
            "permissions": ["cantor:*"]
        }]
        access_token, _ = generate_token_pair(test_user, workspaces)

        # 模拟请求
        request = MagicMock()
        request.app.state.redis = None

        credentials = MagicMock()
        credentials.credentials = access_token

        # 调用 get_current_user
        ctx = await get_current_user(request, credentials, db_session)

        assert ctx is not None
        assert ctx.user_id == str(test_user.id)
        assert ctx.email == test_user.email

    @pytest.mark.asyncio
    async def test_require_auth_returns_dependency(self):
        """测试 require_auth 返回依赖"""
        dep = require_auth()
        assert dep is not None


class TestRequireAuthInvalidToken:
    """require_auth 无效 token 测试"""

    @pytest.mark.asyncio
    async def test_require_auth_no_credentials(self, db_session):
        """测试无凭证"""
        request = MagicMock()
        request.app.state.redis = None

        with pytest.raises(HTTPException) as exc:
            await get_current_user(request, None, db_session)

        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_require_auth_invalid_token_string(self, db_session):
        """测试无效 token 字符串"""
        request = MagicMock()
        request.app.state.redis = None

        credentials = MagicMock()
        credentials.credentials = "invalid-token-string"

        with pytest.raises(HTTPException) as exc:
            await get_current_user(request, credentials, db_session)

        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_require_auth_expired_token(self, db_session):
        """测试过期 token"""
        import jwt
        from datetime import datetime, timedelta
        from core.config import settings

        # 创建已过期的 token
        now = datetime.utcnow()
        claims = {
            "sub": "user-123",
            "email": "test@example.com",
            "jti": "jti-123",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
            "type": "access"
        }
        expired_token = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        request = MagicMock()
        request.app.state.redis = None

        credentials = MagicMock()
        credentials.credentials = expired_token

        with pytest.raises(HTTPException) as exc:
            await get_current_user(request, credentials, db_session)

        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_require_auth_blacklisted_token(self, db_session, test_user, mock_redis):
        """测试黑名单中的 token"""
        workspaces = [{
            "id": "ws-1",
            "name": "Default",
            "permissions": ["cantor:*"]
        }]
        access_token, _ = generate_token_pair(test_user, workspaces)

        # 解码获取 jti
        import jwt
        from core.config import settings
        claims = jwt.decode(access_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        jti = claims["jti"]

        # 模拟 Redis 返回黑名单
        mock_redis._data[f"jwt:blacklist:{jti}"] = "revoked"

        request = MagicMock()
        request.app.state.redis = mock_redis

        credentials = MagicMock()
        credentials.credentials = access_token

        with pytest.raises(HTTPException) as exc:
            await get_current_user(request, credentials, db_session)

        assert exc.value.status_code == 401
        assert "撤销" in exc.value.detail


class TestRequirePermissionAllowed:
    """require_permission 权限允许测试"""

    @pytest.mark.asyncio
    async def test_require_permission_allowed(self, db_session, test_admin_user):
        """测试有权限通过"""
        workspaces = [{
            "id": "ws-1",
            "name": "Default",
            "permissions": ["*"]
        }]
        access_token, _ = generate_token_pair(test_admin_user, workspaces)

        request = MagicMock()
        request.app.state.redis = None

        credentials = MagicMock()
        credentials.credentials = access_token

        # 先获取用户上下文
        ctx = await get_current_user(request, credentials, db_session)

        # 验证有权限
        assert ctx.has_permission("user:create") is True
        assert ctx.has_permission("workspace:delete") is True

    @pytest.mark.asyncio
    async def test_require_permission_exact_match(self, db_session, test_user):
        """测试精确权限匹配"""
        workspaces = [{
            "id": "ws-1",
            "name": "Default",
            "permissions": ["device:read", "device:control"]
        }]
        access_token, _ = generate_token_pair(test_user, workspaces)

        request = MagicMock()
        request.app.state.redis = None

        credentials = MagicMock()
        credentials.credentials = access_token

        ctx = await get_current_user(request, credentials, db_session)

        assert ctx.has_permission("device:read") is True
        assert ctx.has_permission("device:control") is True


class TestRequirePermissionDenied:
    """require_permission 权限拒绝测试"""

    @pytest.mark.asyncio
    async def test_require_permission_denied(self, db_session, test_user):
        """测试无权限被拒绝"""
        workspaces = [{
            "id": "ws-1",
            "name": "Default",
            "permissions": ["device:read"]  # 只有读权限
        }]
        access_token, _ = generate_token_pair(test_user, workspaces)

        request = MagicMock()
        request.app.state.redis = None

        credentials = MagicMock()
        credentials.credentials = access_token

        ctx = await get_current_user(request, credentials, db_session)

        # 有读权限
        assert ctx.has_permission("device:read") is True
        # 没有写权限
        assert ctx.has_permission("device:control") is False
        # 没有管理权限
        assert ctx.has_permission("admin:all") is False

    @pytest.mark.asyncio
    async def test_require_permission_empty_permissions(self, db_session, test_user):
        """测试无任何权限"""
        workspaces = [{
            "id": "ws-1",
            "name": "Default",
            "permissions": []
        }]
        access_token, _ = generate_token_pair(test_user, workspaces)

        request = MagicMock()
        request.app.state.redis = None

        credentials = MagicMock()
        credentials.credentials = access_token

        ctx = await get_current_user(request, credentials, db_session)

        assert ctx.has_permission("any:permission") is False


class TestAPIKeyAuth:
    """API Key 认证测试"""

    @pytest.mark.asyncio
    async def test_api_key_auth_valid(self, db_session, test_api_key):
        """测试有效 API Key"""
        from middleware.auth import APIKeyAuth

        api_key_obj, raw_key = test_api_key

        auth = APIKeyAuth()

        # 模拟请求
        request = MagicMock()
        request.headers = {"X-API-Key": raw_key}
        request.query_params = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        result = await auth(request, db_session)

        assert result is not None
        assert result["id"] == str(api_key_obj.id)

    @pytest.mark.asyncio
    async def test_api_key_auth_from_query(self, db_session, test_api_key):
        """测试从 Query 参数获取 API Key"""
        from middleware.auth import APIKeyAuth

        api_key_obj, raw_key = test_api_key

        auth = APIKeyAuth()

        request = MagicMock()
        request.headers = {}
        request.query_params = {"api_key": raw_key}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        result = await auth(request, db_session)

        assert result is not None

    @pytest.mark.asyncio
    async def test_api_key_auth_invalid(self, db_session):
        """测试无效 API Key"""
        from middleware.auth import APIKeyAuth

        auth = APIKeyAuth()

        request = MagicMock()
        request.headers = {"X-API-Key": "cantor_invalid_key"}
        request.query_params = {}
        request.client = MagicMock()
        request.client.host = "127.0.0.1"

        result = await auth(request, db_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_api_key_auth_missing(self, db_session):
        """测试无 API Key"""
        from middleware.auth import APIKeyAuth

        auth = APIKeyAuth()

        request = MagicMock()
        request.headers = {}
        request.query_params = {}
        request.client = MagicMock()

        result = await auth(request, db_session)

        assert result is None
