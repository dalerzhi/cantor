#!/bin/bash

# ===================================
# Cantor PostgreSQL 连接脚本
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
POSTGRES_USER=${POSTGRES_USER:-cantor}
POSTGRES_DB=${POSTGRES_DB:-cantor}
POSTGRES_PORT=${POSTGRES_PORT:-5432}

# 检查 psql 是否安装
if ! command -v psql &> /dev/null; then
    echo "psql 未安装，使用 docker exec 连接..."
    docker exec -it cantor-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB
else
    # 使用本地 psql 连接
    echo "连接到 PostgreSQL..."
    echo "数据库: $POSTGRES_DB"
    echo "用户:   $POSTGRES_USER"
    echo "主机:   localhost:$POSTGRES_PORT"
    echo ""
    
    PGPASSWORD=${POSTGRES_PASSWORD:-cantor_secret} psql \
        -h localhost \
        -p $POSTGRES_PORT \
        -U $POSTGRES_USER \
        -d $POSTGRES_DB \
        "$@"
fi
