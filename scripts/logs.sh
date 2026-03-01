#!/bin/bash

# ===================================
# Cantor 日志查看脚本
# ===================================

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 默认参数
SERVICE=${1:-}
TAIL=${2:-100}

# 使用说明
usage() {
    echo "用法: $0 [服务名] [行数]"
    echo ""
    echo "服务名:"
    echo "  all        - 所有服务（默认）"
    echo "  gateway    - Gateway 服务"
    echo "  brain      - Brain 服务"
    echo "  postgres   - PostgreSQL 数据库"
    echo "  redis      - Redis 缓存"
    echo ""
    echo "示例:"
    echo "  $0              # 查看所有服务最近 100 行日志"
    echo "  $0 brain 200    # 查看 brain 服务最近 200 行日志"
    echo "  $0 gateway -f   # 实时查看 gateway 日志"
    exit 1
}

# 检查参数
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    usage
fi

# 检查 .env 文件
ENV_FILE="docker/.env"
if [ ! -f "$ENV_FILE" ]; then
    ENV_FILE=".env"
fi

# 实时跟踪模式
if [ "$TAIL" == "-f" ]; then
    if [ -z "$SERVICE" ] || [ "$SERVICE" == "all" ]; then
        docker-compose --env-file $ENV_FILE logs -f
    else
        docker-compose --env-file $ENV_FILE logs -f $SERVICE
    fi
else
    if [ -z "$SERVICE" ] || [ "$SERVICE" == "all" ]; then
        docker-compose --env-file $ENV_FILE logs --tail=$TAIL
    else
        docker-compose --env-file $ENV_FILE logs --tail=$TAIL $SERVICE
    fi
fi
