"""
Pytest 配置和 fixtures
"""
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from core.config import settings
from models.base import Base
from models.auth import User, Organization, Workspace, Role, UserWorkspaceRole, APIKey
from services.auth import hash_password
from tests.utils import MockRedis, generate_test_uuid

# 导入 API 路由
from api.auth import router as auth_router
from api.organizations import router as orgs_router
from api.workspaces import router as workspaces_router


# 测试数据库 URL (使用内存 SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def create_test_app() -> FastAPI:
    """创建测试用的 FastAPI 应用"""
    app = FastAPI()
    app.include_router(auth_router, prefix="/auth", tags=["认证"])
    app.include_router(orgs_router, prefix="/orgs", tags=["组织管理"])
    app.include_router(workspaces_router, prefix="/workspaces", tags=["工作空间管理"])
    return app


# 创建测试应用实例
app = create_test_app()


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_engine():
    """创建测试数据库引擎"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端"""
    from core.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_redis() -> MockRedis:
    """模拟 Redis 客户端"""
    return MockRedis()


@pytest.fixture
async def test_org(db_session: AsyncSession) -> Organization:
    """创建测试组织"""
    org = Organization(
        id=generate_test_uuid(),
        name="Test Organization",
        slug="test-org",
        tier="b2b",
        status="active",
        quotas={"max_users": 50},
        settings={}
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def test_workspace(db_session: AsyncSession, test_org: Organization) -> Workspace:
    """创建测试工作空间"""
    workspace = Workspace(
        id=generate_test_uuid(),
        org_id=test_org.id,
        name="Test Workspace",
        status="active",
        quotas={},
        settings={}
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)
    return workspace


@pytest.fixture
async def test_role(db_session: AsyncSession) -> Role:
    """创建测试角色（系统角色）"""
    role = Role(
        id=generate_test_uuid(),
        org_id=None,  # 系统角色
        name="Operator",
        description="测试操作员角色",
        permissions=["cantor:*", "device:control", "task:execute"],
        is_system=True,
        is_default=True
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest.fixture
async def test_user(
    db_session: AsyncSession,
    test_org: Organization,
    test_workspace: Workspace,
    test_role: Role
) -> User:
    """创建测试用户"""
    user = User(
        id=generate_test_uuid(),
        org_id=test_org.id,
        email="test@example.com",
        password_hash=hash_password("TestPassword123!"),
        name="Test User",
        status="active",
        email_verified_at=None,
        token_version=1
    )
    db_session.add(user)
    await db_session.flush()

    # 添加用户-工作空间-角色关联
    uwr = UserWorkspaceRole(
        id=generate_test_uuid(),
        user_id=user.id,
        workspace_id=test_workspace.id,
        role_id=test_role.id
    )
    db_session.add(uwr)
    await db_session.commit()

    # 刷新并设置关联
    await db_session.refresh(user)
    user.organization = test_org

    return user


@pytest.fixture
async def test_admin_role(db_session: AsyncSession) -> Role:
    """创建管理员角色"""
    role = Role(
        id=generate_test_uuid(),
        org_id=None,
        name="Admin",
        description="管理员角色",
        permissions=["*"],
        is_system=True,
        is_default=False
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest.fixture
async def test_admin_user(
    db_session: AsyncSession,
    test_org: Organization,
    test_workspace: Workspace,
    test_admin_role: Role
) -> User:
    """创建测试管理员用户"""
    user = User(
        id=generate_test_uuid(),
        org_id=test_org.id,
        email="admin@example.com",
        password_hash=hash_password("AdminPassword123!"),
        name="Admin User",
        status="active",
        email_verified_at=None,
        token_version=1
    )
    db_session.add(user)
    await db_session.flush()

    uwr = UserWorkspaceRole(
        id=generate_test_uuid(),
        user_id=user.id,
        workspace_id=test_workspace.id,
        role_id=test_admin_role.id
    )
    db_session.add(uwr)
    await db_session.commit()

    await db_session.refresh(user)
    user.organization = test_org

    return user


@pytest.fixture
async def test_api_key(
    db_session: AsyncSession,
    test_user: User,
    test_org: Organization
) -> tuple:
    """创建测试 API Key，返回 (APIKey 对象, 原始 key)"""
    import hashlib
    import secrets

    raw_key = "cantor_test_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = APIKey(
        id=generate_test_uuid(),
        org_id=test_org.id,
        workspace_id=None,
        name="Test API Key",
        description="测试用 API Key",
        key_hash=key_hash,
        key_preview=raw_key[:10] + "...",
        permissions=["cantor:read", "device:read"],
        status="active",
        created_by=test_user.id
    )
    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)

    return api_key, raw_key


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """创建认证请求头（需要配合实际 token 生成）"""
    # 这个 fixture 需要在测试中配合 generate_token_pair 使用
    return {}


@pytest.fixture
def mock_request():
    """模拟 FastAPI Request 对象"""
    request = MagicMock()
    request.app.state.redis = None
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {}
    request.path_params = {}
    request.query_params = {}
    return request
