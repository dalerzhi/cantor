"""Initial auth schema

Revision ID: 001
Create Date: 2024-01-01

创建认证系统所需的全部表：
- organizations (组织/租户)
- workspaces (工作空间)
- users (用户)
- roles (角色)
- user_workspace_roles (用户-工作空间-角色关联)
- api_keys (API Key)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 organizations 表
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('tier', sa.String(20), nullable=False, server_default='b2b'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('quotas', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('settings', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_organizations_slug', 'organizations', ['slug'])
    op.create_index('idx_organizations_status', 'organizations', ['status'])

    # 创建 workspaces 表
    op.create_table(
        'workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('quotas', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('settings', postgresql.JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('org_id', 'name', name='uq_workspace_org_name'),
    )
    op.create_index('idx_workspaces_org_id', 'workspaces', ['org_id'])
    op.create_index('idx_workspaces_status', 'workspaces', ['status'])

    # 创建 users 表
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('avatar_url', sa.Text, nullable=True),
        sa.Column('timezone', sa.String(50), server_default='Asia/Shanghai'),
        sa.Column('locale', sa.String(10), server_default='zh-CN'),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('phone_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('mfa_enabled', sa.Boolean, server_default='false'),
        sa.Column('mfa_secret', sa.String(255), nullable=True),
        sa.Column('mfa_backup_codes', sa.ARRAY(sa.Text), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_ip', sa.String(45), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer, server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('token_version', sa.Integer, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.UniqueConstraint('org_id', 'email', name='uq_user_org_email'),
    )
    op.create_index('idx_users_org_id', 'users', ['org_id'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_status', 'users', ['status'])

    # 创建 roles 表
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('permissions', sa.ARRAY(sa.String), nullable=False, server_default='{}'),
        sa.Column('workspace_scope', sa.String(20), server_default='specific'),
        sa.Column('is_system', sa.Boolean, server_default='false'),
        sa.Column('is_default', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('org_id', 'name', name='uq_role_org_name'),
    )

    # 创建 user_workspace_roles 表
    op.create_table(
        'user_workspace_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('user_id', 'workspace_id', 'role_id', name='uq_user_workspace_role'),
    )
    op.create_index('idx_user_workspace_roles_user_id', 'user_workspace_roles', ['user_id'])
    op.create_index('idx_user_workspace_roles_workspace_id', 'user_workspace_roles', ['workspace_id'])
    op.create_index('idx_user_workspace_roles_role_id', 'user_workspace_roles', ['role_id'])

    # 创建 api_keys 表
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('key_hash', sa.String(255), unique=True, nullable=False),
        sa.Column('key_preview', sa.String(20), nullable=True),
        sa.Column('permissions', sa.ARRAY(sa.String), nullable=True),
        sa.Column('allowed_ips', sa.ARRAY(sa.String), nullable=True),
        sa.Column('rate_limit', sa.Integer, server_default='1000'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_ip', sa.String(45), nullable=True),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_reason', sa.Text, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_api_keys_org_id', 'api_keys', ['org_id'])
    op.create_index('idx_api_keys_workspace_id', 'api_keys', ['workspace_id'])
    op.create_index('idx_api_keys_key_hash', 'api_keys', ['key_hash'])
    op.create_index('idx_api_keys_status', 'api_keys', ['status'])

    # 插入系统预设角色
    op.execute("""
        INSERT INTO roles (id, org_id, name, description, permissions, is_system, is_default) VALUES
        ('00000000-0000-0000-0000-000000000001', NULL, 'Owner', '组织所有者，拥有所有权限', ARRAY['*'], TRUE, FALSE),
        ('00000000-0000-0000-0000-000000000002', NULL, 'Admin', '管理员，可管理成员和 Workspace', ARRAY['org:read', 'org:update', 'user:*', 'workspace:*', 'cantor:*', 'device:*', 'task:*', 'script:*', 'api_key:*'], TRUE, FALSE),
        ('00000000-0000-0000-0000-000000000003', NULL, 'Operator', '操作员，可管理任务和设备', ARRAY['org:read', 'user:read:self', 'workspace:read', 'cantor:*', 'device:control', 'device:read', 'task:execute', 'task:read', 'script:read', 'script:execute'], TRUE, TRUE),
        ('00000000-0000-0000-0000-000000000004', NULL, 'Viewer', '观察者，只读访问', ARRAY['org:read', 'user:read:self', 'workspace:read', 'cantor:read', 'device:read', 'task:read', 'script:read'], TRUE, FALSE)
    """)


def downgrade() -> None:
    # 按相反顺序删除表
    op.drop_table('api_keys')
    op.drop_table('user_workspace_roles')
    op.drop_table('roles')
    op.drop_table('users')
    op.drop_table('workspaces')
    op.drop_table('organizations')
