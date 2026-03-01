# Cantor 生产环境部署指南

## 1. 资源需求

### 1.1 服务器配置

| 组件 | 最低配置 | 推荐配置 | 说明 |
|------|----------|----------|------|
| **CPU** | 2 核 | 4 核+ | Gateway/Brain 计算密集 |
| **内存** | 4 GB | 8 GB+ | PostgreSQL/Redis 缓存 |
| **存储** | 50 GB SSD | 100 GB+ SSD | 数据库 + 日志 |
| **带宽** | 5 Mbps | 20 Mbps+ | WebSocket 连接 |

### 1.2 服务器数量

| 部署模式 | 数量 | 说明 |
|----------|------|------|
| **单机部署** | 1 台 | 适合测试/小规模 (<100 设备) |
| **标准部署** | 2 台 | 应用服务器 + 数据库服务器 |
| **高可用部署** | 4+ 台 | 负载均衡 + 应用集群 + 数据库主从 |

### 1.3 推荐云服务商

- **阿里云**: ECS + RDS + SLB
- **腾讯云**: CVM + TencentDB + CLB
- **AWS**: EC2 + RDS + ALB

---

## 2. 网络配置

### 2.1 端口要求

| 端口 | 服务 | 协议 | 公网暴露 |
|------|------|------|----------|
| 80 | Nginx | HTTP | ✅ (重定向到 443) |
| 443 | Nginx | HTTPS | ✅ |
| 3000 | Frontend | HTTP | ❌ (内部) |
| 8000 | Brain API | HTTP | ❌ (内部) |
| 8766 | Gateway | WebSocket | ✅ (或通过 Nginx) |
| 5432 | PostgreSQL | TCP | ❌ (内部) |
| 6379 | Redis | TCP | ❌ (内部) |
| 22 | SSH | TCP | ✅ (限制 IP) |

### 2.2 域名要求

| 域名 | 用途 | 示例 |
|------|------|------|
| 主域名 | Dashboard + API | `cantor.yourcompany.com` |
| WebSocket | 实时通信 | `ws.cantor.yourcompany.com` |
| API | 后端接口 | `api.cantor.yourcompany.com` |

### 2.3 SSL 证书

- **类型**: 通配符证书 (`*.yourcompany.com`)
- **来源**: Let's Encrypt (免费) 或商业证书
- **工具**: certbot / acme.sh

---

## 3. 软件环境

### 3.1 操作系统

| 系统 | 版本 | 架构 |
|------|------|------|
| Ubuntu | 22.04 LTS | x86_64 / ARM64 |
| CentOS | 8+ | x86_64 / ARM64 |
| Debian | 12+ | x86_64 / ARM64 |

### 3.2 必装软件

```bash
# Docker
Docker Engine 24.0+
Docker Compose 2.20+

# 或使用 Docker 安装脚本
curl -fsSL https://get.docker.com | sh

# 其他工具
git, curl, wget, jq
```

### 3.3 Docker 版本要求

| 软件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Docker Engine | 20.10 | 24.0+ |
| Docker Compose | 2.0 | 2.20+ |

---

## 4. 数据库配置

### 4.1 PostgreSQL

| 配置项 | 开发环境 | 生产环境 |
|--------|----------|----------|
| 版本 | 15 | 15+ |
| CPU | 1 核 | 2+ 核 |
| 内存 | 1 GB | 4+ GB |
| 存储 | 10 GB | 100+ GB SSD |
| 连接数 | 100 | 500+ |
| 备份 | 无 | 每日自动备份 |

**推荐使用云数据库服务**:
- 阿里云 RDS PostgreSQL
- 腾讯云 TencentDB PostgreSQL
- AWS RDS PostgreSQL

### 4.2 Redis

| 配置项 | 开发环境 | 生产环境 |
|--------|----------|----------|
| 版本 | 7.0 | 7.0+ |
| 内存 | 512 MB | 2+ GB |
| 持久化 | 无 | AOF + RDB |
| 集群 | 单节点 | 哨兵/集群 |

---

## 5. 存储配置

### 5.1 目录结构

```
/opt/cantor/
├── docker-compose.yml
├── .env
├── postgres-data/     # PostgreSQL 数据 (或使用云数据库)
├── redis-data/        # Redis 数据
├── logs/              # 日志目录
├── backups/           # 备份目录
└── ssl/               # SSL 证书
```

### 5.2 存储容量规划

| 数据类型 | 每设备/天 | 100 设备/月 |
|----------|-----------|-------------|
| 日志 | 10 MB | 30 GB |
| 截图缓存 | 50 MB | 150 GB |
| 数据库 | 1 MB | 3 GB |
| **合计** | ~60 MB | ~180 GB |

---

## 6. 安全配置

### 6.1 防火墙规则

```bash
# UFW 示例
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp      # SSH (限制源 IP)
ufw allow 80/tcp      # HTTP
ufw allow 443/tcp     # HTTPS
ufw allow 8766/tcp    # WebSocket (可选)
ufw enable
```

### 6.2 安全组配置 (云平台)

| 规则 | 端口 | 源 | 说明 |
|------|------|-----|------|
| 允许 | 22 | 办公 IP | SSH 管理 |
| 允许 | 80 | 0.0.0.0/0 | HTTP |
| 允许 | 443 | 0.0.0.0/0 | HTTPS |
| 允许 | 8766 | 0.0.0.0/0 | WebSocket |
| 拒绝 | 5432 | - | 数据库禁止外网 |
| 拒绝 | 6379 | - | Redis 禁止外网 |

### 6.3 密钥管理

| 密钥类型 | 长度 | 存储 |
|----------|------|------|
| JWT_SECRET_KEY | 64 字符 | 环境变量 |
| 数据库密码 | 32 字符 | 环境变量 |
| Redis 密码 | 32 字符 | 环境变量 |
| IaaS AK/SK | - | 环境变量 |

**生成密钥**:
```bash
# 生成 64 字符随机密钥
openssl rand -hex 32
```

---

## 7. 监控与日志

### 7.1 监控指标

| 指标 | 告警阈值 | 说明 |
|------|----------|------|
| CPU 使用率 | > 80% | 5 分钟 |
| 内存使用率 | > 85% | 5 分钟 |
| 磁盘使用率 | > 85% | 5 分钟 |
| 服务健康 | != healthy | 1 分钟 |
| WebSocket 连接数 | > 1000 | 实时 |

### 7.2 日志配置

```yaml
# docker-compose.yml 日志配置
services:
  brain:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"
```

### 7.3 推荐监控工具

- **轻量**: Prometheus + Grafana
- **云原生**: 阿里云 ARMS / 腾讯云云监控
- **商业**: Datadog / New Relic

---

## 8. 备份策略

### 8.1 备份内容

| 内容 | 频率 | 保留期 |
|------|------|--------|
| PostgreSQL | 每日 | 30 天 |
| Redis RDB | 每小时 | 7 天 |
| 配置文件 | 变更时 | 永久 |
| SSL 证书 | 3 个月 | 1 年 |

### 8.2 备份脚本

```bash
#!/bin/bash
# 每日备份脚本

BACKUP_DIR="/opt/cantor/backups"
DATE=$(date +%Y%m%d)

# 备份 PostgreSQL
docker exec cantor-postgres pg_dump -U cantor cantor > $BACKUP_DIR/db_$DATE.sql

# 备份配置
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /opt/cantor/.env /opt/cantor/docker-compose.yml

# 清理 30 天前的备份
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

---

## 9. 部署清单

### 9.1 单机部署 (最小)

| 资源 | 规格 | 数量 | 月费用估算 |
|------|------|------|------------|
| 云服务器 | 2核4G | 1 | ¥200-300 |
| 公网带宽 | 5 Mbps | 1 | ¥50 |
| 云盘 | 50 GB SSD | 1 | ¥30 |
| **合计** | - | - | **¥280-380/月** |

### 9.2 标准部署 (推荐)

| 资源 | 规格 | 数量 | 月费用估算 |
|------|------|------|------------|
| 应用服务器 | 4核8G | 1 | ¥500-800 |
| 云数据库 | 2核4G | 1 | ¥400-600 |
| 云 Redis | 1G | 1 | ¥100-200 |
| 负载均衡 | - | 1 | ¥100 |
| 公网带宽 | 20 Mbps | 1 | ¥200 |
| 云盘 | 100 GB SSD | 1 | ¥60 |
| **合计** | - | - | **¥1360-1960/月** |

---

## 10. 部署前检查清单

### 10.1 资源准备

- [ ] 云服务器已购买
- [ ] 域名已注册
- [ ] SSL 证书已准备
- [ ] IaaS API 凭证已获取

### 10.2 网络配置

- [ ] 安全组规则已配置
- [ ] 域名 DNS 已解析
- [ ] 防火墙已配置

### 10.3 软件安装

- [ ] Docker 已安装
- [ ] Docker Compose 已安装
- [ ] Git 已安装

### 10.4 配置文件

- [ ] .env 文件已创建
- [ ] JWT 密钥已生成
- [ ] 数据库密码已设置

---

## 11. 快速部署命令

### 11.1 服务器初始化

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER

# 2. 创建目录
mkdir -p /opt/cantor && cd /opt/cantor

# 3. 克隆代码
git clone https://github.com/dalerzhi/cantor.git .

# 4. 创建环境配置
cp .env.example .env
vim .env  # 编辑配置

# 5. 启动服务
docker compose up -d

# 6. 检查状态
docker compose ps
```

### 11.2 配置 Nginx + SSL

```bash
# 安装 Nginx
apt install nginx certbot python3-certbot-nginx

# 申请 SSL 证书
certbot --nginx -d cantor.yourcompany.com

# 配置 Nginx (见下一节)
```

---

## 12. Nginx 配置示例

```nginx
# /etc/nginx/sites-available/cantor
server {
    listen 80;
    server_name cantor.yourcompany.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name cantor.yourcompany.com;

    ssl_certificate /etc/letsencrypt/live/cantor.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cantor.yourcompany.com/privkey.pem;

    # 前端
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:8766/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

---

## 联系支持

如有问题，请参考:
- 项目文档: `/docs`
- GitHub Issues: https://github.com/dalerzhi/cantor/issues
