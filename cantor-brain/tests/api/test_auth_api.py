"""
认证 API 集成测试
测试注册、登录、刷新、登出、获取当前用户
"""
import pytest
from httpx import AsyncClient
from datetime import datetime

from services.auth import generate_token_pair, hash_password
from tests.utils import generate_test_uuid


class TestRegister:
    """注册 API 测试"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """测试成功注册"""
        response = await client.post("/auth/register", json={
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
            "name": "New User",
            "org_name": "New Organization",
            "org_slug": "new-org-test"
        })

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """测试弱密码注册"""
        response = await client.post("/auth/register", json={
            "email": "weak@example.com",
            "password": "weak",
            "name": "Weak User",
            "org_name": "Weak Org",
            "org_slug": "weak-org-test"
        })

        assert response.status_code == 400
        assert "密码" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_duplicate_org_slug(self, client: AsyncClient, test_org):
        """测试重复组织 slug"""
        response = await client.post("/auth/register", json={
            "email": "another@example.com",
            "password": "StrongPassword123!",
            "name": "Another User",
            "org_name": "Another Org",
            "org_slug": test_org.slug  # 使用已存在的 slug
        })

        assert response.status_code == 400
        assert "已存在" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """测试无效邮箱格式"""
        response = await client.post("/auth/register", json={
            "email": "invalid-email",
            "password": "StrongPassword123!",
            "name": "Invalid User",
            "org_name": "Invalid Org",
            "org_slug": "invalid-org"
        })

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_invalid_org_slug(self, client: AsyncClient):
        """测试无效组织 slug（包含特殊字符）"""
        response = await client.post("/auth/register", json={
            "email": "invalid-slug@example.com",
            "password": "StrongPassword123!",
            "name": "Invalid Slug User",
            "org_name": "Invalid Slug Org",
            "org_slug": "Invalid_Slug!"  # 应该只允许小写字母、数字和连字符
        })

        assert response.status_code == 422


class TestLogin:
    """登录 API 测试"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """测试成功登录"""
        response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """测试错误密码登录"""
        response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "WrongPassword123!"
        })

        assert response.status_code == 401
        assert "错误" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """测试不存在的用户登录"""
        response = await client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "SomePassword123!"
        })

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, db_session, test_org, test_workspace, test_role):
        """测试已禁用用户登录"""
        from models.auth import User, UserWorkspaceRole

        # 创建已禁用用户
        user = User(
            id=generate_test_uuid(),
            org_id=test_org.id,
            email="inactive@example.com",
            password_hash=hash_password("TestPassword123!"),
            name="Inactive User",
            status="inactive"
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post("/auth/login", json={
            "email": "inactive@example.com",
            "password": "TestPassword123!"
        })

        assert response.status_code == 401
        assert "禁用" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_with_org_slug(self, client: AsyncClient, test_user, test_org):
        """测试带组织 slug 登录"""
        response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!",
            "org_slug": test_org.slug
        })

        assert response.status_code == 200


class TestRefresh:
    """Token 刷新 API 测试"""

    @pytest.mark.asyncio
    async def test_refresh_success(self, client: AsyncClient, test_user):
        """测试成功刷新 token"""
        # 先登录获取 refresh token
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        refresh_token = login_response.json()["refresh_token"]

        # 刷新 token
        response = await client.post("/auth/refresh", json={
            "refresh_token": refresh_token
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # 新 token 应该和旧的不同
        assert data["refresh_token"] != refresh_token

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient):
        """测试无效 refresh token"""
        response = await client.post("/auth/refresh", json={
            "refresh_token": "invalid-refresh-token"
        })

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_access_token_instead(self, client: AsyncClient, test_user):
        """测试使用 access token 刷新（应该失败）"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.post("/auth/refresh", json={
            "refresh_token": access_token
        })

        assert response.status_code == 401


class TestLogout:
    """登出 API 测试"""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, test_user):
        """测试成功登出"""
        # 先登录
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        # 登出
        response = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        assert "成功" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_logout_without_token(self, client: AsyncClient):
        """测试无 token 登出"""
        response = await client.post("/auth/logout")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_all_devices(self, client: AsyncClient, test_user):
        """测试登出所有设备"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.post(
            "/auth/logout-all",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200


class TestMe:
    """获取当前用户 API 测试"""

    @pytest.mark.asyncio
    async def test_me_success(self, client: AsyncClient, test_user):
        """测试成功获取当前用户"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name

    @pytest.mark.asyncio
    async def test_me_without_token(self, client: AsyncClient):
        """测试无 token 获取用户信息"""
        response = await client.get("/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_invalid_token(self, client: AsyncClient):
        """测试无效 token"""
        response = await client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_expired_token(self, client: AsyncClient):
        """测试过期 token"""
        # 使用一个明显无效的 token
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid"
        
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401


class TestChangePassword:
    """修改密码 API 测试"""

    @pytest.mark.asyncio
    async def test_change_password_success(self, client: AsyncClient, test_user):
        """测试成功修改密码"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.put(
            "/auth/me/password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "TestPassword123!",
                "new_password": "NewStrongPassword456!"
            }
        )

        assert response.status_code == 200
        assert "成功" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, client: AsyncClient, test_user):
        """测试当前密码错误"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.put(
            "/auth/me/password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "WrongCurrentPassword!",
                "new_password": "NewStrongPassword456!"
            }
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_change_password_weak_new(self, client: AsyncClient, test_user):
        """测试新密码太弱"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.put(
            "/auth/me/password",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "current_password": "TestPassword123!",
                "new_password": "weak"
            }
        )

        assert response.status_code == 400
