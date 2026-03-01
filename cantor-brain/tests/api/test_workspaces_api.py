"""
工作空间 API 集成测试
"""
import pytest
from httpx import AsyncClient

from tests.utils import generate_test_uuid


class TestListWorkspaces:
    """工作空间列表 API 测试"""

    @pytest.mark.asyncio
    async def test_list_workspaces_success(self, client: AsyncClient, test_user, test_workspace):
        """测试获取工作空间列表"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.get(
            "/workspaces",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "workspaces" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_workspaces_empty(self, client: AsyncClient, db_session, test_org):
        """测试无工作空间访问权限的用户"""
        from models.auth import User
        from services.auth import hash_password

        # 创建一个没有工作空间权限的用户
        user = User(
            id=generate_test_uuid(),
            org_id=test_org.id,
            email="no-ws@example.com",
            password_hash=hash_password("TestPassword123!"),
            name="No Workspace User",
            status="active"
        )
        db_session.add(user)
        await db_session.commit()

        login_response = await client.post("/auth/login", json={
            "email": "no-ws@example.com",
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.get(
            "/workspaces",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestCreateWorkspace:
    """创建工作空间 API 测试"""

    @pytest.mark.asyncio
    async def test_create_workspace_success(self, client: AsyncClient, test_admin_user, test_org):
        """测试成功创建工作空间"""
        login_response = await client.post("/auth/login", json={
            "email": test_admin_user.email,
            "password": "AdminPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.post(
            "/workspaces",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": "New Test Workspace",
                "description": "A test workspace"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Test Workspace"
        assert data["org_id"] == str(test_org.id)

    @pytest.mark.asyncio
    async def test_create_workspace_duplicate_name(self, client: AsyncClient, test_admin_user, test_workspace):
        """测试重复名称"""
        login_response = await client.post("/auth/login", json={
            "email": test_admin_user.email,
            "password": "AdminPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.post(
            "/workspaces",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": test_workspace.name,  # 使用已存在的名称
                "description": "Duplicate name"
            }
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_workspace_unauthorized(self, client: AsyncClient):
        """测试未授权创建"""
        response = await client.post(
            "/workspaces",
            json={"name": "Unauthorized WS"}
        )

        assert response.status_code == 401


class TestGetWorkspace:
    """获取工作空间 API 测试"""

    @pytest.mark.asyncio
    async def test_get_workspace_success(self, client: AsyncClient, test_user, test_workspace):
        """测试获取工作空间详情"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.get(
            f"/workspaces/{test_workspace.id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_workspace.id)
        assert data["name"] == test_workspace.name

    @pytest.mark.asyncio
    async def test_get_workspace_no_access(self, client: AsyncClient, test_user, db_session, test_org):
        """测试无权访问的工作空间"""
        from models.auth import Workspace

        # 创建一个用户没有权限的工作空间
        other_ws = Workspace(
            id=generate_test_uuid(),
            org_id=test_org.id,
            name="Other Workspace",
            status="active"
        )
        db_session.add(other_ws)
        await db_session.commit()

        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.get(
            f"/workspaces/{other_ws.id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_workspace_not_found(self, client: AsyncClient, test_user):
        """测试不存在的工作空间"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.get(
            f"/workspaces/{generate_test_uuid()}",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 404


class TestUpdateWorkspace:
    """更新工作空间 API 测试"""

    @pytest.mark.asyncio
    async def test_update_workspace_name(self, client: AsyncClient, test_admin_user, test_workspace):
        """测试更新工作空间名称"""
        login_response = await client.post("/auth/login", json={
            "email": test_admin_user.email,
            "password": "AdminPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.patch(
            f"/workspaces/{test_workspace.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "Updated Workspace Name"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Workspace Name"

    @pytest.mark.asyncio
    async def test_update_workspace_description(self, client: AsyncClient, test_admin_user, test_workspace):
        """测试更新工作空间描述"""
        login_response = await client.post("/auth/login", json={
            "email": test_admin_user.email,
            "password": "AdminPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.patch(
            f"/workspaces/{test_workspace.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"description": "Updated description"}
        )

        assert response.status_code == 200


class TestDeleteWorkspace:
    """删除工作空间 API 测试"""

    @pytest.mark.asyncio
    async def test_delete_workspace_success(self, client: AsyncClient, test_admin_user, db_session, test_org):
        """测试成功删除工作空间"""
        from models.auth import Workspace

        # 创建一个专门用于删除的工作空间
        ws_to_delete = Workspace(
            id=generate_test_uuid(),
            org_id=test_org.id,
            name="Workspace To Delete",
            status="active"
        )
        db_session.add(ws_to_delete)
        await db_session.commit()

        login_response = await client.post("/auth/login", json={
            "email": test_admin_user.email,
            "password": "AdminPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.delete(
            f"/workspaces/{ws_to_delete.id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 204


class TestWorkspaceMembers:
    """工作空间成员 API 测试"""

    @pytest.mark.asyncio
    async def test_list_members_success(self, client: AsyncClient, test_user, test_workspace):
        """测试获取工作空间成员"""
        login_response = await client.post("/auth/login", json={
            "email": test_user.email,
            "password": "TestPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.get(
            f"/workspaces/{test_workspace.id}/members",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_add_member_success(self, client: AsyncClient, test_admin_user, test_workspace, test_role, db_session, test_org):
        """测试添加工作空间成员"""
        from models.auth import User
        from services.auth import hash_password

        # 创建一个新用户
        new_user = User(
            id=generate_test_uuid(),
            org_id=test_org.id,
            email="new-member@example.com",
            password_hash=hash_password("TestPassword123!"),
            name="New Member",
            status="active"
        )
        db_session.add(new_user)
        await db_session.commit()

        login_response = await client.post("/auth/login", json={
            "email": test_admin_user.email,
            "password": "AdminPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.post(
            f"/workspaces/{test_workspace.id}/members",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "user_id": str(new_user.id),
                "role_id": str(test_role.id)
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(new_user.id)

    @pytest.mark.asyncio
    async def test_remove_member_success(self, client: AsyncClient, test_admin_user, test_workspace, test_user):
        """测试移除工作空间成员"""
        login_response = await client.post("/auth/login", json={
            "email": test_admin_user.email,
            "password": "AdminPassword123!"
        })
        access_token = login_response.json()["access_token"]

        response = await client.delete(
            f"/workspaces/{test_workspace.id}/members/{test_user.id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 204
