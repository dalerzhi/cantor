# Cantor - 用户认证与权限系统设计文档

## 1. 设计目标与原则

### 1.1 核心目标
- 支持 B2B/B2C 两种商业模式的多租户架构
- 实现细粒度的 RBAC 权限控制
- 区分人机认证（JWT）与机机认证（API Key）
- 保证租户数据严格隔离

### 1.2 设计原则
- **最小权限原则**：API Key 权限范围 ≤ 创建者权限
- **深度防御**：API Gateway 校验 + 服务层校验 + 数据库 RLS
- **可审计**：所有认证事件记录审计日志
- **可撤销**：JWT 支持黑名单吊销，API Key 支持即时禁用

---

## 2. 数据库表设计（PostgreSQL）

### 2.1 租户与组织表

```sql
-- 组织/租户表
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL, -- URL 标识，如 "acme-corp"
    tier VARCHAR(20) NOT NULL DEFAULT 'b2b', -- b2b/b2c
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- active/suspended/deleted
    
    -- 资源配额（JSONB 灵活扩展）
    quotas JSONB DEFAULT '{
        "max_workspaces": 10,
        "max_devices": 500,
        "max_users": 50,
        "max_api_keys": 100,
        "max_concurrent_tasks": 1000
    }'::jsonb,
    
    -- 组织级设置
    settings JSONB DEFAULT '{
        "mfa_required": false,
        "sso_enabled": false,
        "session_timeout_minutes": 480
    }'::jsonb,
    
    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- 软删除
);

-- 索引
CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_tier ON organizations(tier);
CREATE INDEX idx_organizations_status ON organizations(status);

COMMENT ON TABLE organizations IS '组织/租户表，多租户隔离的顶级单元';
```

### 2.2 工作空间表

```sql
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- 工作空间级配额
    quotas JSONB DEFAULT '{
        "max_devices": 100,
        "max_cantor_instances": 10,
        "max_concurrent_tasks": 100
    }'::jsonb,
    
    -- 工作空间设置
    settings JSONB DEFAULT '{
        "default_device_timeout": 300,
        "auto_cleanup_tasks": true
    }'::jsonb,
    
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    UNIQUE(org_id, name)
);

-- 索引
CREATE INDEX idx_workspaces_org_id ON workspaces(org_id);
CREATE INDEX idx_workspaces_status ON workspaces(status);

COMMENT ON TABLE workspaces IS '工作空间表，业务隔离单元，资源归属和权限范围的边界';
```

### 2.3 用户表

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- 登录凭证（邮箱为主，手机可选）
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    password_hash VARCHAR(255), -- Bcrypt hash (cost 12)
    
    -- 基本信息
    name VARCHAR(100),
    avatar_url TEXT,
    timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
    locale VARCHAR(10) DEFAULT 'zh-CN',
    
    -- 状态管理
    status VARCHAR(20) DEFAULT 'active', -- active/inactive/invited/suspended
    email_verified_at TIMESTAMPTZ,
    phone_verified_at TIMESTAMPTZ,
    
    -- 多因素认证
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255), -- TOTP secret (encrypted)
    mfa_backup_codes TEXT[], -- 一次性备用码（加密存储）
    
    -- 安全相关
    last_login_at TIMESTAMPTZ,
    last_login_ip INET,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    
    UNIQUE(org_id, email)
);

-- 索引
CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_created_at ON users(created_at);

COMMENT ON TABLE users IS '用户表，组织内成员，邮箱在组织内唯一';
```

### 2.4 角色与权限表

```sql
-- 角色定义表（支持系统预设 + 自定义）
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE, -- NULL = 系统预设
    
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- 权限列表（细粒度权限点）
    permissions TEXT[] NOT NULL DEFAULT '{}',
    
    -- 数据范围（workspace 级别的自动授权）
    workspace_scope VARCHAR(20) DEFAULT 'specific', -- all/specific/none
    
    is_system BOOLEAN DEFAULT FALSE,
    is_default BOOLEAN DEFAULT FALSE, -- 新用户默认角色
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(org_id, name)
);

-- 系统预设角色（初始化数据）
INSERT INTO roles (id, name, description, permissions, is_system, is_default) VALUES
-- Owner: 全部权限
('role-owner', 'Owner', '组织所有者，拥有所有权限', 
    ARRAY['*'], TRUE, FALSE),

-- Admin: 成员和 Workspace 管理
('role-admin', 'Admin', '管理员，可管理成员和 Workspace', 
    ARRAY['org:read', 'org:update', 'user:*', 'workspace:*', 
          'cantor:*', 'device:*', 'task:*', 'script:*', 'api_key:*'], 
    TRUE, FALSE),

-- Operator: 日常操作
('role-operator', 'Operator', '操作员，可管理任务和设备', 
    ARRAY['org:read', 'user:read:self', 'workspace:read',
          'cantor:*', 'device:control', 'device:read', 
          'task:execute', 'task:read', 'script:read', 'script:execute'], 
    TRUE, TRUE),

-- Viewer: 只读访问
('role-viewer', 'Viewer', '观察者，只读访问', 
    ARRAY['org:read', 'user:read:self', 'workspace:read',
          'cantor:read', 'device:read', 'task:read', 'script:read'], 
    TRUE, FALSE);

-- 用户-工作空间-角色关联表（数据范围权限）
CREATE TABLE user_workspace_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    
    -- 授权信息
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ, -- 可选的临时授权
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, workspace_id, role_id)
);

-- 索引
CREATE INDEX idx_user_workspace_roles_user_id ON user_workspace_roles(user_id);
CREATE INDEX idx_user_workspace_roles_workspace_id ON user_workspace_roles(workspace_id);
CREATE INDEX idx_user_workspace_roles_role_id ON user_workspace_roles(role_id);

COMMENT ON TABLE roles IS '角色定义表，权限的集合';
COMMENT ON TABLE user_workspace_roles IS '用户角色授权表，定义用户在特定工作空间的权限';
```

### 2.5 API Key 表

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE, -- NULL = 组织级 Key
    
    name VARCHAR(100) NOT NULL, -- 用户可读名称
    description TEXT,
    
    -- Key 存储（只存 hash）
    key_hash VARCHAR(255) UNIQUE NOT NULL, -- SHA256(key)
    key_preview VARCHAR(10), -- 前几位用于展示，如 "sk_live_abc..."
    
    -- 权限限制（可为空表示继承创建者权限）
    permissions TEXT[], -- 限定权限子集
    
    -- 使用限制
    allowed_ips INET[], -- IP 白名单（NULL = 不限制）
    rate_limit INTEGER DEFAULT 1000, -- 每分钟请求数
    
    -- 生命周期
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    last_used_ip INET,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'active', -- active/revoked/expired
    revoked_at TIMESTAMPTZ,
    revoked_reason TEXT,
    
    -- 审计
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_api_keys_org_id ON api_keys(org_id);
CREATE INDEX idx_api_keys_workspace_id ON api_keys(workspace_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_status ON api_keys(status);

COMMENT ON TABLE api_keys IS 'API Key 表，用于设备端和自动化脚本认证';
```

### 2.6 审计日志表

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    workspace_id UUID REFERENCES workspaces(id),
    
    -- 操作者信息
    user_id UUID REFERENCES users(id),
    api_key_id UUID REFERENCES api_keys(id),
    
    -- 操作信息
    action VARCHAR(100) NOT NULL, -- 'user.login', 'task.execute', 'api_key.create'
    resource_type VARCHAR(50), -- 'user', 'task', 'device', 'api_key'
    resource_id UUID,
    
    -- 请求上下文
    ip_address INET,
    user_agent TEXT,
    request_id UUID,
    
    -- 变更详情
    payload JSONB, -- 请求参数（脱敏后）
    changes JSONB, -- 变更前后的值（敏感操作）
    result VARCHAR(20), -- success/failure/denied/error
    error_message TEXT,
    
    -- 时间戳（分区键）
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- 创建月度分区
CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- 索引
CREATE INDEX idx_audit_logs_org_id ON audit_logs(org_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

COMMENT ON TABLE audit_logs IS '审计日志表，记录所有认证和权限相关操作';
```

---

## 3. JWT 实现细节

### 3.1 Token 结构设计

#### Access Token (15 分钟有效期)
```json
{
  "sub": "user-uuid",
  "org": {
    "id": "org-uuid",
    "name": "Acme Corp",
    "slug": "acme-corp"
  },
  "workspaces": [
    {
      "id": "ws-uuid-1",
      "name": "Production",
      "role": "operator",
      "permissions": ["cantor:*", "device:control", "task:execute"]
    },
    {
      "id": "ws-uuid-2", 
      "name": "Staging",
      "role": "viewer",
      "permissions": ["cantor:read", "device:read", "task:read"]
    }
  ],
  "permissions": ["org:read", "user:read:self"],
  "jti": "unique-token-id",
  "iat": 1704067200,
  "exp": 1704068100,
  "type": "access"
}
```

#### Refresh Token (7 天有效期)
```json
{
  "sub": "user-uuid",
  "jti": "unique-refresh-token-id",
  "token_version": 1,
  "iat": 1704067200,
  "exp": 1704672000,
  "type": "refresh"
}
```

### 3.2 Token 签发流程

```go
// Auth Service - Token 签发逻辑
type TokenService struct {
    privateKey *rsa.PrivateKey
    publicKey  *rsa.PublicKey
    redis      *redis.Client
}

func (s *TokenService) GenerateTokenPair(ctx context.Context, user *User) (*TokenPair, error) {
    // 1. 查询用户的 workspaces 和 roles
    workspaceRoles, err := s.loadUserWorkspaceRoles(ctx, user.ID)
    if err != nil {
        return nil, err
    }
    
    // 2. 构建 Access Token Claims
    accessJTI := uuid.New().String()
    accessClaims := AccessTokenClaims{
        StandardClaims: jwt.StandardClaims{
            Subject:   user.ID.String(),
            ExpiresAt: time.Now().Add(15 * time.Minute).Unix(),
            IssuedAt:  time.Now().Unix(),
            ID:        accessJTI,
        },
        Type:       "access",
        OrgID:      user.OrgID,
        OrgSlug:    user.OrgSlug,
        Workspaces: workspaceRoles,
        Permissions: aggregatePermissions(workspaceRoles),
    }
    
    // 3. 构建 Refresh Token Claims
    refreshJTI := uuid.New().String()
    refreshClaims := RefreshTokenClaims{
        StandardClaims: jwt.StandardClaims{
            Subject:   user.ID.String(),
            ExpiresAt: time.Now().Add(7 * 24 * time.Hour).Unix(),
            IssuedAt:  time.Now().Unix(),
            ID:        refreshJTI,
        },
        Type:         "refresh",
        TokenVersion: user.TokenVersion,
    }
    
    // 4. 签名
    accessToken, err := jwt.NewWithClaims(jwt.SigningMethodRS256, accessClaims).SignedString(s.privateKey)
    if err != nil {
        return nil, err
    }
    
    refreshToken, err := jwt.NewWithClaims(jwt.SigningMethodRS256, refreshClaims).SignedString(s.privateKey)
    if err != nil {
        return nil, err
    }
    
    // 5. 记录 JTI 到 Redis（用于吊销）
    s.redis.Set(ctx, fmt.Sprintf("jwt:active:%s", accessJTI), user.ID.String(), 15*time.Minute)
    s.redis.Set(ctx, fmt.Sprintf("jwt:refresh:%s", refreshJTI), user.ID.String(), 7*24*time.Hour)
    
    return &TokenPair{
        AccessToken:  accessToken,
        RefreshToken: refreshToken,
        ExpiresIn:    900, // 15 minutes
    }, nil
}
```

### 3.3 Token 刷新与吊销

```go
// Refresh Token 流程
func (s *TokenService) RefreshToken(ctx context.Context, refreshToken string) (*TokenPair, error) {
    // 1. 解析并验证 Refresh Token
    token, err := jwt.ParseWithClaims(refreshToken, &RefreshTokenClaims{}, 
        func(token *jwt.Token) (interface{}, error) {
            return s.publicKey, nil
        })
    if err != nil || !token.Valid {
        return nil, ErrInvalidToken
    }
    
    claims := token.Claims.(*RefreshTokenClaims)
    
    // 2. 检查是否被吊销
    blacklisted, err := s.redis.Exists(ctx, fmt.Sprintf("jwt:blacklist:%s", claims.ID)).Result()
    if err != nil || blacklisted > 0 {
        return nil, ErrTokenRevoked
    }
    
    // 3. 检查用户 Token Version（密码修改等场景会递增）
    user, err := s.userRepo.GetByID(ctx, claims.Subject)
    if err != nil {
        return nil, err
    }
    if user.TokenVersion != claims.TokenVersion {
        return nil, ErrTokenVersionMismatch
    }
    
    // 4. 生成新的 Token Pair
    newPair, err := s.GenerateTokenPair(ctx, user)
    if err != nil {
        return nil, err
    }
    
    // 5. 将旧的 Refresh Token 加入黑名单（7 天后自动过期）
    ttl := time.Until(time.Unix(claims.ExpiresAt, 0))
    s.redis.Set(ctx, fmt.Sprintf("jwt:blacklist:%s", claims.ID), "revoked", ttl)
    
    return newPair, nil
}

// 全局吊销（登出所有设备）
func (s *TokenService) RevokeAllUserTokens(ctx context.Context, userID string) error {
    // 递增用户的 Token Version，使所有现有 Refresh Token 失效
    return s.userRepo.IncrementTokenVersion(ctx, userID)
}
```

### 3.4 API Gateway 校验中间件

```go
// JWT 校验中间件
func JWTMiddleware(tokenService *TokenService) gin.HandlerFunc {
    return func(c *gin.Context) {
        // 1. 提取 Token
        authHeader := c.GetHeader("Authorization")
        if authHeader == "" || !strings.HasPrefix(authHeader, "Bearer ") {
            c.AbortWithStatusJSON(401, ErrorResponse{Error: "missing token"})
            return
        }
        tokenString := strings.TrimPrefix(authHeader, "Bearer ")
        
        // 2. 解析验证
        claims, err := tokenService.ValidateAccessToken(tokenString)
        if err != nil {
            c.AbortWithStatusJSON(401, ErrorResponse{Error: err.Error()})
            return
        }
        
        // 3. 检查黑名单
        blacklisted, _ := tokenService.redis.Exists(c, fmt.Sprintf("jwt:blacklist:%s", claims.ID)).Result()
        if blacklisted > 0 {
            c.AbortWithStatusJSON(401, ErrorResponse{Error: "token revoked"})
            return
        }
        
        // 4. 设置上下文
        c.Set("user_id", claims.Subject)
        c.Set("org_id", claims.OrgID)
        c.Set("permissions", claims.Permissions)
        c.Set("workspaces", claims.Workspaces)
        c.Set("token_jti", claims.ID)
        
        // 5. 设置数据库 RLS 上下文
        c.Set("db_org_id", claims.OrgID)
        
        c.Next()
    }
}
```

---

## 4. API Key 机制

### 4.1 Key 生成流程

```go
const (
    APIKeyPrefix    = "cantor_"
    APIKeyLength    = 48 // 实际生成的随机部分长度
)

type APIKeyService struct {
    db    *gorm.DB
    redis *redis.Client
}

func (s *APIKeyService) CreateAPIKey(ctx context.Context, req CreateAPIKeyRequest, creator *User) (*APIKeyResponse, error) {
    // 1. 生成随机 Key
    rawKey := generateSecureRandomString(APIKeyLength)
    fullKey := APIKeyPrefix + rawKey // cantor_xxxxxx...
    
    // 2. 计算 Hash（只存 hash）
    keyHash := sha256.Sum256([]byte(fullKey))
    keyHashStr := hex.EncodeToString(keyHash[:])
    
    // 3. 权限校验：API Key 权限不能超过创建者权限
    if err := validatePermissions(req.Permissions, creator.Permissions); err != nil {
        return nil, err
    }
    
    // 4. 创建记录
    apiKey := &APIKey{
        ID:          uuid.New(),
        OrgID:       creator.OrgID,
        WorkspaceID: req.WorkspaceID,
        Name:        req.Name,
        Description: req.Description,
        KeyHash:     keyHashStr,
        KeyPreview:  fullKey[:10] + "...",
        Permissions: req.Permissions,
        AllowedIPs:  req.AllowedIPs,
        RateLimit:   req.RateLimit,
        ExpiresAt:   req.ExpiresAt,
        Status:      "active",
        CreatedBy:   creator.ID,
    }
    
    if err := s.db.Create(apiKey).Error; err != nil {
        return nil, err
    }
    
    // 5. 写入缓存
    s.cacheAPIKey(ctx, keyHashStr, apiKey)
    
    // 6. 返回完整 Key（仅一次）
    return &APIKeyResponse{
        ID:          apiKey.ID,
        Name:        apiKey.Name,
        Key:         fullKey, // ⚠️ 仅返回这一次
        Permissions: apiKey.Permissions,
        ExpiresAt:   apiKey.ExpiresAt,
    }, nil
}

// 缓存 API Key 信息到 Redis
func (s *APIKeyService) cacheAPIKey(ctx context.Context, keyHash string, key *APIKey) {
    data, _ := json.Marshal(key)
    s.redis.Set(ctx, fmt.Sprintf("apikey:%s", keyHash), data, 1*time.Hour)
}
```

### 4.2 Key 校验流程（Signaling Gateway）

```go
// WebSocket 连接时的 API Key 校验
func (gw *SignalingGateway) handleConnection(ws *websocket.Conn, r *http.Request) {
    // 1. 提取 API Key（Query 参数或 Header）
    apiKey := r.URL.Query().Get("api_key")
    if apiKey == "" {
        apiKey = r.Header.Get("X-API-Key")
    }
    
    // 2. 计算 Hash
    keyHash := sha256.Sum256([]byte(apiKey))
    keyHashStr := hex.EncodeToString(keyHash[:])
    
    // 3. 查询缓存/数据库
    apiKeyInfo, err := gw.getAPIKeyInfo(r.Context(), keyHashStr)
    if err != nil {
        ws.WriteJSON(ErrorMessage{Error: "invalid api key"})
        ws.Close()
        return
    }
    
    // 4. 校验状态
    if apiKeyInfo.Status != "active" {
        ws.WriteJSON(ErrorMessage{Error: "api key revoked or expired"})
        ws.Close()
        return
    }
    
    // 5. 校验过期
    if apiKeyInfo.ExpiresAt != nil && apiKeyInfo.ExpiresAt.Before(time.Now()) {
        ws.WriteJSON(ErrorMessage{Error: "api key expired"})
        ws.Close()
        return
    }
    
    // 6. 校验 IP 白名单
    if len(apiKeyInfo.AllowedIPs) > 0 {
        clientIP := parseClientIP(r)
        if !containsIP(apiKeyInfo.AllowedIPs, clientIP) {
            ws.WriteJSON(ErrorMessage{Error: "ip not allowed"})
            ws.Close()
            return
        }
    }
    
    // 7. 更新最后使用时间
    gw.updateKeyLastUsed(r.Context(), apiKeyInfo.ID, parseClientIP(r))
    
    // 8. 建立连接上下文
    conn := &DeviceConnection{
        WS:          ws,
        OrgID:       apiKeyInfo.OrgID,
        WorkspaceID: apiKeyInfo.WorkspaceID,
        Permissions: apiKeyInfo.Permissions,
        APIKeyID:    apiKeyInfo.ID,
        ConnectedAt: time.Now(),
    }
    
    // 9. 注册连接并开始处理消息
    gw.registerConnection(conn)
    gw.handleMessages(conn)
}
```

### 4.3 Rate Limit 实现

```go
func (gw *SignalingGateway) checkRateLimit(ctx context.Context, apiKeyID string, limit int) bool {
    key := fmt.Sprintf("ratelimit:%s", apiKeyID)
    
    // 滑动窗口计数
    now := time.Now().Unix()
    window := now / 60 // 每分钟一个窗口
    
    pipe := gw.redis.Pipeline()
    pipe.Incr(ctx, fmt.Sprintf("%s:%d", key, window))
    pipe.Expire(ctx, fmt.Sprintf("%s:%d", key, window), 2*time.Minute)
    
    // 获取当前窗口计数
    pipe.Get(ctx, fmt.Sprintf("%s:%d", key, window))
    
    results, err := pipe.Exec(ctx)
    if err != nil {
        return true // 出错时放行
    }
    
    count, _ := results[2].(*redis.StringCmd).Int()
    return count <= limit
}
```

---

## 5. RBAC 权限模型

### 5.1 权限字符串规范

```
格式: {resource}:{action}:{scope}

resource:
  - org          组织管理
  - user         用户管理
  - workspace    工作空间管理
  - cantor       Cantor 实例
  - device       设备管理
  - task         任务管理
  - script       脚本管理
  - api_key      API Key 管理
  - audit_log    审计日志

action:
  - *            所有操作
  - create       创建
  - read         读取
  - read:self    仅读取自己的
  - update       更新
  - delete       删除
  - control      控制（设备）
  - execute      执行（任务/脚本）

scope:（可选，用于特定资源）
  - {id}         特定资源 ID
```

### 5.2 权限校验函数

```go
// 权限匹配器
type Permission string

func (p Permission) Match(required string) bool {
    parts := strings.Split(string(p), ":")
    requiredParts := strings.Split(required, ":")
    
    // 通配符权限
    if string(p) == "*" {
        return true
    }
    
    // 逐段匹配
    for i, part := range parts {
        if i >= len(requiredParts) {
            return true // 权限更具体，匹配
        }
        
        if part == "*" {
            return true // 通配
        }
        
        if part != requiredParts[i] {
            return false
        }
    }
    
    return len(parts) == len(requiredParts)
}

// 检查权限
func CheckPermission(userPerms []string, required string) bool {
    for _, perm := range userPerms {
        if Permission(perm).Match(required) {
            return true
        }
    }
    return false
}

// 检查工作空间范围权限
func CheckWorkspacePermission(userWorkspaces []WorkspacePermission, workspaceID string, requiredPerm string) bool {
    for _, ws := range userWorkspaces {
        if ws.ID == workspaceID {
            return CheckPermission(ws.Permissions, requiredPerm)
        }
    }
    return false
}

// Gin 中间件：检查权限
func RequirePermission(permission string) gin.HandlerFunc {
    return func(c *gin.Context) {
        perms, exists := c.Get("permissions")
        if !exists {
            c.AbortWithStatusJSON(403, ErrorResponse{Error: "unauthorized"})
            return
        }
        
        userPerms := perms.([]string)
        if !CheckPermission(userPerms, permission) {
            c.AbortWithStatusJSON(403, ErrorResponse{Error: "insufficient permissions"})
            return
        }
        
        c.Next()
    }
}
```

### 5.3 权限继承关系

```
Owner (组织级)
├── user:*
├── workspace:*
├── cantor:*
├── device:*
├── task:*
├── script:*
└── api_key:*

Admin (组织级)
├── org:read, org:update
├── user:*
├── workspace:*
├── cantor:*
├── device:*
├── task:*
├── script:*
└── api_key:*

Operator (工作空间级)
├── org:read
├── user:read:self
├── workspace:read
├── cantor:* (限本 workspace)
├── device:control, device:read
├── task:execute, task:read
├── script:read, script:execute
└── api_key:read (仅自己创建的)

Viewer (工作空间级)
├── org:read
├── user:read:self
├── workspace:read
├── cantor:read
├── device:read
├── task:read
└── script:read
```

---

## 6. 安全策略

### 6.1 密码策略

```go
const (
    MinPasswordLength     = 12
    PasswordHashCost      = 12
    MaxFailedLoginAttempts = 5
    LockoutDuration       = 30 * time.Minute
)

func ValidatePassword(password string) error {
    if len(password) < MinPasswordLength {
        return fmt.Errorf("password must be at least %d characters", MinPasswordLength)
    }
    
    var (
        hasUpper   bool
        hasLower   bool
        hasNumber  bool
        hasSpecial bool
    )
    
    for _, char := range password {
        switch {
        case unicode.IsUpper(char):
            hasUpper = true
        case unicode.IsLower(char):
            hasLower = true
        case unicode.IsNumber(char):
            hasNumber = true
        case unicode.IsPunct(char) || unicode.IsSymbol(char):
            hasSpecial = true
        }
    }
    
    if !hasUpper || !hasLower || !hasNumber || !hasSpecial {
        return errors.New("password must contain uppercase, lowercase, number, and special character")
    }
    
    return nil
}

func HashPassword(password string) (string, error) {
    bytes, err := bcrypt.GenerateFromPassword([]byte(password), PasswordHashCost)
    return string(bytes), err
}
```

### 6.2 MFA (TOTP) 实现

```go
import "github.com/pquerna/otp/totp"

func (s *AuthService) EnableMFA(ctx context.Context, userID string) (*MFASetup, error) {
    // 生成 TOTP 密钥
    key, err := totp.Generate(totp.GenerateOpts{
        Issuer:      "Cantor",
        AccountName: user.Email,
    })
    if err != nil {
        return nil, err
    }
    
    // 生成备用码
    backupCodes := generateBackupCodes(10)
    
    // 加密存储
    encryptedSecret := s.encrypt(key.Secret())
    encryptedBackupCodes := s.encryptStrings(backupCodes)
    
    // 暂存（需验证一次后才正式启用）
    s.redis.Set(ctx, fmt.Sprintf("mfa:pending:%s", userID), encryptedSecret, 10*time.Minute)
    
    return &MFASetup{
        Secret:      key.Secret(),
        QRCodeURL:   key.URL(),
        BackupCodes: backupCodes, // 仅显示一次
    }, nil
}

func (s *AuthService) VerifyMFAAndEnable(ctx context.Context, userID, code string) error {
    // 获取暂存的密钥
    encryptedSecret, err := s.redis.Get(ctx, fmt.Sprintf("mfa:pending:%s", userID)).Result()
    if err != nil {
        return ErrMFASetupExpired
    }
    
    secret := s.decrypt(encryptedSecret)
    
    // 验证 TOTP 码
    valid := totp.Validate(code, secret)
    if !valid {
        return ErrInvalidMFACode
    }
    
    // 正式启用
    return s.db.Model(&User{}).Where("id = ?", userID).Updates(map[string]interface{}{
        "mfa_enabled":  true,
        "mfa_secret":   encryptedSecret,
    }).Error
}
```

### 6.3 审计日志记录

```go
// 审计日志中间件
func AuditMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        start := time.Now()
        
        // 记录请求前数据
        var requestBody []byte
        if c.Request.Body != nil {
            requestBody, _ = io.ReadAll(c.Request.Body)
            c.Request.Body = io.NopCloser(bytes.NewBuffer(requestBody))
        }
        
        c.Next()
        
        // 记录审计日志（异步）
        go func() {
            auditLog := &AuditLog{
                OrgID:        getOrgIDFromContext(c),
                UserID:       getUserIDFromContext(c),
                APIKeyID:     getAPIKeyIDFromContext(c),
                Action:       fmt.Sprintf("%s.%s", c.Request.Method, c.FullPath()),
                ResourceType: c.Param("resource_type"),
                ResourceID:   parseUUID(c.Param("id")),
                IPAddress:    parseClientIP(c.Request),
                UserAgent:    c.Request.UserAgent(),
                RequestID:    c.GetString("request_id"),
                Payload:      sanitizePayload(requestBody),
                Result:       getResultFromStatus(c.Writer.Status()),
                CreatedAt:    start,
            }
            
            auditRepo.Create(context.Background(), auditLog)
        }()
    }
}
```

---

## 7. 关键设计决策说明

### 7.1 为什么选择 JWT + API Key 双认证模式？

| 场景 | 认证方式 | 理由 |
|------|----------|------|
| Dashboard 用户操作 | JWT (Access + Refresh) | 支持会话管理、可吊销、适合浏览器环境 |
| 设备端 Worker 连接 | API Key | 长期有效、可独立吊销、支持 IP 白名单 |
| 自动化脚本/CI | API Key | 无需用户交互、可精细化权限控制 |
| 第三方集成 | API Key | 权限最小化、可独立监控和限流 |

### 7.2 为什么采用 Organization → Workspace 两级租户模型？

1. **B2B 需求**：企业客户通常需要按业务线/项目组隔离资源
2. **权限边界**：Workspace 是权限的边界，方便实现数据范围控制
3. **资源配额**：可在 Organization 和 Workspace 两级分别设置配额
4. **成本分摊**：Workspace 可作为计费单元

### 7.3 为什么选择 PostgreSQL RLS 作为最终防线？

```
深度防御层次：
┌─────────────────────────────────────┐
│ 1. API Gateway JWT/API Key 校验     │
├─────────────────────────────────────┤
│ 2. Service 层权限检查 middleware     │
├─────────────────────────────────────┤
│ 3. Repository 层强制 org_id 过滤     │
├─────────────────────────────────────┤
│ 4. PostgreSQL RLS 行级安全策略      │ ← 最终防线
└─────────────────────────────────────┘
```

RLS 可防止以下场景的代码漏洞：
- Repository 层忘记加 `WHERE org_id = ?`
- 跨服务调用时 org_id 传递错误
- 数据库直连查询（管理员操作）

### 7.4 为什么 API Key 只存 SHA256 Hash？

1. **安全性**：Key 本身不存储，泄露数据库也无法伪造请求
2. **可查找**：通过 Hash 可快速定位 Key 记录
3. **不可逆**：SHA256 是单向函数，无法从 Hash 反推原始 Key
4. **性能**：Hash 查询可利用索引

### 7.5 JWT 为什么分 Access Token 和 Refresh Token？

| Token 类型 | 有效期 | 用途 | 风险 |
|------------|--------|------|------|
| Access Token | 15 分钟 | 频繁请求携带 | 泄露后可快速吊销 |
| Refresh Token | 7 天 | 换取新 Access Token | 泄露后可吊销，但有更长窗口期 |

**双 Token 优势**：
- Access Token 短有效期降低泄露风险
- Refresh Token 减少登录频率，提升用户体验
- 可独立吊销 Refresh Token 而不影响当前会话
- Token Version 机制支持密码修改后全局吊销

### 7.6 权限模型为什么选择 RBAC + 数据范围？

```
传统 RBAC: 用户 → 角色 → 权限
             ↓
         缺少数据范围控制

本设计: 用户 → 角色 → 权限
           ↓
        Workspace 范围
           ↓
        数据隔离
```

**组合优势**：
- RBAC 简化权限管理，避免 ACL 爆炸
- Workspace 范围实现多租户数据隔离
- 支持同一用户在不同 Workspace 有不同角色

---

## 8. 接口清单

### 8.1 认证接口

| 方法 | 路径 | 描述 | 认证 |
|------|------|------|------|
| POST | /auth/register | 用户注册 | 无 |
| POST | /auth/login | 用户登录 | 无 |
| POST | /auth/refresh | 刷新 Token | Refresh Token |
| POST | /auth/logout | 登出 | Access Token |
| POST | /auth/logout-all | 登出所有设备 | Access Token |
| POST | /auth/mfa/enable | 启用 MFA | Access Token |
| POST | /auth/mfa/verify | 验证 MFA | Access Token |
| POST | /auth/password/reset | 重置密码 | 邮箱验证 |

### 8.2 API Key 管理接口

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | /api-keys | 列出 API Keys | api_key:read |
| POST | /api-keys | 创建 API Key | api_key:create |
| GET | /api-keys/:id | 获取 API Key 详情 | api_key:read |
| DELETE | /api-keys/:id | 删除/吊销 API Key | api_key:delete |
| PATCH | /api-keys/:id | 更新 API Key | api_key:update |

### 8.3 用户管理接口

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | /users | 列出组织成员 | user:read |
| POST | /users | 邀请用户 | user:create |
| GET | /users/:id | 获取用户信息 | user:read |
| PATCH | /users/:id | 更新用户信息 | user:update |
| DELETE | /users/:id | 删除用户 | user:delete |
| POST | /users/:id/roles | 分配角色 | user:update |

### 8.4 Workspace 管理接口

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | /workspaces | 列出 Workspaces | workspace:read |
| POST | /workspaces | 创建 Workspace | workspace:create |
| GET | /workspaces/:id | 获取详情 | workspace:read |
| PATCH | /workspaces/:id | 更新 Workspace | workspace:update |
| DELETE | /workspaces/:id | 删除 Workspace | workspace:delete |
| GET | /workspaces/:id/members | 列出成员 | workspace:read |
| POST | /workspaces/:id/members | 添加成员 | workspace:update |

---

## 9. 部署建议

### 9.1 密钥管理

```yaml
# 需要安全管理的密钥
secrets:
  jwt_private_key: /secrets/jwt-private.pem  # RSA 私钥，用于签名
  jwt_public_key: /secrets/jwt-public.pem    # RSA 公钥，用于验签
  db_encryption_key: /secrets/db-enc.key     # 数据库字段加密密钥
  mfa_encryption_key: /secrets/mfa-enc.key   # MFA 密钥加密
```

### 9.2 Redis 配置

```yaml
redis:
  # JWT 相关
  jwt_blacklist_ttl: 7d      # 黑名单保留时间（与 Refresh Token 一致）
  jwt_active_ttl: 15m        # Active JTI 记录时间
  
  # API Key 缓存
  apikey_cache_ttl: 1h       # API Key 信息缓存时间
  
  # Rate Limit
  ratelimit_window: 1m       # 限流窗口
  
  # 连接池
  pool_size: 100
  min_idle: 10
```

### 9.3 数据库配置

```yaml
postgresql:
  # 连接池
  max_connections: 100
  
  # RLS 配置
  rls_enabled: true
  
  # 审计日志分区
  audit_log_partitions:
    - monthly  # 按月分区
    - retention: 12months  # 保留 12 个月
```
