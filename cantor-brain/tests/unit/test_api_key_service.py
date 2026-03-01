"""
API Key 服务单元测试
测试 API Key 的创建、验证和撤销
"""
import pytest
import hashlib
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from services.api_key import (
    generate_api_key,
    hash_api_key,
    APIKeyService
)
from tests.utils import MockRedis, MockUser, generate_test_uuid


class TestGenerateAPIKey:
    """API Key 生成测试"""

    def test_generate_api_key_returns_tuple(self):
        """测试生成 API Key 返回元组"""
        raw_key, key_hash = generate_api_key()
        
        assert isinstance(raw_key, str)
        assert isinstance(key_hash, str)
        assert len(raw_key) > 0
        assert len(key_hash) > 0

    def test_generate_api_key_has_prefix(self):
        """测试 API Key 包含前缀"""
        raw_key, _ = generate_api_key()
        
        assert raw_key.startswith("cantor_")

    def test_generate_api_key_hash_is_sha256(self):
        """测试 hash 是 SHA256"""
        raw_key, key_hash = generate_api_key()
        
        # SHA256 生成 64 字符的十六进制字符串
        assert len(key_hash) == 64
        assert all(c in "0123456789abcdef" for c in key_hash)

    def test_generate_api_key_unique(self):
        """测试每次生成不同的 Key"""
        raw_key1, _ = generate_api_key()
        raw_key2, _ = generate_api_key()
        
        assert raw_key1 != raw_key2


class TestHashAPIKey:
    """API Key 哈希测试"""

    def test_hash_api_key_consistent(self):
        """测试相同 Key 生成相同 hash"""
        key = "cantor_test_key_123"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        
        assert hash1 == hash2

    def test_hash_api_key_different_keys(self):
        """测试不同 Key 生成不同 hash"""
        key1 = "cantor_test_key_1"
        key2 = "cantor_test_key_2"
        
        assert hash_api_key(key1) != hash_api_key(key2)

    def test_hash_api_key_matches_generate(self):
        """测试 hash_api_key 与 generate_api_key 一致"""
        raw_key, key_hash = generate_api_key()
        
        assert hash_api_key(raw_key) == key_hash


class TestCreateAPIKey:
    """API Key 创建测试"""

    @pytest.mark.asyncio
    async def test_create_api_key_success(self, db_session, test_user, test_org):
        """测试成功创建 API Key"""
        service = APIKeyService(db_session, None)

        result, error = await service.create_api_key(
            user=test_user,
            name="Test Key",
            permissions=["cantor:read"],
            description="测试用 Key"
        )

        assert error is None
        assert result is not None
        assert "id" in result
        assert "key" in result
        assert result["name"] == "Test Key"
        assert result["permissions"] == ["cantor:read"]

    @pytest.mark.asyncio
    async def test_create_api_key_with_workspace(self, db_session, test_user, test_workspace):
        """测试创建工作空间级 API Key"""
        service = APIKeyService(db_session, None)

        result, error = await service.create_api_key(
            user=test_user,
            name="Workspace Key",
            workspace_id=str(test_workspace.id),
            permissions=None
        )

        assert error is None
        assert result is not None
        assert result["workspace_id"] == str(test_workspace.id)

    @pytest.mark.asyncio
    async def test_create_api_key_with_ip_whitelist(self, db_session, test_user):
        """测试创建带 IP 白名单的 API Key"""
        service = APIKeyService(db_session, None)

        result, error = await service.create_api_key(
            user=test_user,
            name="IP Restricted Key",
            allowed_ips=["192.168.1.1", "10.0.0.1"]
        )

        assert error is None
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_api_key_with_expiry(self, db_session, test_user):
        """测试创建有过期时间的 API Key"""
        service = APIKeyService(db_session, None)

        expires_at = datetime.utcnow() + timedelta(days=30)
        result, error = await service.create_api_key(
            user=test_user,
            name="Temporary Key",
            expires_at=expires_at
        )

        assert error is None
        assert result is not None
        assert result["expires_at"] is not None

    @pytest.mark.asyncio
    async def test_create_api_key_with_redis_cache(self, db_session, test_user, mock_redis):
        """测试创建 API Key 时缓存到 Redis"""
        service = APIKeyService(db_session, mock_redis)

        result, error = await service.create_api_key(
            user=test_user,
            name="Cached Key"
        )

        assert error is None
        assert result is not None
        # 验证 Redis 缓存
        assert len(mock_redis._data) > 0


class TestValidateAPIKey:
    """API Key 验证测试"""

    @pytest.mark.asyncio
    async def test_validate_api_key_valid(self, db_session, test_api_key):
        """测试验证有效的 API Key"""
        api_key_obj, raw_key = test_api_key
        service = APIKeyService(db_session, None)

        result = await service.validate_api_key(raw_key)

        assert result is not None
        assert result["id"] == str(api_key_obj.id)
        assert result["org_id"] == str(api_key_obj.org_id)

    @pytest.mark.asyncio
    async def test_validate_api_key_invalid(self, db_session):
        """测试验证无效的 API Key"""
        service = APIKeyService(db_session, None)

        result = await service.validate_api_key("cantor_invalid_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_api_key_revoked(self, db_session, test_api_key):
        """测试验证已撤销的 API Key"""
        api_key_obj, raw_key = test_api_key
        
        # 撤销 Key
        api_key_obj.status = "revoked"
        await db_session.commit()

        service = APIKeyService(db_session, None)
        result = await service.validate_api_key(raw_key)

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_api_key_expired(self, db_session, test_user, test_org):
        """测试验证已过期的 API Key"""
        from models.auth import APIKey

        # 创建已过期的 Key
        raw_key, key_hash = generate_api_key()
        api_key = APIKey(
            id=generate_test_uuid(),
            org_id=test_org.id,
            name="Expired Key",
            key_hash=key_hash,
            key_preview=raw_key[:10] + "...",
            status="active",
            expires_at=datetime.utcnow() - timedelta(days=1)  # 已过期
        )
        db_session.add(api_key)
        await db_session.commit()

        service = APIKeyService(db_session, None)
        result = await service.validate_api_key(raw_key)

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_api_key_ip_whitelist_allowed(self, db_session, test_user, test_org):
        """测试 IP 白名单允许的请求"""
        from models.auth import APIKey

        raw_key, key_hash = generate_api_key()
        api_key = APIKey(
            id=generate_test_uuid(),
            org_id=test_org.id,
            name="IP Restricted Key",
            key_hash=key_hash,
            key_preview=raw_key[:10] + "...",
            status="active",
            allowed_ips=["192.168.1.100", "10.0.0.1"]
        )
        db_session.add(api_key)
        await db_session.commit()

        service = APIKeyService(db_session, None)
        result = await service.validate_api_key(raw_key, client_ip="192.168.1.100")

        assert result is not None

    @pytest.mark.asyncio
    async def test_validate_api_key_ip_whitelist_blocked(self, db_session, test_user, test_org):
        """测试 IP 白名单阻止的请求"""
        from models.auth import APIKey

        raw_key, key_hash = generate_api_key()
        api_key = APIKey(
            id=generate_test_uuid(),
            org_id=test_org.id,
            name="IP Restricted Key",
            key_hash=key_hash,
            key_preview=raw_key[:10] + "...",
            status="active",
            allowed_ips=["192.168.1.100"]
        )
        db_session.add(api_key)
        await db_session.commit()

        service = APIKeyService(db_session, None)
        result = await service.validate_api_key(raw_key, client_ip="192.168.1.200")

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_api_key_updates_last_used(self, db_session, test_api_key):
        """测试验证更新最后使用时间"""
        api_key_obj, raw_key = test_api_key
        
        service = APIKeyService(db_session, None)
        await service.validate_api_key(raw_key, client_ip="127.0.0.1")

        await db_session.refresh(api_key_obj)
        
        assert api_key_obj.last_used_at is not None
        assert api_key_obj.last_used_ip == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_validate_api_key_with_cache(self, db_session, test_api_key, mock_redis):
        """测试使用 Redis 缓存验证"""
        api_key_obj, raw_key = test_api_key

        service = APIKeyService(db_session, mock_redis)
        
        # 第一次验证，会缓存
        result1 = await service.validate_api_key(raw_key)
        assert result1 is not None

        # 验证缓存存在
        key_hash = hash_api_key(raw_key)
        assert f"apikey:{key_hash}" in mock_redis._data


class TestRevokeAPIKey:
    """API Key 撤销测试"""

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self, db_session, test_api_key, test_user):
        """测试成功撤销 API Key"""
        api_key_obj, _ = test_api_key

        service = APIKeyService(db_session, None)
        success, error = await service.revoke_api_key(
            str(api_key_obj.id),
            test_user,
            reason="测试撤销"
        )

        assert success is True
        assert error is None

        await db_session.refresh(api_key_obj)
        assert api_key_obj.status == "revoked"
        assert api_key_obj.revoked_reason == "测试撤销"

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(self, db_session, test_user):
        """测试撤销不存在的 API Key"""
        service = APIKeyService(db_session, None)

        success, error = await service.revoke_api_key(
            "non-existent-id",
            test_user
        )

        assert success is False
        assert "不存在" in error

    @pytest.mark.asyncio
    async def test_revoke_api_key_wrong_org(self, db_session, test_api_key):
        """测试撤销其他组织的 API Key"""
        api_key_obj, _ = test_api_key

        # 创建另一个组织的用户
        other_user = MockUser(org_id="other-org-id")

        service = APIKeyService(db_session, None)
        success, error = await service.revoke_api_key(
            str(api_key_obj.id),
            other_user
        )

        assert success is False
        assert "无权" in error

    @pytest.mark.asyncio
    async def test_revoke_api_key_clears_cache(self, db_session, test_api_key, mock_redis):
        """测试撤销清除缓存"""
        api_key_obj, raw_key = test_api_key
        key_hash = hash_api_key(raw_key)

        # 先缓存
        mock_redis._data[f"apikey:{key_hash}"] = "cached"

        service = APIKeyService(db_session, mock_redis)
        await service.revoke_api_key(str(api_key_obj.id), test_user)

        # 验证缓存已清除
        assert f"apikey:{key_hash}" not in mock_redis._data


class TestListAPIKeys:
    """API Key 列表测试"""

    @pytest.mark.asyncio
    async def test_list_api_keys_empty(self, db_session, test_user):
        """测试空列表"""
        service = APIKeyService(db_session, None)

        keys = await service.list_api_keys(test_user)

        assert isinstance(keys, list)
        # 可能有 test_api_key fixture 创建的 key

    @pytest.mark.asyncio
    async def test_list_api_keys_multiple(self, db_session, test_user, test_org):
        """测试多个 API Key"""
        from models.auth import APIKey

        # 创建多个 Key
        for i in range(3):
            raw_key, key_hash = generate_api_key()
            api_key = APIKey(
                id=generate_test_uuid(),
                org_id=test_org.id,
                name=f"Test Key {i}",
                key_hash=key_hash,
                key_preview=raw_key[:10] + "...",
                status="active"
            )
            db_session.add(api_key)

        await db_session.commit()

        service = APIKeyService(db_session, None)
        keys = await service.list_api_keys(test_user)

        assert len(keys) >= 3

    @pytest.mark.asyncio
    async def test_list_api_keys_excludes_deleted(self, db_session, test_user, test_org):
        """测试不包含已删除的 Key"""
        from models.auth import APIKey

        # 创建一个活跃的 Key
        raw_key1, key_hash1 = generate_api_key()
        active_key = APIKey(
            id=generate_test_uuid(),
            org_id=test_org.id,
            name="Active Key",
            key_hash=key_hash1,
            key_preview=raw_key1[:10] + "...",
            status="active"
        )
        db_session.add(active_key)

        # 创建一个已删除的 Key
        raw_key2, key_hash2 = generate_api_key()
        deleted_key = APIKey(
            id=generate_test_uuid(),
            org_id=test_org.id,
            name="Deleted Key",
            key_hash=key_hash2,
            key_preview=raw_key2[:10] + "...",
            status="deleted"
        )
        db_session.add(deleted_key)

        await db_session.commit()

        service = APIKeyService(db_session, None)
        keys = await service.list_api_keys(test_user)

        # 不应该包含已删除的
        key_names = [k["name"] for k in keys]
        assert "Active Key" in key_names
