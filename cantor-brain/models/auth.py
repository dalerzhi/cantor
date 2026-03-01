"""
认证相关数据库模型
多租户架构：Organization → Workspace → User/Role/APIKey
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List


def utcnow():
    """返回 UTC 时间（Python 3.12+ 兼容）"""
    return datetime.now(timezone.utc)
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Text, Integer,
    ARRAY, JSON, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import relationship
from models.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Organization(Base):
    """组织/租户表"""
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    tier = Column(String(20), nullable=False, default="b2b")  # b2b/b2c
    status = Column(String(20), nullable=False, default="active", index=True)  # active/suspended/deleted

    # 资源配额
    quotas = Column(JSONB, default=dict)

    # 组织级设置
    settings = Column(JSONB, default=dict)

    # 审计字段
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # 关系
    workspaces = relationship("Workspace", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="organization", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="organization", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_organizations_slug', 'slug'),
        Index('idx_organizations_status', 'status'),
    )


class Workspace(Base):
    """工作空间表"""
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # 工作空间级配额
    quotas = Column(JSONB, default=dict)

    # 工作空间设置
    settings = Column(JSONB, default=dict)

    status = Column(String(20), default="active", index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # 关系
    organization = relationship("Organization", back_populates="workspaces")
    user_workspace_roles = relationship("UserWorkspaceRole", back_populates="workspace", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="workspace", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('org_id', 'name', name='uq_workspace_org_name'),
        Index('idx_workspaces_org_id', 'org_id'),
        Index('idx_workspaces_status', 'status'),
    )


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    # 登录凭证
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=True)

    # 基本信息
    name = Column(String(100), nullable=True)
    avatar_url = Column(Text, nullable=True)
    timezone = Column(String(50), default="Asia/Shanghai")
    locale = Column(String(10), default="zh-CN")

    # 状态管理
    status = Column(String(20), default="active", index=True)  # active/inactive/invited/suspended
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    phone_verified_at = Column(DateTime(timezone=True), nullable=True)

    # 多因素认证
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)  # TOTP secret (encrypted)
    mfa_backup_codes = Column(ARRAY(Text), nullable=True)  # 一次性备用码

    # 安全相关
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), default=utcnow)

    # Token 版本（用于全局吊销）
    token_version = Column(Integer, default=1)

    # 审计字段
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # 关系
    organization = relationship("Organization", back_populates="users")
    user_workspace_roles = relationship("UserWorkspaceRole", back_populates="user", foreign_keys="[UserWorkspaceRole.user_id]", cascade="all, delete-orphan")
    created_api_keys = relationship("APIKey", back_populates="creator")

    __table_args__ = (
        UniqueConstraint('org_id', 'email', name='uq_user_org_email'),
        Index('idx_users_org_id', 'org_id'),
        Index('idx_users_email', 'email'),
        Index('idx_users_status', 'status'),
    )


class Role(Base):
    """角色定义表"""
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)  # NULL = 系统预设

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # 权限列表
    permissions = Column(ARRAY(String), nullable=False, default=list)

    # 数据范围
    workspace_scope = Column(String(20), default="specific")  # all/specific/none

    is_system = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # 关系
    organization = relationship("Organization", back_populates="roles")
    user_workspace_roles = relationship("UserWorkspaceRole", back_populates="role", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('org_id', 'name', name='uq_role_org_name'),
    )


class UserWorkspaceRole(Base):
    """用户-工作空间-角色关联表"""
    __tablename__ = "user_workspace_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)

    # 授权信息
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime(timezone=True), default=utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow)

    # 关系
    user = relationship("User", back_populates="user_workspace_roles", foreign_keys=[user_id])
    workspace = relationship("Workspace", back_populates="user_workspace_roles")
    role = relationship("Role", back_populates="user_workspace_roles")
    granted_by_user = relationship("User", foreign_keys=[granted_by])

    __table_args__ = (
        UniqueConstraint('user_id', 'workspace_id', 'role_id', name='uq_user_workspace_role'),
        Index('idx_user_workspace_roles_user_id', 'user_id'),
        Index('idx_user_workspace_roles_workspace_id', 'workspace_id'),
        Index('idx_user_workspace_roles_role_id', 'role_id'),
    )


class APIKey(Base):
    """API Key 表"""
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)  # NULL = 组织级 Key

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Key 存储（只存 hash）
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_preview = Column(String(20), nullable=True)  # 前几位用于展示

    # 权限限制
    permissions = Column(ARRAY(String), nullable=True)

    # 使用限制
    allowed_ips = Column(ARRAY(String), nullable=True)  # IP 白名单
    rate_limit = Column(Integer, default=1000)  # 每分钟请求数

    # 生命周期
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_used_ip = Column(String(45), nullable=True)

    # 状态
    status = Column(String(20), default="active", index=True)  # active/revoked/expired
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(Text, nullable=True)

    # 审计
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # 关系
    organization = relationship("Organization", back_populates="api_keys")
    workspace = relationship("Workspace", back_populates="api_keys")
    creator = relationship("User", back_populates="created_api_keys")

    __table_args__ = (
        Index('idx_api_keys_org_id', 'org_id'),
        Index('idx_api_keys_workspace_id', 'workspace_id'),
        Index('idx_api_keys_key_hash', 'key_hash'),
        Index('idx_api_keys_status', 'status'),
    )


# 默认配额模板
DEFAULT_ORG_QUOTAS = {
    "max_workspaces": 10,
    "max_devices": 500,
    "max_users": 50,
    "max_api_keys": 100,
    "max_concurrent_tasks": 1000
}

DEFAULT_WORKSPACE_QUOTAS = {
    "max_devices": 100,
    "max_cantor_instances": 10,
    "max_concurrent_tasks": 100
}

DEFAULT_ORG_SETTINGS = {
    "mfa_required": False,
    "sso_enabled": False,
    "session_timeout_minutes": 480
}

DEFAULT_WORKSPACE_SETTINGS = {
    "default_device_timeout": 300,
    "auto_cleanup_tasks": True
}

# 系统预设角色
SYSTEM_ROLES = [
    {
        "id": str(uuid.UUID("00000000-0000-0000-0000-000000000001")),
        "name": "Owner",
        "description": "组织所有者，拥有所有权限",
        "permissions": ["*"],
        "is_system": True,
        "is_default": False
    },
    {
        "id": str(uuid.UUID("00000000-0000-0000-0000-000000000002")),
        "name": "Admin",
        "description": "管理员，可管理成员和 Workspace",
        "permissions": [
            "org:read", "org:update", "user:*", "workspace:*",
            "cantor:*", "device:*", "task:*", "script:*", "api_key:*"
        ],
        "is_system": True,
        "is_default": False
    },
    {
        "id": str(uuid.UUID("00000000-0000-0000-0000-000000000003")),
        "name": "Operator",
        "description": "操作员，可管理任务和设备",
        "permissions": [
            "org:read", "user:read:self", "workspace:read",
            "cantor:*", "device:control", "device:read",
            "task:execute", "task:read", "script:read", "script:execute"
        ],
        "is_system": True,
        "is_default": True
    },
    {
        "id": str(uuid.UUID("00000000-0000-0000-0000-000000000004")),
        "name": "Viewer",
        "description": "观察者，只读访问",
        "permissions": [
            "org:read", "user:read:self", "workspace:read",
            "cantor:read", "device:read", "task:read", "script:read"
        ],
        "is_system": True,
        "is_default": False
    }
]
