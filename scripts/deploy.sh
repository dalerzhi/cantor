#!/bin/bash

# ===================================
# Cantor 一键部署脚本
# ===================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Cantor 部署脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查 .env 文件
if [ ! -f "docker/.env" ]; then
    echo -e "${YELLOW}⚠️  未找到 docker/.env 文件${NC}"
    echo -e "${YELLOW}   正在从 docker/.env.docker 创建...${NC}"
    cp docker/.env.docker docker/.env
    echo -e "${GREEN}✓ 已创建 docker/.env${NC}"
    echo -e "${YELLOW}   请修改 docker/.env 中的敏感配置！${NC}"
    echo ""
fi

# 加载环境变量
if [ -f "docker/.env" ]; then
    export $(cat docker/.env | grep -v '^#' | xargs)
fi

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker 未安装${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose 未安装${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker 环境检查通过${NC}"
echo ""

# 停止旧容器
echo -e "${BLUE}[1/4] 停止旧容器...${NC}"
docker-compose --env-file docker/.env down || true

# 清理旧镜像（可选）
if [ "$1" == "--clean" ]; then
    echo -e "${YELLOW}[2/4] 清理旧镜像...${NC}"
    docker-compose --env-file docker/.env down --rmi local -v || true
else
    echo -e "${BLUE}[2/4] 跳过镜像清理（使用 --clean 参数清理）${NC}"
fi

# 构建镜像
echo ""
echo -e "${BLUE}[3/4] 构建 Docker 镜像...${NC}"
docker-compose --env-file docker/.env build --no-cache

# 启动服务
echo ""
echo -e "${BLUE}[4/4] 启动服务...${NC}"
docker-compose --env-file docker/.env up -d

# 等待服务启动
echo ""
echo -e "${YELLOW}⏳ 等待服务启动（约 30-60 秒）...${NC}"
sleep 10

# 检查服务状态
echo ""
echo -e "${BLUE}服务状态:${NC}"
docker-compose --env-file docker/.env ps

# 健康检查
echo ""
echo -e "${BLUE}健康检查:${NC}"

# 检查 PostgreSQL
if docker-compose --env-file docker/.env exec -T postgres pg_isready -U ${POSTGRES_USER:-cantor} > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL 运行正常${NC}"
else
    echo -e "${YELLOW}⚠ PostgreSQL 可能还在启动中${NC}"
fi

# 检查 Redis
if docker-compose --env-file docker/.env exec -T redis redis-cli -a ${REDIS_PASSWORD:-redis_secret} ping 2>/dev/null | grep -q PONG; then
    echo -e "${GREEN}✓ Redis 运行正常${NC}"
else
    echo -e "${YELLOW}⚠ Redis 可能还在启动中${NC}"
fi

# 检查 Brain
sleep 5
if curl -sf http://localhost:${BRAIN_PORT:-8000}/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Brain 运行正常${NC}"
else
    echo -e "${YELLOW}⚠ Brain 可能还在启动中${NC}"
fi

# 完成
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   ✓ 部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}服务地址:${NC}"
echo -e "  Brain API:    http://localhost:${BRAIN_PORT:-8000}"
echo -e "  Gateway WS:   ws://localhost:${GATEWAY_PORT:-8766}/ws"
echo -e "  PostgreSQL:   localhost:${POSTGRES_PORT:-5432}"
echo -e "  Redis:        localhost:${REDIS_PORT:-6379}"
echo ""
echo -e "${BLUE}常用命令:${NC}"
echo -e "  查看日志:     ./scripts/logs.sh"
echo -e "  连接数据库:   ./scripts/psql.sh"
echo -e "  停止服务:     docker-compose --env-file docker/.env down"
echo ""
