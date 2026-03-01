# Cantor 部署文档

## 快速开始

### 1. 配置环境变量

```bash
# 复制环境变量模板
cp docker/.env.docker docker/.env

# 编辑配置（⚠️ 必须修改敏感信息）
vim docker/.env
```

**必须修改的配置：**
- `POSTGRES_PASSWORD` - PostgreSQL 密码
- `REDIS_PASSWORD` - Redis 密码
- `JWT_SECRET_KEY` - JWT 签名密钥

### 2. 一键部署

```bash
./scripts/deploy.sh
```

部署脚本会自动：
- 创建 `.env` 文件（如果不存在）
- 构建 Docker 镜像
- 启动所有服务
- 执行健康检查

### 3. 验证服务

```bash
# 查看服务状态
docker-compose --env-file docker/.env ps

# 查看日志
./scripts/logs.sh

# 实时跟踪日志
./scripts/logs.sh all -f
```

## 服务架构

```
┌─────────────────┐
│   Gateway       │  WebSocket :8766
│   (Go)          │
└────────┬────────┘
         │
         ├──────────────┐
         │              │
         ▼              ▼
┌─────────────┐  ┌─────────────┐
│   Redis     │  │    Brain    │
│   (消息队列)  │  │  (FastAPI)  │
└─────────────┘  └──────┬──────┘
                        │
                        ▼
                 ┌─────────────┐
                 │ PostgreSQL  │
                 │   (数据库)   │
                 └─────────────┘
```

## 端口映射

| 服务 | 容器端口 | 主机端口 | 说明 |
|------|---------|---------|------|
| Gateway | 8766 | 8766 | WebSocket 服务 |
| Brain | 8000 | 8000 | FastAPI REST API |
| PostgreSQL | 5432 | 5432 | 数据库 |
| Redis | 6379 | 6379 | 缓存/消息队列 |

## 常用命令

### 部署相关

```bash
# 部署（构建 + 启动）
./scripts/deploy.sh

# 完全清理后重新部署
./scripts/deploy.sh --clean

# 停止服务
docker-compose --env-file docker/.env down

# 停止并删除数据卷
docker-compose --env-file docker/.env down -v
```

### 日志查看

```bash
# 查看所有服务日志
./scripts/logs.sh

# 查看特定服务日志
./scripts/logs.sh brain
./scripts/logs.sh gateway

# 实时跟踪日志
./scripts/logs.sh all -f
```

### 数据库操作

```bash
# 连接 PostgreSQL
./scripts/psql.sh

# 执行 SQL 文件
./scripts/psql.sh -f path/to/file.sql

# 连接 Redis
./scripts/redis-cli.sh

# 执行 Redis 命令
./scripts/redis-cli.sh ping
```

### 健康检查

```bash
# Brain 健康检查
curl http://localhost:8000/health

# Gateway 健康检查
curl http://localhost:8766/health

# PostgreSQL 健康检查
docker exec cantor-postgres pg_isready -U cantor

# Redis 健康检查
docker exec cantor-redis redis-cli -a <password> ping
```

## 数据持久化

Docker Compose 会创建以下数据卷：

- `postgres_data` - PostgreSQL 数据
- `redis_data` - Redis AOF 持久化数据

数据卷位置：`/var/lib/docker/volumes/cantor_*`

### 备份数据

```bash
# 备份 PostgreSQL
docker exec cantor-postgres pg_dump -U cantor cantor > backup_$(date +%Y%m%d).sql

# 恢复 PostgreSQL
cat backup.sql | docker exec -i cantor-postgres psql -U cantor cantor
```

## 生产环境建议

### 安全配置

1. **修改所有默认密码**
   ```bash
   # 生成强密码
   openssl rand -base64 32
   ```

2. **配置防火墙**
   ```bash
   # 只允许本地访问数据库
   ufw allow 8766/tcp  # Gateway
   ufw allow 8000/tcp  # Brain API
   ufw deny 5432/tcp   # PostgreSQL
   ufw deny 6379/tcp   # Redis
   ```

3. **使用 HTTPS**
   - 配置反向代理（Nginx/Caddy）
   - 启用 SSL/TLS

### 性能优化

1. **调整 PostgreSQL 配置**
   ```yaml
   # docker-compose.yml
   postgres:
     command:
       - "postgres"
       - "-c"
       - "max_connections=200"
       - "-c"
       - "shared_buffers=256MB"
   ```

2. **调整 Redis 配置**
   ```yaml
   # docker-compose.yml
   redis:
     command:
       - "redis-server"
       - "--appendonly"
       - "yes"
       - "--maxmemory"
       - "256mb"
       - "--maxmemory-policy"
       - "allkeys-lru"
   ```

### 监控

1. **日志收集**
   ```bash
   # 使用 ELK/Loki 收集日志
   docker-compose logs -f --tail=1000 > cantor.log
   ```

2. **健康监控**
   - 使用 Prometheus + Grafana
   - 配置告警规则

## 故障排查

### 服务无法启动

```bash
# 查看详细日志
docker-compose --env-file docker/.env logs --tail=100

# 检查容器状态
docker ps -a | grep cantor

# 检查端口占用
netstat -tulpn | grep -E '8766|8000|5432|6379'
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
docker exec cantor-postgres pg_isready

# 检查连接字符串
echo $DATABASE_URL

# 手动连接测试
./scripts/psql.sh
```

### Redis 连接失败

```bash
# 检查 Redis 是否运行
docker exec cantor-redis redis-cli ping

# 检查密码
docker exec cantor-redis redis-cli -a <password> ping
```

## 更新部署

```bash
# 拉取最新代码
git pull

# 重新构建并部署
./scripts/deploy.sh

# 或者使用 --clean 完全重建
./scripts/deploy.sh --clean
```
