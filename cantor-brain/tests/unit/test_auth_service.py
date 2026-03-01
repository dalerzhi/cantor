"""
认证服务单元测试
测试密码哈希、JWT 生成和验证、权限匹配
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock

from services.auth import (
    hash_password,
    verify_password,
    generate_token_pair,
    validate_access_token,
    validate_refresh_token,
    check_permission,
    Permission,
    validate_password_strength,
    refresh_access_token
)
from core.config import settings


class TestPasswordHash:
    """密码哈希测试"""

    def test_hash_password_returns_string(self):
        """测试哈希密码返回字符串"""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password

    def test_hash_password_creates_different_hashes(self):
        """测试相同密码生成不同哈希（bcrypt salt）"""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # bcrypt 每次生成不同的哈希
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """测试验证正确密码"""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """测试验证错误密码"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """测试空密码验证"""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password("", hashed) is False


class TestPasswordStrength:
    """密码强度验证测试"""

    def test_valid_strong_password(self):
        """测试有效的强密码"""
        password = "StrongPassword123!"
        valid, msg = validate_password_strength(password)
        
        assert valid is True
        assert msg == ""

    def test_password_too_short(self):
        """测试密码太短"""
        password = "Short1!"
        valid, msg = validate_password_strength(password)
        
        assert valid is False
        assert "至少" in msg

    def test_password_no_uppercase(self):
        """测试密码无大写字母"""
        password = "lowercase123!"
        valid, msg = validate_password_strength(password)
        
        assert valid is False
        assert "大写字母" in msg

    def test_password_no_lowercase(self):
        """测试密码无小写字母"""
        password = "UPPERCASE123!"
        valid, msg = validate_password_strength(password)
        
        assert valid is False
        assert "小写字母" in msg

    def test_password_no_number(self):
        """测试密码无数字"""
        password = "NoNumbersHere!"
        valid, msg = validate_password_strength(password)
        
        assert valid is False
        assert "数字" in msg

    def test_password_no_special_char(self):
        """测试密码无特殊字符"""
        password = "NoSpecialChar123"
        valid, msg = validate_password_strength(password)
        
        assert valid is False
        assert "特殊字符" in msg


class TestGenerateTokenPair:
    """JWT Token 生成测试"""

    def test_generate_token_pair_returns_tuple(self):
        """测试生成 token 对返回元组"""
        user = MagicMock()
        user.id = "test-user-id"
        user.email = "test@example.com"
        user.org_id = "test-org-id"
        user.token_version = 1
        user.organization = MagicMock()
        user.organization.name = "Test Org"

        workspaces = [{
            "id": "ws-1",
            "name": "Default",
            "role": "Operator",
            "permissions": ["cantor:*"]
        }]

        access_token, refresh_token = generate_token_pair(user, workspaces)

        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)
        assert len(access_token) > 0
        assert len(refresh_token) > 0
        assert access_token != refresh_token

    def test_generate_token_pair_includes_permissions(self):
        """测试 access token 包含权限"""
        import jwt

        user = MagicMock()
        user.id = "test-user-id"
        user.email = "test@example.com"
        user.org_id = "test-org-id"
        user.token_version = 1
        user.organization = MagicMock()
        user.organization.name = "Test Org"

        workspaces = [{
            "id": "ws-1",
            "name": "Default",
            "role": "Admin",
            "permissions": ["user:*", "workspace:*"]
        }]

        access_token, _ = generate_token_pair(user, workspaces)
        claims = jwt.decode(access_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        assert "permissions" in claims
        assert "user:*" in claims["permissions"]
        assert "workspace:*" in claims["permissions"]

    def test_generate_token_pair_has_correct_type(self):
        """测试 token 类型正确"""
        import jwt

        user = MagicMock()
        user.id = "test-user-id"
        user.email = "test@example.com"
        user.org_id = "test-org-id"
        user.token_version = 1
        user.organization = MagicMock()
        user.organization.name = "Test Org"

        workspaces = []

        access_token, refresh_token = generate_token_pair(user, workspaces)

        access_claims = jwt.decode(access_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        refresh_claims = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        assert access_claims["type"] == "access"
        assert refresh_claims["type"] == "refresh"


class TestValidateAccessToken:
    """Access Token 验证测试"""

    def test_validate_access_token_valid(self):
        """测试验证有效的 access token"""
        user = MagicMock()
        user.id = "test-user-id"
        user.email = "test@example.com"
        user.org_id = "test-org-id"
        user.token_version = 1
        user.organization = MagicMock()
        user.organization.name = "Test Org"

        access_token, _ = generate_token_pair(user, [])
        claims = validate_access_token(access_token)

        assert claims is not None
        assert claims["sub"] == "test-user-id"
        assert claims["email"] == "test@example.com"
        assert claims["type"] == "access"

    def test_validate_access_token_invalid_string(self):
        """测试验证无效字符串"""
        claims = validate_access_token("invalid-token")
        
        assert claims is None

    def test_validate_access_token_expired(self):
        """测试验证过期的 token"""
        import jwt

        # 创建已过期的 token
        now = datetime.utcnow()
        claims = {
            "sub": "test-user-id",
            "email": "test@example.com",
            "jti": "test-jti",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),  # 已过期
            "type": "access"
        }
        expired_token = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        result = validate_access_token(expired_token)
        
        assert result is None

    def test_validate_access_token_wrong_type(self):
        """测试验证错误类型的 token"""
        import jwt

        now = datetime.utcnow()
        claims = {
            "sub": "test-user-id",
            "jti": "test-jti",
            "iat": now,
            "exp": now + timedelta(hours=1),
            "type": "refresh"  # 错误类型
        }
        token = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        result = validate_access_token(token)
        
        assert result is None


class TestRefreshToken:
    """Refresh Token 验证测试"""

    def test_validate_refresh_token_valid(self):
        """测试验证有效的 refresh token"""
        user = MagicMock()
        user.id = "test-user-id"
        user.token_version = 1
        user.email = "test@example.com"
        user.org_id = "test-org-id"
        user.organization = MagicMock()
        user.organization.name = "Test Org"

        _, refresh_token = generate_token_pair(user, [])
        claims = validate_refresh_token(refresh_token)

        assert claims is not None
        assert claims["sub"] == "test-user-id"
        assert claims["type"] == "refresh"
        assert "token_version" in claims

    def test_validate_refresh_token_invalid_string(self):
        """测试验证无效字符串"""
        claims = validate_refresh_token("invalid-refresh-token")
        
        assert claims is None

    def test_validate_refresh_token_wrong_type(self):
        """测试验证错误类型的 token"""
        import jwt

        now = datetime.utcnow()
        claims = {
            "sub": "test-user-id",
            "jti": "test-jti",
            "iat": now,
            "exp": now + timedelta(hours=1),
            "type": "access"  # 错误类型
        }
        token = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        result = validate_refresh_token(token)
        
        assert result is None


class TestPermissionMatch:
    """权限匹配测试"""

    def test_permission_exact_match(self):
        """测试精确匹配"""
        perm = Permission("user:read")
        
        assert perm.match("user:read") is True
        assert perm.match("user:write") is False
        assert perm.match("admin:read") is False

    def test_permission_wildcard_all(self):
        """测试通配符 * 匹配所有"""
        perm = Permission("*")
        
        assert perm.match("user:read") is True
        assert perm.match("admin:delete") is True
        assert perm.match("any:action") is True

    def test_permission_wildcard_segment(self):
        """测试段通配符 user:*"""
        perm = Permission("user:*")
        
        assert perm.match("user:read") is True
        assert perm.match("user:write") is True
        assert perm.match("user:delete") is True
        assert perm.match("admin:read") is False

    def test_permission_multi_segment(self):
        """测试多段权限"""
        perm = Permission("org:user:read")
        
        assert perm.match("org:user:read") is True
        assert perm.match("org:user:write") is False
        assert perm.match("org:admin:read") is False

    def test_check_permission_function(self):
        """测试 check_permission 函数"""
        user_perms = ["user:*", "workspace:read", "device:control"]
        
        assert check_permission(user_perms, "user:read") is True
        assert check_permission(user_perms, "user:delete") is True
        assert check_permission(user_perms, "workspace:read") is True
        assert check_permission(user_perms, "workspace:write") is False
        assert check_permission(user_perms, "admin:all") is False

    def test_check_permission_with_star(self):
        """测试 check_permission 使用 * 通配符"""
        user_perms = ["*"]
        
        assert check_permission(user_perms, "any:permission") is True
        assert check_permission(user_perms, "admin:delete") is True


class TestRefreshAccessToken:
    """刷新 Access Token 测试"""

    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid_token(self):
        """测试刷新无效 token"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        result = await refresh_access_token(mock_db, "invalid-token", mock_redis)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_access_token_blacklisted(self):
        """测试刷新已黑名单的 token"""
        import jwt

        # 创建 refresh token
        now = datetime.utcnow()
        claims = {
            "sub": "test-user-id",
            "jti": "test-jti-blacklisted",
            "token_version": 1,
            "iat": now,
            "exp": now + timedelta(days=7),
            "type": "refresh"
        }
        token = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="revoked")

        result = await refresh_access_token(mock_db, token, mock_redis)
        
        assert result is None
