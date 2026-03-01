"""
认证服务
处理密码哈希、JWT 生成和验证
"""
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any, List
import jwt
from passlib.context import CryptContext
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.auth import User, Organization, Workspace, Role, UserWorkspaceRole

# 密码哈希上下文
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.PASSWORD_HASH_COST
)


class Permission:
    """权限匹配器"""

    def __init__(self, perm: str):
        self.perm = perm

    def match(self, required: str) -> bool:
        """
        检查权限是否匹配
        支持通配符: * 匹配所有
        例如:
        - "*" 匹配 "user:create"
        - "user:*" 匹配 "user:create", "user:delete"
        - "user:read" 只匹配 "user:read"
        """
        if self.perm == "*":
            return True

        parts = self.perm.split(":")
        required_parts = required.split(":")

        for i, part in enumerate(parts):
            if i >= len(required_parts):
                return True

            if part == "*":
                return True

            if part != required_parts[i]:
                return False

        return len(parts) == len(required_parts)


def check_permission(user_perms: List[str], required: str) -> bool:
    """检查用户是否拥有所需权限"""
    for perm in user_perms:
        if Permission(perm).match(required):
            return True
    return False


def hash_password(password: str) -> str:
    """哈希密码"""
    return pwd_context.hash(password)


def verify_password(password: str, hash: str) -> bool:
    """验证密码"""
    return pwd_context.verify(password, hash)


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    验证密码强度
    返回: (是否有效, 错误信息)
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"密码长度必须至少 {settings.PASSWORD_MIN_LENGTH} 个字符"

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_number = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)

    if not (has_upper and has_lower and has_number and has_special):
        return False, "密码必须包含大写字母、小写字母、数字和特殊字符"

    return True, ""


def generate_token_pair(user: User, workspaces: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    生成 JWT Token 对 (access_token, refresh_token)

    Args:
        user: 用户对象
        workspaces: 用户的工作空间和权限列表

    Returns:
        (access_token, refresh_token)
    """
    now = datetime.now(timezone.utc)

    # 收集所有权限
    all_permissions = set()
    for ws in workspaces:
        all_permissions.update(ws.get("permissions", []))

    # Access Token
    access_jti = secrets.token_urlsafe(16)
    access_claims = {
        "sub": str(user.id),
        "email": user.email,
        "org": {
            "id": str(user.org_id),
            "name": user.organization.name if user.organization else None,
        },
        "workspaces": workspaces,
        "permissions": list(all_permissions),
        "jti": access_jti,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access"
    }
    access_token = jwt.encode(
        access_claims,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    # Refresh Token
    refresh_jti = secrets.token_urlsafe(16)
    refresh_claims = {
        "sub": str(user.id),
        "jti": refresh_jti,
        "token_version": user.token_version,
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh"
    }
    refresh_token = jwt.encode(
        refresh_claims,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return access_token, refresh_token


def validate_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    验证 Access Token

    Args:
        token: JWT token 字符串

    Returns:
        解码后的 claims，无效时返回 None
    """
    try:
        claims = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        if claims.get("type") != "access":
            return None

        return claims
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def validate_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    验证 Refresh Token

    Args:
        token: JWT refresh token 字符串

    Returns:
        解码后的 claims，无效时返回 None
    """
    try:
        claims = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        if claims.get("type") != "refresh":
            return None

        return claims
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_user_workspaces(db: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
    """
    获取用户的工作空间和权限

    Returns:
        [
            {
                "id": "workspace-uuid",
                "name": "Production",
                "role": "operator",
                "permissions": ["cantor:*", "device:control", ...]
            },
            ...
        ]
    """
    result = await db.execute(
        select(UserWorkspaceRole, Workspace, Role)
        .join(Workspace, UserWorkspaceRole.workspace_id == Workspace.id)
        .join(Role, UserWorkspaceRole.role_id == Role.id)
        .where(
            and_(
                UserWorkspaceRole.user_id == user_id,
                Workspace.status == "active",
                Workspace.deleted_at.is_(None)
            )
        )
    )

    workspaces = []
    for uwr, ws, role in result.all():
        workspaces.append({
            "id": str(ws.id),
            "name": ws.name,
            "role": role.name,
            "permissions": role.permissions or []
        })

    return workspaces


async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
    redis_client
) -> Optional[Tuple[str, str]]:
    """
    使用 Refresh Token 刷新 Access Token

    Args:
        db: 数据库会话
        refresh_token: refresh token 字符串
        redis_client: Redis 客户端（用于检查黑名单）

    Returns:
        (new_access_token, new_refresh_token) 或 None
    """
    # 验证 token
    claims = validate_refresh_token(refresh_token)
    if not claims:
        return None

    # 检查黑名单
    jti = claims.get("jti")
    if redis_client:
        blacklisted = await redis_client.get(f"jwt:blacklist:{jti}")
        if blacklisted:
            return None

    # 获取用户
    user_id = claims.get("sub")
    token_version = claims.get("token_version")

    result = await db.execute(
        select(User)
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user or user.status != "active":
        return None

    # 检查 token version
    if user.token_version != token_version:
        return None

    # 获取工作空间
    workspaces = await get_user_workspaces(db, str(user.id))

    # 生成新 token 对
    new_access, new_refresh = generate_token_pair(user, workspaces)

    # 将旧的 refresh token 加入黑名单
    if redis_client:
        exp = claims.get("exp", 0)
        ttl = max(exp - datetime.now(timezone.utc).timestamp(), 60)
        await redis_client.setex(f"jwt:blacklist:{jti}", int(ttl), "revoked")

    return new_access, new_refresh


async def revoke_all_tokens(db: AsyncSession, user_id: str) -> bool:
    """
    撤销用户所有 token（通过递增 token_version）

    Args:
        db: 数据库会话
        user_id: 用户 ID

    Returns:
        是否成功
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return False

    user.token_version += 1
    await db.commit()

    return True


class AuthService:
    """认证服务类"""

    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client

    async def register_user(
        self,
        email: str,
        password: str,
        name: str,
        org_name: str,
        org_slug: str
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        注册新用户（同时创建组织）

        Returns:
            (user, error_message)
        """
        # 验证密码强度
        valid, msg = validate_password_strength(password)
        if not valid:
            return None, msg

        # 检查 slug 是否已存在
        result = await self.db.execute(
            select(Organization).where(Organization.slug == org_slug)
        )
        if result.scalar_one_or_none():
            return None, "组织标识已存在"

        # 创建组织
        from models.auth import DEFAULT_ORG_QUOTAS, DEFAULT_ORG_SETTINGS
        org = Organization(
            name=org_name,
            slug=org_slug,
            tier="b2b",
            quotas=DEFAULT_ORG_QUOTAS,
            settings=DEFAULT_ORG_SETTINGS
        )
        self.db.add(org)
        await self.db.flush()

        # 检查邮箱是否已存在
        result = await self.db.execute(
            select(User).where(
                and_(User.org_id == org.id, User.email == email)
            )
        )
        if result.scalar_one_or_none():
            return None, "邮箱已存在"

        # 创建用户
        user = User(
            org_id=org.id,
            email=email,
            password_hash=hash_password(password),
            name=name,
            status="active",
            email_verified_at=datetime.now(timezone.utc)  # 注册时默认验证
        )
        self.db.add(user)
        await self.db.flush()

        # 创建默认工作空间
        from models.auth import DEFAULT_WORKSPACE_QUOTAS, DEFAULT_WORKSPACE_SETTINGS
        workspace = Workspace(
            org_id=org.id,
            name="默认工作空间",
            quotas=DEFAULT_WORKSPACE_QUOTAS,
            settings=DEFAULT_WORKSPACE_SETTINGS
        )
        self.db.add(workspace)
        await self.db.flush()

        # 分配 Owner 角色
        result = await self.db.execute(
            select(Role).where(
                and_(Role.org_id.is_(None), Role.name == "Owner")
            )
        )
        owner_role = result.scalar_one_or_none()

        if owner_role:
            uwr = UserWorkspaceRole(
                user_id=user.id,
                workspace_id=workspace.id,
                role_id=owner_role.id
            )
            self.db.add(uwr)

        await self.db.commit()
        await self.db.refresh(user)

        return user, None

    async def login(
        self,
        email: str,
        password: str,
        org_slug: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        用户登录

        Args:
            email: 邮箱
            password: 密码
            org_slug: 组织 slug（可选，用于多组织场景）

        Returns:
            (token_data, error_message)
        """
        # 查询用户
        query = select(User).where(User.email == email)

        if org_slug:
            query = query.join(Organization).where(Organization.slug == org_slug)

        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return None, "邮箱或密码错误"

        # 检查账户状态
        if user.status != "active":
            return None, "账户已被禁用"

        # 检查锁定
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            return None, f"账户已锁定，请 {user.locked_until} 后重试"

        # 验证密码
        if not verify_password(password, user.password_hash):
            # 增加失败次数
            user.failed_login_attempts += 1

            # 检查是否需要锁定
            if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.LOCKOUT_DURATION_MINUTES
                )
                await self.db.commit()
                return None, f"登录失败次数过多，账户已锁定 {settings.LOCKOUT_DURATION_MINUTES} 分钟"

            await self.db.commit()
            return None, "邮箱或密码错误"

        # 登录成功，重置失败次数
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()

        # 加载组织
        result = await self.db.execute(
            select(Organization).where(Organization.id == user.org_id)
        )
        user.organization = result.scalar_one_or_none()

        # 获取工作空间
        workspaces = await get_user_workspaces(self.db, str(user.id))

        # 生成 token
        access_token, refresh_token = generate_token_pair(user, workspaces)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "org_id": str(user.org_id),
                "org_name": user.organization.name if user.organization else None
            }
        }, None

    async def get_current_user(self, user_id: str) -> Optional[User]:
        """获取当前用户"""
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user:
            # 加载组织
            result = await self.db.execute(
                select(Organization).where(Organization.id == user.org_id)
            )
            user.organization = result.scalar_one_or_none()

        return user

    async def logout(self, jti: str, exp: int) -> bool:
        """
        登出（将 token 加入黑名单）

        Args:
            jti: token ID
            exp: token 过期时间戳
        """
        if self.redis:
            ttl = max(exp - datetime.now(timezone.utc).timestamp(), 60)
            await self.redis.setex(f"jwt:blacklist:{jti}", int(ttl), "logout")

        return True
