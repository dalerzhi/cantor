#!/bin/bash

# ===================================
# Cantor 部署验证脚本
# ===================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Cantor 部署验证${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 加载环境变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

ENV_FILE="docker/.env"
if [ -f "$ENV_FILE" ]; then
    export $(cat $ENV_FILE | grep -v '^#' | xargs)
fi

# 设置默认值
POSTGRES_USER=${POSTGRES_USER:-cantor}
POSTGRES_DB=${POSTGRES_DB:-cantor}
BRAIN_PORT=${BRAIN_PORT:-8000}
GATEWAY_PORT=${GATEWAY_PORT:-8766}
REDIS_PASSWORD=${REDIS_PASSWORD:-redis_secret}

# 检查函数
check_service() {
    local service=$1
    local command=$2
    local name=$3
    
    echo -e "${BLUE}检查 $name...${NC}"
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $name 运行正常${NC}"
        return 0
    else
        echo -e "${RED}✗ $name 未运行或异常${NC}"
        return 1
    fi
}

# 1. 检查 Docker 容器
echo -e "${BLUE}[1/5] 检查 Docker 容器状态${NC}"
docker-compose --env-file $ENV_FILE ps
echo ""

# 2. 检查 PostgreSQL
echo -e "${BLUE}[2/5] 检查 PostgreSQL${NC}"
check_service "postgres" \
    "docker exec cantor-postgres pg_isready -U $POSTGRES_USER -d $POSTGRES_DB" \
    "PostgreSQL"
echo ""

# 3. 检查 Redis
echo -e "${BLUE}[3/5] 检查 Redis${NC}"
check_service "redis" \
    "docker exec cantor-redis redis-cli -a $REDIS_PASSWORD ping | grep -q PONG" \
    "Redis"
echo ""

# 4. 检查 Brain API
echo -e "${BLUE}[4/5] 检查 Brain API${NC}"
check_service "brain" \
    "curl -sf http://localhost:$BRAIN_PORT/health > /dev/null" \
    "Brain API (端口 $BRAIN_PORT)"
echo ""

# 5. 检查 Gateway
echo -e "${BLUE}[5/5] 检查 Gateway${NC}"
check_service "gateway" \
    "curl -sf http://localhost:$GATEWAY_PORT/health > /dev/null" \
    "Gateway (端口 $GATEWAY_PORT)"
echo ""

# 服务连接信息
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   服务端点信息${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Brain API:${NC}    http://localhost:$BRAIN_PORT"
echo -e "${GREEN}✓ API 文档:${NC}     http://localhost:$BRAIN_PORT/docs"
echo -e "${GREEN}✓ Gateway WS:${NC}   ws://localhost:$GATEWAY_PORT/ws"
echo -e "${GREEN}✓ PostgreSQL:${NC}   localhost:5432"
echo -e "${GREEN}✓ Redis:${NC}        localhost:6379"
echo ""

# 测试 API 端点
echo -e "${BLUE}测试 API 端点:${NC}"
echo -e "${YELLOW}Health Check:${NC}"
curl -s http://localhost:$BRAIN_PORT/health | jq . 2>/dev/null || curl -s http://localhost:$BRAIN_PORT/health
echo ""

echo -e "${YELLOW}Gateway Health:${NC}"
curl -s http://localhost:$GATEWAY_PORT/health | jq . 2>/dev/null || curl -s http://localhost:$GATEWAY_PORT/health
echo ""
