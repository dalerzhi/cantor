"""
组织 API 集成测试
"""
import pytest
from httpx import AsyncClient

from tests.utils import generate_test_uuid


class TestListOrganizations:
    """组织列表 API 测试"""

    @pytest.mark.asyncio
    async def test_list_organizations_success(self, client: AsyncClient, test_user):
        """测试获取组织列表"""
        # 登录
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.get(
            "/orgs",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "organizations" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_organizations_unauthorized(self, client: AsyncClient):
        """测试未授权访问"""
        response = await client.get("/orgs")

        assert response.status_code == 401


class TestCreateOrganization:
    """创建组织 API 测试"""

    @pytest.mark.asyncio
    async def test_create_organization_success(self, client: AsyncClient, test_user):
        """测试成功创建组织"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.post(
            "/orgs",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": "New Test Org",
                "slug": "new-test-org-unique",
                "tier": "b2b"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Test Org"
        assert data["slug"] == "new-test-org-unique"

    @pytest.mark.asyncio
    async def test_create_organization_duplicate_slug(self, client: AsyncClient, test_user, test_org):
        """测试重复 slug"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.post(
            "/orgs",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": "Another Org",
                "slug": test_org.slug,  # 使用已存在的 slug
                "tier": "b2b"
            }
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_organization_invalid_tier(self, client: AsyncClient, test_user):
        """测试无效的 tier"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.post(
            "/orgs",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": "Invalid Tier Org",
                "slug": "invalid-tier-org",
                "tier": "invalid"
            }
        )

        assert response.status_code == 422


class TestGetCurrentOrganization:
    """获取当前组织 API 测试"""

    @pytest.mark.asyncio
    async def test_get_current_org_success(self, client: AsyncClient, test_user, test_org):
        """测试获取当前组织"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.get(
            "/orgs/current",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_org.id)
        assert data["name"] == test_org.name


class TestUpdateOrganization:
    """更新组织 API 测试"""

    @pytest.mark.asyncio
    async def test_update_organization_name(self, client: AsyncClient, test_admin_user, test_org):
        """测试更新组织名称"""
        login_response = await client.post("/auth/login", json={
            "email": test_admin_user.email,
            "password": "AdminPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.patch(
            f"/orgs/{test_org.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "Updated Org Name"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Org Name"

    @pytest.mark.asyncio
    async def test_update_organization_settings(self, client: AsyncClient, test_admin_user, test_org):
        """测试更新组织设置"""
        login_response = await client.post("/auth/login", json={
            "email": test_admin_user.email,
            "password": "AdminPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.patch(
            f"/orgs/{test_org.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"settings": {"mfa_required": True}}
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_other_organization_forbidden(self, client: AsyncClient, test_admin_user):
        """测试更新其他组织（应该被拒绝）"""
        login_response = await client.post("/auth/login", json={
            "email": test_admin_user.email,
            "password": "AdminPassword123!"
        })
        access_token = login_response.json()["access_token"]

        other_org_id = generate_test_uuid()

        response = await client.patch(
            f"/orgs/{other_org_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "Other Org"}
        )

        assert response.status_code == 403


class TestListOrganizationMembers:
    """组织成员列表 API 测试"""

    @pytest.mark.asyncio
    async def test_list_members_success(self, client: AsyncClient, test_admin_user, test_org):
        """测试获取成员列表"""
        login_response = await client.post("/auth/login", json={
            "email": test_admin_user.email,
            "password": "AdminPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.get(
            f"/orgs/{test_org.id}/members",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_members_other_org_forbidden(self, client: AsyncClient, test_user):
        """测试获取其他组织成员（无权限）"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        other_org_id = generate_test_uuid()

        response = await client.get(
            f"/orgs/{other_org_id}/members",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 403
