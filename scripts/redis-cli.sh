#!/bin/bash

# ===================================
# Cantor Redis 连接脚本
# ===================================

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 加载环境变量
ENV_FILE="docker/.env"
if [ ! -f "$ENV_FILE" ]; then
    ENV_FILE=".env"
fi

if [ -f "$ENV_FILE" ]; then
    export $(cat $ENV_FILE | grep -v '^#' | xargs)
fi

# 默认值
REDIS_PORT=${REDIS_PORT:-6379}
REDIS_PASSWORD=${REDIS_PASSWORD:-redis_secret}

# 检查 redis-cli 是否安装
if ! command -v redis-cli &> /dev/null; then
    echo "redis-cli 未安装，使用 docker exec 连接..."
    docker exec -it cantor-redis redis-cli -a $REDIS_PASSWORD
else
    # 使用本地 redis-cli 连接
    echo "连接到 Redis..."
    echo "主机: localhost:$REDIS_PORT"
    echo ""
    
    redis-cli -h localhost -p $REDIS_PORT -a $REDIS_PASSWORD "$@"
fi
