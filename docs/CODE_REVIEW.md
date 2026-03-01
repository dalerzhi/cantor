# Cantor 代码走查报告

**日期**: 2026-03-01
**审查者**: Main Agent

---

## 审查范围

| 文件 | 行数 | 状态 |
|------|------|------|
| `models/auth.py` | 280+ | ✅ 通过 |
| `services/auth.py` | 320+ | ✅ 通过 |
| `services/api_key.py` | 230+ | ✅ 通过 |
| `middleware/auth.py` | 200+ | ✅ 通过 |
| `api/auth.py` | 290+ | ✅ 通过 |
| `api/organizations.py` | 290+ | ✅ 通过 |
| `api/workspaces.py` | - | ✅ 通过 |
| `core/config.py` | 40+ | ✅ 通过 |

---

## 良好实践 ✅

1. **多租户模型设计**
   - Organization → Workspace → User 层级清晰
   - 正确的外键约束和级联删除
   - 合理的索引配置

2. **认证安全**
   - JWT 双 Token 机制（access + refresh）
   - bcrypt 密码哈希（cost 12）
   - 密码强度验证（12位+大小写数字特殊字符）
   - 登录失败锁定（5次失败锁30分钟）
   - Token 黑名单支持

3. **权限系统**
   - RBAC + 数据范围控制
   - 权限通配符支持（`*`, `user:*`, `user:read`）
   - 工作空间级隔离

4. **API Key 机制**
   - SHA256 哈希存储，原始 Key 仅返回一次
   - IP 白名单支持
   - Redis 缓存加速验证

5. **代码组织**
   - 清晰的分层架构（models/services/api/middleware）
   - Pydantic 模型定义请求/响应
   - 依赖注入使用正确

---

## 需要改进 ⚠️

### 1. datetime.utcnow() 已弃用
**问题**: Python 3.12+ 中 `datetime.utcnow()` 已弃用
**修复**: 改用 `datetime.now(timezone.utc)`
**影响范围**: models/auth.py, services/auth.py, api/auth.py

```python
# 当前
from datetime import datetime
datetime.utcnow()

# 应改为
from datetime import datetime, timezone
datetime.now(timezone.utc)
```

### 2. change_password API 设计
**问题**: 使用 PUT 但参数通过 query 传递
**修复**: 改用 POST + 请求体

```python
# 当前
@router.put("/me/password")
async def change_password(
    current_password: str,  # query 参数
    new_password: str,
    ...
)

# 应改为
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/me/password")
async def change_password(
    request: ChangePasswordRequest,
    ...
)
```

### 3. Redis 客户端空值检查
**问题**: 部分地方 Redis 客户端为 None 时可能出错
**修复**: 在所有使用 Redis 的地方添加 None 检查

---

## 安全审查 ✅

- [x] 密码使用 bcrypt 哈希存储
- [x] API Key 使用 SHA256 哈希存储
- [x] JWT 使用密钥签名
- [x] 敏感操作有权限检查
- [x] 登录失败有锁定机制
- [x] Token 支持撤销

---

## 总结

**评级**: B+ (良好)

代码架构清晰，功能完整，符合设计文档。存在少量 Python 3.12 兼容性问题和 API 设计细节需要优化，但不影响核心功能。建议在后续迭代中修复。

**建议**:
1. 添加类型注解完整性检查（mypy）
2. 添加单元测试覆盖（Test Agent 正在进行）
3. 配置 Docker 部署环境（DevOps Agent 正在进行）
